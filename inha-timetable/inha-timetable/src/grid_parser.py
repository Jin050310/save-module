"""시간표 격자(교시 x 요일)를 복사해 붙여넣은 텍스트 -> 과목 목록.

실제 복사 결과 (수강시간표.txt 기준):
    교시/요일<TAB>월<TAB>화<TAB>수<TAB>목<TAB>금
    5교시
    [11:00 ~ 11:30]<TAB>
    일반화학실험
    CHM1927-008
    강동원

확인된 것:
    - 과목은 3줄(과목명, 학수번호, 교수)이고 걸친 교시마다 반복된다.
    - 교시별 시각이 [시작 ~ 끝]으로 적혀 있다. 25교시(21:00~21:30)까지 확인.
    - 같은 교시에 칸이 둘이면 과목 줄이 연달아 두 번 나온다.

복사 결과에 없는 것 (그래서 경고를 남긴다):
    - 요일: 빈 칸의 탭이 사라져서 어느 열인지 알 수 없다. 같은 교시에 몇 번
      나왔는지로 '주 몇 일'만 알 수 있고, 요일은 days 인자로 직접 받는다.
    - 강의실
"""

import re

from timetable_parser import DAY_MAP, merge_periods, split_code_section

_PERIOD = re.compile(r"^(\d+)교시$")
_TIME = re.compile(r"^\[(\d{2}:\d{2})\s*~\s*(\d{2}:\d{2})\]$")
_CODE = re.compile(r"^[A-Za-z]+\d+-\d+$")


def is_grid(text):
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return bool(lines) and lines[0].startswith("교시/요일")


def _read_periods(text):
    """-> [(교시, (시작, 끝), [줄, ...]), ...]"""
    periods = []
    for raw in text.splitlines():
        ln = raw.strip()
        if not ln or ln.startswith("교시/요일"):
            continue
        m = _PERIOD.match(ln)
        if m:
            periods.append([int(m.group(1)), None, []])
            continue
        if not periods:
            raise ValueError(f"교시 줄보다 앞에 있는 내용: '{ln}'")
        t = _TIME.match(ln)
        if t and periods[-1][1] is None:
            periods[-1][1] = (t.group(1), t.group(2))
        else:
            periods[-1][2].append(ln)
    for p, times, _ in periods:
        if times is None:
            raise ValueError(f"{p}교시의 시각([시작 ~ 끝])을 찾지 못함")
    return periods


def _split_entries(period, lines):
    """한 교시의 줄들 -> [(과목명, 학수번호, 교수), ...]"""
    entries = []
    i = 0
    while i < len(lines):
        if i + 1 >= len(lines) or not _CODE.match(lines[i + 1]):
            raise ValueError(f"{period}교시: 과목 형식(과목명/학수번호/교수)이 아닌 줄 '{lines[i]}'")
        name, code = lines[i], lines[i + 1]
        # 교수 줄은 다음 과목명일 수도 있다 (그 뒤에 학수번호가 바로 나오면 교수 줄이 없는 것)
        has_prof = i + 2 < len(lines) and not (i + 3 < len(lines) and _CODE.match(lines[i + 3]))
        prof = lines[i + 2] if has_prof else ""
        entries.append((name, code, prof))
        i += 3 if has_prof else 2
    return entries


def grid_to_courses(text, days=None):
    """days: {"GEB1108-027": ["화", "목"]} 처럼 직접 지정한 요일 (선택)."""
    days = days or {}
    found = {}  # 학수번호 -> {name, professor, counts: {교시: 칸 수}, times: {교시: (시작, 끝)}}
    for period, times, lines in _read_periods(text):
        for name, code, prof in _split_entries(period, lines):
            c = found.setdefault(code, {"name": name, "professor": prof, "counts": {}, "times": {}})
            c["counts"][period] = c["counts"].get(period, 0) + 1
            c["times"][period] = times

    courses = []
    for code_with_section, c in found.items():
        counts = c["counts"]
        warnings = []
        n = max(counts.values())
        if len(set(counts.values())) > 1:
            warnings.append("교시마다 겹친 칸 수가 다름: 요일별 시간이 다를 수 있어 확인 필요")

        chosen = days.get(code_with_section)
        if chosen is None:
            chosen = [None] * n
            warnings.append(f"요일을 알 수 없음(복사 결과에 열 구분이 없음, 주 {n}일): 확인 필요")
        elif len(chosen) != n:
            warnings.append(f"지정한 요일 {len(chosen)}개와 표에서 센 {n}일이 다름: 확인 필요")
            chosen = [None] * n
        warnings.append("강의실 정보가 복사 결과에 없음")

        meetings = []
        for day_kr in chosen:
            for first, last in merge_periods(counts):
                meetings.append({
                    "day": DAY_MAP[day_kr] if day_kr else None,
                    "start": c["times"][first][0],
                    "end": c["times"][last][1],
                    "room": None,
                })
        code, section = split_code_section(code_with_section)
        courses.append({
            "name": c["name"],
            "course_code": code,
            "section": section,
            "professor": c["professor"],
            "credits": None,
            "meetings": meetings,
            "warnings": warnings,
        })
    return courses
