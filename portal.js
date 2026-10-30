(function () {
  // TODO: 학교 포털 화면에 맞게 이 설정을 수정하세요.
  const CONFIG = {
    rowSelector: ".course-table tbody tr",
    columns: { code: 0, name: 1, meeting: 3, location: 4 }
  };

  const DAY_CODES = { "월": "MON", "화": "TUE", "수": "WED", "목": "THU", "금": "FRI", "토": "SAT", "일": "SUN" };
  const MEETING_PATTERN = /(월|화|수|목|금|토|일)(?:요일)?\s*(\d{1,2}:\d{2})\s*[~\-–〜]\s*(\d{1,2}:\d{2})/g;

  function parseMeetings(text) {
    const meetings = [];
    for (const match of text.matchAll(MEETING_PATTERN)) {
      meetings.push({
        day: DAY_CODES[match[1]],
        start: match[2].padStart(5, "0"),
        end: match[3].padStart(5, "0")
      });
    }
    return meetings;
  }

  function getCell(cells, index) {
    return (cells[index] && cells[index].innerText || "").replace(/\s+/g, " ").trim();
  }

  function readCourses() {
    const rows = Array.from(document.querySelectorAll(CONFIG.rowSelector));
    return rows.map((row) => {
      const cells = Array.from(row.querySelectorAll("td"));
      return {
        code: getCell(cells, CONFIG.columns.code),
        name: getCell(cells, CONFIG.columns.name),
        location: getCell(cells, CONFIG.columns.location),
        meetings: parseMeetings(getCell(cells, CONFIG.columns.meeting))
      };
    }).filter((course) => course.name && course.meetings.length > 0);
  }

  function addButton() {
    if (document.getElementById("ttx-portal-save")) return;
    const button = document.createElement("button");
    button.id = "ttx-portal-save";
    button.className = "ttx-button ttx-floating-button";
    button.textContent = "수강시간표 저장";
    button.addEventListener("click", async () => {
      try {
        const courses = readCourses();
        if (!courses.length) {
          alert("시간표를 찾지 못했어요. portal.js의 표 선택자와 열 번호를 확인해 주세요.");
          return;
        }
        const payload = {
          format: "timetable-bridge-v1",
          exportedAt: new Date().toISOString(),
          source: location.origin,
          courses
        };
        await chrome.storage.local.set({ savedSchedule: payload });
        alert(courses.length + "개 과목을 이 브라우저에 저장했어요. 이제 에타에서 가져오기를 눌러 보세요.");
      } catch (error) {
        console.error("시간표 저장 실패:", error);
        alert("시간표 저장에 실패했어요. 확장 프로그램 권한과 포털 표 설정을 확인해 주세요.");
      }
    });
    document.body.appendChild(button);
  }

  addButton();
})();
