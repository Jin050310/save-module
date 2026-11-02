"""'강의시간표' PDF(교시 x 요일 격자) -> 과목 목록. 요일·시각·강의실을 모두 얻는다.

PDF에서 글자만 뽑으면 요일(열)이 사라지므로 글자·회색 칸의 좌표를 쓴다.
    - 회색 칸이 과목 칸이다. 칸의 가로 위치 = 요일, 세로 위치 = 교시.
    - 같은 요일 열에서 서로 다른 과목이 붙어 있을 수 있어, 칸 묶음 안의 글자를
      '과목명 교수(강의실)' 단위로 끊어 나눈다. (강의실이 줄바꿈되어도 괄호가 닫힐 때까지 한 과목)
    - 격자 아래의 '시간표 이외의 강의' 줄(온라인 등)은 시간 없이 따로 담는다.

성명 등 인적사항은 읽지 않는다. 회색 칸 안의 글자만 사용한다.
pdfplumber가 필요하다: pip install pdfplumber
"""

import re

from timetable_parser import (
    DAY_MAP, VERIFIED_MAX_PERIOD, build_course, fmt, period_to_range,
    split_code_section,
)

_LABEL = re.compile(r"^(\d+)교시$")
_COURSE = re.compile(r"^(?P<name>.+?)\s+(?P<prof>\S+?)\((?P<room>.*)\)$")
_EXTRA = re.compile(
    r"시간표 이외의 강의:\s*(?P<name>.+?)\((?P<code>[A-Za-z]+\d+-\d+)\),\s*"
    r"담당교수:\s*(?P<prof>.+?),\s*강의시간:\s*(?P<when>[^\n]+)"
)
_DAY_ORDER = list(DAY_MAP)


def _nearest(centers, value):
    return min(centers, key=lambda k: abs(centers[k] - value))


def _lines_of(words):
    """같은 열의 글자들 -> [(top, text), ...] (위에서 아래로)."""
    lines = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and w["top"] - lines[-1][0] <= 4:
            lines[-1][1].append(w)
        else:
            lines.append([w["top"], [w]])
    return [(top, " ".join(w["text"] for w in sorted(ws, key=lambda w: w["x0"])))
            for top, ws in lines]


def _split_courses(lines):
    """줄들 -> [(시작 top, 'name prof(room)'), ...]. 괄호가 닫히면 한 과목이 끝난다."""
    courses, cur = [], None
    for top, text in lines:
        if cur is None:
            cur = [top, text]
        elif cur[1].count("(") > cur[1].count(")"):
            cur[1] += text  # 괄호 안에서 줄바꿈된 강의실: 공백 없이 이어 붙인다
        else:
            cur[1] += " " + text
        if cur[1].count("(") == cur[1].count(")") and ")" in text:
            courses.append((cur[0], cur[1]))
            cur = None
    if cur is not None:
        raise ValueError(f"괄호가 닫히지 않은 과목 칸: '{cur[1]}'")
    return courses


def parse_layout(words, rects):
    """words: [{text,x0,x1,top,bottom}], rects: 회색 칸 [{x0,x1,top,bottom}].
    -> [{"name","professor","day","first","last","room"}, ...]  (first/last = 교시)"""
    label_tops = {int(m.group(1)): w["top"] for w in words
                  if w["x0"] < 100 and (m := _LABEL.match(w["text"]))}
    day_centers = {w["text"]: (w["x0"] + w["x1"]) / 2 for w in words
                   if w["x0"] > 100 and w["top"] < 110 and w["text"] in DAY_MAP}
    if not label_tops or not day_centers:
        raise ValueError("교시 또는 요일 머리글을 찾지 못함: 강의시간표 PDF가 맞는지 확인 필요")

    # 칸 -> 요일별로 세로로 이어지는 묶음(run)
    by_day = {}
    for r in rects:
        day = _nearest(day_centers, (r["x0"] + r["x1"]) / 2)
        by_day.setdefault(day, []).append(r)
    runs = []
    for day, rs in by_day.items():
        rs.sort(key=lambda r: r["top"])
        group = [rs[0]]
        for r in rs[1:]:
            if r["top"] - group[-1]["bottom"] > 3:
                runs.append((day, group))
                group = []
            group.append(r)
        runs.append((day, group))

    def run_box(group):
        return (min(r["x0"] for r in group), max(r["x1"] for r in group),
                group[0]["top"], group[-1]["bottom"])

    # 글자 -> 겹치는 폭이 가장 큰 묶음
    assigned = {i: [] for i in range(len(runs))}
    for w in words:
        if w["x0"] < 105 or w["top"] < 115:
            continue  # 교시 머리글·표 밖
        mid = (w["top"] + w["bottom"]) / 2
        best, best_overlap = None, 0
        for i, (_, group) in enumerate(runs):
            x0, x1, top, bottom = run_box(group)
            overlap = min(w["x1"], x1) - max(w["x0"], x0)
            if top - 1 <= mid <= bottom + 1 and overlap > best_overlap:
                best, best_overlap = i, overlap
        if best is not None:
            assigned[best].append(w)

    meetings = []
    for i, (day, group) in enumerate(runs):
        last_row = _nearest(label_tops, group[-1]["top"])
        found = _split_courses(_lines_of(assigned[i]))
        for k, (top, text) in enumerate(found):
            m = _COURSE.match(text)
            if not m:
                raise ValueError(f"과목명/교수(강의실) 형식이 아님: '{text}'")
            first = _nearest(label_tops, top)
            last = _nearest(label_tops, found[k + 1][0]) - 1 if k + 1 < len(found) else last_row
            meetings.append({"name": m["name"], "professor": m["prof"], "day": day,
                             "first": first, "last": last, "room": m["room"]})
    return meetings


def meetings_to_courses(meetings):
    courses = {}
    for m in sorted(meetings, key=lambda m: (_DAY_ORDER.index(m["day"]), m["first"])):
        c = build_course("", m["name"], m["professor"], "")
        c = courses.setdefault((m["name"], m["professor"]), c)
        c["meetings"].append({
            "day": DAY_MAP[m["day"]],
            "start": fmt(period_to_range(m["first"])[0]),
            "end": fmt(period_to_range(m["last"])[1]),
            "room": m["room"],
        })
        if m["last"] > VERIFIED_MAX_PERIOD:
            note = f"{VERIFIED_MAX_PERIOD}교시 이후({m['last']}교시)는 시각 규칙 미확인: 확인 필요"
            if note not in c["warnings"]:
                c["warnings"].append(note)
    for c in courses.values():
        c["warnings"] = ["학수번호·분반 없음: 수강신청 확인서와 합쳐야 함"]
    return list(courses.values())


def parse_extra(text):
    """'시간표 이외의 강의' 줄(온라인 등) -> 시간 없는 과목들."""
    extra = []
    for m in _EXTRA.finditer(text):
        code, section = split_code_section(m["code"])
        extra.append({
            "name": m["name"].strip(), "course_code": code, "section": section,
            "professor": m["prof"].strip(), "credits": None, "meetings": [],
            "warnings": [f"시간표 밖 강의(강의시간: {m['when'].strip()}): 요일·시간 없음"],
        })
    return extra


def read_pdf(path):
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        first = pdf.pages[0]
        if any(p.rects for p in pdf.pages[1:]):
            raise ValueError("2쪽 이후에 과목 칸이 있음: 아직 지원하지 않음")
        rects = [r for r in first.rects if r["x1"] - r["x0"] < 150]  # 맨 위 머리글 띠 제외
        courses = meetings_to_courses(parse_layout(first.extract_words(), rects))
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    return courses + parse_extra(text)
