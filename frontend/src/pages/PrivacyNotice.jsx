import React, { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";

import { PrivacyNoticeContent } from "./privacyNotice/PrivacyNoticeContent";

// Public Privacy Notice (no sign-in). /privacy, /privacy-policy and /confidentiality redirect here.
export default function PrivacyNotice() {
  const { hash } = useLocation();
  useEffect(() => {
    if (!hash) return window.scrollTo(0, 0);
    const el = document.getElementById(decodeURIComponent(hash.slice(1)));
    el?.scrollIntoView({ block: "start" });
  }, [hash]);
  return (
    <div data-testid="privacy-notice-page" className="min-h-screen bg-[#FBFAFE] text-[#1A1330]">
      <header className="max-w-3xl mx-auto px-5 sm:px-6 pt-8 pb-4">
        <Link to="/" data-testid="privacy-notice-home-link" className="text-sm font-semibold text-[#3D1A78] hover:underline">
          ← SA CoParents
        </Link>
      </header>
      <main className="max-w-3xl mx-auto px-5 sm:px-6 pb-16 text-[15px] leading-relaxed">
        <PrivacyNoticeContent />
      </main>
    </div>
  );
}
