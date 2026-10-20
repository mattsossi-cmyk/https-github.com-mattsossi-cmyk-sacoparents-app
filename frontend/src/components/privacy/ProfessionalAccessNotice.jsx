import React from "react";

// Align's own "who can see your information" notice; set REACT_APP_ALIGN_NOTICE_URL when Align gives its address.
export const ALIGN_NOTICE_URL = process.env.REACT_APP_ALIGN_NOTICE_URL;

export function AlignNoticeLink({ testid, className = "" }) {
  return (
    <a
      href={ALIGN_NOTICE_URL}
      target="_blank"
      rel="noopener noreferrer"
      data-testid={testid}
      className={`inline-block font-semibold text-[#3D1A78] underline underline-offset-2 ${className}`}
    >
      Read who can see your information on SACOparentsAlign
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}

// Who can see your information: only sentences that are true now that safety questions live on SACOparentsAlign.
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
      <p>Safety questions are answered privately on SACOparentsAlign, not in this app.</p>
      <p>
        On SACOparentsAlign, your co-parent never sees your answers. The professionals assigned to your case and a small number of SA CoParents
        administrators can, and every view is recorded.
      </p>
      <p>
        Nothing about your answers appears in this app&apos;s reports or documents. They show only whether your safety step is completed or not
        started.
      </p>
      <AlignNoticeLink testid={`${testid}-align-link`} />
    </section>
  );
}
