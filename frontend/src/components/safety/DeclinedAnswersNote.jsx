import React from "react";
import { Link } from "react-router-dom";

// Shown on the results when the parent skipped questions; points gently to Get Help if a Section 1 item was skipped.
export function DeclinedAnswersNote({ total = 0, section1 = 0 }) {
  if (!total) return null;
  return (
    <div
      data-testid="results-declined-note"
      className="mb-6 rounded-2xl border border-[#E5E0EE] bg-[#F8F7FC] p-3.5 text-xs text-[#1A1330] leading-relaxed"
    >
      <p data-testid="results-declined-count">
        You skipped {total} question{total === 1 ? "" : "s"}. That's okay. Skipped questions don't change your result.
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
