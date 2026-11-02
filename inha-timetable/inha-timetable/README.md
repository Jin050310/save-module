# inha-timetable

인하대 수강신청 화면의 표를 복사해 붙여넣으면 JSON/CSV 시간표로 바꿔주는 도구 (MVP 초기 버전).

## 개인정보 규칙
- 학번, 이름, 비밀번호는 읽지도 저장하지도 않는다.
- 실제 학번/이름이 들어 있는 캡처나 텍스트를 저장소에 올리지 않는다. (`samples/`에는 과목 정보만 넣기)

## 폴더 구조
```
inha-timetable/
├── src/
│   ├── timetable_parser.py   # 교시 → 시각 변환, '시간 및 강의실' 해석
│   └── convert.py            # 붙여넣은 표(탭 구분) → JSON/CSV
├── tests/test_parser.py      # 자동 테스트
└── samples/sample_paste.tsv  # 캡처에서 확인한 두 과목
```

## 실행 방법 (Python 3.9 이상, 별도 설치 없음)
프로젝트 폴더에서:

```
python3 -m unittest discover -s tests -v
python3 src/convert.py samples/sample_paste.tsv --semester 2026-2 --format json
python3 src/convert.py samples/sample_paste.tsv --semester 2026-2 --format csv -o out.csv
```

## 확인된 것 / 아직 모르는 것
확인됨 (캡처 1장 기준)
- 시간 표기: `수5,6,7,8(5동511)`, `화10,11,12,목10,11,12(60주년-502)`
- 1교시 = 09:00, 교시당 30분 (1~13교시 확인)
- 학수번호에 분반이 합쳐져 있음 (`CHM1927-008`)

미확인 (코드가 '확인 필요' 경고로 표시함)
- 요일마다 강의실이 다른 과목의 표기
- 온라인/시간 미지정 과목의 표기
- 13교시 이후
- **표를 복사했을 때 실제로 어떤 텍스트가 나오는지** → `convert.py`의 입력 형식은 가정이므로, 실제 복사 결과를 받으면 맞춰 고쳐야 함
- "신청확인" 화면(최종 신청 내역)이 이 수강희망 화면과 같은 형태인지

## 다음 단계
1. 실제로 표를 복사한 텍스트로 `convert.py` 입력부 수정
2. 예외 표기 샘플 수집 후 테스트 추가
3. 붙여넣기 웹 화면 (브라우저 안에서만 처리, 서버 전송 없음)
