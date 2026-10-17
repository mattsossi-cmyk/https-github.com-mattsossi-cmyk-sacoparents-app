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
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, ShieldCheck, Loader2, CheckCircle2,
  MinusCircle, Circle, AlertTriangle, Send, X,
} from "lucide-react";
import { toast } from "sonner";

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
      <div className="text-[0.6875rem] uppercase tracking-[0.14em] font-semibold mt-1">
        {label}
      </div>
    </div>
  );
}

/**
 * Return the co-parent's already-recorded release-consent
 * professional_name (if any) so we can prefill it into the modal.
 * When multiple parents match the caller's email we defer to
 * whichever row is NOT the caller — this is best-effort UX and
 * relies on the endpoint returning both parents' shapes.
 */
function pickCoparentProfessionalName(statusData) {
  const parents = statusData?.parents || [];
  const named = parents.find(
    (p) => p?.release?.professional_name && !p?.release?.revoked_at,
  );
  return named?.release?.professional_name || null;
}

function anyReleased(statusData) {
  // Terminal-state check — `released_at` is set once execute-release
  // has fired. Persists across page refresh so the parent doesn't
  // see the "Continue to release consent" CTA reappear after a
  // successful release earlier in the day.
  return !!(statusData && statusData.released_at);
}

export default function JointAlignmentPreview() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const [preview, setPreview] = useState(null);
  const [consentStatus, setConsentStatus] = useState(null);
  const [error, setError] = useState(null);
  const [errorDetail, setErrorDetail] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [profName, setProfName] = useState("");
  const [profNameLocked, setProfNameLocked] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [releaseState, setReleaseState] = useState(null);
  // ↑ one of null | "awaiting_coparent" | "released"

  const loadAll = async () => {
    try {
      const [prevRes, statusRes] = await Promise.all([
        api.get(`/joint-alignment/cases/${caseId}/preview`),
        api.get(`/joint-alignment/cases/${caseId}/consent-status`),
      ]);
      setPreview(prevRes.data);
      setConsentStatus(statusRes.data || null);
      // Seed the modal from co-parent's already-recorded release name
      // (recommended prefill so the two parents agree on the same
      // professional without retyping).
      const coparentName = pickCoparentProfessionalName(statusRes.data);
      if (coparentName) {
        setProfName(coparentName);
        setProfNameLocked(true);
      }
      // If the case is already released, surface the terminal banner.
      if (statusRes.data?.release_eligible && anyReleased(statusRes.data)) {
        setReleaseState("released");
      }
    } catch (err) {
      logError("joint-alignment preview load failed", err);
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 403) setError("You cannot view this preview yet.");
      else if (status === 409) setError("Preview isn't ready.");
      else if (status === 404) setError("Case not found.");
      else setError("Couldn't load the preview.");
      setErrorDetail(typeof detail === "string" ? detail : null);
    }
  };

  useEffect(() => { loadAll(); /* eslint-disable-next-line */ }, [caseId]);

  const handleSubmitRelease = async () => {
    if (!profName.trim()) {
      toast.error("Please enter the professional's name.");
      return;
    }
    if (!consentChecked) {
      toast.error("You need to check the authorization box.");
      return;
    }
    setSubmitting(true);
    try {
      const r = await api.post(
        `/joint-alignment/cases/${caseId}/release-consent`,
        { consented: true, professional_name: profName.trim() },
      );
      const eligibleNow = !!r.data?.release_eligible;

      if (eligibleNow) {
        // Both parents on the same page — trigger the actual release.
        try {
          await api.post(
            `/joint-alignment/cases/${caseId}/execute-release`,
          );
          setReleaseState("released");
          toast.success(
            "Both parents have released. Awaiting SA CoParents to hand off.",
          );
          // Small delay so the terminal banner is visible before we
          // whisk the parent to their share console.
          setTimeout(() => navigate("/shared-with-professionals"), 3200);
        } catch (execErr) {
          logError("execute-release failed", execErr);
          setReleaseState("released_pending");
          toast.error(
            "Consent recorded, but SA CoParents couldn't complete "
            + "the automatic handoff. It will be retried shortly.",
          );
        }
      } else {
        setReleaseState("awaiting_coparent");
        toast.success(
          "Your release consent is recorded. Waiting on your co-parent.",
        );
      }
      setModalOpen(false);
      await loadAll();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      logError("release-consent failed", err);
      toast.error(
        typeof detail === "string" ? detail : "Couldn't record consent.",
      );
    } finally {
      setSubmitting(false);
    }
  };

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
        <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
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
          className="mt-6 rounded-2xl border border-[#D6CFE8] bg-[#F5F1FB] p-4 text-[0.8125rem] text-[#3D1A78]"
          data-testid="preview-not-shared-banner"
        >
          <div className="font-semibold flex items-center gap-1.5 mb-1">
            <ShieldCheck size={14} /> Nothing is shared with anyone else yet
          </div>
          You are inside the private compare step. Releasing the full
          Co-Parenting Agreement to a named professional is a{" "}
          <em>separate</em> action that requires both of you to record
          release consent afterward.
        </div>

        {!preview && !error && (
          <div className="mt-8 text-center text-[#6E6787]" data-testid="preview-loading">
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
                  <div className="text-[0.75rem] mt-1 leading-relaxed">
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
                <div className="text-[0.6875rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
                  Topic-by-topic
                </div>
              </div>
              {topics.length === 0 ? (
                <div className="p-6 text-center text-[0.8125rem] text-[#6E6787]" data-testid="preview-empty">
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
                            <div className="text-[0.6875rem] text-[#6E6787] mt-0.5">
                              {t.parent_a_completed ? "Parent A ✓" : "Parent A —"}
                              {" · "}
                              {t.parent_b_completed ? "Parent B ✓" : "Parent B —"}
                            </div>
                          )}
                        </div>
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[0.6875rem] font-semibold ${meta.cls}`}
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
              {!releaseState && (
                <button
                  type="button"
                  onClick={() => setModalOpen(true)}
                  className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold"
                  data-testid="preview-continue-release"
                >
                  Continue to release consent
                  <ArrowRight size={14} />
                </button>
              )}
            </div>

            {releaseState === "awaiting_coparent" && (
              <div
                className="mt-6 rounded-2xl border border-[#D6CFE8] bg-[#F5F1FB] p-4 text-[0.8125rem] text-[#3D1A78]"
                data-testid="preview-awaiting-coparent"
              >
                <div className="font-semibold flex items-center gap-1.5 mb-1">
                  <ShieldCheck size={14} /> Your release consent is recorded
                </div>
                We&rsquo;re waiting on your co-parent to record their own
                release consent before the report is handed off. Nothing has
                left your household yet.
              </div>
            )}
            {(releaseState === "released" || releaseState === "released_pending") && (
              <div
                className="mt-6 rounded-2xl border border-[#B7DEC6] bg-[#E1F3E8] p-4 text-[0.8125rem] text-[#186142]"
                data-testid="preview-released-banner"
              >
                <div className="font-semibold flex items-center gap-1.5 mb-1">
                  <CheckCircle2 size={14} /> Both parents have released
                </div>
                Awaiting SA CoParents to hand off the completed Joint
                Alignment Report. You&rsquo;ll be redirected to your Shared
                with Professionals page in a moment.
              </div>
            )}

            <div
              className="mt-8 rounded-2xl bg-[#F5F1FB] border border-[#D6CFE8] p-4 text-[0.75rem] text-[#3D1A78] leading-relaxed"
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

      {modalOpen && (
        <ReleaseConsentModal
          consentText={consentStatus?.consent_texts?.release_template
            || "I authorize the completed Co-Parenting Agreement to be made available to {professional_name} through SA CoParents Align."}
          profName={profName}
          setProfName={setProfName}
          profNameLocked={profNameLocked}
          consentChecked={consentChecked}
          setConsentChecked={setConsentChecked}
          submitting={submitting}
          onClose={() => setModalOpen(false)}
          onSubmit={handleSubmitRelease}
        />
      )}
    </AppShell>
  );
}

function ReleaseConsentModal({
  consentText, profName, setProfName, profNameLocked,
  consentChecked, setConsentChecked, submitting, onClose, onSubmit,
}) {
  const filledText = consentText.replace(
    "{professional_name}",
    profName.trim() || "(the professional you name below)",
  );
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="release-modal-title"
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 backdrop-blur-sm px-4 py-6"
      data-testid="release-consent-modal"
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) onClose();
      }}
    >
      <div className="bg-white rounded-3xl max-w-xl w-full max-h-[92vh] overflow-y-auto shadow-2xl">
        <div className="flex items-start justify-between gap-3 px-6 pt-6">
          <div className="min-w-0">
            <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Release consent
            </div>
            <h2
              id="release-modal-title"
              className="font-serif text-2xl text-[#1A1330] leading-tight mt-1"
              data-testid="release-modal-title"
            >
              Authorize release to a named professional
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            aria-label="Close"
            className="text-[#6E6787] hover:text-[#1A1330] p-1 rounded-full flex-shrink-0"
            data-testid="release-modal-close"
          >
            <X size={16} />
          </button>
        </div>

        <div className="px-6 py-4">
          <label
            className="text-[0.6875rem] uppercase tracking-[0.16em] font-bold text-[#3D1A78] block"
            htmlFor="release-professional-name"
          >
            Professional&rsquo;s name
          </label>
          <input
            id="release-professional-name"
            type="text"
            value={profName}
            onChange={(e) => setProfName(e.target.value)}
            readOnly={profNameLocked}
            className="mt-1 w-full rounded-xl border border-[#D6CFE8] bg-white px-3 py-2 text-sm focus:border-[#3D1A78] focus:outline-none"
            placeholder="e.g. Adele van Wyk"
            data-testid="release-modal-professional-name"
          />
          {profNameLocked && (
            <p className="text-[0.6875rem] text-[#6E6787] mt-1">
              Your co-parent already named this professional. Both consents
              must target the same person before release fires.
            </p>
          )}

          <div className="mt-4 rounded-2xl border border-[#D6CFE8] bg-[#FAF8FD] p-4 text-[12.5px] text-[#4B4567] leading-relaxed"
            data-testid="release-modal-consent-text"
          >
            {filledText}
          </div>

          <label
            className="mt-4 flex items-start gap-2 text-[0.8125rem] text-[#1A1330]"
            data-testid="release-modal-consent-label"
          >
            <input
              type="checkbox"
              checked={consentChecked}
              onChange={(e) => setConsentChecked(e.target.checked)}
              className="mt-0.5"
              data-testid="release-modal-consent-checkbox"
            />
            <span>
              I authorize release of the completed Co-Parenting Agreement to{" "}
              <strong>{profName.trim() || "the professional named above"}</strong>.
            </span>
          </label>
        </div>

        <div className="px-6 py-4 border-t border-[#EEE8F7] flex flex-wrap gap-2 justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#D6CFE8] hover:bg-[#F5F1FB] text-[#3D1A78] px-4 py-2 text-sm font-semibold disabled:opacity-50"
            data-testid="release-modal-cancel"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onSubmit}
            disabled={submitting || !profName.trim() || !consentChecked}
            className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold disabled:opacity-50"
            data-testid="release-modal-submit"
          >
            {submitting ? (
              <><Loader2 size={13} className="animate-spin" /> Recording…</>
            ) : (
              <><Send size={13} /> Record my release consent</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
