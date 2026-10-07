import React from "react";

import { CONTENT } from "./content";

const dayAgo = (n) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d;
};
const key = (d) => d.toLocaleDateString("en-CA");

// Consecutive practised days ending today (or yesterday, so today isn't "broken" yet).
const streakOf = (done) => {
  let n = done.has(key(dayAgo(0))) ? 0 : 1;
  let streak = 0;
  while (done.has(key(dayAgo(n)))) {
    streak += 1;
    n += 1;
  }
  return streak;
};

function WeekStrip({ recentDates, testid }) {
  const done = new Set(recentDates);
  const streak = streakOf(done);
  const days = [6, 5, 4, 3, 2, 1, 0].map((n) => dayAgo(n));
  return (
    <div className="mt-3 flex items-center justify-between gap-2">
      <div data-testid={`${testid}-week`} className="flex items-end gap-1.5">
        {days.map((d, i) => {
          const on = done.has(key(d));
          const today = i === 6;
          return (
            <div key={key(d)} className="flex flex-col items-center gap-0.5">
              <span
                data-testid={`${testid}-day-${i}`}
                data-done={on ? "true" : "false"}
                className={`w-4 h-4 rounded-full transition-colors ${on ? "bg-emerald-500" : "bg-white border border-emerald-200"} ${
                  today ? "ring-2 ring-offset-1 ring-emerald-600" : ""
                }`}
              />
              <span className={`text-[9px] font-bold ${today ? "text-emerald-800" : "text-slate-400"}`}>
                {d.toLocaleDateString("en-US", { weekday: "narrow" })}
              </span>
            </div>
          );
        })}
      </div>
      {streak > 0 && (
        <span data-testid={`${testid}-streak`} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-orange-50 border border-orange-200 text-orange-700 text-[11px] font-extrabold">
          <i className="fa-solid fa-fire text-orange-500"></i>
          {streak}-day streak
        </span>
      )}
    </div>
  );
}

function PracticeRow({ practice, onPractise, testid }) {
  const { count, practisedToday } = practice;
  return (
    <>
    <WeekStrip recentDates={practice.recentDates || []} testid={testid} />
    <div className="mt-3 flex items-center justify-between gap-2 flex-wrap">
      <p data-testid={`${testid}-practice-count`} className="text-[11.5px] font-semibold text-emerald-900">
        <i className="fa-solid fa-seedling mr-1.5 text-emerald-600"></i>
        {count === 0 ? "Not practised yet" : `Practised ${count} day${count === 1 ? "" : "s"}`}
      </p>
      <button
        type="button"
        data-testid={`${testid}-practise`}
        onClick={onPractise}
        disabled={practisedToday}
        className="px-3 py-1.5 rounded-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-100 disabled:text-emerald-800 text-white text-[11px] font-bold transition-colors active:scale-95"
      >
        {practisedToday ? (
          <>
            <i className="fa-solid fa-check mr-1"></i>Practised today
          </>
        ) : (
          "I practised this today"
        )}
      </button>
    </div>
    </>
  );
}

// Personal Co-Parenting Goal — shown on the dashboard until the next Self-Assessment.
export function GoalBanner({ goal, setAt, practice, onPractise, dueDays = 0, onOpen, testid }) {
  if (!goal && !dueDays) return null;
  const when = setAt
    ? new Date(setAt).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })
    : null;
  return (
    <section
      data-testid={testid}
      className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-4 shadow-sm"
    >
      {goal && (
        <div className="flex items-start gap-3">
          <div className="shrink-0 w-10 h-10 rounded-full bg-emerald-600 text-white flex items-center justify-center">
            <i className="fa-solid fa-bullseye"></i>
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[10px] uppercase font-bold tracking-wider text-emerald-800">{CONTENT.goal.label}</div>
            <p data-testid={`${testid}-text`} className="text-sm font-semibold text-slate-900 leading-snug mt-0.5 break-words">
              {goal}
            </p>
            {when && <p className="text-[10px] text-slate-500 mt-1">Set {when}</p>}
          </div>
        </div>
      )}
      {goal && <PracticeRow practice={practice} onPractise={onPractise} testid={testid} />}
      {dueDays > 0 && (
        <div
          data-testid={`${testid}-reassess-due`}
          className={`${goal ? "mt-3" : ""} rounded-xl bg-amber-50 border border-amber-200 px-3 py-2 text-[12px] text-amber-900 leading-snug`}
        >
          <i className="fa-solid fa-clock-rotate-left mr-1.5"></i>
          <span className="font-bold">Time to reassess.</span> It's been {Math.floor(dueDays / 7)} weeks since your
          last Self-Assessment — see how far you've come.
        </div>
      )}
      <button
        type="button"
        data-testid={`${testid}-open`}
        onClick={onOpen}
        className={`mt-3 w-full py-2 rounded-full text-xs font-bold transition-colors ${
          dueDays > 0
            ? "bg-[#4c2889] hover:bg-[#371a68] text-white"
            : "bg-white hover:bg-emerald-50 border border-emerald-300 text-emerald-900"
        }`}
      >
        <i className={`fa-solid ${dueDays > 0 ? "fa-rotate" : "fa-chart-line"} mr-1.5`}></i>
        {dueDays > 0 ? "Start my next Self-Assessment" : "See my progress or reassess"}
      </button>
    </section>
  );
}
