/**
 * ActivitiesAlignment.jsx — the Activities Alignment Report page.
 * Mirrors CommunicationAlignment.jsx.
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
  Palette,
  Send,
  ShieldAlert,
  Sparkles,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import AppShell from "../components/AppShell";
import BackToDashboardLink from "../components/BackToDashboardLink";
import PathwayEndCTA from "../components/PathwayEndCTA";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

function ScoreBar({ value, tone = "self" }) {
  const width = `${Math.min(100, Math.max(0, value || 0))}%`;
  const color = tone === "self" ? "bg-[#1E7A55]" : "bg-[#8471B3]";
  return (
    <div className="h-2 w-full bg-[#EEF5F0] rounded-full overflow-hidden">
      <div className={`h-full ${color}`} style={{ width }} />
    </div>
  );
}

function DimensionRow({ row, coparentName }) {
  return (
    <div
      className="rounded-2xl border border-[#C7E5D3] bg-white p-4"
      data-testid={`activities-dim-${row.dimension}`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="font-serif text-lg text-[#1A1330] leading-tight">
            {row.label}
          </div>
          <p className="text-[12px] text-[#4B4567] mt-0.5 leading-snug">
            {row.blurb}
          </p>
        </div>
        <div className="text-[11px] text-[#4B4567]">
          Delta:{" "}
          <span
            className={`font-semibold ${row.delta <= 15 ? "text-[#1E7A55]" : "text-[#B45F13]"}`}
          >
            {row.delta}
          </span>
        </div>
      </div>
      <div className="mt-3 grid gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#1E7A55] mb-1">
            You · {row.self_score}
          </div>
          <ScoreBar value={row.self_score} tone="self" />
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#8471B3] mb-1">
            {coparentName || "Co-parent"} · {row.coparent_score}
          </div>
          <ScoreBar value={row.coparent_score} tone="coparent" />
        </div>
      </div>
    </div>
  );
}

export default function ActivitiesAlignment() {
  const [self, setSelf] = useState(null);
  const [loading, setLoading] = useState(true);
  const [coparentEmail, setCoparentEmail] = useState("");
  const [comparing, setComparing] = useState(false);
  const [payload, setPayload] = useState(null);
  const [summary, setSummary] = useState(null);
  const [summarizing, setSummarizing] = useState(false);
  const [shareCode, setShareCode] = useState(null);
  const [shareError, setShareError] = useState(null);
  const [minting, setMinting] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const mine = await api.get("/activities-reflection/mine");
        setSelf(mine.data);
      } catch (err) {
        logError("activities-alignment load", err);
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
      const r = await api.post("/activities-alignment/compare", {
        coparent_email: v,
      });
      setPayload(r.data);
      if (r.data?.status === "ready") {
        setSummarizing(true);
        try {
          const s = await api.post("/activities-alignment/compare/summary", {
            compare_payload: r.data,
          });
          setSummary(s.data?.summary || null);
        } catch (err) {
          logError("activities-alignment summary", err);
        } finally {
          setSummarizing(false);
        }
      }
    } catch (err) {
      logError("activities-alignment compare", err);
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
      const r = await api.post("/link-codes", { context: "activities" });
      setShareCode(r.data);
    } catch (err) {
      const detail = err?.response?.data?.detail;
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
        data-testid="activities-alignment-root"
      >
        <BackToDashboardLink
          className="mb-3"
          testId="activities-alignment-back-dashboard"
        />
        <Link
          to="/joint-reports"
          className="inline-flex items-center gap-2 text-sm text-[#1E7A55] hover:text-[#0F5638] mb-4"
        >
          <ArrowLeft size={14} /> Joint reports
        </Link>

        <div className="rounded-3xl bg-gradient-to-br from-[#1E7A55] to-[#4CB88C] text-white p-6 sm:p-8 shadow-md">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-white/15 grid place-items-center backdrop-blur-sm">
              <Palette size={22} strokeWidth={2.2} />
            </div>
            <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-white/85">
              Activities Alignment Report
            </div>
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl leading-tight mt-4">
            Where you already back the kids the same way — and where a small tune-up would help
          </h1>
          <p className="text-white/85 mt-3 max-w-2xl leading-relaxed text-[15px]">
            Neutral, non-adjudicative — three dimensions:{" "}
            <strong>Awareness</strong>, <strong>Support</strong>, and{" "}
            <strong>Logistics</strong>. Your co-parent sees the same shared
            view; individual notes stay private.
          </p>
        </div>

        {!hasSelf && (
          <div
            className="mt-6 rounded-2xl border border-[#C7E5D3] bg-[#F1F9F4] p-5 flex items-start gap-3"
            data-testid="activities-alignment-need-reflection"
          >
            <Info size={18} className="text-[#1E7A55] shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="font-serif text-lg text-[#0F5638]">
                Complete your reflection first
              </div>
              <p className="text-sm text-[#0F5638]/90 mt-1 leading-relaxed">
                12 short questions about your own habits. Takes about 3
                minutes.
              </p>
              <Link
                to="/activities/reflection"
                className="mt-3 inline-flex items-center gap-2 rounded-full bg-[#1E7A55] text-white px-4 py-2 text-sm font-semibold hover:brightness-110"
                data-testid="activities-alignment-take-reflection-cta"
              >
                Start reflection <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        )}

        {hasSelf && !payload && (
          <div
            className="mt-6 rounded-3xl border border-[#C7E5D3] bg-white p-6 sm:p-7"
            data-testid="activities-alignment-pair-panel"
          >
            <div className="flex items-start gap-3 mb-4">
              <Users size={20} className="text-[#1E7A55] shrink-0 mt-1" />
              <div>
                <h2 className="font-serif text-xl text-[#1A1330] leading-tight">
                  Pair with your co-parent
                </h2>
                <p className="text-sm text-[#4B4567] mt-1 leading-relaxed">
                  Enter your co-parent&rsquo;s email — the same email they
                  use to sign in.
                </p>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative flex-1">
                <Mail
                  size={16}
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-[#857E9C]"
                />
                <input
                  type="email"
                  value={coparentEmail}
                  onChange={(e) => setCoparentEmail(e.target.value)}
                  placeholder="co-parent@email.com"
                  data-testid="activities-alignment-coparent-email"
                  className="w-full pl-11 pr-4 py-3 rounded-2xl border border-[#C7E5D3] text-sm focus:outline-none focus:border-[#1E7A55]"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") runCompare();
                  }}
                />
              </div>
              <button
                type="button"
                onClick={runCompare}
                disabled={comparing}
                data-testid="activities-alignment-compare-button"
                className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-[#1E7A55] text-white font-semibold text-sm hover:brightness-110 disabled:opacity-60"
              >
                {comparing ? <Loader2 className="animate-spin" size={16} /> : <Handshake size={16} />}
                Build report
              </button>
            </div>
          </div>
        )}

        {waiting && (
          <div
            className="mt-6 rounded-3xl border border-[#C7E5D3] bg-white p-6 sm:p-7"
            data-testid="activities-alignment-waiting"
          >
            <div className="flex items-start gap-3">
              <Sparkles size={20} className="text-[#1E7A55] shrink-0 mt-1" />
              <div>
                <h2 className="font-serif text-xl text-[#1A1330] leading-tight">
                  Waiting on{" "}
                  {payload?.coparent?.name ||
                    payload?.coparent?.email ||
                    "your co-parent"}
                </h2>
                <p className="text-sm text-[#4B4567] mt-1 leading-relaxed">
                  You&rsquo;ve completed your reflection. The alignment
                  report will build as soon as your co-parent completes
                  theirs. We never show either parent the other&rsquo;s
                  free-text notes.
                </p>
              </div>
            </div>
          </div>
        )}

        {ready && (
          <div className="mt-6 space-y-6" data-testid="activities-alignment-ready">
            <div className="rounded-3xl border border-[#C7E5D3] bg-white p-6 sm:p-7 shadow-sm">
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#1E7A55] mb-2">
                Neutral summary
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
                  data-testid="activities-alignment-summary"
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

            {payload.shared && payload.shared.length > 0 && (
              <div>
                <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#1E7A55] mb-2 flex items-center gap-2">
                  <CheckCircle2 size={13} /> Where you agree
                </div>
                <div className="grid gap-3">
                  {payload.shared.map((row) => (
                    <DimensionRow key={row.dimension} row={row} coparentName={coparentName} />
                  ))}
                </div>
              </div>
            )}

            {payload.gaps && payload.gaps.length > 0 && (
              <div>
                <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#B45F13] mb-2 flex items-center gap-2">
                  <ShieldAlert size={13} /> Where a small tune-up would help
                </div>
                <div className="grid gap-3">
                  {payload.gaps.map((row) => (
                    <DimensionRow key={row.dimension} row={row} coparentName={coparentName} />
                  ))}
                </div>
              </div>
            )}

            <div className="rounded-3xl border border-[#C7E5D3] bg-white p-6 sm:p-7">
              <div className="flex items-start gap-3 mb-3">
                <LinkIcon size={20} className="text-[#1E7A55] shrink-0 mt-1" />
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
                  data-testid="activities-alignment-share-error"
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
                  data-testid="activities-alignment-share-success"
                >
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#1E7A55] mb-1">
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
                      data-testid="activities-alignment-copy-code"
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
                  data-testid="activities-alignment-mint-code"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#1E7A55] text-white text-sm font-semibold hover:brightness-110 disabled:opacity-60"
                >
                  {minting ? <Loader2 className="animate-spin" size={14} /> : <Send size={14} />}
                  Get a share code
                </button>
              )}
            </div>

            <PathwayEndCTA
              testId="activities-alignment-end-cta"
              tone="green"
              eyebrow="Activities pathway"
              title="Ready to hand this off?"
              description="Send this Alignment Report to a mediator or attorney directly — they'll receive the code with your name attached."
              primary={{
                label: "Send to a professional",
                to: "/professionals?assessment=activities",
              }}
            />
          </div>
        )}
      </div>
    </AppShell>
  );
}
