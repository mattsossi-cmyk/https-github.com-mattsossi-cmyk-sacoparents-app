import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight } from "lucide-react";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function monthCells(year, month) {
  const first = new Date(year, month, 1).getDay();
  const days = new Date(year, month + 1, 0).getDate();
  return [...Array(first).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)];
}

// A plain month view. Quick exit from Get help lands here.
export default function CalendarPage() {
  const today = new Date();
  const [view, setView] = useState({ y: today.getFullYear(), m: today.getMonth() });
  const cells = useMemo(() => monthCells(view.y, view.m), [view]);
  const shift = (d) => setView(({ y, m }) => ({ y: m + d < 0 ? y - 1 : m + d > 11 ? y + 1 : y, m: (m + d + 12) % 12 }));
  const label = new Date(view.y, view.m, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
  const isToday = (d) => d === today.getDate() && view.m === today.getMonth() && view.y === today.getFullYear();
  return (
    <main data-testid="calendar-page" className="min-h-screen bg-white px-4 py-8">
      <div className="max-w-lg mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Calendar</h1>
          <Link to="/" data-testid="calendar-home-link" className="text-sm font-semibold text-[#3D1A78]">Home</Link>
        </div>
        <div className="flex items-center justify-between mb-4">
          <button type="button" onClick={() => shift(-1)} aria-label="Previous month" data-testid="calendar-prev" className="p-2 rounded-lg hover:bg-slate-100">
            <ChevronLeft size={18} />
          </button>
          <p className="font-semibold text-slate-800" data-testid="calendar-month">{label}</p>
          <button type="button" onClick={() => shift(1)} aria-label="Next month" data-testid="calendar-next" className="p-2 rounded-lg hover:bg-slate-100">
            <ChevronRight size={18} />
          </button>
        </div>
        <div className="grid grid-cols-7 gap-1 text-center" data-testid="calendar-grid">
          {DAYS.map((d) => (
            <div key={d} className="text-[11px] font-bold uppercase text-slate-400 py-1">{d}</div>
          ))}
          {cells.map((d, i) => (
            <div
              key={i}
              className={`aspect-square rounded-lg grid place-items-center text-sm ${d ? "border border-slate-100" : ""} ${isToday(d) ? "bg-[#3D1A78] text-white font-bold" : "text-slate-700"}`}
            >
              {d || ""}
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
