/**
 * PathwayReviewerCommentsCard — Dashboard card showing the newest
 * reviewer comments left on any Pathway Report the parent has issued.
 *
 * Closes the loop between the mediator (who scans the QR from the
 * emailed PDF and leaves a comment on the public verify page) and the
 * parent (who sees the comment the next time they open the app).
 *
 * Self-hides for parents with no comments on file — otherwise clutters
 * the dashboard for anyone who has never emailed a pathway report.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MessageSquare, ArrowRight } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";


const ROLE_LABEL = {
  mediator:                    "Mediator",
  parent_facilitator_ad_litem: "Parent Facilitator Ad Litem",
  trial_court:                 "Trial Court",
  attorney:                    "Family Law Attorney",
  therapist:                   "Therapist / Counsellor",
  other:                       "Reviewer",
};


function formatWhen(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(undefined, {
      month: "short", day: "numeric", year: "numeric",
    });
  } catch {
    return iso;
  }
}


export default function PathwayReviewerCommentsCard() {
  const [state, setState] = useState({ loading: true, comments: [] });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get("/pathway-report/comments/mine");
        if (!cancelled) {
          setState({ loading: false, comments: data?.comments || [] });
        }
      } catch (err) {
        logError("pathway reviewer comments card", err);
        if (!cancelled) setState({ loading: false, comments: [] });
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (state.loading || state.comments.length === 0) return null;

  // Show up to three newest comments inline; deeper history stays behind
  // the "View all" link on the report page itself.
  const preview = state.comments.slice(0, 3);
  const overflowCount = Math.max(0, state.comments.length - preview.length);

  return (
    <div
      id="pathway-reviewer-comments"
      className="rounded-3xl border border-[#E5E0EE] bg-white p-5"
      data-testid="pathway-reviewer-comments-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="inline-flex items-center gap-2 min-w-0">
          <span className="inline-flex items-center justify-center w-8 h-8 rounded-full shrink-0 bg-[#F0EEF8] text-[#3D1A78]">
            <MessageSquare size={16} />
          </span>
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Reviewer Comments · Pathway Report
            </div>
            <div className="font-serif text-lg text-[#1A1330] leading-snug">
              A professional replied to your pathway report
            </div>
          </div>
        </div>
        <span
          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] uppercase tracking-[0.16em] font-bold bg-[#F0EEF8] text-[#3D1A78] shrink-0"
          data-testid="pathway-reviewer-comments-count"
        >
          {state.comments.length} new
        </span>
      </div>

      <ul className="mt-3 space-y-2"
        data-testid="pathway-reviewer-comments-list">
        {preview.map((c) => (
          <li
            key={c.comment_id}
            className="rounded-2xl border border-[#F0EBF7] bg-[#FCFBFE] p-3"
            data-testid={`pathway-reviewer-comment-${c.comment_id}`}
          >
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-[#1A1330]">
                {c.reviewer_name}
              </span>
              <span className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] bg-[#F5F1FB] rounded-full px-2 py-0.5">
                {ROLE_LABEL[c.reviewer_role] || c.reviewer_role}
              </span>
              {c.reviewer_org && (
                <span className="text-[11px] text-[#4B4567]">· {c.reviewer_org}</span>
              )}
              <span className="text-[11px] text-[#6E6787] ml-auto">
                {formatWhen(c.created_at)}
              </span>
            </div>
            <p className="text-sm text-[#1A1330] mt-1.5 leading-relaxed whitespace-pre-wrap line-clamp-4">
              {c.comment_text}
            </p>
          </li>
        ))}
      </ul>

      {overflowCount > 0 && (
        <p className="text-[11px] text-[#4B4567] italic mt-2"
          data-testid="pathway-reviewer-comments-overflow">
          {overflowCount} older comment{overflowCount === 1 ? "" : "s"} not shown here.
        </p>
      )}

      <div className="mt-4 flex items-center justify-end">
        <Link
          to="/pathway-report"
          className="inline-flex items-center gap-1 text-[11px] font-bold text-[#3D1A78]"
          data-testid="pathway-reviewer-comments-cta"
        >
          Open pathway report <ArrowRight size={12} />
        </Link>
      </div>
    </div>
  );
}
