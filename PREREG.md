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
- 명령: `python3 -I -m unittest discover -s tests` / `time python3 -I planner.py --ics samples/day1.ics --stations samples/stations.json --soc 55 --out results/2026-MM-DD.json`
- 원시 결과 저장: `results/<날짜>.json`, 테스트 출력 `results/<날짜>-tests.txt`
- 센 것: 통과 테스트 수 / 타임라인 충전 항목의 필드 수 / 실행 초

## 변경
_(결과를 본 뒤 기준을 바꾸면 날짜·이유와 함께 여기에만 추가. 원래 기준은 지우지 않는다)_

## 판정
_(측정 후 작성: 기준별 PASS/FAIL, 그리고 '규칙 밖 판단'은 따로)_
