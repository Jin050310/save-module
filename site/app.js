import * as pdfjs from "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.10.38/pdf.min.mjs";
import { readPdf, toCsv } from "./timetable.js";

pdfjs.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.10.38/pdf.worker.min.mjs";

const DAY_KR = { MON: "월", TUE: "화", WED: "수", THU: "목", FRI: "금", SAT: "토", SUN: "일" };

const $ = (id) => document.getElementById(id);
let courses = [];

function showError(message) {
  $("error").textContent = message;
  $("error").hidden = !message;
}

function render() {
  const rows = $("rows");
  rows.replaceChildren();
  for (const c of courses) {
    const tr = rows.insertRow();
    tr.insertCell().textContent = c.name + (c.course_code ? ` (${c.course_code}-${c.section})` : "");
    tr.insertCell().textContent = c.professor;
    tr.insertCell().textContent = c.meetings.length
      ? c.meetings.map((m) => `${DAY_KR[m.day]} ${m.start}~${m.end}`).join("\n")
      : "-";
    tr.insertCell().textContent = c.meetings.length ? [...new Set(c.meetings.map((m) => m.room))].join(", ") : "-";
    tr.style.whiteSpace = "pre-line";
  }
  const warnings = $("warnings");
  warnings.replaceChildren();
  const unique = [...new Set(courses.flatMap((c) => c.warnings))];
  const shared = unique.filter((w) => w.startsWith("학수번호·분반 없음"));
  const rest = courses.flatMap((c) => c.warnings.filter((w) => !shared.includes(w)).map((w) => `${c.name}: ${w}`));
  for (const text of [...(shared.length ? ["학수번호·분반은 PDF에 없습니다. 수강신청 확인서와 합쳐야 채워집니다."] : []), ...rest]) {
    const div = document.createElement("div");
    div.className = "warn";
    div.textContent = text;
    warnings.append(div);
  }
  $("result").hidden = !courses.length;
}

async function handle(file) {
  showError("");
  courses = [];
  render();
  if (!file) return;
  try {
    courses = await readPdf(pdfjs, new Uint8Array(await file.arrayBuffer()));
  } catch (e) {
    showError(`읽지 못했습니다: ${e.message}`);
    return;
  }
  if (!courses.length) showError("과목을 찾지 못했습니다. 강의시간표 PDF가 맞는지 확인하세요.");
  render();
}

function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}

const data = () => ({ university: "인하대학교", semester: $("semester").value.trim(), courses });

$("dl-json").onclick = () => download("timetable.json", JSON.stringify(data(), null, 2), "application/json");
// 엑셀에서 한글이 깨지지 않도록 CSV 앞에 BOM을 붙인다
$("dl-csv").onclick = () => download("timetable.csv", "﻿" + toCsv(data()), "text/csv");

const drop = $("drop");
drop.onclick = () => $("file").click();
drop.onkeydown = (e) => (e.key === "Enter" || e.key === " ") && $("file").click();
$("file").onchange = (e) => handle(e.target.files[0]);
drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("over"); };
drop.ondragleave = () => drop.classList.remove("over");
drop.ondrop = (e) => {
  e.preventDefault();
  drop.classList.remove("over");
  handle(e.dataTransfer.files[0]);
};
