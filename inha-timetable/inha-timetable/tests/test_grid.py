import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from convert import convert, parse_days  # noqa: E402
from grid_parser import grid_to_courses, is_grid  # noqa: E402

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "samples", "sample_grid.txt")


def load():
    with open(SAMPLE, encoding="utf-8") as f:
        return f.read()


class TestGrid(unittest.TestCase):
    def test_detects_grid(self):
        self.assertTrue(is_grid(load()))
        self.assertFalse(is_grid("학수번호\t과목명\n"))

    def test_two_courses_with_times_from_text(self):
        chem, eng = grid_to_courses(load())
        self.assertEqual((chem["name"], chem["course_code"], chem["section"], chem["professor"]),
                         ("일반화학실험", "CHM1927", "008", "강동원"))
        self.assertEqual([(m["start"], m["end"]) for m in chem["meetings"]], [("11:00", "13:00")])
        self.assertEqual(eng["name"], "의사소통 영어: 중급")
        self.assertEqual(eng["professor"], "테리로즈")
        # 같은 교시에 칸이 둘 -> 주 2일
        self.assertEqual([(m["start"], m["end"]) for m in eng["meetings"]],
                         [("13:30", "15:00"), ("13:30", "15:00")])

    def test_day_unknown_is_flagged(self):
        for c in grid_to_courses(load()):
            self.assertTrue(any("요일" in w for w in c["warnings"]))
            self.assertTrue(all(m["day"] is None for m in c["meetings"]))

    def test_days_override(self):
        days = parse_days(["GEB1108-027=화,목", "CHM1927-008=수"])
        chem, eng = grid_to_courses(load(), days)
        self.assertEqual([m["day"] for m in chem["meetings"]], ["WED"])
        self.assertEqual([m["day"] for m in eng["meetings"]], ["TUE", "THU"])
        self.assertFalse(any("요일" in w for w in eng["warnings"]))

    def test_days_count_mismatch_is_flagged(self):
        _, eng = grid_to_courses(load(), {"GEB1108-027": ["화"]})
        self.assertTrue(any("요일" in w for w in eng["warnings"]))
        self.assertTrue(all(m["day"] is None for m in eng["meetings"]))

    def test_bad_days_spec(self):
        with self.assertRaises(ValueError):
            parse_days(["GEB1108-027=화,xx"])

    def test_unknown_line_raises(self):
        with self.assertRaises(ValueError):
            grid_to_courses("교시/요일\t월\n5교시\n[11:00 ~ 11:30]\t\n이상한줄\n")

    def test_convert_picks_grid(self):
        data = convert(load(), "2026-2")
        self.assertEqual(len(data["courses"]), 2)


if __name__ == "__main__":
    unittest.main()
