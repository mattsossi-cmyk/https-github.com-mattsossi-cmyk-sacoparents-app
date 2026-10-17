/**
 * CommunicationAlignment.jsx — the Communication Alignment Report page.
 *
 * Two states:
 *   1. Solo: parent has completed their reflection but has not yet paired
 *      with a co-parent. Renders a "Ready to compare" panel with a
 *      co-parent email input that pairs by calling `/communication-
 *      alignment/compare`.
 *   2. Ready: both parents complete. Renders the neutral shared / gaps
 *      dimensions + the LLM-authored exec summary. Includes a "Get a
 *      shareable link" mint via the existing `/link-codes` flow with
 *      `context="communication"`. Family-violence gate + one-invite
 *      lifetime rule are enforced at the backend so this page never
 *      needs local mirroring.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Copy,
  Handshake,
  Info,
  Link as LinkIcon,
  Loader2,
  Mail,
  MessageCircle,
  Send,
  ShieldAlert,
  Sparkles,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import AppShell from "../components/AppShell";
import BackToDashboardLink from "../components/BackToDashboardLink";
import AIDraftedPill from "../components/AIDraftedPill";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

function ScoreBar({ value, tone = "self" }) {
  const width = `${Math.min(100, Math.max(0, value || 0))}%`;
  const color = tone === "self" ? "bg-[#1E6FA8]" : "bg-[#8471B3]";
  return (
    <div className="h-2 w-full bg-[#EEF3F7] rounded-full overflow-hidden">
      <div className={`h-full ${color}`} style={{ width }} />
    </div>
  );
}

function DimensionRow({ row, coparentName }) {
  return (
    <div
      className="rounded-2xl border border-[#D8E7F3] bg-white p-4"
      data-testid={`comm-dim-${row.dimension}`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="font-serif text-lg text-[#1A1330] leading-tight">
            {row.label}
          </div>
          <p className="text-[0.75rem] text-[#4B4567] mt-0.5 leading-snug">
            {row.blurb}
          </p>
        </div>
        <div className="text-[0.6875rem] text-[#4B4567]">
          Delta:{" "}
          <span
            className={`font-semibold ${row.delta <= 15 ? "text-[#1E7A55]" : "text-[#904B0E]"}`}
          >
            {row.delta}
          </span>
        </div>
      </div>
      <div className="mt-3 grid gap-3">
        <div>
          <div className="text-[0.625rem] uppercase tracking-[0.16em] font-bold text-[#1E6FA8] mb-1">
            You · {row.self_score}
          </div>
          <ScoreBar value={row.self_score} tone="self" />
        </div>
        <div>
          <div className="text-[0.625rem] uppercase tracking-[0.16em] font-bold text-[#6A5799] mb-1">
            {coparentName || "Co-parent"} · {row.coparent_score}
          </div>
          <ScoreBar value={row.coparent_score} tone="coparent" />
        </div>
      </div>
    </div>
  );
}

export default function CommunicationAlignment() {
  const [self, setSelf] = useState(null);
  const [loading, setLoading] = useState(true);
  const [coparentEmail, setCoparentEmail] = useState("");
  const [comparing, setComparing] = useState(false);
  const [payload, setPayload] = useState(null); // /compare response
  const [summary, setSummary] = useState(null);
  const [summaryModel, setSummaryModel] = useState(null);
  const [summarizing, setSummarizing] = useState(false);
  const [shareCode, setShareCode] = useState(null);
  const [shareError, setShareError] = useState(null);
  const [minting, setMinting] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const mine = await api.get("/communication-reflection/mine");
        setSelf(mine.data);
      } catch (err) {
        logError("comm-alignment load", err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const runCompare = async () => {
    const v = coparentEmail.trim().toLowerCase();
    if (!v || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) {
      toast.error("Please enter a valid email address.");
      return;
    }
    setComparing(true);
    try {
      const r = await api.post("/communication-alignment/compare", {
        coparent_email: v,
      });
      setPayload(r.data);
      if (r.data?.status === "ready") {
        // Fetch the neutral LLM summary
        setSummarizing(true);
        try {
          const s = await api.post("/communication-alignment/compare/summary", {
            compare_payload: r.data,
          });
          setSummary(s.data?.summary || null);
          setSummaryModel(s.data?.model || "claude");
        } catch (err) {
          logError("comm-alignment summary", err);
        } finally {
          setSummarizing(false);
        }
      }
    } catch (err) {
      logError("comm-alignment compare", err);
      const detail = err?.response?.data?.detail;
      toast.error(
        (detail && typeof detail === "object" && detail.message) ||
          detail ||
          "Could not build the alignment report.",
      );
    } finally {
      setComparing(false);
    }
  };

  const mintShareLink = async () => {
    setMinting(true);
    setShareError(null);
    try {
      const r = await api.post("/link-codes", { context: "communication" });
      setShareCode(r.data);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      // Structured 403 payloads (from safety_gate)
      if (detail && typeof detail === "object" && detail.code) {
        setShareError(detail);
      } else {
        toast.error(detail || "Could not mint a share link.");
      }
    } finally {
      setMinting(false);
    }
  };

  const copyCode = async (code) => {
    try {
      await navigator.clipboard.writeText(code);
      toast.success("Code copied.");
    } catch {
      toast.error("Could not copy.");
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="max-w-4xl mx-auto px-4 py-10 text-[#4B4567]">
          <Loader2 className="animate-spin inline" /> Loading your alignment report…
        </div>
      </AppShell>
    );
  }

  const hasSelf = self && self.score && (self.score.answered_count || 0) > 0;
  const ready = payload?.status === "ready";
  const waiting = payload?.status === "waiting_on_coparent";
  const coparentName = payload?.coparent?.name;

  return (
    <AppShell>
      <div
        className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10"
        data-testid="comm-alignment-root"
      >
        <BackToDashboardLink
          className="mb-3"
          testId="comm-alignment-back-dashboard"
        />
        <Link
          to="/communication"
          className="inline-flex items-center gap-2 text-sm text-[#1E6FA8] hover:text-[#0E4C7A] mb-4"
        >
          <ArrowLeft size={14} /> Communication pathway
        </Link>

        <div className="rounded-3xl bg-gradient-to-br from-[#1E6FA8] to-[#3A9DD6] text-white p-6 sm:p-8 shadow-md">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-white/15 grid place-items-center backdrop-blur-sm">
              <MessageCircle size={22} strokeWidth={2.2} />
            </div>
            <div className="text-[0.6875rem] uppercase tracking-[0.18em] font-bold text-white/85">
              Communication Alignment Report
            </div>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl leading-tight mt-4">
            Where you already agree — and where a small tune-up would help
          </h1>
          <p className="text-white/85 mt-3 max-w-2xl leading-relaxed text-[15px]">
            Neutral, non-adjudicative — designed to show shared habits and
            gaps in three dimensions: Clarity, Regulation, and Structure. Your
            co-parent sees the same shared view; individual notes stay
            private.
          </p>
        </div>

        {/* Guardrail: reflection required first */}
        {!hasSelf && (
          <div
            className="mt-6 rounded-2xl border border-[#F1D9B7] bg-[#FFF6EA] p-5 flex items-start gap-3"
            data-testid="comm-alignment-need-reflection"
          >
            <Info size={18} className="text-[#904B0E] shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="font-serif text-lg text-[#5A3C10]">
                Complete your reflection first
              </div>
              <p className="text-sm text-[#5A3C10]/90 mt-1 leading-relaxed">
                12 short questions about your own habits. Takes about 3
                minutes.
              </p>
              <Link
                to="/communication/reflection"
                className="mt-3 inline-flex items-center gap-2 rounded-full bg-[#B45F13] text-white px-4 py-2 text-sm font-semibold hover:brightness-110"
                data-testid="comm-alignment-take-reflection-cta"
              >
                Start reflection <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        )}

        {/* Pair-by-email panel */}
        {hasSelf && !payload && (
          <div
            className="mt-6 rounded-3xl border border-[#D8E7F3] bg-white p-6 sm:p-7"
            data-testid="comm-alignment-pair-panel"
          >
            <div className="flex items-start gap-3 mb-4">
              <Users size={20} className="text-[#1E6FA8] shrink-0 mt-1" />
              <div>
                <h2 className="font-serif text-xl text-[#1A1330] leading-tight">
                  Pair with your co-parent
                </h2>
                <p className="text-sm text-[#4B4567] mt-1 leading-relaxed">
                  Enter your co-parent&rsquo;s email — the same email they
                  use to sign in. If they have finished their reflection, the
                  report will build immediately. Otherwise you&rsquo;ll see a
                  waiting message.
                </p>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative flex-1">
                <Mail
                  size={16}
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-[#6E6787]"
                />
                <input
                  type="email"
                  value={coparentEmail}
                  onChange={(e) => setCoparentEmail(e.target.value)}
                  placeholder="co-parent@email.com"
                  data-testid="comm-alignment-coparent-email"
                  className="w-full pl-11 pr-4 py-3 rounded-2xl border border-[#D8E7F3] text-sm focus:outline-none focus:border-[#1E6FA8]"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") runCompare();
                  }}
                />
              </div>
              <button
                type="button"
                onClick={runCompare}
                disabled={comparing}
                data-testid="comm-alignment-compare-button"
                className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-[#1E6FA8] text-white font-semibold text-sm hover:brightness-110 disabled:opacity-60"
              >
                {comparing ? <Loader2 className="animate-spin" size={16} /> : <Handshake size={16} />}
                Build report
              </button>
            </div>
          </div>
        )}

        {/* Waiting-on-coparent */}
        {waiting && (
          <div
            className="mt-6 rounded-3xl border border-[#D8E7F3] bg-white p-6 sm:p-7"
            data-testid="comm-alignment-waiting"
          >
            <div className="flex items-start gap-3">
              <Sparkles size={20} className="text-[#1E6FA8] shrink-0 mt-1" />
              <div>
                <h2 className="font-serif text-xl text-[#1A1330] leading-tight">
                  Waiting on{" "}
                  {payload?.coparent?.name ||
                    payload?.coparent?.email ||
                    "your co-parent"}
                </h2>
                <p className="text-sm text-[#4B4567] mt-1 leading-relaxed">
                  You&rsquo;ve completed your reflection. The alignment report
                  will build as soon as your co-parent completes theirs. We
                  never show either parent the other&rsquo;s free-text notes.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Ready state — shared + gaps + summary + share-link */}
        {ready && (
          <div className="mt-6 space-y-6" data-testid="comm-alignment-ready">
            {/* Neutral exec summary */}
            <div className="rounded-3xl border border-[#D8E7F3] bg-white p-6 sm:p-7 shadow-sm">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#1E6FA8]">
                  Neutral summary
                </span>
                {summary && summaryModel && (
                  <AIDraftedPill
                    model={summaryModel}
                    tone="blue"
                    testId="comm-alignment-summary-pill"
                  />
                )}
              </div>
              <h2 className="font-serif text-xl text-[#1A1330] leading-tight mb-3">
                What the two of you actually said
              </h2>
              {summarizing && (
                <div className="text-sm text-[#4B4567] inline-flex items-center gap-2">
                  <Loader2 size={14} className="animate-spin" /> Composing a neutral summary…
                </div>
              )}
              {!summarizing && summary && (
                <p
                  className="text-[15px] text-[#1A1330] leading-relaxed whitespace-pre-wrap"
                  data-testid="comm-alignment-summary"
                >
                  {summary}
                </p>
              )}
              {!summarizing && !summary && (
                <p className="text-sm text-[#4B4567] italic">
                  Summary unavailable — the dimensions below still tell the
                  story.
                </p>
              )}
            </div>

            {/* Shared dimensions */}
            {payload.shared && payload.shared.length > 0 && (
              <div>
                <div className="text-[0.6875rem] uppercase tracking-[0.16em] font-bold text-[#1E7A55] mb-2 flex items-center gap-2">
                  <CheckCircle2 size={13} /> Where you agree
                </div>
                <div className="grid gap-3">
                  {payload.shared.map((row) => (
                    <DimensionRow key={row.dimension} row={row} coparentName={coparentName} />
                  ))}
                </div>
              </div>
            )}

            {/* Gaps */}
            {payload.gaps && payload.gaps.length > 0 && (
              <div>
                <div className="text-[0.6875rem] uppercase tracking-[0.16em] font-bold text-[#904B0E] mb-2 flex items-center gap-2">
                  <ShieldAlert size={13} /> Where a small tune-up would help
                </div>
                <div className="grid gap-3">
                  {payload.gaps.map((row) => (
                    <DimensionRow key={row.dimension} row={row} coparentName={coparentName} />
                  ))}
                </div>
              </div>
            )}

            {/* Share-link mint */}
            <div className="rounded-3xl border border-[#D8E7F3] bg-white p-6 sm:p-7">
              <div className="flex items-start gap-3 mb-3">
                <LinkIcon size={20} className="text-[#1E6FA8] shrink-0 mt-1" />
                <div>
                  <h2 className="font-serif text-xl text-[#1A1330] leading-tight">
                    Send this to your mediator or attorney
                  </h2>
                  <p className="text-sm text-[#4B4567] mt-1 leading-relaxed">
                    Get a short one-time code they can enter on{" "}
                    <strong className="text-[#1A1330]">sacoparentsalign.com</strong>{" "}
                    to pull up your Alignment Report.
                  </p>
                </div>
              </div>

              {shareError ? (
                <div
                  className="rounded-2xl border-2 border-[#F1B7B7] bg-[#FDECEC] p-4 flex items-start gap-3"
                  data-testid="comm-alignment-share-error"
                >
                  <ShieldAlert size={18} className="text-[#9A3A23] shrink-0 mt-0.5" />
                  <div className="text-sm text-[#5B1F1F] leading-relaxed">
                    <div className="font-semibold">
                      {shareError.code === "safety_screen_required"
                        ? "Complete the family-violence safety screen first"
                        : "Direct outreach isn't recommended right now"}
                    </div>
                    <p className="mt-1">{shareError.message}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Link
                        to="/safety"
                        className="inline-flex items-center gap-2 rounded-full bg-[#9A3A23] text-white px-4 py-2 text-xs font-semibold hover:brightness-110"
                      >
                        {shareError.code === "safety_screen_required"
                          ? "Take the safety screen"
                          : "Review my safety plan"}
                      </Link>
                      {shareError.code === "safety_screen_blocked" && (
                        <Link
                          to="/professionals"
                          className="inline-flex items-center gap-2 rounded-full border border-[#9A3A23] text-[#9A3A23] px-4 py-2 text-xs font-semibold hover:bg-[#FDECEC]"
                        >
                          Send my case to a mediator instead
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              ) : shareCode ? (
                <div
                  className="rounded-2xl bg-[#F1F9F4] border border-[#C7E5D3] p-5"
                  data-testid="comm-alignment-share-success"
                >
                  <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#1E7A55] mb-1">
                    Share code
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <code className="font-mono text-2xl tracking-widest text-[#1A1330] px-4 py-2 rounded-xl bg-white border border-[#C7E5D3]">
                      {shareCode.code}
                    </code>
                    <button
                      type="button"
                      onClick={() => copyCode(shareCode.code)}
                      className="inline-flex items-center gap-1.5 px-3 py-2 rounded-full text-xs font-semibold border border-[#1E7A55] text-[#1E7A55] hover:bg-[#DEF5E0]"
                      data-testid="comm-alignment-copy-code"
                    >
                      <Copy size={12} /> Copy
                    </button>
                  </div>
                  <p className="text-xs text-[#1E7A55] mt-3 leading-relaxed">
                    Valid for 15 minutes. Send this code to your mediator or
                    attorney — they enter it on the sibling app to view the
                    report.
                  </p>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={mintShareLink}
                  disabled={minting}
                  data-testid="comm-alignment-mint-code"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#1E6FA8] text-white text-sm font-semibold hover:brightness-110 disabled:opacity-60"
                >
                  {minting ? <Loader2 className="animate-spin" size={14} /> : <Send size={14} />}
                  Get a share code
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
