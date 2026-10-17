import React from "react";
import { Link, useLocation } from "react-router-dom";

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
  // The Quick exit calendar shows no app name or footer.
  if (useLocation().pathname === "/calendar") return null;
  return (
    <div
      className="w-full border-t border-[#E5E0EE] bg-white/70 py-3 text-center"
      data-testid="global-copyright"
    >
      <span className="text-[0.6875rem] text-[#6E6787]">
        © {year} SA CoParents · All rights reserved. ·{" "}
        <Link to="/privacy-notice" data-testid="global-footer-privacy-notice" className="text-[#3D1A78] font-semibold underline underline-offset-2">
          Privacy Notice
        </Link>
        {" "}·{" "}
        <Link to="/help" data-testid="global-footer-get-help" className="text-[#3D1A78] font-semibold underline underline-offset-2">
          Get help
        </Link>
      </span>
    </div>
  );
}
