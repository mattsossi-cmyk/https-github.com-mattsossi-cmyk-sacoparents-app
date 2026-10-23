/**
 * SA CoParents — Journey Guide avatar
 * The SA CoParents logo inside a slowly rotating ring of brand colors.
 *
 * Props
 *  - size        px diameter (default 40)
 *  - logoSrc     URL of the SA CoParents logo (square icon, SVG or transparent PNG).
 *                Falls back to an "SA" monogram until the real logo is supplied.
 *  - calm        true on the safety page: soft purple ring, no rotation
 *  - speaking    true while the guide is replying: ring spins faster
 *  - decorative  true when a visible label sits next to it (hides it from screen readers)
 *  - label       accessible name when not decorative
 */

import React from "react";

export default function GuideAvatar({
  size = 40,
  logoSrc,
  calm = false,
  speaking = false,
  decorative = false,
  label = "SA CoParents Journey Guide",
  testid,
}) {
  const classes = ["sj-avatar", calm ? "is-calm" : "", speaking && !calm ? "is-speaking" : ""]
    .filter(Boolean)
    .join(" ");

  const a11y = decorative ? { "aria-hidden": true } : { role: "img", "aria-label": label };

  return (
    <span className={classes} style={{ "--sj-avatar-size": `${size}px` }} data-testid={testid} {...a11y}>
      <span className="sj-avatar-ring" />
      <span className="sj-avatar-core">
        {logoSrc ? <img src={logoSrc} alt="" /> : <span className="sj-avatar-mark">SA</span>}
      </span>
    </span>
  );
}
