/**
 * Shared band-color helpers for the Special Needs Deep Dive reports.
 *
 * Both the Psychological and Educational Deep Dive reports render score
 * bands as pill badges and progress bars. Centralising the class strings
 * here removes 4x nested-ternary blocks per file and keeps colour tokens
 * in one place if the design system evolves.
 *
 * Bands come from the backend scoring: "high" | "moderate" | "low" |
 * anything-else (rendered as the neutral "not enough info" style).
 */

const PILL_CLASSES = {
  high: "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
  moderate: "bg-[#FFF6E5] text-[#8A5B00] border-[#F0D9A8]",
  low: "bg-[#F8D7D7] text-[#B02A2A] border-[#EFB4B4]",
};
const PILL_FALLBACK = "bg-[#F1EEF7] text-[#4B4567] border-[#E5E0EE]";

const BAR_CLASSES = {
  high: "bg-[#1F5C3B]",
  moderate: "bg-[#8A5B00]",
  low: "bg-[#B02A2A]",
};
const BAR_FALLBACK = "bg-[#D6CFE8]";

export function bandPillClass(band) {
  return PILL_CLASSES[band] || PILL_FALLBACK;
}

export function bandBarClass(band) {
  return BAR_CLASSES[band] || BAR_FALLBACK;
}
