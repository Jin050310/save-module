import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from timetable_parser import (  # noqa: E402
    build_course, merge_periods, parse_time_location, period_to_range, fmt,
    split_code_section,
)


class TestPeriods(unittest.TestCase):
    def test_period_times_match_screenshot(self):
        # 캡처의 격자: 1교시 09:00~09:30, 5교시 11:00~11:30, 10교시 13:30~14:00, 13교시 15:00~15:30
        expected = {1: ("09:00", "09:30"), 5: ("11:00", "11:30"),
                    10: ("13:30", "14:00"), 13: ("15:00", "15:30")}
        for p, (s, e) in expected.items():
            start, end = period_to_range(p)
            self.assertEqual((fmt(start), fmt(end)), (s, e))

    def test_merge(self):
        self.assertEqual(merge_periods([5, 6, 7, 8]), [(5, 8)])
        self.assertEqual(merge_periods([1, 2, 5]), [(1, 2), (5, 5)])
        self.assertEqual(merge_periods([8, 7, 6, 6]), [(6, 8)])


class TestTimeLocation(unittest.TestCase):
    def test_chemistry_lab(self):
        meetings, warnings = parse_time_location("수5,6,7,8(5동511)")
        self.assertEqual(meetings, [
            {"day": "WED", "start": "11:00", "end": "13:00", "room": "5동511"},
        ])
        self.assertEqual(warnings, [])

    def test_english_two_days_shared_room(self):
        meetings, warnings = parse_time_location("화10,11,12,목10,11,12(60주년-502)")
        self.assertEqual(meetings, [
            {"day": "TUE", "start": "13:30", "end": "15:00", "room": "60주년-502"},
            {"day": "THU", "start": "13:30", "end": "15:00", "room": "60주년-502"},
        ])
        self.assertEqual(warnings, [])

    def test_non_consecutive_periods_split(self):
        meetings, _ = parse_time_location("월1,2,5(A101)")
        self.assertEqual([(m["start"], m["end"]) for m in meetings],
                         [("09:00", "10:00"), ("11:00", "11:30")])

    def test_unknown_text_is_flagged_not_dropped(self):
        meetings, warnings = parse_time_location("온라인")
        self.assertEqual(meetings, [])
        self.assertTrue(warnings)

    def test_empty_is_flagged(self):
        meetings, warnings = parse_time_location("")
        self.assertEqual(meetings, [])
        self.assertTrue(warnings)

    def test_different_rooms_per_day_is_flagged(self):
        _, warnings = parse_time_location("월1,2(A101),수1,2(B202)")
        self.assertTrue(any("강의실" in w for w in warnings))

    def test_period_beyond_verified_is_flagged(self):
        _, warnings = parse_time_location("금35(A101)")
        self.assertTrue(any("미확인" in w for w in warnings))

    def test_period_34_is_verified(self):
        self.assertEqual(period_to_range(34), (25 * 60 + 30, 26 * 60))
        _, warnings = parse_time_location("금33,34(A101)")
        self.assertEqual(warnings, [])


class TestCourse(unittest.TestCase):
    def test_split_code(self):
        self.assertEqual(split_code_section("CHM1927-008"), ("CHM1927", "008"))
        self.assertEqual(split_code_section("이상한값"), ("이상한값", None))

    def test_build_course_from_screenshot_row(self):
        c = build_course("GEB1108-027", "의사소통 영어: 중급", "테리로즈",
                         "화10,11,12,목10,11,12(60주년-502)", "3.0")
        self.assertEqual(c["course_code"], "GEB1108")
        self.assertEqual(c["section"], "027")
        self.assertEqual(len(c["meetings"]), 2)
        self.assertEqual(c["warnings"], [])


if __name__ == "__main__":
    unittest.main()
