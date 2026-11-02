"""인하대 수강신청 화면의 '시간 및 강의실' 문자열을 구조화된 데이터로 바꾸는 모듈.

확인된 표기 (캡처 기준):
    수5,6,7,8(5동511)
    화10,11,12,목10,11,12(60주년-502)

확인된 규칙:
    - 요일 한 글자 뒤에 교시 번호가 쉼표로 이어진다.
    - 강의실은 괄호 안에 있다.
    - 1교시 = 09:00~09:30, 교시당 30분 (화면 격자에서 1~13교시까지 확인)

아직 확인 안 된 것 (그래서 아래 코드는 '확인 필요' 경고를 남긴다):
    - 요일마다 강의실이 다를 때의 표기
    - 온라인/시간 미지정 과목의 표기
    - 13교시 이후 교시
"""

import re

DAY_MAP = {
    "월": "MON", "화": "TUE", "수": "WED", "목": "THU",
    "금": "FRI", "토": "SAT", "일": "SUN",
}
VERIFIED_MAX_PERIOD = 13  # 캡처 격자에서 확인된 마지막 교시
FIRST_PERIOD_START_MIN = 9 * 60  # 09:00
PERIOD_MINUTES = 30


def period_to_range(period):
    """n교시 -> (시작분, 종료분). 1교시 = 09:00~09:30."""
    start = FIRST_PERIOD_START_MIN + PERIOD_MINUTES * (period - 1)
    return start, start + PERIOD_MINUTES


def fmt(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def merge_periods(periods):
    """[5,6,7,8] -> [(5, 8)], [1,2,5] -> [(1, 2), (5, 5)]. 연속 교시만 합친다."""
    blocks = []
    for p in sorted(set(periods)):
        if blocks and p == blocks[-1][1] + 1:
            blocks[-1] = (blocks[-1][0], p)
        else:
            blocks.append((p, p))
    return blocks


# 요일 한 글자 + 숫자/쉼표 + (선택) (강의실)
_GROUP = re.compile(r"([월화수목금토일])\s*([0-9][0-9,\s]*)\s*(?:\(([^)]*)\))?")


def parse_time_location(text):
    """'시간 및 강의실' 문자열 -> (meetings, warnings).

    meetings: [{"day","start","end","room"}, ...]
    warnings: 사람이 확인해야 할 내용 목록 (비어 있으면 문제 없음)
    """
    warnings = []
    text = (text or "").strip()
    if not text:
        return [], ["시간 정보가 비어 있음: 확인 필요"]

    groups = []  # [day_kr, [periods], room or None]
    last_end = 0
    for m in _GROUP.finditer(text):
        # 인식되지 않고 건너뛴 글자가 있으면 경고
        skipped = text[last_end:m.start()].strip(" ,")
        if skipped:
            warnings.append(f"해석하지 못한 부분: '{skipped}'")
        last_end = m.end()
        periods = [int(x) for x in re.findall(r"\d+", m.group(2))]
        groups.append([m.group(1), periods, m.group(3)])
    tail = text[last_end:].strip(" ,")
    if tail:
        warnings.append(f"해석하지 못한 부분: '{tail}'")
    if not groups:
        return [], warnings + [f"요일/교시를 찾지 못함: '{text}'"]

    # 강의실이 없는 그룹은 뒤에 나오는 가장 가까운 강의실을 따른다.
    # (확인된 사례: '화10,11,12,목10,11,12(60주년-502)'). 요일별로 다른 표기는 미확인.
    next_room = None
    for g in reversed(groups):
        if g[2] is not None:
            next_room = g[2]
        else:
            g[2] = next_room
    rooms = {g[2] for g in groups}
    if len(groups) > 1 and len(rooms) > 1:
        warnings.append("요일별로 강의실이 다름: 표기 규칙 미확인, 확인 필요")

    meetings = []
    for day_kr, periods, room in groups:
        if max(periods) > VERIFIED_MAX_PERIOD:
            warnings.append(
                f"{VERIFIED_MAX_PERIOD}교시 이후({max(periods)}교시)는 시각 규칙 미확인: 확인 필요"
            )
        for first, last in merge_periods(periods):
            start = period_to_range(first)[0]
            end = period_to_range(last)[1]
            meetings.append({
                "day": DAY_MAP[day_kr],
                "start": fmt(start),
                "end": fmt(end),
                "room": room,
            })
    return meetings, warnings


_CODE = re.compile(r"^([A-Za-z]+\d+)-(\d+)$")


def split_code_section(value):
    """'CHM1927-008' -> ('CHM1927', '008'). 형식이 다르면 (value, None)."""
    m = _CODE.match((value or "").strip())
    if not m:
        return (value or "").strip(), None
    return m.group(1), m.group(2)


def build_course(code_with_section, name, professor, time_text, credits=None):
    code, section = split_code_section(code_with_section)
    meetings, warnings = parse_time_location(time_text)
    if section is None:
        warnings.append(f"학수번호에서 분반을 나누지 못함: '{code_with_section}'")
    return {
        "name": (name or "").strip(),
        "course_code": code,
        "section": section,
        "professor": (professor or "").strip(),
        "credits": credits,
        "meetings": meetings,
        "warnings": warnings,
    }
