import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Award } from "lucide-react";

import { api } from "../../lib/api";
import { downloadPdf } from "../../lib/pdf";
import { AWARDS } from "../../pages/selfJourney/Awards";

const ORDER = ["selfAssessment", "coparenting", "foundation", "journey"];

const fmt = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
};

// Account: the parent's Self Journey awards. Earned ones in colour with their date; the rest greyed out.
export function SelfJourneyAwards() {
  const [awards, setAwards] = useState(null);

  useEffect(() => {
    let live = true;
    api
      .get("/self-journey/me")
      .then(({ data }) => live && setAwards(data.progress?.awards || {}))
      .catch(() => live && setAwards({}));
    return () => {
      live = false;
    };
  }, []);

  if (!awards) return null;
  const earnedCount = ORDER.filter((k) => awards[k]).length;

  return (
    <section className="mt-4 rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5" data-testid="account-awards">
      <div className="flex items-start gap-3">
        <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-[#F5F1FB] text-[#3D1A78]" aria-hidden>
          <Award size={15} />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">My Self Journey awards</h2>
          <p className="text-xs text-[#4B4567] mt-1 leading-relaxed" data-testid="account-awards-count">
            {earnedCount} of {ORDER.length} earned. Only you can see these.
          </p>
        </div>
      </div>

      <ul className="mt-4 grid grid-cols-2 gap-3">
        {ORDER.map((k) => {
          const on = Boolean(awards[k]);
          return (
            <li
              key={k}
              className={`rounded-xl border p-3 text-center ${on ? "border-[#5b3fa0] bg-white" : "border-dashed border-[#d9d3e6] bg-[#faf9fc]"}`}
              data-testid={`account-award-${k}`}
              data-earned={on}
            >
              <img
                src="/images/award-logo.webp"
                alt=""
                className={`mx-auto w-full max-w-[120px] rounded-lg ${on ? "" : "grayscale opacity-40"}`}
              />
              <p className={`mt-2 text-sm font-bold leading-tight ${on ? "text-[#1b2a6b]" : "text-[#8a849a]"}`}>{AWARDS[k].title}</p>
              <p className={`mt-1 text-xs ${on ? "text-[#4B4567]" : "text-[#8a849a]"}`} data-testid={`account-award-${k}-status`}>
                {on ? `Earned ${fmt(awards[k])}` : "Not yet"}
              </p>
            </li>
          );
        })}
      </ul>

      <div className="mt-4 flex flex-wrap gap-2">
        {awards.journey && (
          <button
            type="button"
            onClick={() => downloadPdf("/self-journey/certificate", { filename: "SA_CoParents_Self_Journey_Certificate.pdf" })}
            className="min-h-[44px] px-4 rounded-full bg-[#1f7a4d] text-white text-sm font-bold hover:bg-[#17663f] transition-colors"
            data-testid="account-awards-certificate"
          >
            Download my certificate
          </button>
        )}
        <Link
          to="/self-journey"
          className="min-h-[44px] inline-flex items-center px-4 rounded-full border border-[#5b3fa0] text-[#3D1A78] text-sm font-bold hover:bg-[#F5F1FB] transition-colors"
          data-testid="account-awards-open-journey"
        >
          Open my Self Journey
        </Link>
      </div>
    </section>
  );
}
