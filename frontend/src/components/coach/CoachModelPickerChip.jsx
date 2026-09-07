/**
 * CoachModelPickerChip — visible tone toggle on the /coach header.
 *
 * Two-state pill that lets the parent flip between:
 *   • "Sharper" — GPT (app-wide primary in most environments)
 *   • "Warmer"  — Claude (the empathetic Sonnet 4.5 voice)
 *
 * The choice persists in localStorage under `sacoparents.coach.model` so
 * the tone survives page reloads and stays consistent across a
 * conversation. `null` means "use whatever the server default is" —
 * we deliberately don't pin the parent to one model until they touch
 * the toggle so a Universal Key balance/default flip lands seamlessly.
 */
import { useCallback, useEffect, useState } from "react";
import { Sparkles, Heart } from "lucide-react";

const STORAGE_KEY = "sacoparents.coach.model";

export function useCoachModelPreference() {
  const [preference, setPreferenceState] = useState(() => {
    try {
      const v = window.localStorage.getItem(STORAGE_KEY);
      return v === "gpt" || v === "claude" ? v : null;
    } catch {
      return null;
    }
  });

  const setPreference = useCallback((next) => {
    setPreferenceState(next);
    try {
      if (next === "gpt" || next === "claude") {
        window.localStorage.setItem(STORAGE_KEY, next);
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      /* localStorage disabled — the state stays session-only. */
    }
  }, []);

  return [preference, setPreference];
}

export default function CoachModelPickerChip({ value, onChange }) {
  // `value === null` means "use server default" — we highlight neither
  // side to signal that the parent hasn't picked yet. Once they tap,
  // we pin the choice explicitly.
  const activeGpt = value === "gpt";
  const activeClaude = value === "claude";

  return (
    <div
      className="inline-flex items-center gap-1 rounded-full border border-[#E5E0EE] bg-white p-1 text-xs font-semibold shadow-sm"
      role="group"
      aria-label="Coach voice"
      data-testid="coach-model-chip"
    >
      <button
        type="button"
        onClick={() => onChange(activeGpt ? null : "gpt")}
        aria-pressed={activeGpt}
        title="Sharper, more structured replies (GPT)."
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 transition-colors ${
          activeGpt
            ? "bg-[#3D1A78] text-white"
            : "text-[#4B4567] hover:text-[#3D1A78]"
        }`}
        data-testid="coach-model-chip-gpt"
      >
        <Sparkles size={12} /> Sharper
      </button>
      <button
        type="button"
        onClick={() => onChange(activeClaude ? null : "claude")}
        aria-pressed={activeClaude}
        title="Warmer, more empathetic replies (Claude)."
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 transition-colors ${
          activeClaude
            ? "bg-[#3D1A78] text-white"
            : "text-[#4B4567] hover:text-[#3D1A78]"
        }`}
        data-testid="coach-model-chip-claude"
      >
        <Heart size={12} /> Warmer
      </button>
    </div>
  );
}
