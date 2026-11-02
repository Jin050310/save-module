// 강의시간표 PDF(교시 x 요일 격자) -> 과목 목록. 브라우저와 Node 양쪽에서 돈다.
// inha-timetable/src/pdf_timetable.py 와 같은 로직을 옮긴 것이다. 고칠 때는 두 곳을 함께 고친다.
//
// PDF에서 글자만 뽑으면 요일(열)이 사라지므로 글자·회색 칸의 좌표를 쓴다.
//   - 회색 칸이 과목 칸이다. 칸의 가로 위치 = 요일, 세로 위치 = 교시.
//   - 같은 요일 열에서 서로 다른 과목이 붙어 있을 수 있어, 칸 묶음 안의 글자를
//     '과목명 교수(강의실)' 단위로 끊어 나눈다. (강의실이 줄바꿈되어도 괄호가 닫힐 때까지 한 과목)
//   - 격자 아래의 '시간표 이외의 강의' 줄(온라인 등)은 시간 없이 따로 담는다.
// 성명 등 인적사항은 읽지 않는다. 회색 칸 안의 글자만 사용한다.

export const DAY_MAP = { 월: "MON", 화: "TUE", 수: "WED", 목: "THU", 금: "FRI", 토: "SAT", 일: "SUN" };
const DAY_ORDER = Object.keys(DAY_MAP);
export const VERIFIED_MAX_PERIOD = 34; // 34교시 = 25:30~26:00

const LABEL = /^(\d+)교시$/;
const COURSE = /^(.+?)\s+(\S+?)\((.*)\)$/;
const EXTRA = /시간표 이외의 강의:\s*(.+?)\(([A-Za-z]+\d+-\d+)\),\s*담당교수:\s*(.+?),\s*강의시간:\s*([^\n]+)/g;

export function periodToRange(period) {
  const start = 9 * 60 + 30 * (period - 1);
  return [start, start + 30];
}

