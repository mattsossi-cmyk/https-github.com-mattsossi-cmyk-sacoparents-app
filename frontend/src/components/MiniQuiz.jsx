/**
 * MiniQuiz — "Which scenario matches your family?" inline on the
 * public /samples/joint-alignment-preview page.
 *
 * The 6 prompts, 3 answers per prompt, and outcome legend are kept
 * in EXACT LOCKSTEP with the PDF renderer at
 * `/app/backend/joint_alignment_sample_pdf.py::QUIZ_PROMPTS` — the
 * founder's guardrail is "PDFs and frontend strings must remain in
 * exact lockstep". If the PDF copy changes, this constant must
 * change identically in the same commit.
 *
 * Behaviour:
 *  * User taps one answer per prompt. Answers are single-select and
 *    persisted only in local component state (never sent to the
 *    server — this is a rough self-check, not a saved reflection).
 *  * Once at least one answer is picked, a live tally + outcome
 *    banner appears at the bottom, matching the PDF's "Your rough
 *    result" legend verbatim.
 *  * "Reset" clears the whole quiz. "Copy summary" copies the
 *    counts + outcome sentence to the clipboard so a parent can
 *    email it to their co-parent alongside the sample PDF.
 */
import React, { useMemo, useState } from "react";
import { RefreshCcw, ClipboardCheck, Check, Circle } from "lucide-react";

// ---- Copy — LOCKSTEP with joint_alignment_sample_pdf.QUIZ_PROMPTS ----
// The `...` ASCII ellipsis on each prompt is intentional — the PDF
// module uses the same three-dot form (fpdf2 has to Latin-1 encode
// so a Unicode `…` would decompose). Keep the strings identical.
const QUIZ_PROMPTS = [
  {
    prompt: "1. School mornings at your two homes look...",
    answers: {
      agree: "Roughly the same routine at both places.",
      differ: "Meaningfully different from home to home.",
      incomplete: "We haven't compared notes on it yet.",
    },
  },
  {
    prompt: "2. Weeknight screen-time rules for the child...",
    answers: {
      agree: "Both parents apply the same limit.",
      differ: "Each parent has their own limit.",
      incomplete: "One or both of us hasn't set one.",
    },
  },
  {
    prompt: "3. Extracurricular activities (frequency and cost)...",
    answers: {
      agree: "We agree on the current schedule.",
      differ: "We see the schedule differently.",
      incomplete: "It's an open question at the moment.",
    },
  },
  {
    prompt: "4. Handovers on a typical week...",
    answers: {
      agree: "Same preferred time and place for both of us.",
      differ: "Different preferred windows.",
      incomplete: "We handle it week-by-week.",
    },
  },
  {
    prompt: "5. Winter holidays this year...",
    answers: {
      agree: "Same view on how to split them.",
      differ: "Different plans in mind.",
      incomplete: "We haven't talked about it yet.",
    },
  },
  {
    prompt: "6. Healthcare / big-picture decisions...",
    answers: {
      agree: "We usually make them together.",
      differ: "We each decide separately in our own home.",
      incomplete: "We haven't tested this yet.",
    },
  },
];

// Three answer tones — colours match the sample topic pills at the
// top of the same page so a visitor's eye connects "green agree" here
// with "agreed" up there.
const TONE = {
  agree: {
    label: "Same / together",
    ring: "border-[#B0E1C3]",
    activeRing: "border-[#1E6A42]",
    activeBg: "bg-[#E6F5EC]",
    activeText: "text-[#1E6A42]",
  },
  differ: {
    label: "Different",
    ring: "border-[#F0D9A1]",
    activeRing: "border-[#AA6A00]",
    activeBg: "bg-[#FCEFD7]",
    activeText: "text-[#8A5500]",
  },
  incomplete: {
    label: "Haven't tested it",
    ring: "border-[#D6CFE8]",
    activeRing: "border-[#4B4567]",
    activeBg: "bg-[#EEEAF5]",
    activeText: "text-[#4B4567]",
  },
};


function outcomeFor(counts) {
  // Match the PDF legend exactly. Returns null when nothing answered.
  const total = counts.agree + counts.differ + counts.incomplete;
  if (total === 0) return null;
  const maxKey = ["agree", "differ", "incomplete"].reduce(
    (best, k) => (counts[k] > counts[best] ? k : best),
    "agree"
  );
  if (maxKey === "agree") {
    return {
      tone: "agree",
      title: "Closest to the 'Mostly agreed' sample",
      body:
        "A short reflection each may be enough to keep everyone aligned. Start with SA CoParents on your own if you like the sound of that.",
    };
  }
  if (maxKey === "differ") {
    return {
      tone: "differ",
      title: "Closest to the 'Mostly differed' sample",
      body:
        "A professional-guided joint session is likely to add the most value — a mediator, attorney, or therapist can turn the differences into a shared plan.",
    };
  }
  return {
    tone: "incomplete",
    title: "Your first job is finishing the reflection together",
    body:
      "There's not enough shared ground yet to score either way. Complete a reflection each so you can actually see where you stand.",
  };
}


