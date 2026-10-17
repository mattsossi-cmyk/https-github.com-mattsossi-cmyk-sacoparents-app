/**
 * ReviewerPanelCard — Transparency component on the Methodology page.
 * Lists independent expert reviewers who have signed off on the Family
 * Violence and Communication Safety Screen. Falls back to a clear
 * "pending" state when no reviewers have been added.
 *
 * Also surfaces a "Download reviewer packet" link for the app operator
 * to hand to a candidate reviewer.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Users, Download, Loader2, ShieldCheck, Clock, Send, Settings } from "lucide-react";
import { toast } from "sonner";
import { api, API } from "../lib/api";
import ReviewerSendDialog from "./ReviewerSendDialog";

const ROLE_LABEL = {
  dv_advocate:            "Domestic-violence advocate",
  forensic_psychologist:  "Forensic psychologist",
  family_law_attorney:    "Family-law attorney (Texas)",
  clinician:              "Licensed clinician",
  other:                  "Other",
};

function StatusPill({ status }) {
  if (status === "reviewed") {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.625rem] font-bold bg-[#E6F4EC] text-[#1F5C3B] ring-1 ring-[#1F5C3B]/25"
        data-testid="reviewer-panel-status-reviewed"
      >
        <ShieldCheck size={10} /> Reviewed
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.625rem] font-bold bg-[#F0EAFB] text-[#3D1A78] ring-1 ring-[#3D1A78]/25"
      data-testid="reviewer-panel-status-pending"
    >
      <Clock size={10} /> Review pending
    </span>
  );
}

export default function ReviewerPanelCard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isOperator, setIsOperator] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [sending, setSending] = useState(false);
  const [sends, setSends] = useState([]);

  const loadSends = async () => {
    try {
      const r = await api.get("/reviewer-panel/sends");
      setSends(r.data.sends || []);
    } catch { /* not operator or 403 */ }
  };

  useEffect(() => {
    (async () => {
      try {
        const [r, op] = await Promise.all([
          api.get("/reviewer-panel"),
          api.get("/reviewer-panel/is-operator").catch(() => ({ data: { is_operator: false } })),
        ]);
        setData(r.data);
        setIsOperator(Boolean(op.data?.is_operator));
        if (op.data?.is_operator) await loadSends();
      } catch {
        setData({ status: "pending", reviewers: [] });
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const sendPacket = async (payload) => {
    setSending(true);
    try {
      const r = await api.post("/reviewer-panel/send", payload);
      toast.success(`Reviewer packet sent to ${r.data.emailed_to}.`);
      setDialogOpen(false);
      await loadSends();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const status = err?.response?.status;
      if (status === 403) {
        toast.error(detail || "Only the site operator can send.");
      } else if (status === 503) {
        toast.error(detail || "Email service isn't available right now.");
      } else {
        toast.error(detail || "Couldn't send. Please try again.");
      }
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <aside
        className="not-prose rounded-3xl border border-[#E5E0EE] bg-white p-5 my-6 inline-flex items-center gap-2 text-sm text-[#4B4567]"
        data-testid="reviewer-panel-loading"
      >
        <Loader2 size={14} className="animate-spin" /> Loading reviewer panel…
      </aside>
    );
  }

  const reviewers = data?.reviewers || [];
  const packetUrl = `${API}/reviewer-panel/packet`;

  return (
    <aside
      className="not-prose rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 my-6"
      data-testid="reviewer-panel"
      aria-labelledby="reviewer-panel-title"
    >
      <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
        <div>
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
            Independent expert review
          </div>
          <h3
            id="reviewer-panel-title"
            className="font-serif text-xl text-[#1A1330]"
          >
            Who has reviewed this screen
          </h3>
        </div>
        <StatusPill status={data?.status || "pending"} />
      </div>

      <p className="text-sm text-[#4B4567] leading-relaxed mb-4">
        Because a family-violence screen carries weight, we publish the
        names, credentials, roles, and review dates of every independent
        expert who has evaluated the current questions and scoring rules.
        No reviewer&rsquo;s name appears here unless they have signed off
        in writing and agreed to be listed.
      </p>

      {reviewers.length === 0 ? (
        <div
          className="rounded-2xl border-2 border-dashed border-[#E5E0EE] bg-[#FAF8FE] p-5"
          data-testid="reviewer-panel-empty"
        >
          <div className="flex items-start gap-2 mb-2">
            <Users size={16} className="text-[#3D1A78] shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-[#1A1330]">
                Independent expert review is pending
              </div>
              <p className="text-sm text-[#4B4567] mt-1 leading-relaxed">
                We are seeking sign-off from three professionals: a
                domestic-violence advocate, a forensic psychologist, and
                a Texas family-law attorney. Their credentials, roles,
                and review dates will appear here immediately upon
                approval.
              </p>
            </div>
          </div>
        </div>
      ) : (
        <ul className="space-y-3" data-testid="reviewer-panel-list">
          {reviewers.map((r, i) => (
            <li
              key={`${r.name}-${r.review_date}-${i}`}
              className="rounded-2xl border border-[#E5E0EE] bg-white p-4"
              data-testid={`reviewer-item-${i}`}
            >
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <div className="font-bold text-[#1A1330]">{r.name}</div>
                  <div className="text-[0.6875rem] uppercase tracking-[0.15em] text-[#3D1A78] font-bold mt-0.5">
                    {ROLE_LABEL[r.role] || r.role}
                    {r.org ? ` · ${r.org}` : ""}
                  </div>
                </div>
                <div className="text-xs text-[#4B4567]">
                  Reviewed {r.review_date}
                </div>
              </div>
              {r.review_scope && (
                <div className="mt-2 text-[0.75rem] text-[#4B4567]">
                  <strong>Scope:</strong> {r.review_scope}
                </div>
              )}
              {r.attestation && (
                <blockquote className="mt-2 pl-3 border-l-2 border-[#3D1A78]/30 text-sm text-[#1A1330] italic">
                  "{r.attestation}"
                </blockquote>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 pt-3 border-t border-[#EFECF6] flex items-center justify-between gap-3 flex-wrap">
        <div className="text-[0.6875rem] text-[#6A5799]">
          Screen version: <strong>{data?.review_scope_version || "v1.0"}</strong>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <a
            href={packetUrl}
            data-testid="reviewer-panel-download-packet"
            className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] font-semibold hover:underline"
          >
            <Download size={12} /> Download reviewer packet (PDF)
          </a>
          {isOperator && (
            <Link
              to="/admin/reviewers"
              data-testid="reviewer-panel-manage-link"
              className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] font-semibold hover:underline"
            >
              <Settings size={12} /> Manage reviewers
            </Link>
          )}
          {isOperator && (
            <button
              type="button"
              onClick={() => setDialogOpen(true)}
              data-testid="reviewer-panel-open-send"
              className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-3 py-1.5 text-xs font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
            >
              <Send size={12} /> Send packet to a reviewer
            </button>
          )}
        </div>
      </div>

      {isOperator && sends.length > 0 && (
        <div
          className="mt-4 rounded-2xl border border-[#E5E0EE] bg-[#FAF8FE] p-3"
          data-testid="reviewer-panel-sends-log"
        >
          <div className="text-[0.625rem] uppercase tracking-[0.2em] font-bold text-[#3D1A78] mb-2">
            Operator only · Recently sent to
          </div>
          <ul className="space-y-1.5 text-[0.75rem]">
            {sends.slice(0, 5).map((s, i) => (
              <li
                key={`${s.recipient_email}-${s.sent_at}-${i}`}
                className="flex items-center justify-between gap-2 flex-wrap"
                data-testid={`reviewer-send-log-${i}`}
              >
                <span className="text-[#1A1330]">
                  <strong>{s.recipient_name || s.recipient_email}</strong>
                  <span className="text-[#4B4567]"> · {s.recipient_email} · {s.recipient_role}</span>
                </span>
                <span className="text-[#6A5799]">
                  {s.sent_at ? new Date(s.sent_at).toLocaleString() : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <ReviewerSendDialog
        open={dialogOpen}
        onClose={() => { if (!sending) setDialogOpen(false); }}
        onSend={sendPacket}
        sending={sending}
      />
    </aside>
  );
}
