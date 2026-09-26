import React, { useEffect, useState } from "react";

/**
 * SafetyPlanBuilder — a small optional stepper embedded in the flagged
 * safety-card. Captures the five classic Safety-Plan elements the
 * National DV Hotline recommends:
 *   1. Safe place I can go
 *   2. Trusted person I can call (name + phone)
 *   3. Essentials to grab if I need to leave
 *   4. Code word to signal danger to a friend/family
 *   5. Tech-safety notes (private device? shared computer?)
 *
 * Kept simple and NEVER required. Saves to localStorage first
 * (offline-first) and syncs to `portal_state.safety_plan` when the
 * parent is signed in. Renders a "Show private summary" panel with a
 * copy-to-clipboard button so the parent can save a screenshot or
 * print the plan and hide the paper somewhere safe.
 *
 * Privacy note surfaced in the UI: the plan is NEVER shared with the
 * co-parent — no joint reports, no share links carry it.
 */
const FIELDS = [
  {
    key: "safe_place",
    label: "Somewhere safe I can go",
    hint: "A friend, family member, shelter, or public place. Address if you have it.",
    placeholder: "e.g. Mom's house — 123 Elm St. Or the library on Main.",
  },
  {
    key: "trusted_contact",
    label: "Someone I can call for help",
    hint: "Name + phone number. Pick a person who's been reliable in the past.",
    placeholder: "e.g. Sarah — 210-555-0101",
  },
  {
    key: "essentials",
    label: "Things to grab if I leave in a hurry",
    hint: "ID, phone charger, meds, cash, kid's essentials, important papers.",
    placeholder: "e.g. Driver's license, kid's inhaler, charger, $60 cash, custody papers",
  },
  {
    key: "code_word",
    label: "A code word or phrase",
    hint: "A short word you'd text/say to a friend or older child that means 'call for help now.'",
    placeholder: "e.g. 'pineapple' — Sarah knows this means call 911",
  },
  {
    key: "tech_notes",
    label: "Tech-safety notes",
    hint: "Shared device? Location tracking on? Browser history? Consider a private/incognito window or a friend's phone.",
    placeholder: "e.g. Home computer is monitored — use library or Sarah's phone",
  },
];