export function fmt(minutes) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(Math.floor(minutes / 60))}:${pad(minutes % 60)}`;
}

function nearest(centers, value) {
  let best = null;
  for (const [key, c] of centers) {
    if (best === null || Math.abs(c - value) < Math.abs(centers.get(best) - value)) best = key;
  }
  return best;
}

// 같은 열의 글자들 -> [[top, text], ...] (위에서 아래로)
export function linesOf(words) {
  const sorted = [...words].sort((a, b) => a.top - b.top || a.x0 - b.x0);
  const lines = [];
  for (const w of sorted) {
    const last = lines[lines.length - 1];
    if (last && w.top - last.top <= 4) last.words.push(w);
    else lines.push({ top: w.top, words: [w] });
  }
  return lines.map((l) => [l.top, l.words.sort((a, b) => a.x0 - b.x0).map((w) => w.text).join(" ")]);
}

const count = (s, ch) => s.split(ch).length - 1;

// 줄들 -> [[시작 top, 'name prof(room)'], ...]. 괄호가 닫히면 한 과목이 끝난다.
export function splitCourses(lines) {
  const courses = [];
  let cur = null;
  for (const [top, text] of lines) {
    if (cur === null) cur = [top, text];
    else if (count(cur[1], "(") > count(cur[1], ")")) cur[1] += text; // 괄호 안에서 줄바꿈된 강의실
    else cur[1] += " " + text;
    if (count(cur[1], "(") === count(cur[1], ")") && text.includes(")")) {
      courses.push(cur);
      cur = null;
    }
  }
  if (cur !== null) throw new Error(`괄호가 닫히지 않은 과목 칸: '${cur[1]}'`);
  return courses;
}

// words: [{text,x0,x1,top,bottom}], rects: 회색 칸 [{x0,x1,top,bottom}]
// -> [{name, professor, day, first, last, room}]  (first/last = 교시)
export function parseLayout(words, rects) {
  const labelTops = new Map();
  for (const w of words) {
    const m = w.x0 < 100 && LABEL.exec(w.text);
    if (m) labelTops.set(Number(m[1]), w.top);
  }
  const dayCenters = new Map();
  for (const w of words) {
    if (w.x0 > 100 && w.top < 110 && Object.hasOwn(DAY_MAP, w.text)) dayCenters.set(w.text, (w.x0 + w.x1) / 2);
  }
  if (!labelTops.size || !dayCenters.size) {
    throw new Error("교시 또는 요일 머리글을 찾지 못함: 강의시간표 PDF가 맞는지 확인 필요");
  }

  // 칸 -> 요일별로 세로로 이어지는 묶음(run)
  const byDay = new Map();
  for (const r of rects) {
    const day = nearest(dayCenters, (r.x0 + r.x1) / 2);
    if (!byDay.has(day)) byDay.set(day, []);
    byDay.get(day).push(r);
  }
  const runs = [];
  for (const [day, rs] of byDay) {
    rs.sort((a, b) => a.top - b.top);
    let group = [rs[0]];
    for (const r of rs.slice(1)) {
      if (r.top - group[group.length - 1].bottom > 3) {
        runs.push({ day, group });
        group = [];
      }
      group.push(r);
    }
    runs.push({ day, group });
  }
  const box = (g) => ({
    x0: Math.min(...g.map((r) => r.x0)),
    x1: Math.max(...g.map((r) => r.x1)),
    top: g[0].top,
    bottom: g[g.length - 1].bottom,
  });

  // 글자 -> 겹치는 폭이 가장 큰 묶음
  const assigned = runs.map(() => []);
  for (const w of words) {
    if (w.x0 < 105 || w.top < 115) continue; // 교시 머리글·표 밖
    const mid = (w.top + w.bottom) / 2;
    let best = null;
    let bestOverlap = 0;
    runs.forEach(({ group }, i) => {
      const b = box(group);
      const overlap = Math.min(w.x1, b.x1) - Math.max(w.x0, b.x0);
      if (b.top - 1 <= mid && mid <= b.bottom + 1 && overlap > bestOverlap) {
        best = i;
        bestOverlap = overlap;
      }
    });
    if (best !== null) assigned[best].push(w);
  }

  const meetings = [];
  runs.forEach(({ day, group }, i) => {
    const lastRow = nearest(labelTops, group[group.length - 1].top);
    const found = splitCourses(linesOf(assigned[i]));
    found.forEach(([top, text], k) => {
      const m = COURSE.exec(text);
      if (!m) throw new Error(`과목명/교수(강의실) 형식이 아님: '${text}'`);
      const first = nearest(labelTops, top);
      const last = k + 1 < found.length ? nearest(labelTops, found[k + 1][0]) - 1 : lastRow;
      meetings.push({ name: m[1], professor: m[2], day, first, last, room: m[3] });
    });
  });
  return meetings;
}

export function meetingsToCourses(meetings) {
  const sorted = [...meetings].sort(
    (a, b) => DAY_ORDER.indexOf(a.day) - DAY_ORDER.indexOf(b.day) || a.first - b.first,
  );
  const courses = new Map();
  for (const m of sorted) {
    const key = `${m.name}\u0000${m.professor}`;
    if (!courses.has(key)) {
      courses.set(key, {
        name: m.name, course_code: "", section: null, professor: m.professor, credits: null,
        meetings: [], warnings: ["학수번호·분반 없음: 수강신청 확인서와 합쳐야 함"],
      });
    }
    const c = courses.get(key);
    c.meetings.push({
      day: DAY_MAP[m.day],
      start: fmt(periodToRange(m.first)[0]),
      end: fmt(periodToRange(m.last)[1]),
      room: m.room,
    });
    if (m.last > VERIFIED_MAX_PERIOD) {
      c.warnings.push(`${VERIFIED_MAX_PERIOD}교시 이후(${m.last}교시)는 시각 규칙 미확인: 확인 필요`);
    }
  }
  return [...courses.values()];
}

// '시간표 이외의 강의' 줄(온라인 등) -> 시간 없는 과목들
export function parseExtra(text) {
  return [...text.matchAll(EXTRA)].map((m) => {
    const [code, section] = m[2].split("-");
    return {
      name: m[1].trim(), course_code: code, section, professor: m[3].trim(), credits: null,
      meetings: [],
      warnings: [`시간표 밖 강의(강의시간: ${m[4].trim()}): 요일·시간 없음`],
    };
  });
}

const isWhite = (rgb) => rgb.every((v) => v >= 250);

// pdf.js 페이지 -> {words, rects, text}
export async function extractPage(page, OPS) {
  const H = page.view[3] - page.view[1];
  const content = await page.getTextContent();
  const words = [];
  let text = "";
  for (const it of content.items) {
    text += it.str + (it.hasEOL ? "\n" : "");
    if (!it.str.trim()) continue;
    const size = Math.abs(it.transform[3]) || Math.abs(it.height) || 8;
    const x = it.transform[4];
    const y = H - it.transform[5]; // 글자 기준선의 위에서부터의 거리
    words.push({ text: it.str.trim(), x0: x, x1: x + it.width, top: y - size, bottom: y });
  }

  const ops = await page.getOperatorList();
  const rects = [];
  let fill = [0, 0, 0];
  let pending = [];
  for (let i = 0; i < ops.fnArray.length; i++) {
    const fn = ops.fnArray[i];
    const args = ops.argsArray[i];
    if (fn === OPS.setFillRGBColor) fill = [args[0], args[1], args[2]];
    else if (fn === OPS.setFillGray) fill = [args[0], args[0], args[0]];
    else if (fn === OPS.constructPath) {
      let c = 0;
      for (const op of args[0]) {
        if (op === OPS.rectangle) {
          const [x, y, w, h] = args[1].slice(c, c + 4);
          c += 4;
          pending.push({
            x0: Math.min(x, x + w), x1: Math.max(x, x + w),
            top: H - Math.max(y, y + h), bottom: H - Math.min(y, y + h),
          });
        } else if (op === OPS.moveTo || op === OPS.lineTo) c += 2;
        else if (op === OPS.curveTo) c += 6;
        else if (op === OPS.curveTo2 || op === OPS.curveTo3) c += 4;
      }
    } else if (fn === OPS.fill || fn === OPS.eoFill || fn === OPS.fillStroke || fn === OPS.eoFillStroke) {
      if (!isWhite(fill)) rects.push(...pending);
      pending = [];
    } else if (fn === OPS.stroke || fn === OPS.endPath || fn === OPS.closeStroke) pending = [];
  }
  return { words, rects, text };
}

// pdfjs: pdf.js 모듈(getDocument, OPS), data: Uint8Array -> 과목 목록
export async function readPdf(pdfjs, data) {
  const pdf = await pdfjs.getDocument({ data }).promise;
  const pages = [];
  for (let i = 1; i <= pdf.numPages; i++) pages.push(await extractPage(await pdf.getPage(i), pdfjs.OPS));
  if (pages.slice(1).some((p) => p.rects.length)) {
    throw new Error("2쪽 이후에 과목 칸이 있음: 아직 지원하지 않음");
  }
  const rects = pages[0].rects.filter((r) => r.x1 - r.x0 < 150); // 맨 위 머리글 띠 제외
  const courses = meetingsToCourses(parseLayout(pages[0].words, rects));
  return [...courses, ...parseExtra(pages.map((p) => p.text).join("\n"))];
}

const csvCell = (v) => {
  const s = v === null || v === undefined ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
};

export function toCsv(data) {
  const rows = [["semester", "course_code", "section", "name", "professor", "day", "start", "end", "room", "warnings"]];
  for (const c of data.courses) {
    const base = [data.semester, c.course_code, c.section, c.name, c.professor];
    const warn = c.warnings.join("; ");
    if (!c.meetings.length) rows.push([...base, "", "", "", "", warn]);
    for (const m of c.meetings) rows.push([...base, m.day, m.start, m.end, m.room, warn]);
  }
  return rows.map((r) => r.map(csvCell).join(",")).join("\r\n") + "\r\n";
}
