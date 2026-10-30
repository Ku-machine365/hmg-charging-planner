#!/usr/bin/env python3
"""무의식 충전 플래너 — 핵심 엔진 v1 (표준 라이브러리만, 네트워크 없음).

.ics 일정 → 구간 동선(직선거리×계수) → 가상 SoC 하락 → 부족 구간 탐지
→ 식사/카페 슬롯과 겹치는 충전소 후보 2개 → A 막히면 B 교체 → 타임라인 JSON/텍스트.

사용: python3 -I planner.py --ics samples/day1.ics --stations samples/stations.json --soc 55 [--out results/x.json]
"""
import argparse, json, math, re, sys
from datetime import datetime, timedelta

# 가정값(기획서 ④ "수치는 모두 예시"). 실제 차량 값은 SDK EvBattery/ChargingPlan 몫.
BATTERY_KWH = 58.0          # 스탠다드 배터리 급 [가정]
KWH_PER_KM = 0.20           # 전비(간선+시내 혼합) [가정]
ROAD_FACTOR = 1.3           # 직선거리→도로거리 계수 [가정]
AVG_KMH = 45.0              # 평균 속도 [가정]
RESERVE_SOC = 20.0          # 도착 시 유지할 최소 SoC
CHARGE_KW = 100.0           # 급속 충전기 출력 [가정]
MAX_CHARGE_MIN = 40         # 식사 슬롯 안에 끝나도록 상한
SLOT_KEYWORDS = ('점심', '식사', '저녁', '카페', '커피', 'lunch', 'dinner', 'cafe', 'coffee')
BLOCKED_STATES = ('점검중', '충전중', '고장', '통신이상')


def parse_ics(path):
    """VEVENT의 DTSTART/DTEND/SUMMARY/GEO/LOCATION만 읽는다(줄 접기 처리). 시각은 로컬 naive."""
    text = open(path, encoding='utf-8').read().replace('\r\n', '\n')
    text = re.sub(r'\n[ \t]', '', text)  # RFC5545 folding
    events = []
    for block in re.findall(r'BEGIN:VEVENT\n(.*?)\nEND:VEVENT', text, re.S):
        ev = {}
        for line in block.split('\n'):
            if ':' not in line:
                continue
            key, val = line.split(':', 1)
            key = key.split(';')[0].upper()
            ev[key] = val.strip()
        if 'DTSTART' not in ev or 'GEO' not in ev:
            continue
        lat, lon = [float(v) for v in ev['GEO'].split(';')]
        events.append({
            'summary': ev.get('SUMMARY', ''),
            'start': _dt(ev['DTSTART']),
            'end': _dt(ev['DTEND']) if 'DTEND' in ev else _dt(ev['DTSTART']) + timedelta(hours=1),
            'lat': lat, 'lon': lon,
            'location': ev.get('LOCATION', ''),
        })
    events.sort(key=lambda e: e['start'])
    return events


def _dt(s):
    s = s.rstrip('Z')
    return datetime.strptime(s, '%Y%m%dT%H%M%S')


def haversine_km(a_lat, a_lon, b_lat, b_lon):
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = math.radians(b_lat - a_lat), math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def road_km(a, b):
    return haversine_km(a['lat'], a['lon'], b['lat'], b['lon']) * ROAD_FACTOR


def soc_drop(km):
    return km * KWH_PER_KM / BATTERY_KWH * 100.0


def is_slot(event):
    s = event['summary'].lower()
    return any(k in s for k in SLOT_KEYWORDS)


