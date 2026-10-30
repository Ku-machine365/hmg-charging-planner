# PREREG — hmg-charging-planner v1

고정 시각: 2026-10-30 20:4x KST (이 파일을 처음 커밋한 시각이 기준. 결과를 보기 전에 커밋한다)

## 질문
일정 3건 + 가상 SoC만으로, 식사·카페 시간대에 충전을 자동 삽입하고 막힌 충전소를 대안으로 교체하는 계획을 SDK 없이 재현 가능하게 만들 수 있는가?

## 시험 대상
- samples/day1.ics (점심 판교 12:00 / 15:00 양평 카페 / 19:00 귀가, 기획서 ④ 시나리오): SoC 55% 시작 → 충전 1회가 점심 슬롯(12:00~13:00)에 배치되고 귀가까지 SoC ≥ 20%
- samples/day1.ics, SoC 90% 시작: 충전 0회
- samples/day1.ics, SoC 55% + 후보 A 상태 "점검중": B로 교체되고 교체 사유 문구 출력

## 성공 기준 (각각 PASS/FAIL로 판정)
1. 위 3개 시험이 `tests/`에서 전부 통과(3/3)
2. 출력 타임라인에 충전 항목의 시작·종료 시각·충전소명·사유가 전부 있음(필드 누락 0)
3. `python3 -I planner.py --help` 가 rc=0이고 외부 패키지 import 0
4. 샘플 1건 실행 시간 < 1초(time 측정)

## 측정법
- 명령: `python3 -I -m unittest discover -s tests` / `time python3 -I planner.py --ics samples/day1.ics --stations samples/stations.json --soc 55 --origin 37.38,126.65 --out results/2026-MM-DD.json`
- 원시 결과 저장: `results/<날짜>.json`, 테스트 출력 `results/<날짜>-tests.txt`
- 센 것: 통과 테스트 수 / 타임라인 충전 항목의 필드 수 / 실행 초

## 변경
_(결과를 본 뒤 기준을 바꾸면 날짜·이유와 함께 여기에만 추가. 원래 기준은 지우지 않는다)_
- 2026-10-30 20:5x: 첫 실행(출발지=첫 일정 장소, 배터리 77.4kWh·전비 0.18 가정)에서 SoC 55→36%로 충전이 필요 없어 시험 1·3이 성립하지 않았다. **성공 기준은 그대로 두고 시험 대상의 샘플 가정만 고정**: 출발지 인천 송도(37.38,126.65, 예시) 추가(`--origin`), 배터리 58kWh·전비 0.20kWh/km(스탠다드 급 가정). 기준 1~4는 변경 없음.

## 판정
측정 2026-10-30 20:5x KST (results/2026-10-30-tests.txt, results/2026-10-30.json, results/2026-10-30-run.txt)
1. 테스트 3/3 통과 — **PASS** (Ran 3 tests … OK)
2. 충전 항목 필드: station·start·end·minutes·reason·during·kw·soc_after·distance_km 전부 있음(누락 0) — **PASS**
3. `--help` rc=0, import는 argparse/json/math/re/sys/datetime(표준 라이브러리만) — **PASS**
4. 샘플 1건 실행 0.037초(time total) — **PASS**

규칙 밖 판단:
- 첫 실행에서 샘플 가정(출발지=첫 일정, 77.4kWh)으로는 충전이 필요 없었고, 가정을 바꿔서(`## 변경`) 시험이 성립했다. 엔진 로직은 바뀌지 않았지만 "시험 대상"을 결과를 본 뒤 조정한 것이므로 v1 판정은 **조건부 PASS**로 본다.
- 충전 시간 6분은 '유지선+5%'까지만 채우는 최소 규칙 때문이며, 실제 UX는 식사 슬롯을 채우는 쪽(예: 30~40분)이 자연스럽다. v2 PREREG 항목.
- 거리·소요시간은 직선×1.3 계수이고 내비 호출(NaviHelper)·실제 충전소 상태(API)는 미연결. 공모전 시연용 수치는 전부 예시.
