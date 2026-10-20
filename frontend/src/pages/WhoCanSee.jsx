import React from "react";
import { Link } from "react-router-dom";

import { ProfessionalAccessNotice } from "../components/privacy/ProfessionalAccessNotice";
import { useAccessLogLink } from "../lib/useCheckinLink";

// Placeholder until Align sends the address (REACT_APP_ALIGN_ACCESS_LOG_URL with {case_id}); hidden when unset or not linked.
function AccessLogLink() {
  const href = useAccessLogLink();
  if (!href) return null;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" data-testid="who-can-see-access-log-link"
       className="mt-4 inline-block font-semibold text-[#3D1A78] underline underline-offset-2">
      Who has looked at my information (on SACOparentsAlign)<span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}

// Footer "Who can see my information": the full notice.
export default function WhoCanSee() {
  return (
    <div data-testid="who-can-see-page" className="min-h-screen bg-[#FBFAFE] text-[#1A1330]">
      <header className="max-w-3xl mx-auto px-5 sm:px-6 pt-8 pb-4">
        <Link to="/" data-testid="who-can-see-home-link" className="text-sm font-semibold text-[#3D1A78] hover:underline">
          ← SA CoParents
        </Link>
      </header>
      <main className="max-w-3xl mx-auto px-5 sm:px-6 pb-16">
        <h1 className="font-serif text-4xl sm:text-5xl mt-4 mb-8">Who can see my information</h1>
        <ProfessionalAccessNotice testid="who-can-see-notice" showTitle={false} className="text-[0.9375rem]" />
        <AccessLogLink />
      </main>
    </div>
  );
}
