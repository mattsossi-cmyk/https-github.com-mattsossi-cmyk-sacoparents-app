/**
 * VerifyPathway — public page reached by scanning the QR in the footer
 * of any Dispute Resolution Pathway Report PDF. It asks the backend
 * whether the given pathway id was issued by SA CoParents.
 *
 * Privacy: same stance as VerifyBriefing — the public response is
 * intentionally minimal. It confirms issued yes/no, the issue date,
 * and whether the report was a single-parent preview or a full
 * two-parent report. NEVER leaks pathway recommendations, hard-lock
 * reasons, or parent identities.
 */
import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle2, ShieldAlert, Loader2, MessageSquare, Send } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const ROLES = [
  { key: "mediator",                    label: "Mediator" },
  { key: "parent_facilitator_ad_litem", label: "Parent Facilitator Ad Litem" },
  { key: "trial_court",                 label: "Trial Court" },
  { key: "attorney",                    label: "Family Law Attorney" },
  { key: "therapist",                   label: "Therapist / Counsellor" },
  { key: "other",                       label: "Other" },
];

const ROLE_LABEL = Object.fromEntries(ROLES.map((r) => [r.key, r.label]));

const formatIssuedOn = (iso) => {
  if (!iso) return "";
  try {
    const d = new Date(`${iso}T00:00:00Z`);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(undefined, {
      year: "numeric", month: "long", day: "numeric", timeZone: "UTC",
    });
  } catch {
    return iso;
  }
};

export default function VerifyPathway() {
  const { sig_id: sigId } = useParams();
  const [state, setState] = useState({ loading: true, data: null, error: null });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get(
          `/verify/pathway/${encodeURIComponent(sigId)}`
        );
        if (!cancelled) setState({ loading: false, data: res.data, error: null });
      } catch (err) {
        logError("verify pathway", err);
        if (!cancelled) {
          setState({
            loading: false,
            data: null,
            error:
              err?.response?.data?.detail ||
              "Could not check this pathway report right now.",
          });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [sigId]);

  const issued = !!(state.data && state.data.issued);
  const isDual = !!(state.data && state.data.is_dual_party);

  return (
    <div
      className="min-h-screen bg-[#FCFBFE] flex flex-col items-center px-4 py-12"
      data-testid="verify-pathway-root"
    >
      <div className="w-full max-w-lg">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] underline mb-6"
          data-testid="verify-pathway-back"
        >
          ← SA CoParents
        </Link>

        <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Pathway Report Verification
          </div>
          <h1 className="mt-1 font-serif text-2xl text-[#1A1330]">
            Was this Dispute Resolution Pathway Report issued by SA CoParents?
          </h1>

          {state.loading && (
            <div
              className="mt-6 text-sm text-[#4B4567] inline-flex items-center gap-2"
              data-testid="verify-pathway-loading"
            >
              <Loader2 className="animate-spin" size={14} /> Checking the pathway id…
            </div>
          )}

          {!state.loading && issued && (
            <div
              className="mt-6 rounded-2xl border-2 border-[#B5DFC5] bg-[#F1F9F4] p-4 sm:p-5"
              data-testid="verify-pathway-ok"
            >
              <div className="flex items-start gap-3">
                <CheckCircle2 size={22} className="text-[#1F5C3B] shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold text-[#1F5C3B]">
                    Yes — this pathway report was issued by SA CoParents.
                  </div>
                  <p className="text-xs text-[#1F5C3B] mt-1">
                    Issued on{" "}
                    <span className="font-semibold" data-testid="verify-pathway-date">
                      {formatIssuedOn(state.data.issued_on)}
                    </span>{" "}
                    (UTC).
                  </p>
                  <p className="text-xs text-[#1F5C3B] mt-1"
                    data-testid="verify-pathway-scope">
                    Report scope:{" "}
                    <span className="font-semibold">
                      {isDual
                        ? "Two-parent report (mutual consent via Compare share)"
                        : "Single-parent preview"}
                    </span>
                    .
                  </p>
                </div>
              </div>
              <div className="mt-4 text-[0.625rem] text-[#4B4567]">
                Pathway report ID:{" "}
                <span className="font-mono" data-testid="verify-pathway-id">
                  {state.data.sig_id}
                </span>
              </div>
            </div>
          )}

          {!state.loading && state.data && !issued && (
            <div
              className="mt-6 rounded-2xl border-2 border-[#EFB4B4] bg-[#F8D7D7] p-4 sm:p-5"
              data-testid="verify-pathway-not-issued"
            >
              <div className="flex items-start gap-3">
                <ShieldAlert size={22} className="text-[#B02A2A] shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold text-[#B02A2A]">
                    Not recognised
                  </div>
                  <p className="text-xs text-[#B02A2A] mt-1">
                    This id is not on record as a pathway report issued by
                    SA CoParents. It may have been mistyped, or the QR may
                    have come from a document that was not generated on
                    this platform.
                  </p>
                </div>
              </div>
              <div className="mt-3 text-[0.625rem] text-[#4B4567]">
                Checked id:{" "}
                <span className="font-mono">{state.data.sig_id}</span>
              </div>
            </div>
          )}

          {!state.loading && state.error && (
            <div
              className="mt-6 text-sm text-[#B02A2A]"
              data-testid="verify-pathway-error"
            >
              {state.error}
            </div>
          )}

          {issued && (
            <ReviewerCommentsSection sigId={sigId} />
          )}

          <p className="mt-6 text-[0.6875rem] text-[#4B4567] italic">
            This check only confirms that a pathway report id was issued
            here and when. It does not attest to the truth of any content
            in the report, nor does it constitute a clinical, legal, or
            evidentiary endorsement. SA CoParents pathway reports are
            informational and not legal advice.
          </p>
        </div>
      </div>
    </div>
  );
}


