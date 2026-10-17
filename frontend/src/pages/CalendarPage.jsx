import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

import { CALENDAR_ICON, eventsFor, monthCells, toneDot } from "../lib/sampleCalendar";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

// Plain tab title and icon while the calendar is open; the app's own come back on leave.
function useNeutralTab() {
  useEffect(() => {
    const prevTitle = document.title;
    const icons = [...document.querySelectorAll("link[rel~='icon']")];
    const prevIcons = icons.map((l) => l.href);
    document.title = "Calendar";
    icons.forEach((l) => { l.href = CALENDAR_ICON; });
    return () => {
      document.title = prevTitle;
      icons.forEach((l, i) => { l.href = prevIcons[i]; });
    };
  }, []);
}

function DayCell({ d, view, selected, today, onPick }) {
  const ev = eventsFor(view.y, view.m, d);
  const date = new Date(view.y, view.m, d);
  const label = `${date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}, ${ev.length} ${ev.length === 1 ? "event" : "events"}`;
  return (
    <button
      type="button"
      onClick={() => onPick(d)}
      aria-label={label}
      aria-pressed={selected}
      data-testid={`calendar-day-${d}`}
      className={`aspect-square rounded-lg flex flex-col items-center justify-start pt-1.5 text-sm transition-colors ${selected ? "bg-slate-900 text-white" : today ? "bg-red-50 text-red-700 font-bold" : "text-slate-800 hover:bg-slate-100"}`}
    >
      <span>{d}</span>
      <span className="mt-1 flex gap-0.5" aria-hidden="true">
        {ev.slice(0, 3).map((e) => <span key={e.title} className={`h-1.5 w-1.5 rounded-full ${toneDot(e.tone)}`} />)}
      </span>
    </button>
  );
}

function Agenda({ view, day }) {
  const ev = eventsFor(view.y, view.m, day);
  const label = new Date(view.y, view.m, day).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
  return (
    <section className="mt-6" data-testid="calendar-agenda" aria-live="polite">
      <h2 className="text-sm font-semibold text-slate-900 font-[inherit]">{label}</h2>
      {ev.length ? (
        <ul className="mt-2 space-y-2">
          {ev.map((e) => (
            <li key={e.title} className="flex items-center gap-3 rounded-xl border border-slate-200 px-3 py-2.5" data-testid="calendar-event">
              <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${toneDot(e.tone)}`} aria-hidden="true" />
              <span className="flex-1 text-sm text-slate-900">{e.title}</span>
              <span className="text-xs text-slate-600 tabular-nums">{e.time}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-slate-600">Nothing planned.</p>
      )}
    </section>
  );
}

// Quick exit from Get help lands here: an ordinary-looking family calendar with no app name.
export default function CalendarPage() {
  useNeutralTab();
  const navigate = useNavigate();
  const now = new Date();
  const [view, setView] = useState({ y: now.getFullYear(), m: now.getMonth() });
  const [day, setDay] = useState(now.getDate());
  const cells = useMemo(() => monthCells(view.y, view.m), [view]);
  const shift = (n) => {
    setView(({ y, m }) => ({ y: m + n < 0 ? y - 1 : m + n > 11 ? y + 1 : y, m: (m + n + 12) % 12 }));
    setDay(1);
  };
  const goToday = () => {
    setView({ y: now.getFullYear(), m: now.getMonth() });
    setDay(now.getDate());
  };
  const isToday = (d) => d === now.getDate() && view.m === now.getMonth() && view.y === now.getFullYear();
  const label = new Date(view.y, view.m, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
  return (
    <main data-testid="calendar-page" className="min-h-screen bg-white px-4 py-6" style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
      <div className="max-w-lg mx-auto">
        <header className="flex items-center justify-between gap-2 mb-5">
          <h1 className="text-2xl font-bold text-slate-900 font-[inherit]">Calendar</h1>
          <div className="flex items-center gap-1">
            <button type="button" onClick={goToday} data-testid="calendar-today" className="rounded-full border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-100">Today</button>
            <button type="button" onClick={() => navigate("/")} aria-label="Close calendar" data-testid="calendar-close" className="rounded-full p-2 text-slate-600 transition-colors hover:bg-slate-100">
              <X size={18} />
            </button>
          </div>
        </header>
        <div className="flex items-center justify-between mb-3">
          <button type="button" onClick={() => shift(-1)} aria-label="Previous month" data-testid="calendar-prev" className="p-2 rounded-lg transition-colors hover:bg-slate-100"><ChevronLeft size={18} /></button>
          <p className="font-semibold text-slate-900" data-testid="calendar-month" aria-live="polite">{label}</p>
          <button type="button" onClick={() => shift(1)} aria-label="Next month" data-testid="calendar-next" className="p-2 rounded-lg transition-colors hover:bg-slate-100"><ChevronRight size={18} /></button>
        </div>
        <div className="grid grid-cols-7 gap-1 text-center" data-testid="calendar-grid">
          {DAYS.map((d) => <div key={d} className="text-[0.6875rem] font-semibold uppercase text-slate-500 py-1" aria-hidden="true">{d}</div>)}
          {cells.map((d, i) => (d ? <DayCell key={i} d={d} view={view} selected={d === day} today={isToday(d)} onPick={setDay} /> : <div key={i} />))}
        </div>
        <Agenda view={view} day={day} />
      </div>
    </main>
  );
}
