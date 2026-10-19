import React from "react";
import { Link } from "react-router-dom";

import { ProfessionalAccessNotice } from "../components/privacy/ProfessionalAccessNotice";
import { useAuth } from "../context/AuthContext";
import { useAccessLogLink } from "../lib/useCheckinLink";

// Footer "Who can see my information": the full notice, plus Align's view list for a parent linked to an Align case.
export default function WhoCanSee() {
  const { user } = useAuth();
  const alignList = useAccessLogLink(!!user);
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
        {alignList && (
          <a
            href={alignList}
            target="_blank"
            rel="noopener noreferrer"
            data-testid="who-can-see-align-list-link"
            className="mt-5 inline-flex items-center gap-2 min-h-11 px-4 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2A0F5F] transition-colors"
          >
            Who has looked at my information
            <i className="fa-solid fa-arrow-up-right-from-square text-xs" aria-hidden="true"></i>
          </a>
        )}
      </main>
    </div>
  );
}
