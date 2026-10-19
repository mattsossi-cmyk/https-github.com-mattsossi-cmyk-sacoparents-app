import React from "react";
import { Link } from "react-router-dom";

// Professional Access Notice, full version: only the sentences that are true for this app (checked 2026-10-19).
export function ProfessionalAccessNotice({ testid = "professional-access-notice", className = "", showTitle = true }) {
  return (
    <section
      data-testid={testid}
      aria-labelledby={showTitle ? `${testid}-title` : undefined}
      className={`rounded-xl border border-purple-200 bg-[#F5F1FB] px-3.5 py-3 text-[0.8125rem] leading-relaxed text-[#2A0F5F] space-y-2 ${className}`}
    >
      {showTitle && (
        <h3 id={`${testid}-title`} className="font-bold text-sm">
          <i className="fa-solid fa-user-shield mr-1.5" aria-hidden="true"></i>Who can see your information
        </h3>
      )}
      <p>Your co-parent never sees your answers. Nothing you write in the safety questions is ever shown to them.</p>
      <p>Texas law requires anyone who suspects child abuse or neglect to report it.</p>
      <p>Every question can be skipped, and you can stop at any time.</p>
      <Link
        to="/privacy-notice"
        target="_blank"
        rel="noopener noreferrer"
        data-testid={`${testid}-privacy-link`}
        className="inline-block font-semibold text-[#3D1A78] underline underline-offset-2"
      >
        Read the full privacy notice
      </Link>
    </section>
  );
}
