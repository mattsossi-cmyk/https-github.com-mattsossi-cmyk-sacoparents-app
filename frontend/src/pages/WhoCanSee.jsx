import React from "react";
import { Link } from "react-router-dom";

import { ProfessionalAccessNotice } from "../components/privacy/ProfessionalAccessNotice";

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
      </main>
    </div>
  );
}
