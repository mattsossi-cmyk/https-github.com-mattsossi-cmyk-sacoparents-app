import React from "react";
import { Link } from "react-router-dom";

// Shown on the results when the parent chose "I'd rather not answer"; points gently to Get Help if a Section 1 item was skipped.
export function DeclinedAnswersNote({ total = 0, section1 = 0, floor = 0 }) {
  if (!total && !floor) return null;
  return (
    <div
      data-testid="results-declined-note"
      className="mb-6 rounded-2xl border border-[#E5E0EE] bg-[#F8F7FC] p-3.5 text-xs text-[#1A1330] leading-relaxed"
    >
      {total > 0 && (
        <p data-testid="results-declined-count">
          You chose <strong>Prefer not to answer</strong> for {total} question{total === 1 ? "" : "s"}. That's okay.
        </p>
      )}
      <p className={total > 0 ? "mt-1.5" : ""} data-testid="results-declined-effect">
        {floor > 0
          ? "Because a question about immediate danger, physical or sexual harm, or harm to your children was skipped, your result is set to at least Level 2."
          : "Skipped questions don't raise your result."}
      </p>
      {section1 > 0 && (
        <p className="mt-1.5" data-testid="results-declined-get-help">
          If some questions were hard to answer, support is available any time.{" "}
          <Link to="/help" className="font-semibold text-[#3D1A78] underline underline-offset-2" data-testid="results-declined-get-help-link">
            Get help
          </Link>
        </p>
      )}
    </div>
  );
}