function formatWhen(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}


function ReviewerCommentsSection({ sigId }) {
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    reviewer_name: "",
    reviewer_role: "mediator",
    reviewer_org:  "",
    comment_text:  "",
  });
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get(
          `/verify/pathway/${encodeURIComponent(sigId)}/comments`
        );
        if (!cancelled) {
          setComments(res.data?.comments || []);
          setLoading(false);
        }
      } catch (err) {
        logError("verify pathway comments", err);
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [sigId]);

  const canSubmit =
    form.reviewer_name.trim().length >= 1
    && form.comment_text.trim().length >= 4
    && !sending;

  const submit = async () => {
    if (!canSubmit) return;
    setSending(true);
    try {
      const res = await api.post(
        `/verify/pathway/${encodeURIComponent(sigId)}/comments`,
        {
          reviewer_name: form.reviewer_name.trim(),
          reviewer_role: form.reviewer_role,
          reviewer_org:  form.reviewer_org.trim() || null,
          comment_text:  form.comment_text.trim(),
        },
      );
      const newRow = res.data?.comment;
      if (newRow) setComments((prev) => [newRow, ...prev]);
      setForm({ ...form, comment_text: "" });
      setShowForm(false);
      toast.success("Comment posted. The parent will see it on their dashboard.");
    } catch (err) {
      logError("post pathway comment", err);
      toast.error(err?.response?.data?.detail || "Couldn't post the comment right now.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mt-6" data-testid="verify-pathway-comments-root">
      <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2 inline-flex items-center gap-1.5">
        <MessageSquare size={12} />
        Reviewer comments
      </div>

      {loading && (
        <div className="text-xs text-[#4B4567] inline-flex items-center gap-1.5"
          data-testid="verify-pathway-comments-loading">
          <Loader2 size={12} className="animate-spin" /> Loading comments…
        </div>
      )}

      {!loading && comments.length === 0 && (
        <div className="text-xs text-[#4B4567] italic mb-3"
          data-testid="verify-pathway-comments-empty">
          No comments have been posted on this report yet.
        </div>
      )}

      {!loading && comments.length > 0 && (
        <ul className="space-y-2 mb-3"
          data-testid="verify-pathway-comments-list">
          {comments.map((c) => (
            <li key={c.comment_id}
              className="rounded-2xl border border-[#E5E0EE] bg-white p-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-semibold text-[#1A1330]">
                  {c.reviewer_name}
                </span>
                <span className="text-[0.625rem] uppercase tracking-[0.16em] font-bold text-[#3D1A78] bg-[#F5F1FB] rounded-full px-2 py-0.5">
                  {ROLE_LABEL[c.reviewer_role] || c.reviewer_role}
                </span>
                {c.reviewer_org && (
                  <span className="text-[0.6875rem] text-[#4B4567]">· {c.reviewer_org}</span>
                )}
                <span className="text-[0.6875rem] text-[#6E6787] ml-auto">
                  {formatWhen(c.created_at)}
                </span>
              </div>
              <p className="text-sm text-[#1A1330] mt-2 whitespace-pre-wrap leading-relaxed">
                {c.comment_text}
              </p>
            </li>
          ))}
        </ul>
      )}

      {!showForm && !loading && (
        <button
          type="button"
          onClick={() => setShowForm(true)}
          data-testid="verify-pathway-comment-open"
          className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#3D1A78] text-[#3D1A78] px-4 py-2 text-sm font-semibold hover:bg-[#F5F1FB] transition-colors"
        >
          <MessageSquare size={14} />
          Add a professional comment
        </button>
      )}

      {showForm && (
        <div className="rounded-3xl border border-[#E5E0EE] bg-[#F8F7FC] p-4 space-y-3"
          data-testid="verify-pathway-comment-form">
          <div>
            <label className="block text-[0.6875rem] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Your role
            </label>
            <div className="flex flex-wrap gap-1.5">
              {ROLES.map((r) => (
                <button
                  key={r.key}
                  type="button"
                  onClick={() => setForm({ ...form, reviewer_role: r.key })}
                  data-testid={`verify-pathway-role-${r.key}`}
                  aria-pressed={form.reviewer_role === r.key}
                  className={`text-[0.75rem] px-3 py-1.5 rounded-full border transition ${
                    form.reviewer_role === r.key
                      ? "bg-[#3D1A78] text-white border-[#3D1A78] font-semibold"
                      : "bg-white text-[#4B4567] border-[#E5E0EE] hover:border-[#3D1A78]"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-[0.6875rem] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
                Your name <span aria-hidden="true" className="text-[#9A3A23]">*</span>
              </label>
              <input
                type="text"
                value={form.reviewer_name}
                onChange={(e) => setForm({ ...form, reviewer_name: e.target.value })}
                placeholder="e.g. Jamie Rivera"
                data-testid="verify-pathway-comment-name"
                maxLength={120}
                className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
              />
            </div>
            <div>
              <label className="block text-[0.6875rem] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
                Organisation <span className="text-[#6E6787] font-normal normal-case tracking-normal">· optional</span>
              </label>
              <input
                type="text"
                value={form.reviewer_org}
                onChange={(e) => setForm({ ...form, reviewer_org: e.target.value })}
                placeholder="Firm, agency, or court"
                data-testid="verify-pathway-comment-org"
                maxLength={160}
                className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
              />
            </div>
          </div>

          <div>
            <label className="block text-[0.6875rem] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Comment <span aria-hidden="true" className="text-[#9A3A23]">*</span>
            </label>
            <textarea
              value={form.comment_text}
              onChange={(e) => setForm({ ...form, comment_text: e.target.value })}
              placeholder="Anything you want the parent to know before their next session…"
              rows={4}
              maxLength={4000}
              data-testid="verify-pathway-comment-text"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30 resize-none"
            />
            <p className="text-[0.6875rem] text-[#6E6787] mt-1">
              Comments are permanent and visible to the parent on their
              dashboard. This is not a clinical record or a legal filing.
            </p>
          </div>

          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              disabled={sending}
              data-testid="verify-pathway-comment-cancel"
              className="rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-4 py-2 text-sm font-semibold hover:bg-[#F8F7FC] disabled:opacity-60"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={submit}
              disabled={!canSubmit}
              data-testid="verify-pathway-comment-send"
              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2 text-sm font-semibold disabled:opacity-60"
            >
              {sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
              {sending ? "Posting…" : "Post comment"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
