/**
 * SplitSuggestion.jsx — inline sub-component of CostSplitterPanel that
 * offers three neutral splitting suggestions once both parents have
 * logged expenses.
 *
 * Modes:
 *   1. 50/50 even        — each parent covers 50% of combined total.
 *   2. Income-weighted   — parents enter each other's monthly gross
 *                          income; share = parent's income / combined.
 *   3. Custom %          — parent picks their own share (0-100%).
 *
 * Output: a single "balance line" — "You've paid $X toward your $Y
 * share — co-parent owes you $Z" (or vice versa when the sign flips).
 *
 * Non-adjudicative guardrails:
 *   - Every suggestion is captioned "This is a suggestion, not an
 *     order. Take it to your mediator."
 *   - No LLM. Deterministic math only.
 *   - Income values are stored ONLY in localStorage — never sent to
 *     the server, never shown to the co-parent. Removes at any time
 *     with "Clear inputs".
 *   - When the parent has no co-parent linked, the mode selector still
 *     renders but the balance area shows an inline hint instead of a
 *     misleading zero.
 */
import React, { useEffect, useMemo, useState } from "react";
import { Info, Percent, RotateCcw, Scale, Wallet } from "lucide-react";

const STORAGE_KEY = "sacoparents.costSplitter.split";

/**
 * Read the caller's saved split preferences from localStorage. Exposed
 * so sibling components (like the PDF download button) can build query
 * params without lifting state up.
 */
export function loadSplitPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { mode: "even", selfIncome: 0, coparentIncome: 0, customSelfPct: 50 };
    const parsed = JSON.parse(raw);
    return {
      mode: parsed.mode || "even",
      selfIncome: Number(parsed.selfIncome) || 0,
      coparentIncome: Number(parsed.coparentIncome) || 0,
      customSelfPct: Number.isFinite(Number(parsed.customSelfPct))
        ? Number(parsed.customSelfPct)
        : 50,
    };
  } catch {
    return { mode: "even", selfIncome: 0, coparentIncome: 0, customSelfPct: 50 };
  }
}

function formatUSD(cents) {
  return ((cents || 0) / 100).toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function loadPrefs() {
  return loadSplitPrefs();
}

function savePrefs(prefs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    /* localStorage unavailable — non-fatal */
  }
}

