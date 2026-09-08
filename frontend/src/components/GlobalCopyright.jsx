import React from "react";

/**
 * GlobalCopyright — appears at the bottom of every page in the app.
 *
 * Mounted once in App.js as a sibling of <Routes /> so it renders
 * beneath whatever page is currently visible. Individual pages
 * therefore never repeat this line themselves. The year is derived
 * from `new Date().getFullYear()` so we don't hand-edit in January.
 */
export default function GlobalCopyright() {
  const year = new Date().getFullYear();
  return (
    <div
      className="w-full border-t border-[#E5E0EE] bg-white/70 py-3 text-center"
      data-testid="global-copyright"
    >
      <span className="text-[11px] text-[#857E9C]">
        © {year} sacoparentsalign.com · All rights reserved.
      </span>
    </div>
  );
}
