import React from "react";

/**
 * Lightweight password strength meter.
 * Scoring (0-4):
 *   0 = empty / very weak (<8 chars)
 *   1 = weak (length only)
 *   2 = fair (length + 1 char class)
 *   3 = strong (length + 2 char classes)
 *   4 = excellent (length 12+ with 3+ classes, no obvious pattern)
 *
 * Penalties: all-same-char, all-digits, common patterns (password, qwerty, 123456…).
 *
 * Deliberately dependency-free — zxcvbn is ~400KB.
 */

const COMMON_PATTERNS = /(password|qwerty|admin|letmein|welcome|123456|111111|000000|iloveyou|monkey|dragon|abc123)/i;

export function scorePassword(pw) {
  if (!pw) return { score: 0, label: "Enter a password", classes: 0 };
  const len = pw.length;
  const classes =
    (/[a-z]/.test(pw) ? 1 : 0) +
    (/[A-Z]/.test(pw) ? 1 : 0) +
    (/\d/.test(pw) ? 1 : 0) +
    (/[^a-zA-Z0-9]/.test(pw) ? 1 : 0);

  // Hard floor: <8 chars or a common pattern -> never above 1
  if (len < 8) return { score: 1, label: "Too short", classes };
  if (COMMON_PATTERNS.test(pw)) return { score: 1, label: "Too common", classes };
  if (/^(.)\1+$/.test(pw)) return { score: 1, label: "Repeated character", classes };
  if (/^\d+$/.test(pw)) return { score: 1, label: "Only digits", classes };

  let score = 1;
  if (len >= 8 && classes >= 2) score = 2;
  if (len >= 10 && classes >= 3) score = 3;
  if (len >= 12 && classes >= 3) score = 4;

  const labels = ["", "Weak", "Fair", "Strong", "Excellent"];
  return { score, label: labels[score], classes };
}

const BAR_COLORS = {
  0: "bg-[#E5E0EE]",
  1: "bg-[#D14A2D]",
  2: "bg-[#D89A2D]",
  3: "bg-[#3D9D6E]",
  4: "bg-[#2DB5B5]",
};
const TEXT_COLORS = {
  0: "text-[#6E6787]",
  1: "text-[#B03A20]",
  2: "text-[#965231]",
  3: "text-[#2A7A52]",
  4: "text-[#0E7A7A]",
};

export default function PasswordStrengthMeter({ password, testid }) {
  const { score, label } = scorePassword(password);
  return (
    <div className="mt-2" data-testid={testid || "password-strength-meter"}>
      <div className="flex gap-1 h-1.5">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className={`flex-1 rounded-full transition-colors ${
              i <= score ? BAR_COLORS[score] : "bg-[#E5E0EE]"
            }`}
          />
        ))}
      </div>
      <div
        className={`text-[0.6875rem] uppercase tracking-[0.12em] font-medium mt-1.5 ${TEXT_COLORS[score]}`}
        data-testid={`${testid || "password-strength-meter"}-label`}
      >
        {label}
      </div>
    </div>
  );
}