export default function SplitSuggestion({
  selfCents,
  coparentCents,
  coparentName,
  hasCompare,
}) {
  const initial = loadPrefs();
  const [mode, setMode] = useState(initial?.mode || "even");
  const [selfIncome, setSelfIncome] = useState(initial?.selfIncome || 0);
  const [coparentIncome, setCoparentIncome] = useState(
    initial?.coparentIncome || 0,
  );
  const [customSelfPct, setCustomSelfPct] = useState(
    initial?.customSelfPct ?? 50,
  );

  useEffect(() => {
    savePrefs({ mode, selfIncome, coparentIncome, customSelfPct });
  }, [mode, selfIncome, coparentIncome, customSelfPct]);

  const combinedCents = selfCents + coparentCents;

  const selfShareRatio = useMemo(() => {
    if (mode === "even") return 0.5;
    if (mode === "income") {
      const total = selfIncome + coparentIncome;
      if (total <= 0) return 0.5; // fall back to even until both incomes are entered
      return selfIncome / total;
    }
    // custom
    const pct = Math.min(100, Math.max(0, Number(customSelfPct) || 0));
    return pct / 100;
  }, [mode, selfIncome, coparentIncome, customSelfPct]);

  const selfSharePct = Math.round(selfShareRatio * 100);
  const coparentSharePct = 100 - selfSharePct;

  const selfShareCents = Math.round(combinedCents * selfShareRatio);
  const coparentShareCents = combinedCents - selfShareCents;

  // Balance = amount OWED by ME to co-parent (positive) OR owed TO
  // me by co-parent (negative). If I've paid MORE than my share,
  // the co-parent owes me the difference.
  const balanceCents = selfShareCents - selfCents;
  const balanceLabel = (() => {
    if (!hasCompare) {
      return {
        headline: "Link your co-parent to see a suggested balance",
        subline: "Add your co-parent's email above so we can pair the two ledgers.",
        tone: "muted",
      };
    }
    if (combinedCents === 0) {
      return {
        headline: "Log some expenses to see a split",
        subline: "No costs are logged yet on either side.",
        tone: "muted",
      };
    }
    if (mode === "income" && selfIncome + coparentIncome <= 0) {
      return {
        headline: "Enter both monthly incomes to weight the split",
        subline: "Values stay in your browser — we never send them to the server.",
        tone: "muted",
      };
    }
    const abs = Math.abs(balanceCents);
    if (abs < 100) {
      return {
        headline: "You're roughly square",
        subline: `Your share is ${formatUSD(selfShareCents)} — you've paid ${formatUSD(selfCents)}.`,
        tone: "even",
      };
    }
    if (balanceCents > 0) {
      return {
        headline: `You still owe ${formatUSD(balanceCents)}`,
        subline: `Your ${selfSharePct}% share is ${formatUSD(selfShareCents)} — you've paid ${formatUSD(selfCents)}.`,
        tone: "self-owes",
      };
    }
    return {
      headline: `${coparentName || "Your co-parent"} owes you ${formatUSD(abs)}`,
      subline: `Your ${selfSharePct}% share is ${formatUSD(selfShareCents)} — you've paid ${formatUSD(selfCents)}.`,
      tone: "coparent-owes",
    };
  })();

  const TONE_CLASSES = {
    "self-owes": "bg-[#FFF6EA] border-[#E6D8C1] text-[#5A3C10]",
    "coparent-owes": "bg-[#F1F9F4] border-[#C7E5D3] text-[#0F5638]",
    even: "bg-[#F5F1FB] border-[#D6CFE8] text-[#3D1A78]",
    muted: "bg-[#FAF8FD] border-[#EFECF6] text-[#4B4567]",
  };
  const balanceClass = TONE_CLASSES[balanceLabel.tone] || TONE_CLASSES.muted;

  const clearInputs = () => {
    setSelfIncome(0);
    setCoparentIncome(0);
    setCustomSelfPct(50);
  };

  return (
    <div
      className="mt-5 rounded-2xl border border-[#D6CFE8] bg-white p-4"
      data-testid="split-suggestion"
    >
      <div className="flex items-start gap-3 mb-3">
        <Scale size={18} className="text-[#3D1A78] shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-serif text-lg text-[#1A1330] leading-tight">
            Suggested split
          </h3>
          <p className="text-[12px] text-[#4B4567] mt-0.5 leading-snug">
            A neutral starting point. This is a suggestion, not an order — take it to your mediator.
          </p>
        </div>
      </div>

      {/* Mode selector */}
      <div
        role="tablist"
        aria-label="Split mode"
        className="flex flex-wrap gap-2 mb-3"
        data-testid="split-suggestion-modes"
      >
        {[
          { key: "even", label: "50/50 even", icon: Percent },
          { key: "income", label: "Income-weighted", icon: Wallet },
          { key: "custom", label: "Custom %", icon: Scale },
        ].map(({ key, label, icon: Icon }) => {
          const active = mode === key;
          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setMode(key)}
              data-testid={`split-suggestion-mode-${key}`}
              data-selected={active}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                active
                  ? "bg-[#3D1A78] border-[#3D1A78] text-white"
                  : "bg-white border-[#D6CFE8] text-[#3D1A78] hover:bg-[#F5F1FB]"
              }`}
            >
              <Icon size={12} strokeWidth={2.4} />
              {label}
            </button>
          );
        })}
      </div>

      {/* Mode-specific inputs */}
      {mode === "income" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
          <label className="text-sm">
            <span className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] block mb-1">
              Your monthly income
            </span>
            <input
              type="number"
              inputMode="decimal"
              min="0"
              step="100"
              value={selfIncome || ""}
              onChange={(e) => setSelfIncome(Number(e.target.value) || 0)}
              placeholder="4500"
              data-testid="split-suggestion-input-self-income"
              className="w-full rounded-xl border border-[#D6CFE8] bg-white px-3 py-2 text-sm focus:outline-none focus:border-[#3D1A78]"
            />
          </label>
          <label className="text-sm">
            <span className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] block mb-1">
              {coparentName ? `${coparentName}'s` : "Co-parent's"} monthly income
            </span>
            <input
              type="number"
              inputMode="decimal"
              min="0"
              step="100"
              value={coparentIncome || ""}
              onChange={(e) => setCoparentIncome(Number(e.target.value) || 0)}
              placeholder="5500"
              data-testid="split-suggestion-input-coparent-income"
              className="w-full rounded-xl border border-[#D6CFE8] bg-white px-3 py-2 text-sm focus:outline-none focus:border-[#3D1A78]"
            />
          </label>
        </div>
      )}

      {mode === "custom" && (
        <div className="mb-3">
          <label className="text-sm">
            <span className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] block mb-1">
              Your share ({customSelfPct}% · co-parent {100 - customSelfPct}%)
            </span>
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={customSelfPct}
              onChange={(e) => setCustomSelfPct(Number(e.target.value))}
              data-testid="split-suggestion-input-custom-pct"
              aria-label="Your share percentage"
              className="w-full accent-[#3D1A78]"
            />
          </label>
        </div>
      )}

      {/* Balance line */}
      <div
        className={`rounded-xl border p-4 ${balanceClass}`}
        data-testid="split-suggestion-balance"
        data-tone={balanceLabel.tone}
      >
        <div className="font-serif text-lg leading-tight">
          {balanceLabel.headline}
        </div>
        <p className="text-[12px] mt-1 leading-snug opacity-90">
          {balanceLabel.subline}
        </p>
        {hasCompare && combinedCents > 0 && (
          <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
            <div className="rounded-lg bg-white/60 px-2 py-1.5">
              <div className="uppercase tracking-[0.14em] text-[9px] font-bold">You</div>
              <div className="font-serif text-sm">
                {formatUSD(selfShareCents)} <span className="text-[10px] opacity-70">({selfSharePct}%)</span>
              </div>
            </div>
            <div className="rounded-lg bg-white/60 px-2 py-1.5">
              <div className="uppercase tracking-[0.14em] text-[9px] font-bold">
                {coparentName || "Co-parent"}
              </div>
              <div className="font-serif text-sm">
                {formatUSD(coparentShareCents)} <span className="text-[10px] opacity-70">({coparentSharePct}%)</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {(mode === "income" || mode === "custom") && (
        <div className="mt-3 flex flex-wrap items-center gap-3 justify-between">
          <p className="text-[11px] text-[#4B4567] inline-flex items-start gap-1.5 max-w-md leading-snug">
            <Info size={12} className="mt-0.5 shrink-0" />
            Values stay in your browser only — we never send them to
            the server or your co-parent.
          </p>
          <button
            type="button"
            onClick={clearInputs}
            className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] hover:text-[#2A0F5F] rounded-full border border-[#D6CFE8] px-3 py-1.5 hover:bg-[#F5F1FB]"
            data-testid="split-suggestion-clear"
          >
            <RotateCcw size={12} /> Clear inputs
          </button>
        </div>
      )}
    </div>
  );
}