export default function MiniQuiz() {
  // answers = { promptIdx: "agree" | "differ" | "incomplete" }
  const [answers, setAnswers] = useState({});

  const counts = useMemo(() => {
    const acc = { agree: 0, differ: 0, incomplete: 0 };
    for (const k of Object.values(answers)) {
      if (acc[k] !== undefined) acc[k] += 1;
    }
    return acc;
  }, [answers]);

  const outcome = outcomeFor(counts);
  const answered = Object.keys(answers).length;

  const pick = (idx, key) => setAnswers((prev) => ({ ...prev, [idx]: key }));
  const reset = () => setAnswers({});

  const copySummary = async () => {
    const lines = [
      "Which scenario matches your family? — quick self-check",
      `Answered: ${answered}/${QUIZ_PROMPTS.length}`,
      `- Same/together: ${counts.agree}`,
      `- Different: ${counts.differ}`,
      `- Haven't tested it: ${counts.incomplete}`,
    ];
    if (outcome) {
      lines.push("");
      lines.push(outcome.title + ".");
      lines.push(outcome.body);
    }
    try {
      await navigator.clipboard.writeText(lines.join("\n"));
    } catch (_) {
      // Clipboard blocked (older browsers / http). Fallback: alert the text.
      window.prompt("Copy your summary:", lines.join("\n"));
    }
  };

  return (
    <section
      className="mt-10 rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-7"
      data-testid="sample-preview-mini-quiz"
      aria-labelledby="mini-quiz-heading"
    >
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Rough self-check · not a diagnosis
          </div>
          <h2
            id="mini-quiz-heading"
            className="font-serif text-2xl sm:text-3xl text-[#1A1330] mt-1 leading-tight"
          >
            Which scenario matches your family?
          </h2>
        </div>
        <div className="text-xs text-[#4B4567]">
          {answered}/{QUIZ_PROMPTS.length} answered
        </div>
      </div>

      <p className="text-sm text-[#4B4567] mt-3 leading-relaxed max-w-3xl">
        Six prompts. For each one, tap the answer that fits your family
        today. A rough outcome banner appears below once you've started.
        Nothing you tap is sent to a server or saved.
      </p>

      <ol className="mt-5 space-y-5" data-testid="sample-preview-mini-quiz-prompts">
        {QUIZ_PROMPTS.map((q, idx) => {
          const picked = answers[idx];
          return (
            <li
              key={idx}
              className="rounded-2xl border border-[#EEE8F7] bg-[#FBF8FE] p-4"
              data-testid={`sample-preview-mini-quiz-prompt-${idx + 1}`}
            >
              <div className="text-[15px] font-semibold text-[#1A1330]">
                {q.prompt}
              </div>
              <div
                className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-2"
                role="radiogroup"
                aria-label={q.prompt}
              >
                {["agree", "differ", "incomplete"].map((key) => {
                  const cfg = TONE[key];
                  const isActive = picked === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      role="radio"
                      aria-checked={isActive}
                      onClick={() => pick(idx, key)}
                      className={
                        "text-left text-[0.8125rem] font-medium leading-snug rounded-xl border-2 transition-colors px-3 py-2.5 " +
                        (isActive
                          ? `${cfg.activeBg} ${cfg.activeText} ${cfg.activeRing}`
                          : `bg-white text-[#1A1330] ${cfg.ring} hover:bg-[#F5F1FB]`)
                      }
                      data-testid={`sample-preview-mini-quiz-${idx + 1}-${key}`}
                    >
                      <span className="inline-flex items-center gap-1.5">
                        {isActive ? <Check size={12} /> : <Circle size={12} />}
                        <span className="text-[0.625rem] uppercase tracking-[0.16em] font-bold">
                          {cfg.label}
                        </span>
                      </span>
                      <div className="mt-1">{q.answers[key]}</div>
                    </button>
                  );
                })}
              </div>
            </li>
          );
        })}
      </ol>

      {/* Outcome banner */}
      {outcome && (
        <div
          className={
            "mt-6 rounded-2xl border-2 p-4 sm:p-5 " +
            (outcome.tone === "agree"
              ? "border-[#B0E1C3] bg-[#E6F5EC]"
              : outcome.tone === "differ"
              ? "border-[#F0D9A1] bg-[#FCEFD7]"
              : "border-[#D6CFE8] bg-[#EEEAF5]")
          }
          data-testid="sample-preview-mini-quiz-outcome"
        >
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <span
                className="inline-flex items-center rounded-full bg-white/70 text-[#1A1330] text-[0.625rem] font-bold uppercase tracking-[0.18em] px-2.5 py-1"
                data-testid="sample-preview-mini-quiz-tally"
              >
                {counts.agree} same · {counts.differ} different · {counts.incomplete} untested
              </span>
            </div>
          </div>
          <div className="mt-3 font-serif text-lg text-[#1A1330] leading-snug">
            {outcome.title}
          </div>
          <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
            {outcome.body}
          </p>
        </div>
      )}

      {/* Controls */}
      {answered > 0 && (
        <div className="mt-5 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={reset}
            className="inline-flex items-center gap-1.5 rounded-full border border-[#D6CFE8] text-[#3D1A78] hover:bg-[#F5F1FB] px-4 py-2 text-xs font-semibold"
            data-testid="sample-preview-mini-quiz-reset"
          >
            <RefreshCcw size={12} /> Reset quiz
          </button>
          <button
            type="button"
            onClick={copySummary}
            className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-xs font-semibold"
            data-testid="sample-preview-mini-quiz-copy"
          >
            <ClipboardCheck size={12} /> Copy summary
          </button>
        </div>
      )}

      <p className="mt-4 text-[0.6875rem] text-[#6E6787] italic leading-relaxed">
        Educational and organizational self-check — not a diagnosis, not a
        court submission, and never a judgment about which parent is right.
      </p>
    </section>
  );
}