def plan(events, stations, start_soc, origin=None, blocked=None):
    """events: parse_ics 결과. stations: [{name,lat,lon,status,kw}]. 반환 dict(타임라인·SoC 경로·충전)."""
    blocked = set(blocked or [])
    if not events:
        raise ValueError('일정이 없습니다')
    cur = origin or {'lat': events[0]['lat'], 'lon': events[0]['lon'], 'summary': '출발'}
    soc = float(start_soc)
    timeline, charges = [], []
    # 1) 구간별 소모 계산(충전 없이)
    legs = []
    for ev in events:
        km = road_km(cur, ev)
        legs.append({'to': ev, 'km': round(km, 1), 'min': round(km / AVG_KMH * 60), 'drop': soc_drop(km)})
        cur = ev
    # 2) 충전 없이 갔을 때 최소 SoC가 RESERVE 아래로 내려가는 첫 구간 찾기
    need_total = sum(l['drop'] for l in legs)
    deficit = (soc - need_total) - RESERVE_SOC  # 음수면 부족
    timeline.append({'type': 'start', 'time': None, 'soc': round(soc, 1), 'note': f'시작 SoC {soc:.0f}%'})
    running = soc
    charged_once = False
    for i, leg in enumerate(legs):
        ev = leg['to']
        running -= leg['drop']
        timeline.append({'type': 'drive', 'time': ev['start'].strftime('%H:%M'), 'to': ev['summary'],
                         'km': leg['km'], 'min': leg['min'], 'soc': round(running, 1)})
        timeline.append({'type': 'event', 'time': ev['start'].strftime('%H:%M'), 'end': ev['end'].strftime('%H:%M'),
                         'name': ev['summary'], 'slot': is_slot(ev)})
        # 부족하고 이 이벤트가 식사/카페 슬롯이면 여기서 충전
        remaining_drop = sum(l['drop'] for l in legs[i + 1:])
        if not charged_once and is_slot(ev) and (running - remaining_drop) < RESERVE_SOC:
            target = min(100.0, RESERVE_SOC + remaining_drop + 5.0)  # 여유 5%
            need_kwh = (target - running) / 100.0 * BATTERY_KWH
            cands = nearest(stations, ev, 2)
            if not cands:
                timeline.append({'type': 'warn', 'note': '후보 충전소 없음'})
                continue
            chosen, reason = cands[0], '가장 가까움'
            if chosen['status'] in BLOCKED_STATES or chosen['name'] in blocked:
                if len(cands) > 1:
                    reason = f"후보 A '{chosen['name']}' {chosen['status'] if chosen['status'] in BLOCKED_STATES else '사용 불가'} → B로 교체"
                    chosen = cands[1]
                else:
                    reason = '대안 없음'
            kw = min(CHARGE_KW, float(chosen.get('kw', CHARGE_KW)))
            minutes = min(MAX_CHARGE_MIN, math.ceil(need_kwh / kw * 60))
            slot_len = int((ev['end'] - ev['start']).total_seconds() // 60)
            minutes = min(minutes, slot_len)
            gained = minutes / 60.0 * kw / BATTERY_KWH * 100.0
            running = min(100.0, running + gained)
            c_start, c_end = ev['start'] + timedelta(minutes=5), ev['start'] + timedelta(minutes=5 + minutes)
            charge = {'type': 'charge', 'station': chosen['name'], 'start': c_start.strftime('%H:%M'),
                      'end': c_end.strftime('%H:%M'), 'minutes': minutes, 'kw': kw,
                      'soc_after': round(running, 1), 'reason': reason, 'during': ev['summary'],
                      'distance_km': round(road_km(ev, chosen), 1)}
            charges.append(charge)
            timeline.append(charge)
            charged_once = True
    final_soc = running
    return {
        'start_soc': start_soc, 'final_soc': round(final_soc, 1), 'reserve_soc': RESERVE_SOC,
        'deficit_without_charge': round(deficit, 1), 'charges': charges, 'timeline': timeline,
        'ok': final_soc >= RESERVE_SOC,
        'assumptions': {'battery_kwh': BATTERY_KWH, 'kwh_per_km': KWH_PER_KM, 'road_factor': ROAD_FACTOR,
                        'avg_kmh': AVG_KMH, 'charge_kw': CHARGE_KW},
    }


def nearest(stations, ev, n):
    return sorted(stations, key=lambda s: haversine_km(ev['lat'], ev['lon'], s['lat'], s['lon']))[:n]


def render(result):
    lines = [f"시작 SoC {result['start_soc']}% → 도착 SoC {result['final_soc']}% (유지선 {result['reserve_soc']}%)"]
    for t in result['timeline']:
        if t['type'] == 'drive':
            lines.append(f"  이동 → {t['to']} {t['km']}km·{t['min']}분, 도착 SoC {t['soc']}%")
        elif t['type'] == 'event':
            lines.append(f"  {t['time']}~{t['end']} {t['name']}{' [슬롯]' if t['slot'] else ''}")
        elif t['type'] == 'charge':
            lines.append(f"  ⚡ {t['start']}~{t['end']} {t['station']} {t['minutes']}분 ({t['during']} 중) → SoC {t['soc_after']}% — {t['reason']}")
        elif t['type'] == 'warn':
            lines.append(f"  ! {t['note']}")
    lines.append('충전 ' + (f"{len(result['charges'])}회" if result['charges'] else '없음'))
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--ics', required=True)
    ap.add_argument('--stations', required=True, help='충전소 JSON [{name,lat,lon,status,kw}]')
    ap.add_argument('--soc', type=float, required=True, help='시작 SoC %%')
    ap.add_argument('--origin', help='출발지 lat,lon (없으면 첫 일정 장소)')
    ap.add_argument('--block', action='append', default=[], help='사용 불가로 둘 충전소명(대안 교체 시연)')
    ap.add_argument('--out', help='결과 JSON 저장 경로')
    a = ap.parse_args(argv)
    events = parse_ics(a.ics)
    stations = json.load(open(a.stations, encoding='utf-8'))
    origin = None
    if a.origin:
        la, lo = [float(v) for v in a.origin.split(',')]
        origin = {'lat': la, 'lon': lo, 'summary': '출발'}
    res = plan(events, stations, a.soc, origin=origin, blocked=a.block)
    print(render(res))
    if a.out:
        json.dump(res, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('saved', a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
