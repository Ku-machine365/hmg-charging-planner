# hmg-charging-planner — 무의식 충전 플래너 프로토타입(핵심 엔진)

- 문제: EV 운전자가 하루 일정(점심·카페·귀가)을 짜면 충전을 따로 생각해야 한다. 식사·카페 시간대에 충전을 자동으로 끼워 넣어 "충전을 의식하지 않게" 만든다.
- 사용자: 현대차그룹 차량용 앱 개발 공모전(appdevchallenge.auto-hmg.io, 2026) 심사용 시연 + Pleos 탑재 EV 운전자.
- 출처: 토픽 1327 공모전 기획서 draft-ABC4(2026-10-25, outbox/hmg-contest/draft-ABC4.md ③⑤절). 1차 접수 2026-10-29 발송 완료. 11.15 전 재제출용 선택 제출물(GitHub 저장소·시연 영상, 가산점).
- 이미 있는 것: Pleos Connect SDK(NaviHelper·EvBattery·ChargingPlan)는 Dokka 본문으로 필드만 확인(outbox/2026-10-25-hmg-pleos-dokka.md), 에뮬레이터·SDK 실행은 미검증. 공공 충전소 API(data.go.kr 15076352)는 키 미발급. 이 저장소는 **SDK 없이 돌아가는 핵심 엔진**(일정 → 동선 → 충전 삽입 → 대안 교체)만 Python 표준 라이브러리로 만든다. Android/Pleos 래퍼는 v2.

## 범위 (v1)
1. `.ics`(구글 캘린더 내보내기) 읽기 → 일정 모델(시각·장소 좌표)
2. 구간별 거리·소요시간 추정(직선거리×계수, 실제 내비 호출은 SDK 몫)
3. 가상 SoC 하락 계산 → 부족 구간 탐지 → 식사/카페 슬롯과 겹치는 충전소 후보 2개 선택
4. 후보 A가 "점검중/충전중"이면 B로 교체
5. 결과를 타임라인 JSON + 텍스트로 출력(차량 앱 UI·TTS 문구의 입력)

자르는 것: 실제 예약·결제, POI 실검색, LLM, 외기온, 캘린더 쓰기(기획서 ⑤ "자르는 것"과 동일).

## 사용법
```sh
python3 -I planner.py --help
python3 -I planner.py --ics samples/day1.ics --stations samples/stations.json --soc 55
```

## 안전
- 외부 코드 실행 0. 네트워크: 없음(샘플 파일만 읽음). 쓰기: `results/` 아래 출력 파일만.
- 원격 push·GitHub 공개는 Master 승인 전 금지(programs/README 규칙). 공개 시 개인정보·연락처 0건 확인 후.
