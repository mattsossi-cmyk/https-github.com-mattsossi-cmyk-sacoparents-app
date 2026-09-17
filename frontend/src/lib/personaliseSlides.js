/**
 * personaliseSlides — iter201.
 *
 * Pure function (no React, no side effects) that reorders the
 * DashboardSlideshow slides based on the parent's most-recent
 * situation choice + whether they've linked a court-ordered case.
 *
 * The base order is the recommended co-parenting sequence (Assess
 * → Child → Relationship → Communicate → Foundation). We only
 * rotate ONE slide to the front — never hide slides — so a Path B
 * parent still sees the full journey, just starting at a stage
 * that matches where they are.
 *
 * Rules:
 *   1. Court-ordered parents (linked a case) start with Foundation
 *      Statement — they've already committed to alignment work; the
 *      Foundation Statement is the anchor they'll come back to.
 *   2. Situation "safety" or "high-conflict" → start with
 *      "Assess family situation" (already default) — clarity + a
 *      private read before anything else.
 *   3. Situation "special-needs" → start with "Identify child's
 *      needs" — child-specific needs are the driving concern.
 *   4. Situation "mediation" → start with "Strengthen communication"
 *      — mediation prep is communication-heavy.
 *   5. Situation "cooperate" / "difficult" / unknown → default order.
 *
 * Kept intentionally small: rotate-to-front, no hiding, no shuffling.
 * A future iteration can hide slides based on completion, but that
 * couples with progress state — decoupled here on purpose.
 */

/** Rotate the entry with matching `key` to index 0, preserving the
 * relative order of the other slides. Idempotent when the target is
 * already at index 0. No-op if the key isn't in the list.
 */
export function rotateToFront(slides, targetKey) {
  if (!targetKey) return slides;
  const idx = slides.findIndex((s) => s.key === targetKey);
  if (idx <= 0) return slides;
  const copy = slides.slice();
  const [target] = copy.splice(idx, 1);
  copy.unshift(target);
  return copy;
}

export function personaliseSlides(baseSlides, { courtOrdered, situation } = {}) {
  // Court-ordered wins — a parent who's linked a case has committed
  // to alignment work; anchor them at Foundation Statement.
  if (courtOrdered) return rotateToFront(baseSlides, "foundation");

  switch (situation) {
    case "special-needs":
      return rotateToFront(baseSlides, "child-needs");
    case "mediation":
      return rotateToFront(baseSlides, "communication");
    // safety / high-conflict / cooperate / difficult all default to
    // "Assess your family situation" first — same as base order.
    case "safety":
    case "high-conflict":
    case "cooperate":
    case "difficult":
    default:
      return baseSlides;
  }
}
