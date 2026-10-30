(function () {
  function formatCourse(course) {
    const times = course.meetings.map(TimetableBridge.describeMeeting).join(", ");
    const code = course.code ? " (" + course.code + ")" : "";
    const location = course.location ? " · " + course.location : "";
    return course.name + code + "\n" + times + location;
  }

  function closePanel(panel) { panel.remove(); }

  async function showSchedule() {
    const result = await chrome.storage.local.get("savedSchedule");
    const payload = result.savedSchedule;
    if (!payload) {
      alert("저장된 시간표가 없어요. 먼저 학교 포털에서 ‘수강시간표 저장’을 눌러 주세요.");
      return;
    }

    let courses;
    try {
      courses = TimetableBridge.validateSchedule(payload);
    } catch (error) {
      alert(error.message);
      return;
    }

    const panel = document.createElement("section");
    panel.className = "ttx-overlay";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    const card = document.createElement("div");
    card.className = "ttx-card";
    const heading = document.createElement("h2");
    heading.className = "ttx-heading";
    heading.textContent = "포털 시간표 미리보기";
    const note = document.createElement("p");
    note.className = "ttx-note";
    note.textContent = "포털에서 저장한 " + courses.length + "개 과목입니다. 현재 버전은 미리보기 단계이며 에타에 자동 저장하지 않습니다.";
    const list = document.createElement("ul");
    list.className = "ttx-course-list";

    for (const course of courses) {
      const item = document.createElement("li");
      item.className = "ttx-course-item";
      item.textContent = formatCourse(course);
      list.appendChild(item);
    }

    const actions = document.createElement("div");
    actions.className = "ttx-actions";
    const clearButton = document.createElement("button");
    clearButton.className = "ttx-button ttx-secondary";
    clearButton.textContent = "저장 데이터 지우기";
    clearButton.addEventListener("click", async () => {
      await chrome.storage.local.remove("savedSchedule");
      closePanel(panel);
      alert("브라우저에 저장된 시간표 데이터를 지웠어요.");
    });
    const closeButton = document.createElement("button");
    closeButton.className = "ttx-button";
    closeButton.textContent = "닫기";
    closeButton.addEventListener("click", () => closePanel(panel));
    actions.append(clearButton, closeButton);
    card.append(heading, note, list, actions);
    panel.appendChild(card);
    panel.addEventListener("click", (event) => {
      if (event.target === panel) closePanel(panel);
    });
    document.body.appendChild(panel);
  }

  function addButton() {
    if (document.getElementById("ttx-everytime-import")) return;
    const button = document.createElement("button");
    button.id = "ttx-everytime-import";
    button.className = "ttx-button ttx-floating-button";
    button.textContent = "포털 시간표 붙여넣기";
    button.addEventListener("click", () => {
      showSchedule().catch((error) => {
        console.error("시간표 불러오기 실패:", error);
        alert("시간표를 불러오지 못했어요. 확장 프로그램을 새로고침한 뒤 다시 시도해 주세요.");
      });
    });
    document.body.appendChild(button);
  }

  addButton();
})();
