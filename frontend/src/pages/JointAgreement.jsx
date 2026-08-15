/**
 * Joint Co-Parenting Agreement Draft.
 *
 * Deterministic side-by-side merge of both parents' individual agreement
 * drafts. Unlocked by the same active Compare share the Joint
 * Professional Report uses. Language stays neutral throughout — no
 * possession/custody phrasing.
 *
 * Query params:
 *   ?share=<share_id>   Required. Active Compare share.
 */
import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowLeft, Download, Loader2, ShieldCheck, Users, Info,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import { api, API } from "../lib/api";
import { logError } from "../lib/logger";


function Bucket({ label, colour, items, mode, parentAName, parentBName }) {
  return (
    <div
      className="rounded-2xl border p-4 sm:p-5"
      style={{ backgroundColor: `${colour}0F`, borderColor: `${colour}55` }}
      data-testid={`joint-agreement-bucket-${mode}`}
    >
      <div
        className="text-[11px] uppercase tracking-[0.22em] font-bold mb-3"
        style={{ color: colour }}
      >
        {label}{" "}
        <span className="text-[#857E9C] font-semibold">· {items.length}</span>
      </div>
      {items.length === 0 ? (
        <div className="text-sm text-[#857E9C] italic">(none)</div>
      ) : (
        <ul className="space-y-3">
          {items.map((it, i) => {
            if (mode === "both") {
              return (
                <li key={i} className="rounded-xl bg-white p-3 border border-white/60">
                  {it.area && (
                    <div className="text-[10px] uppercase tracking-wider text-[#857E9C] font-semibold mb-1">
                      {it.area}
                    </div>
                  )}
                  <div className="grid sm:grid-cols-2 gap-3">
                    <div className="rounded-lg bg-[#F7F4FC] p-2.5">
                      <div className="text-[10px] uppercase tracking-wider text-[#3D1A78] font-semibold mb-1">
                        {parentAName}
                      </div>
                      <div className="text-sm text-[#1A1330]">{it.parent_a_text}</div>
                    </div>
                    <div className="rounded-lg bg-[#EAF7F7] p-2.5">
                      <div className="text-[10px] uppercase tracking-wider text-[#0F6F6F] font-semibold mb-1">
                        {parentBName}
                      </div>
                      <div className="text-sm text-[#1A1330]">{it.parent_b_text}</div>
                    </div>
                  </div>
                </li>
              );
            }
            return (
              <li
                key={i}
                className="rounded-xl bg-white p-3 border border-white/60"
              >
                {it.area && (
                  <div className="text-[10px] uppercase tracking-wider text-[#857E9C] font-semibold mb-1">
                    {it.area}
                  </div>
                )}
                <div className="text-sm text-[#1A1330]">{it.text}</div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function Section({ section, parentAName, parentBName }) {
  return (
    <section
      className="mt-8"
      data-testid={`joint-agreement-section-${section.key}`}
    >
      <div className="flex items-center gap-2 mb-2">
        <h2 className="font-serif text-2xl text-[#1A1330]">{section.title}</h2>
        <span className="text-xs text-[#857E9C]">
          {section.counts.both_proposed} both ·{" "}
          {section.counts.parent_a_only} {parentAName} ·{" "}
          {section.counts.parent_b_only} {parentBName}
        </span>
      </div>
      {section.description && (
        <p className="text-sm text-[#4B4567] mb-4 leading-relaxed max-w-3xl">
          {section.description}
        </p>
      )}
      <div className="grid gap-3">
        <Bucket
          label="Both proposed"
          colour="#1F5C3B"
          items={section.both_proposed || []}
          mode="both"
          parentAName={parentAName}
          parentBName={parentBName}
        />
        <Bucket
          label={`${parentAName} only`}
          colour="#3D1A78"
          items={section.parent_a_only || []}
          mode="a"
          parentAName={parentAName}
          parentBName={parentBName}
        />
        <Bucket
          label={`${parentBName} only`}
          colour="#8A6B12"
          items={section.parent_b_only || []}
          mode="b"
          parentAName={parentAName}
          parentBName={parentBName}
        />
      </div>
    </section>
  );
}

export default function JointAgreement() {
  const [params] = useSearchParams();
  const shareId = params.get("share");
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!shareId) {
      setState({ loading: false, data: null, error: "missing-share" });
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get(
          `/joint-agreement/${encodeURIComponent(shareId)}`,
        );
        if (!cancelled) setState({ loading: false, data: res.data, error: null });
      } catch (err) {
        logError("joint agreement load", err);
        if (!cancelled) {
          setState({
            loading: false, data: null,
            error: err?.response?.data?.detail || "load-failed",
          });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [shareId]);

  const downloadPdf = async () => {
    if (!shareId) return;
    setDownloading(true);
    try {
      const res = await fetch(
        `${API}/joint-agreement/${encodeURIComponent(shareId)}/pdf`,
        { credentials: "include" },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `joint-coparenting-agreement-${shareId.slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      logError("joint agreement pdf", err);
      toast.error("Could not download PDF. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  if (state.loading) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto p-8 text-center text-[#4B4567]"
             data-testid="joint-agreement-loading">
          <Loader2 size={20} className="animate-spin inline-block mr-2" />
          Merging both parents' agreement drafts...
        </div>
      </AppShell>
    );
  }

  if (state.error === "missing-share" || (state.error && !state.data)) {
    const msg = state.error === "missing-share"
      ? "Both parents need an active Compare share for the joint agreement to unlock. Start (or accept) a Compare invite from your Dashboard."
      : (typeof state.error === "string" && state.error.length > 2
          ? state.error
          : "We couldn't load the joint agreement.");
    return (
      <AppShell>
        <div className="max-w-2xl mx-auto p-8" data-testid="joint-agreement-error">
          <h1 className="font-serif text-3xl text-[#1A1330] mb-4">
            Joint Co-Parenting Agreement Draft
          </h1>
          <p className="text-[#4B4567] leading-relaxed mb-6">{msg}</p>
          <div className="flex flex-wrap gap-2">
            <Link
              to="/summary?tab=agreement"
              className="btn-sage inline-flex items-center gap-2"
              data-testid="joint-agreement-generate-mine"
            >
              Generate my agreement draft
            </Link>
            <Link to="/dashboard" className="btn-soft inline-flex items-center gap-2">
              <ArrowLeft size={14} /> Back to dashboard
            </Link>
          </div>
        </div>
      </AppShell>
    );
  }

  const d = state.data;
  const parentA = d.parent_a_name || "Parent A";
  const parentB = d.parent_b_name || "Parent B";
  const summary = d.summary || {};

  return (
    <AppShell>
      <div
        className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10"
        data-testid="joint-agreement-root"
      >
        <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] hover:text-[#3D1A78]"
          >
            <ArrowLeft size={12} /> Back to dashboard
          </Link>
          <button
            type="button"
            onClick={downloadPdf}
            disabled={downloading}
            data-testid="joint-agreement-download-pdf"
            className="inline-flex items-center gap-1.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-4 py-2 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-60"
          >
            {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            Download PDF
          </button>
        </div>

        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
          Joint Agreement Draft
        </div>
        <h1
          className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-1 leading-tight"
          data-testid="joint-agreement-title"
        >
          {d.report_title}
        </h1>
        <div className="mt-2 text-sm text-[#4B4567]" data-testid="joint-agreement-parents">
          {parentA} <span className="text-[#857E9C] mx-1">·</span> {parentB}
        </div>

        {/* Draft-for-discussion disclaimer (yellow). */}
        <div
          className="mt-5 rounded-3xl border-2 border-[#E4D8B8] bg-[#FFF6D8] p-5"
          data-testid="joint-agreement-disclaimer"
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

        {/* At-a-glance convergence + neutral-language note. */}
        <div className="mt-3 grid sm:grid-cols-2 gap-3">
          <div
            className="rounded-2xl border border-[#E5E0EE] bg-white p-4"
            data-testid="joint-agreement-summary"
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

        {(d.sections || []).map((section) => (
          <Section
            key={section.key}
            section={section}
            parentAName={parentA}
            parentBName={parentB}
          />
        ))}

        {(d.closing_notes?.parent_a || d.closing_notes?.parent_b) && (
          <section className="mt-10" data-testid="joint-agreement-closing-notes">
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
          Draft for discussion · Not a signed agreement, court order, or legal
          document. Share ID {d.share_id}.
        </div>
      </div>
    </AppShell>
  );
}
