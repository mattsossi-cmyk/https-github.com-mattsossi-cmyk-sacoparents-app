import React, { useEffect, useRef } from "react";

/**
 * 6-box numeric code input.
 *
 * Behaviour:
 *   - Types a digit → auto-advances to next box.
 *   - Backspace on an empty box → focus + clear previous box.
 *   - Left/Right arrows → move focus.
 *   - Paste (⌘V) of a 6-digit string → distributes across all boxes.
 *   - Rejects non-digits.
 *   - Fires `onChange(fullCode)` on every keystroke.
 *   - Fires `onComplete(fullCode)` once all boxes are filled.
 *
 * Props:
 *   length?: number = 6
 *   value: string
 *   onChange: (val: string) => void
 *   onComplete?: (val: string) => void
 *   disabled?: boolean
 *   autoFocus?: boolean
 *   testidPrefix?: string = "code-input"
 */
export default function CodeInput({
  length = 6,
  value,
  onChange,
  onComplete,
  disabled = false,
  autoFocus = true,
  testidPrefix = "code-input",
}) {
  const refs = useRef([]);
  const digits = Array.from({ length }, (_, i) => value[i] || "");

  useEffect(() => {
    if (autoFocus && refs.current[0]) {
      refs.current[0].focus();
    }
    // Fire once on mount only; changing `autoFocus` mid-life is uncommon.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const updateAt = (idx, digit) => {
    const next = digits.slice();
    next[idx] = digit;
    const joined = next.join("");
    onChange(joined);
    if (joined.length === length && !joined.includes("") && onComplete) {
      onComplete(joined);
    }
  };

  const handleChange = (idx, raw) => {
    const clean = (raw || "").replace(/\D/g, "");
    if (!clean) {
      updateAt(idx, "");
      return;
    }
    // If the user typed / autofilled multiple digits into one box, spread.
    if (clean.length > 1) {
      const spread = clean.slice(0, length - idx).split("");
      const next = digits.slice();
      spread.forEach((d, i) => {
        next[idx + i] = d;
      });
      const joined = next.join("");
      onChange(joined);
      const focusIdx = Math.min(idx + spread.length, length - 1);
      refs.current[focusIdx]?.focus();
      if (joined.length === length && !joined.includes("") && onComplete) {
        onComplete(joined);
      }
      return;
    }
    updateAt(idx, clean);
    if (idx < length - 1) refs.current[idx + 1]?.focus();
  };

  const handleKeyDown = (idx, e) => {
    if (e.key === "Backspace" && !digits[idx] && idx > 0) {
      e.preventDefault();
      const next = digits.slice();
      next[idx - 1] = "";
      onChange(next.join(""));
      refs.current[idx - 1]?.focus();
    } else if (e.key === "ArrowLeft" && idx > 0) {
      e.preventDefault();
      refs.current[idx - 1]?.focus();
    } else if (e.key === "ArrowRight" && idx < length - 1) {
      e.preventDefault();
      refs.current[idx + 1]?.focus();
    }
  };

  const handlePaste = (idx, e) => {
    const pasted = (e.clipboardData?.getData("text") || "").replace(/\D/g, "");
    if (!pasted) return;
    e.preventDefault();
    const spread = pasted.slice(0, length - idx).split("");
    const next = digits.slice();
    spread.forEach((d, i) => {
      next[idx + i] = d;
    });
    const joined = next.join("");
    onChange(joined);
    const focusIdx = Math.min(idx + spread.length, length - 1);
    refs.current[focusIdx]?.focus();
    if (joined.length === length && !joined.includes("") && onComplete) {
      onComplete(joined);
    }
  };

  return (
    <div
      className="flex gap-2 sm:gap-3 justify-center"
      data-testid={`${testidPrefix}-row`}
    >
      {digits.map((d, i) => (
        <input
          key={i}
          ref={(el) => { refs.current[i] = el; }}
          type="text"
          inputMode="numeric"
          autoComplete={i === 0 ? "one-time-code" : "off"}
          maxLength={length}
          disabled={disabled}
          value={d}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
          onPaste={(e) => handlePaste(i, e)}
          onFocus={(e) => e.target.select()}
          className="w-11 h-14 sm:w-12 sm:h-16 text-center text-2xl font-bold rounded-xl border-2 border-[#E5E0EE] bg-white text-[#1A1330] focus:border-[#3D1A78] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/20 disabled:opacity-50 transition-colors"
          data-testid={`${testidPrefix}-${i}`}
          aria-label={`Digit ${i + 1} of ${length}`}
        />
      ))}
    </div>
  );
}
