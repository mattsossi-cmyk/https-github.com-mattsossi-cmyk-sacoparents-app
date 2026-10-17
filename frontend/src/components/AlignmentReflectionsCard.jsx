/**
 * AlignmentReflectionsCard.jsx — Iter193 · dashboard tile.
 *
 * One card per parent showing per-subject reflection progress
 * ("N of 6 answered") across the 5 registered subjects. Two goals:
 *   1. Remind parents to finish reflections before losing momentum
 *      (the tile lights up the moment they save any answer).
 *   2. Route Safety through the same UX as the other subjects but
 *      with a subtle "dual-consent" badge so it never feels casual.
 *
 * Data source: `GET /api/alignment-reflection/my-progress` — single
 * round-trip returns every subject's answered/total.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, ShieldAlert, Sparkles, CheckCircle2, Loader2,
} from "lucide-react";

import { api } from "../lib/api";
import { logError } from "../lib/logger";


function ProgressPill({ answered, total }) {
  const done = answered >= total && total > 0;
  const pct = total > 0 ? Math.round((answered / total) * 100) : 0;
  const label = done ? "Complete" : `${answered} of ${total}`;
  return (
    <div className="flex items-center gap-2 shrink-0">
      <div
        className="h-1.5 w-16 rounded-full bg-[#EEE8F7] overflow-hidden"
        aria-hidden="true"
      >
        <div
          className={`h-full transition-[width] ${
            done ? "bg-[#1F5C3B]" : "bg-[#3D1A78]"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span
        className={`text-[0.625rem] uppercase tracking-[0.14em] font-bold whitespace-nowrap ${
          done ? "text-[#1F5C3B]" : "text-[#6E6787]"
        }`}
      >
        {done && <CheckCircle2 size={10} className="inline mr-1 -mt-0.5" />}
        {label}
      </span>
    </div>
  );
}


function SubjectRow({ subject }) {
  return (
    <Link
      to={`/alignment/reflect/${subject.id}`}
      data-testid={`dashboard-alignment-subject-${subject.id}`}
      className="flex items-center justify-between gap-3 rounded-2xl border border-transparent bg-white/60 hover:bg-white hover:border-[#D6CFE8] px-3 py-2.5 transition"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-[#1A1330] truncate">
            {subject.label}
          </span>
          {subject.sensitive && (
            <span
              className="inline-flex items-center gap-0.5 rounded-full bg-[#AA0033]/10 text-[#AA0033] px-1.5 py-0.5 text-[0.5625rem] uppercase tracking-[0.1em] font-bold"
              data-testid={`dashboard-alignment-subject-${subject.id}-sensitive`}
            >
              <ShieldAlert size={9} /> Dual-consent
            </span>
          )}
        </div>
      </div>
      <ProgressPill answered={subject.answered} total={subject.total} />
      <ArrowRight
        size={14}
        className="text-[#6E6787] group-hover:text-[#3D1A78] shrink-0"
      />
    </Link>
  );
}


export default function AlignmentReflectionsCard() {
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get("/alignment-reflection/my-progress");
        setSubjects(res.data.subjects || []);
      } catch (err) {
        logError("alignment-reflections-card load", err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const answeredTotal = subjects.reduce((n, s) => n + (s.answered || 0), 0);
  const promptTotal   = subjects.reduce((n, s) => n + (s.total || 0), 0);
  const anyProgress   = answeredTotal > 0;

  return (
    <div
      className="mt-6 rounded-3xl border border-[#D6CFE8] bg-gradient-to-br from-[#F5EFFB] to-[#EDE3FA] p-5 sm:p-6"
      data-testid="dashboard-alignment-reflections-card"
    >
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0 flex-1">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
            <Sparkles size={11} /> Alignment reflections
          </div>
          <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-1 leading-snug">
            {anyProgress
              ? "Keep going — your co-parent is waiting on this."
              : "Six prompts. Your voice. Your child."}
          </h3>
          <p className="text-[0.8125rem] text-[#4B4567] mt-2 leading-relaxed max-w-2xl">
            Pick a subject and answer six short prompts in your own words.
            Once both you and your co-parent finish a subject, a neutral
            Co-Parenting Agreement highlights where you already agree,
            where you differ, and what your child needs next.
          </p>
        </div>
        {!loading && (
          <div
            className="rounded-full bg-white/70 backdrop-blur px-3 py-1.5 text-[0.6875rem] font-bold text-[#3D1A78] shrink-0"
            data-testid="dashboard-alignment-reflections-total"
          >
            {answeredTotal} / {promptTotal} answered
          </div>
        )}
      </div>

      {loading ? (
        <div
          className="mt-4 grid place-items-center py-6 text-[#6E6787]"
          data-testid="dashboard-alignment-reflections-loading"
        >
          <Loader2 size={16} className="animate-spin" />
        </div>
      ) : (
        <div
          className="mt-4 space-y-1"
          data-testid="dashboard-alignment-reflections-list"
        >
          {subjects.map((s) => (
            <SubjectRow key={s.id} subject={s} />
          ))}
        </div>
      )}

      <div className="mt-4 flex items-center gap-3 flex-wrap">
        <Link
          to="/alignment/subjects"
          className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold"
          data-testid="dashboard-alignment-reflections-open-picker"
        >
          Open subject picker <ArrowRight size={14} />
        </Link>
        <Link
          to="/samples/co-parenting"
          className="inline-flex items-center gap-1.5 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-white px-4 py-2 text-sm font-semibold"
          data-testid="dashboard-alignment-reflections-sample-link"
        >
          Preview the sample report
        </Link>
      </div>
    </div>
  );
}
