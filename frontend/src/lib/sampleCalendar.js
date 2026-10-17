// Made-up everyday events so the Quick exit calendar looks like an ordinary family calendar.
const TONES = {
  sky: "bg-sky-500",
  green: "bg-emerald-500",
  amber: "bg-amber-500",
  rose: "bg-rose-500",
  violet: "bg-violet-500",
  slate: "bg-slate-400",
};

export const toneDot = (tone) => TONES[tone] || TONES.slate;

export function eventsFor(y, m, d) {
  const dow = new Date(y, m, d).getDay();
  const nth = Math.ceil(d / 7);
  const isLast = d + 7 > new Date(y, m + 1, 0).getDate();
  const ev = [];
  if (dow === 0) ev.push({ time: "10:00 AM", title: "Grocery run", tone: "amber" });
  if (dow === 1 || dow === 3 || dow === 5) ev.push({ time: "3:00 PM", title: "School pickup", tone: "sky" });
  if (dow === 2 || dow === 4) ev.push({ time: "5:30 PM", title: "Soccer practice", tone: "green" });
  if (dow === 3 && nth % 2 === 1) ev.push({ time: "4:30 PM", title: "Piano lesson", tone: "violet" });
  if (dow === 1 && nth === 2) ev.push({ time: "4:15 PM", title: "Dentist", tone: "rose" });
  if (dow === 4 && nth === 2) ev.push({ time: "All day", title: "Library books due", tone: "slate" });
  if (dow === 6 && nth === 1) ev.push({ time: "2:00 PM", title: "Birthday party", tone: "violet" });
  if (dow === 6 && nth === 3) ev.push({ time: "9:00 AM", title: "Soccer game", tone: "green" });
  if (d === 15) ev.push({ time: "All day", title: "Pay water bill", tone: "slate" });
  if (dow === 5 && isLast) ev.push({ time: "6:30 PM", title: "Pizza night", tone: "amber" });
  return ev.sort((a, b) => (a.time === "All day" ? -1 : b.time === "All day" ? 1 : toMinutes(a.time) - toMinutes(b.time)));
}

function toMinutes(t) {
  const [, h, min, ap] = t.match(/(\d+):(\d+) (AM|PM)/);
  return ((+h % 12) + (ap === "PM" ? 12 : 0)) * 60 + +min;
}

export function monthCells(year, month) {
  const first = new Date(year, month, 1).getDay();
  const days = new Date(year, month + 1, 0).getDate();
  return [...Array(first).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)];
}

// Plain calendar glyph for the browser tab while this page is open.
export const CALENDAR_ICON =
  "data:image/svg+xml," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect x="3" y="6" width="26" height="23" rx="4" fill="#fff" stroke="#475569" stroke-width="2"/><rect x="3" y="6" width="26" height="7" rx="3" fill="#ef4444"/><rect x="9" y="3" width="2.5" height="6" rx="1" fill="#475569"/><rect x="20.5" y="3" width="2.5" height="6" rx="1" fill="#475569"/><text x="16" y="25" font-family="Arial" font-size="11" font-weight="700" text-anchor="middle" fill="#334155">31</text></svg>'
  );