export function SafetyPlanBuilder({ plan, onSave }) {
  const [values, setValues] = useState({});
  const [expanded, setExpanded] = useState(false);
  const [showSummary, setShowSummary] = useState(false);
  const [savedAt, setSavedAt] = useState("");
  const [copyState, setCopyState] = useState("");

  // Hydrate from prop when plan changes (e.g. server pull).
  useEffect(() => {
    if (plan && typeof plan === "object") {
      const seed = {};
      for (const f of FIELDS) {
        if (typeof plan[f.key] === "string") seed[f.key] = plan[f.key];
      }
      setValues(seed);
      if (plan.updated_at) setSavedAt(plan.updated_at);
    }
  }, [plan]);

  const handleChange = (key, val) => {
    setValues((prev) => ({ ...prev, [key]: val }));
  };

  const persist = () => {
    const payload = {};
    for (const f of FIELDS) {
      const v = (values[f.key] || "").trim();
      if (v) payload[f.key] = v.slice(0, 500);
    }
    if (Object.keys(payload).length === 0) return;
    payload.updated_at = new Date().toISOString();
    setSavedAt(payload.updated_at);
    onSave(payload);
  };

  const summaryText = () => {
    const lines = ["My Safety Plan", "---"];
    for (const f of FIELDS) {
      const v = (values[f.key] || "").trim();
      if (v) lines.push(`${f.label}: ${v}`);
    }
    lines.push("---");
    lines.push("DV Hotline: 1-800-799-7233 · Text START to 88788");
    lines.push("Emergency: 911 · Crisis: 988");
    return lines.join("\n");
  };

  const copySummary = async () => {
    const text = summaryText();
    try {
      await navigator.clipboard.writeText(text);
      setCopyState("copied");
    } catch {
      setCopyState("copied");
      window.prompt("Copy your Safety Plan (Ctrl+C / Cmd+C):", text);
    }
    setTimeout(() => setCopyState(""), 3000);
  };

  const hasAnything = FIELDS.some((f) => (values[f.key] || "").trim().length > 0);

  return (
    <div
      data-testid="safety-plan-builder"
      className="border border-purple-200 rounded-xl bg-white overflow-hidden"
    >
      <button
        type="button"
        data-testid="safety-plan-toggle"
        onClick={() => setExpanded((v) => !v)}
        className="w-full p-3 text-left flex justify-between items-center hover:bg-purple-50 transition"
      >
        <div>
          <div className="font-bold text-purple-900 text-[11px] uppercase tracking-wider">
            Optional — Build a private Safety Plan
          </div>
          <div className="text-[10px] text-slate-500 leading-snug mt-0.5">
            Five short prompts. Saved on this device (or your account
            if signed in). <strong>Never shared with your co-parent.</strong>
          </div>
        </div>
        <i
          className={`fa-solid ${
            expanded ? "fa-chevron-up" : "fa-chevron-down"
          } text-purple-700 ml-2`}
          aria-hidden
        ></i>
      </button>

      {expanded && (
        <div className="p-3 space-y-3 border-t border-purple-100 bg-purple-50/40">
          {FIELDS.map((f) => (
            <div key={f.key} data-testid={`safety-plan-field-${f.key}`}>
              <label className="font-semibold text-slate-700 text-[11px] block">
                {f.label}
              </label>
              <p className="text-[10px] text-slate-500 leading-snug mt-0.5 mb-1">
                {f.hint}
              </p>
              <textarea
                rows={2}
                data-testid={`safety-plan-input-${f.key}`}
                value={values[f.key] || ""}
                onChange={(e) => handleChange(f.key, e.target.value)}
                maxLength={500}
                className="w-full p-2 border border-slate-300 rounded-lg text-xs bg-white"
                placeholder={f.placeholder}
              />
            </div>
          ))}

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              data-testid="safety-plan-save-btn"
              onClick={persist}
              disabled={!hasAnything}
              className="flex-1 min-w-[100px] px-3 py-2 bg-purple-800 hover:bg-purple-900 disabled:opacity-40 text-white rounded-lg font-bold text-[11px]"
            >
              <i className="fa-solid fa-floppy-disk mr-1"></i>
              {savedAt ? "Save changes" : "Save my Safety Plan"}
            </button>
            <button
              type="button"
              data-testid="safety-plan-summary-btn"
              onClick={() => setShowSummary((v) => !v)}
              disabled={!hasAnything}
              className="px-3 py-2 border border-purple-300 text-purple-800 rounded-lg font-bold text-[11px] disabled:opacity-40"
            >
              {showSummary ? "Hide summary" : "Show private summary"}
            </button>
          </div>

          {savedAt && (
            <p
              data-testid="safety-plan-saved-at"
              className="text-[10px] text-emerald-700 font-semibold"
            >
              <i className="fa-solid fa-check-circle mr-1"></i>
              Saved · {new Date(savedAt).toLocaleString()}
            </p>
          )}

          {showSummary && hasAnything && (
            <div
              data-testid="safety-plan-summary"
              className="p-3 bg-white border border-slate-200 rounded-lg text-[11px] text-slate-800 space-y-1"
            >
              <div className="flex justify-between items-center border-b border-slate-100 pb-1">
                <span className="font-bold text-purple-900 text-[11px] uppercase tracking-wider">
                  My Safety Plan
                </span>
                <button
                  type="button"
                  data-testid="safety-plan-copy-btn"
                  onClick={copySummary}
                  className="text-[10px] px-2 py-0.5 bg-emerald-700 text-white rounded font-bold"
                >
                  {copyState === "copied" ? "Copied!" : "Copy to clipboard"}
                </button>
              </div>
              {FIELDS.map((f) => {
                const v = (values[f.key] || "").trim();
                if (!v) return null;
                return (
                  <div key={f.key} className="leading-snug">
                    <span className="font-semibold text-slate-700">
                      {f.label}:
                    </span>{" "}
                    <span className="text-slate-800">{v}</span>
                  </div>
                );
              })}
              <div className="pt-1 border-t border-slate-100 text-[10px] text-slate-500">
                DV Hotline: 1-800-799-7233 · Text START to 88788 · Emergency: 911 · Crisis: 988
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
