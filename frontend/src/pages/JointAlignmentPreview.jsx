/**
 * JointAlignmentPreview — on-screen "did we agree?" preview shown
 * BETWEEN comparison-consent and release-consent on a Joint
 * Alignment case. Consumes:
 *
 *   GET  /api/joint-alignment/cases/{case_id}/consent-status
 *   GET  /api/joint-alignment/cases/{case_id}/preview
 *
 * Never displays any raw content — only agreement flags per topic.
 * Explicit "nothing has been shared yet" banner so the parent
 * understands this is a private review step.
 */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft, ShieldCheck, Loader2, CheckCircle2, MinusCircle,
  Circle, AlertTriangle,
} from "lucide-react";

import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const ALIGNMENT_META = {
  agree: {
    label: "You agree",
    icon: CheckCircle2,
    cls: "text-[#186142] bg-[#E1F3E8] border-[#B7DEC6]",
  },
  differ: {
    label: "You differ",
    icon: MinusCircle,
    cls: "text-[#8A5B00] bg-[#FFF6E5] border-[#F0D9A1]",
  },
  incomplete: {
    label: "Not both completed",
    icon: Circle,
    cls: "text-[#5C5471] bg-[#F1EEF4] border-[#DED8E5]",
  },
};

function CountPill({ count, label, tone }) {
  return (
    <div
      className={`rounded-2xl border px-4 py-3 flex-1 min-w-[110px] ${tone}`}
      data-testid={`preview-count-${label.toLowerCase()}`}
    >
      <div className="text-2xl font-serif leading-none">{count}</div>
      <div className="text-[11px] uppercase tracking-[0.14em] font-semibold mt-1">
        {label}
      </div>
    </div>
  );
}

export default function JointAlignmentPreview() {
  const { caseId } = useParams();
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [errorDetail, setErrorDetail] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await api.get(`/joint-alignment/cases/${caseId}/preview`);
        if (!cancelled) setPreview(r.data);
      } catch (err) {
        logError("joint-alignment preview load failed", err);
        if (!cancelled) {
          const status = err?.response?.status;
          const detail = err?.response?.data?.detail;
          if (status === 403) setError("You cannot view this preview yet.");
          else if (status === 409) setError("Preview isn't ready.");
          else if (status === 404) setError("Case not found.");
          else setError("Couldn't load the preview.");
          setErrorDetail(typeof detail === "string" ? detail : null);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [caseId]);

  const topics = preview?.topics || [];
  const summary = preview?.summary || {};

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10" data-testid="joint-alignment-preview-page">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="preview-back-link"
        >
          <ArrowLeft size={14} /> Back to dashboard
        </Link>
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
          <ShieldCheck size={12} /> Private review
        </div>
        <h1
          className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight mt-1"
          data-testid="preview-title"
        >
          A quick look at where you two land
        </h1>
        <p className="text-[#4B4567] mt-3 leading-relaxed max-w-2xl">
          This is an agreement-flag-only preview. Neither of your
          answers is visible on this page — you only see whether each
          topic reads as an <strong>agree</strong>, a{" "}
          <strong>differ</strong>, or a section one of you didn&rsquo;t
          finish. This preview is private to the two of you.
        </p>

        <div
          className="mt-6 rounded-2xl border border-[#D6CFE8] bg-[#F5F1FB] p-4 text-[13px] text-[#3D1A78]"
          data-testid="preview-not-shared-banner"
        >
          <div className="font-semibold flex items-center gap-1.5 mb-1">
            <ShieldCheck size={14} /> Nothing is shared with anyone else yet
          </div>
          You are inside the private compare step. Releasing the full
          Joint Alignment Report to a named professional is a{" "}
          <em>separate</em> action that requires both of you to record
          release consent afterward.
        </div>

        {!preview && !error && (
          <div className="mt-8 text-center text-[#857E9C]" data-testid="preview-loading">
            <Loader2 className="animate-spin inline mr-2" size={16} />
            Loading your preview…
          </div>
        )}

        {error && (
          <div
            className="mt-8 rounded-2xl border border-[#F5D0C5] bg-[#FCE3DC] text-[#9A3A23] px-5 py-4"
            role="alert"
            data-testid="preview-error"
          >
            <div className="flex items-start gap-2">
              <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <div className="font-semibold text-sm">{error}</div>
                {errorDetail && (
                  <div className="text-[12px] mt-1 leading-relaxed">
                    {errorDetail}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {preview && (
          <>
            <div className="mt-6 flex flex-wrap gap-3" data-testid="preview-summary">
              <CountPill
                count={summary.agreed || 0} label="Agreed"
                tone="text-[#186142] bg-[#E1F3E8] border-[#B7DEC6]"
              />
              <CountPill
                count={summary.differed || 0} label="Differed"
                tone="text-[#8A5B00] bg-[#FFF6E5] border-[#F0D9A1]"
              />
              <CountPill
                count={summary.incomplete || 0} label="Incomplete"
                tone="text-[#5C5471] bg-[#F1EEF4] border-[#DED8E5]"
              />
            </div>

            <div className="mt-6 rounded-2xl border border-[#E5E0EE] bg-white overflow-hidden">
              <div className="px-5 py-3 border-b border-[#EEE8F7] bg-[#FAF8FD]">
                <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
                  Topic-by-topic
                </div>
              </div>
              {topics.length === 0 ? (
                <div className="p-6 text-center text-[13px] text-[#857E9C]" data-testid="preview-empty">
                  Neither of you produced content for this case yet.
                </div>
              ) : (
                <ul data-testid="preview-topics-list">
                  {topics.map((t) => {
                    const meta = ALIGNMENT_META[t.alignment] || ALIGNMENT_META.incomplete;
                    const Icon = meta.icon;
                    return (
                      <li
                        key={t.topic_key}
                        className="flex items-center justify-between gap-3 px-5 py-3 border-b border-[#EEE8F7] last:border-b-0"
                        data-testid={`preview-topic-${t.topic_key}`}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-semibold text-[#1A1330]">
                            {t.topic_label}
                          </div>
                          {t.alignment === "incomplete" && (
                            <div className="text-[11px] text-[#857E9C] mt-0.5">
                              {t.parent_a_completed ? "Parent A ✓" : "Parent A —"}
                              {" · "}
                              {t.parent_b_completed ? "Parent B ✓" : "Parent B —"}
                            </div>
                          )}
                        </div>
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold ${meta.cls}`}
                          data-testid={`preview-topic-${t.topic_key}-flag`}
                        >
                          <Icon size={11} />
                          {meta.label}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#D6CFE8] hover:bg-[#F5F1FB] text-[#3D1A78] px-4 py-2 text-sm font-semibold"
                data-testid="preview-close"
              >
                <ArrowLeft size={14} /> Close preview
              </Link>
            </div>

            <div
              className="mt-8 rounded-2xl bg-[#F5F1FB] border border-[#D6CFE8] p-4 text-[12px] text-[#3D1A78] leading-relaxed"
              data-testid="preview-legal-note"
            >
              <div className="font-semibold flex items-center gap-1.5 mb-1">
                <ShieldCheck size={12} /> How this compare works
              </div>
              {preview.preview_notice}
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
