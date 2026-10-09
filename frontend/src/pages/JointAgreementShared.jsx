/**
 * Public Joint Co-Parenting Agreement Draft viewer.
 *
 * Anyone with the signed share link can open this page — no login. The
 * sending parent minted the link from `JointAgreement.jsx` with
 * `POST /api/joint-agreement/{share_id}/share-link`; the backend
 * revalidates the token, revocation state, and both parents' Compare
 * consent on every read.
 *
 * URL pattern: `/joint-agreement/shared/:token`
 */
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Download, Loader2, ShieldCheck, Users, Info, ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { Section } from "../components/joint/JointAgreementSections";
import JointAgreementParentView from "../components/joint/JointAgreementParentView";
import SignedInEscapeHatch from "../components/SignedInEscapeHatch";
import { API } from "../lib/api";
import { logError } from "../lib/logger";


export default function JointAgreementShared() {
  const { token } = useParams();
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!token) {
      setState({ loading: false, data: null, error: "missing-token" });
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${API}/joint-agreement/shared/${encodeURIComponent(token)}`,
        );
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body?.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled) setState({ loading: false, data, error: null });
      } catch (err) {
        logError("shared joint agreement load", err);
        if (!cancelled) {
          setState({
            loading: false, data: null,
            error: err?.message || "load-failed",
          });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [token]);

  const downloadPdf = async () => {
    if (!token) return;
    setDownloading(true);
    try {
      const res = await fetch(
        `${API}/joint-agreement/shared/${encodeURIComponent(token)}/pdf`,
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `joint-coparenting-agreement.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      logError("shared joint agreement pdf", err);
      toast.error("Could not download PDF. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  if (state.loading) {
    return (
      <div
        className="min-h-screen grid place-items-center bg-[#F8F7FC] text-[#4B4567]"
        data-testid="joint-agreement-shared-loading"
      >
        <div className="text-center">
          <Loader2 size={22} className="animate-spin inline-block mr-2" />
          Loading the joint agreement draft…
        </div>
      </div>
    );
  }

  if (state.error || !state.data) {
    const msg = state.error === "missing-token"
      ? "This link is missing a token."
      : (typeof state.error === "string" && state.error.length > 2
          ? state.error
          : "We couldn't open this shared link.");
    return (
      <div
        className="min-h-screen grid place-items-center bg-[#F8F7FC] px-6 py-10"
        data-testid="joint-agreement-shared-error"
      >
        <div className="max-w-lg w-full rounded-3xl border border-[#E5E0EE] bg-white p-8 text-center shadow-sm">
          <h1 className="font-serif text-2xl text-[#1A1330] mb-3">
            Co-Parenting Agreement
          </h1>
          <p className="text-[#4B4567] leading-relaxed mb-5">{msg}</p>
          <p className="text-xs text-[#857E9C]">
            If you were sent this link, please ask the parent who shared
            it to generate a fresh link from their SA CoParents account.
          </p>
        </div>
      </div>
    );
  }

  const d = state.data;
  const parentA = d.parent_a_name || "Parent A";
  const parentB = d.parent_b_name || "Parent B";
  const sharedBy = d.shared_by_name || parentA;
  const summary = d.summary || {};

  return (
    <div
      className="min-h-screen bg-[#F8F7FC]"
      data-testid="joint-agreement-shared-root"
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Signed-in parents landing on their own shared link need a way
            home — public reviewers see nothing. */}
        <SignedInEscapeHatch testid="joint-agreement-shared-signed-in-back" />

        {/* Provenance banner */}
        <div
          className="rounded-3xl border border-[#CFC1EA] bg-[#EFE9F9] p-5 sm:p-6"
          data-testid="joint-agreement-shared-provenance"
        >
          <div className="flex items-start gap-3">
            <div className="shrink-0 h-10 w-10 rounded-full grid place-items-center bg-[#3D1A78] text-white">
              <ExternalLink size={16} />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                Shared with you
              </div>
              <p className="mt-1 text-sm text-[#1A1330] leading-relaxed">
                <strong>{sharedBy}</strong> shared this Co-Parenting
                Agreement with you through SA CoParents. This is a neutral
                alignment map — not a court order or legal advice, and not
                binding unless a court approves it.
              </p>
            </div>
          </div>
        </div>

        {d.sender_note && (
          <div
            className="mt-4 rounded-3xl border-2 border-[#CFC1EA] bg-white p-5 sm:p-6 shadow-sm"
            data-testid="joint-agreement-shared-sender-note"
          >
            <div className="flex items-start gap-3">
              <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-white border-2 border-[#3D1A78] text-[#3D1A78] font-serif text-sm font-bold">
                &ldquo;
              </div>
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
                  A note from {sharedBy}
                </div>
                <p className="text-[15px] text-[#1A1330] leading-relaxed whitespace-pre-wrap">
                  {d.sender_note}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="mt-6 flex items-center justify-between gap-3 flex-wrap">
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              {d.report_subtitle || "Co-Parenting Agreement"}
            </div>
            <h1
              className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-1 leading-tight"
              data-testid="joint-agreement-shared-title"
            >
              {d.report_title}
            </h1>
            <div
              className="mt-2 text-sm text-[#4B4567]"
              data-testid="joint-agreement-shared-parents"
            >
              {parentA} <span className="text-[#857E9C] mx-1">·</span> {parentB}
            </div>
          </div>
          <button
            type="button"
            onClick={downloadPdf}
            disabled={downloading}
            data-testid="joint-agreement-shared-download-pdf"
            className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-4 py-2 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-60"
          >
            {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            Download PDF
          </button>
        </div>

        {/* Draft-for-discussion disclaimer */}
        <div
          className="mt-5 rounded-3xl border-2 border-[#E4D8B8] bg-[#FFF6D8] p-5"
          data-testid="joint-agreement-shared-disclaimer"
        >
          <div className="flex items-start gap-3">
            <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-[#8A6B12] text-white">
              <ShieldCheck size={16} />
            </div>
            <div className="min-w-0">
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#8A6B12]">
                This is a draft for discussion
              </div>
              <p className="mt-1 text-sm text-[#1A1330] leading-relaxed">
                {d.disclaimer}
              </p>
            </div>
          </div>
        </div>

        {/* At-a-glance convergence + neutral-language note */}
        <div className="mt-3 grid sm:grid-cols-2 gap-3">
          <div
            className="rounded-2xl border border-[#E5E0EE] bg-white p-4"
            data-testid="joint-agreement-shared-summary"
          >
            <div className="flex items-center gap-2 mb-2">
              <Users size={14} className="text-[#3D1A78]" />
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#3D1A78] font-semibold">
                At a glance
              </div>
            </div>
            <div className="text-sm text-[#1A1330] leading-relaxed">
              <div><strong>{summary.both_proposed || 0}</strong> proposed by <strong>both</strong> parents</div>
              <div><strong>{summary.parent_a_only || 0}</strong> proposed by {parentA} only</div>
              <div><strong>{summary.parent_b_only || 0}</strong> proposed by {parentB} only</div>
              <div className="mt-2 text-[#1F5C3B] font-semibold">
                Convergence: {summary.converged_pct || 0}%
              </div>
            </div>
          </div>
          <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4 text-xs text-[#4B4567] leading-relaxed">
            <div className="flex items-center gap-2 mb-1">
              <Info size={14} className="text-[#3D1A78]" />
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#3D1A78] font-semibold">
                Neutral language
              </div>
            </div>
            {d.neutral_language_note}
          </div>
        </div>

        {/* Primary presentation — parent-friendly 5-bucket view. */}
        <div className="mt-6">
          <JointAgreementParentView
            parentView={d.parent_view}
            parentAName={parentA}
            parentBName={parentB}
          />
        </div>

        <details
          className="mt-8 rounded-3xl border border-[#E5E0EE] bg-white/60 overflow-hidden"
          data-testid="joint-agreement-shared-detailed-comparison"
        >
          <summary className="cursor-pointer px-5 py-4 flex items-center justify-between gap-3 hover:bg-white/80 transition-colors">
            <div>
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                For attorneys, mediators &amp; therapists
              </div>
              <div className="font-serif text-lg text-[#1A1330] mt-0.5">
                Detailed Comparison
              </div>
            </div>
            <span className="text-xs text-[#857E9C] font-semibold">
              Click to expand
            </span>
          </summary>
          <div className="px-5 pb-6 pt-2 border-t border-[#E5E0EE]">
            {(d.sections || []).map((section) => (
              <Section
                key={section.key}
                section={section}
                parentAName={parentA}
                parentBName={parentB}
              />
            ))}
          </div>
        </details>

        {(d.closing_notes?.parent_a || d.closing_notes?.parent_b) && (
          <section
            className="mt-10"
            data-testid="joint-agreement-shared-closing-notes"
          >
            <h2 className="font-serif text-2xl text-[#1A1330] mb-3">
              Closing notes from each parent
            </h2>
            <div className="grid sm:grid-cols-2 gap-3">
              {d.closing_notes?.parent_a && (
                <div className="rounded-2xl border border-[#E5E0EE] bg-[#F7F4FC] p-4">
                  <div className="text-[10px] uppercase tracking-wider text-[#3D1A78] font-semibold mb-1">
                    {parentA}
                  </div>
                  <div className="text-sm text-[#1A1330] italic">
                    {d.closing_notes.parent_a}
                  </div>
                </div>
              )}
              {d.closing_notes?.parent_b && (
                <div className="rounded-2xl border border-[#E5E0EE] bg-[#EAF7F7] p-4">
                  <div className="text-[10px] uppercase tracking-wider text-[#0F6F6F] font-semibold mb-1">
                    {parentB}
                  </div>
                  <div className="text-sm text-[#1A1330] italic">
                    {d.closing_notes.parent_b}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {d.next_step && (
          <div className="mt-8 rounded-2xl bg-[#EFE9F9] border border-[#D6CFE8] p-4">
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#3D1A78] font-semibold mb-1">
              Suggested next step
            </div>
            <p className="text-sm text-[#1A1330]">{d.next_step}</p>
          </div>
        )}

        <div className="mt-10 text-[11px] text-[#857E9C] leading-relaxed border-t border-[#E5E0EE] pt-4">
          Draft for discussion · Not a court order or legal advice, and not
          binding unless a court approves it. Rendered via a signed link the sending parent
          created; the link can be revoked at any time from their account.
        </div>
      </div>
    </div>
  );
}
