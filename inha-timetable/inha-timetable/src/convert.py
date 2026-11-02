"""붙여넣은 수강신청 표(탭으로 구분된 텍스트) -> JSON 또는 CSV.

사용법 (프로젝트 폴더에서):
    python3 src/convert.py samples/sample_paste.tsv --semester 2026-2 --format json
    python3 src/convert.py samples/sample_paste.tsv --semester 2026-2 --format csv -o out.csv

입력은 세 가지를 알아봅니다.
- 강의시간표 PDF(.pdf): 요일·시각·강의실을 모두 읽습니다. pdfplumber가 필요합니다.
    python3 src/convert.py 강의시간표.pdf --semester 2026-2
- 시간표 격자(첫 줄이 '교시/요일'): 실제 복사 결과로 확인됨. 요일과 강의실은 복사 결과에 없어
  --days로 요일을 직접 줘야 합니다. 예: --days GEB1108-027=화,목
- 헤더가 있는 탭 구분 목록(학수번호, 과목명, ...): '이렇게 나올 것'이라는 가정이며 아직 실제
  복사 결과로 확인하지 못했습니다.
학번과 이름은 읽지도 저장하지도 않습니다.
"""

import argparse
import csv
import io
import json
import sys

from grid_parser import grid_to_courses, is_grid
from timetable_parser import DAY_MAP, build_course

# 화면 표 헤더 이름 -> 내부 이름
COLUMNS = {
    "학수번호": "code",
    "과목명": "name",
    "학점": "credits",
    "시간 및 강의실": "time",
    "담당교수": "professor",
}


def read_rows(text):
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    header = [h.strip() for h in lines[0].split("\t")]
    missing = [k for k in COLUMNS if k not in header]
    if missing:
        raise ValueError(f"헤더에서 찾지 못한 열: {missing} (찾은 열: {header})")
    idx = {COLUMNS[k]: header.index(k) for k in COLUMNS}
    rows = []
    for ln in lines[1:]:
        cells = [c.strip() for c in ln.split("\t")]
        rows.append({k: (cells[i] if i < len(cells) else "") for k, i in idx.items()})
    return rows


def convert(text, semester, days=None):
    if is_grid(text):
        courses = grid_to_courses(text, days)
    else:
        courses = [
            build_course(r["code"], r["name"], r["professor"], r["time"], r["credits"])
            for r in read_rows(text)
        ]
    return {"university": "인하대학교", "semester": semester, "courses": courses}


def to_csv(data):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["semester", "course_code", "section", "name", "professor",
                "day", "start", "end", "room", "warnings"])
    for c in data["courses"]:
        base = [data["semester"], c["course_code"], c["section"], c["name"], c["professor"]]
        warn = "; ".join(c["warnings"])
        if not c["meetings"]:
            w.writerow(base + ["", "", "", "", warn])
        for m in c["meetings"]:
            w.writerow(base + [m["day"], m["start"], m["end"], m["room"], warn])
    return out.getvalue()


def parse_days(specs):
    """['GEB1108-027=화,목', ...] -> {'GEB1108-027': ['화', '목']}"""
    days = {}
    for spec in specs or []:
        code, _, value = spec.partition("=")
        names = [d.strip() for d in value.split(",") if d.strip()]
        bad = [d for d in names if d not in DAY_MAP]
        if not code.strip() or not names or bad:
            raise ValueError(f"--days 형식 오류: '{spec}' (예: GEB1108-027=화,목)")
        days[code.strip()] = names
    return days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--semester", required=True, help="예: 2026-2")
    ap.add_argument("--days", action="append", metavar="학수번호=요일,요일",
                    help="격자 복사 결과는 요일이 없으므로 직접 지정 (여러 번 사용 가능). 예: GEB1108-027=화,목")
    ap.add_argument("--format", choices=["json", "csv"], default="json")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()

    if args.input.lower().endswith(".pdf"):
        from pdf_timetable import read_pdf
        data = {"university": "인하대학교", "semester": args.semester,
                "courses": read_pdf(args.input)}
    else:
        with open(args.input, encoding="utf-8") as f:
            data = convert(f.read(), args.semester, parse_days(args.days))

    text = (json.dumps(data, ensure_ascii=False, indent=2)
            if args.format == "json" else to_csv(data))
    if args.output:
        with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
            f.write(text)
    else:
        sys.stdout.write(text)

    flagged = [c["name"] for c in data["courses"] if c["warnings"]]
    if flagged:
        print(f"\n확인 필요한 과목: {flagged}", file=sys.stderr)


if __name__ == "__main__":
    main()
