/**
 * personaliseSlides — iter201 (+ iter202 hides).
 *
 * Pure function (no React, no side effects) that filters + reorders
 * the DashboardSlideshow slides based on the parent's most-recent
 * situation choice + whether they've linked a court-ordered case.
 *
 * The base order is the recommended co-parenting sequence (Assess
 * → Child → Relationship → Communicate → Foundation). We apply two
 * transforms so the opening frame matches where the parent actually
 * is:
 *
 *   Hide rules (iter202):
 *     * Situation "safety" → hide `communication` + `foundation`
 *       (joint-oriented tools are inappropriate when family violence
 *        is present — parent sees Situation · Child Needs ·
 *        Relationship only)
 *     * Court-ordered (case linked) → hide `situation` (Assess your
 *       family situation) — a parent under a court order didn't come
 *       to explore, they came to comply; showing them the
 *       exploratory frame first would be tone-deaf
 *
 *   Rotate-to-front rules:
 *     1. Court-ordered → Foundation Statement first
 *     2. Situation "special-needs" → Identify child's needs first
 *     3. Situation "mediation" → Strengthen communication first
 *     4. Situation "safety" / "high-conflict" / "cooperate" /
 *        "difficult" / unknown → default order (Assess situation
 *        first — or Child Needs if situation slide is hidden)
 *
 *   Edge cases:
 *     * safety + court-ordered simultaneously → hides win in both
 *       axes (result: child-needs + relationship only, no rotation
 *       target left to apply)
 *     * rotation target hidden → no rotation, the filtered list
 *       renders in its natural order
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

/** Iter202 · slide keys to REMOVE from the base list given the
 * parent's situation + court-ordered flag. Exposed so tests + the
 * component can inspect the rule set in isolation.
 */
export function hiddenSlideKeys({ courtOrdered, situation } = {}) {
  const hidden = new Set();
  if (situation === "safety") {
    // Joint-oriented tools shouldn't be surfaced when family violence
    // is present. Keeps Situation · Child Needs · Relationship —
    // enough to guide a parent toward the safety pathway without
    // ever showing "invite the other parent" copy.
    hidden.add("communication");
    hidden.add("foundation");
  }
  if (courtOrdered) {
    // Court-referred parents skipped the "how are you arriving"
    // question by definition — they know why they're here.
    hidden.add("situation");
  }
  return hidden;
}

function _rotationTarget({ courtOrdered, situation }) {
  if (courtOrdered) return "foundation";
  switch (situation) {
    case "special-needs":  return "child-needs";
    case "mediation":      return "communication";
    default:               return null; // fall through to natural order
  }
}

export function personaliseSlides(baseSlides, opts = {}) {
  const hidden = hiddenSlideKeys(opts);
  const filtered = baseSlides.filter((s) => !hidden.has(s.key));
  const target = _rotationTarget(opts);
  // If the intended rotation target was filtered out (e.g. safety +
  // court-ordered both apply → foundation is hidden), skip rotation
  // so the list renders in its natural post-filter order.
  if (target && filtered.some((s) => s.key === target)) {
    return rotateToFront(filtered, target);
  }
  return filtered;
}
