import React from "react";

/**
 * GlobalCopyright — appears at the bottom of every page in the app.
 *
 * Mounted once in App.js as a sibling of <Routes /> so it renders
 * beneath whatever page is currently visible. Individual pages
 * therefore never repeat this line themselves.
 */
export default function GlobalCopyright() {
  return (
    <div
      className="w-full border-t border-[#E5E0EE] bg-white/70 py-3 text-center"
      data-testid="global-copyright"
    >
      <span className="text-[11px] text-[#857E9C]">
        © 2026 sacoparentsalign.com · All rights reserved.
      </span>
    </div>
  );
}
