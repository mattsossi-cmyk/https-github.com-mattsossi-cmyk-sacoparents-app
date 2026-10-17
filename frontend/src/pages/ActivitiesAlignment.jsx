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
  Handshake,
  Info,
  Loader2,
  Mail,
  Palette,
  ShieldAlert,
  Sparkles,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import AppShell from "../components/AppShell";
import BackToDashboardLink from "../components/BackToDashboardLink";
import CostSplitterPanel from "../components/CostSplitterPanel";
import PathwayEndCTA from "../components/PathwayEndCTA";
import ActivitiesSummaryCard from "../components/activities/ActivitiesSummaryCard";
import ActivitiesShareCodeCard from "../components/activities/ActivitiesShareCodeCard";
import { DimensionRow } from "../components/activities/ActivitiesDimensionPrimitives";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

export default function ActivitiesAlignment() {
  const [self, setSelf] = useState(null);
  const [loading, setLoading] = useState(true);
  const [coparentEmail, setCoparentEmail] = useState("");
  const [comparing, setComparing] = useState(false);
  const [payload, setPayload] = useState(null);
  const [summary, setSummary] = useState(null);
  const [summaryModel, setSummaryModel] = useState(null);
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
          setSummaryModel(s.data?.model || "claude");
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
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-[#6E6787]"
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
            <ActivitiesSummaryCard
              summary={summary}
              summaryModel={summaryModel}
              summarizing={summarizing}
            />

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
                <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#904B0E] mb-2 flex items-center gap-2">
                  <ShieldAlert size={13} /> Where a small tune-up would help
                </div>
                <div className="grid gap-3">
                  {payload.gaps.map((row) => (
                    <DimensionRow key={row.dimension} row={row} coparentName={coparentName} />
                  ))}
                </div>
              </div>
            )}

            <ActivitiesShareCodeCard
              shareError={shareError}
              shareCode={shareCode}
              minting={minting}
              onMint={mintShareLink}
              onCopy={copyCode}
            />

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

        {/* Cost splitter is useful before, during, and after pairing —
            keep it visible whenever the parent has completed their
            reflection. */}
        {hasSelf && (
          <div className="mt-6">
            <CostSplitterPanel
              coparentEmail={payload?.coparent?.email}
              coparentName={coparentName}
            />
          </div>
        )}
      </div>
    </AppShell>
  );
}
