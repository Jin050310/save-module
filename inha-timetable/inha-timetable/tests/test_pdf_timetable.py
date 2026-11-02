import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pdf_timetable import (  # noqa: E402
    meetings_to_courses, parse_extra, parse_layout, _split_courses,
)


def word(text, x0, top, width=30):
    return {"text": text, "x0": x0, "x1": x0 + width, "top": top, "bottom": top + 8}


def rect(x0, top, x1=187):
    return {"x0": x0, "x1": x1, "top": top, "bottom": top + 26}


# 교시 머리글(1~6교시, 세로 간격 26)과 요일 머리글(월 x=108~187, 화 x=187~266)
HEADER = (
    [word(f"{p}교시", 60, 118 + 26 * (p - 1), 20) for p in range(1, 7)]
    + [word("월", 140, 98, 10), word("화", 220, 98, 10)]
)


class TestSplitCourses(unittest.TestCase):
    def test_room_wrapped_inside_parentheses(self):
        lines = [(10, "의사소통 영어: 중급"), (19, "테리로즈(60주년"), (28, "-502)")]
        self.assertEqual(_split_courses(lines), [(10, "의사소통 영어: 중급 테리로즈(60주년-502)")])

    def test_two_courses_back_to_back(self):
        lines = [(10, "물리학2"), (19, "장우제(5E407)"), (50, "일반수학 2"), (59, "전용운(5E107A)")]
        self.assertEqual([t for _, t in _split_courses(lines)],
                         ["물리학2 장우제(5E407)", "일반수학 2 전용운(5E107A)"])

    def test_unclosed_parenthesis_raises(self):
        with self.assertRaises(ValueError):
            _split_courses([(10, "이상한과목 교수(5E")])


class TestLayout(unittest.TestCase):
    def test_two_courses_in_one_contiguous_column(self):
        # 화요일 1~5교시가 이어진 회색 칸: 1~2교시 과목 + 3~5교시 과목
        rects = [rect(187, 116 + 26 * i, 266) for i in range(5)]
        words = HEADER + [
            word("물리학2", 200, 118), word("장우제(5E407)", 200, 127),
            word("일반수학", 200, 170), word("2", 235, 170), word("전용운(5E107A)", 200, 179),
        ]
        got = parse_layout(words, rects)
        self.assertEqual(
            [(m["name"], m["professor"], m["day"], m["first"], m["last"], m["room"]) for m in got],
            [("물리학2", "장우제", "화", 1, 2, "5E407"),
             ("일반수학 2", "전용운", "화", 3, 5, "5E107A")])

    def test_day_comes_from_column(self):
        rects = [rect(108, 116), rect(108, 142)]
        words = HEADER + [word("과목", 115, 118), word("교수(A1)", 115, 127)]
        (m,) = parse_layout(words, rects)
        self.assertEqual((m["day"], m["first"], m["last"]), ("월", 1, 2))

    def test_words_outside_cells_are_ignored(self):
        rects = [rect(108, 116)]
        words = HEADER + [word("과목", 115, 118), word("교수(A1)", 115, 127),
                          word("성명:", 50, 51), word("누군가", 90, 51)]
        self.assertEqual(len(parse_layout(words, rects)), 1)

    def test_missing_header_raises(self):
        with self.assertRaises(ValueError):
            parse_layout([word("과목", 115, 118)], [rect(108, 116)])


class TestCourses(unittest.TestCase):
    def test_same_course_on_two_days_is_one_course(self):
        meetings = [
            {"name": "영어", "professor": "갑", "day": "화", "first": 10, "last": 12, "room": "R1"},
            {"name": "영어", "professor": "갑", "day": "목", "first": 10, "last": 12, "room": "R1"},
        ]
        (c,) = meetings_to_courses(meetings)
        self.assertEqual([(m["day"], m["start"], m["end"]) for m in c["meetings"]],
                         [("TUE", "13:30", "15:00"), ("THU", "13:30", "15:00")])

    def test_extra_online_course(self):
        text = ("※ 시간표 이외의 강의: 미래사회와 소프트웨어-IT계열(GEB1143-001), "
                "담당교수: 심정섭,김유성, 강의시간: 웹")
        (c,) = parse_extra(text)
        self.assertEqual((c["name"], c["course_code"], c["section"]),
                         ("미래사회와 소프트웨어-IT계열", "GEB1143", "001"))
        self.assertEqual(c["professor"], "심정섭,김유성")
        self.assertEqual(c["meetings"], [])
        self.assertTrue(c["warnings"])


if __name__ == "__main__":
    unittest.main()
