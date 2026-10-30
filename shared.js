(function () {
  const DAYS_KO = {
    MON: "월", TUE: "화", WED: "수", THU: "목", FRI: "금", SAT: "토", SUN: "일"
  };

  function isValidTime(value) {
    return typeof value === "string" && /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/.test(value);
  }

  function validateSchedule(payload) {
    if (!payload || payload.format !== "timetable-bridge-v1" || !Array.isArray(payload.courses)) {
      throw new Error("저장된 시간표 데이터 형식이 올바르지 않습니다.");
    }
    const courses = payload.courses.filter((course) =>
      course && typeof course.name === "string" && course.name.trim() && Array.isArray(course.meetings)
    );
    for (const course of courses) {
      for (const meeting of course.meetings) {
        if (!DAYS_KO[meeting.day] || !isValidTime(meeting.start) || !isValidTime(meeting.end)) {
          throw new Error(course.name + " 과목의 요일 또는 시간이 올바르지 않습니다.");
        }
      }
    }
    return courses;
  }

  function describeMeeting(meeting) {
    return DAYS_KO[meeting.day] + " " + meeting.start + "-" + meeting.end;
  }

  window.TimetableBridge = { validateSchedule, describeMeeting, DAYS_KO };
})();
