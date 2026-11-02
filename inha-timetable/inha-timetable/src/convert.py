"""붙여넣은 수강신청 표(탭으로 구분된 텍스트) -> JSON 또는 CSV.

사용법 (프로젝트 폴더에서):
    python3 src/convert.py samples/sample_paste.tsv --semester 2026-2 --format json
    python3 src/convert.py samples/sample_paste.tsv --semester 2026-2 --format csv -o out.csv

주의: 입력 형식(헤더가 있는 탭 구분 텍스트)은 '표를 복사해 붙여넣으면 이렇게 나올 것'이라는
가정입니다. 실제 복사 결과를 확인한 뒤 맞춰서 고쳐야 합니다.
학번과 이름은 읽지도 저장하지도 않습니다.
"""

import argparse
import csv
import io
import json
import sys

from timetable_parser import build_course

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


def convert(text, semester):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--semester", required=True, help="예: 2026-2")
    ap.add_argument("--format", choices=["json", "csv"], default="json")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = convert(f.read(), args.semester)

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
