import React from "react";
import { Link } from "react-router-dom";

// Professional Access Notice, full version. Wording matches Align version 2026-10-19.1; change both apps together.
export const NOTICE_VERSION = "2026-10-19.1";

const SEES = [
  "Your individual answers, including anything you write in your own words",
  "Which questions you skipped (they see that you skipped, not why)",
  "The safe ways to contact you, if you choose to share them",
  "A concern level based on your answers, which helps your professional decide what support to offer",
  "Whether you have started, finished, or declined this step",
];

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
      <p>Your co-parent never sees your answers. Nothing you write in the safety check-in is ever shown to them.</p>
      <div>
        <p>The professionals assigned to your case can see:</p>
        <ul className="list-disc pl-5 mt-1 space-y-0.5">
          {SEES.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
      </div>
      <p>A small number of SA CoParents administrators can also open your answers, only to check that the service is working safely.</p>
      <p>
        Your answers are kept on a protected screen. Each time anyone opens it, that is recorded, and you can see who looked and when under &ldquo;Who
        has looked at my information.&rdquo;
      </p>
      <p>
        Court documents and reports show only whether this step was completed, not started, or declined. They never show your answers, what you
        wrote, or your concern level.
      </p>
      <p>
        If your answers suggest a child has been abused or neglected, the professional who reads them must report it. Texas law requires anyone who
        suspects child abuse or neglect to report it.
      </p>
      <p>
        Every question can be skipped, and you can stop at any time. If you skip a question about immediate danger, physical or sexual harm, or harm
        to your children, your professional will be asked to check in with you.
      </p>
      <Link
        to="/privacy-notice"
        target="_blank"
        rel="noopener noreferrer"
        data-testid={`${testid}-privacy-link`}
        className="inline-block font-semibold text-[#3D1A78] underline underline-offset-2"
      >
        Read the full privacy notification
      </Link>
    </section>
  );
}
