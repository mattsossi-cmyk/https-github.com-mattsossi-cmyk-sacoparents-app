/**
 * Joint Reports Picker.
 *
 * Route: `/joint-reports` (protected; parent must be signed in)
 *
 * The design goal from the walkthrough feedback was to strip cognitive
 * load: parents shouldn't need to understand the app's architecture to
 * pick a joint report. Two big circles at the top, eight topic circles
 * below — and one legend that names the private-vs-shared boundary.
 *
 *   ┌─────────────────────┐   ┌─────────────────────┐
 *   │ Complete Joint      │   │ Family Violence /   │
 *   │ Alignment Report    │   │ Communication Safety│
 *   └─────────────────────┘   └─────────────────────┘
 *
 *              Or focus on one area
 *   ○ Co-Parenting   ○ Education   ○ Medical   ○ Psychological
 *   ○ Special Needs  ○ Communication  ○ Schedule  ○ Activities
 *
 * Wiring:
 *   - Circles route to existing pages when a Compare share exists
 *     (`sncHighlights.share_id`); when it doesn't, they route to the
 *     matching intake so the parent knows what to complete first.
 *   - Topics still under construction (Communication / Parenting
 *     Schedule / Activities) render as "Coming soon" chips — non-
 *     interactive to prevent dead-end taps.
 *   - Family Violence tile shows a crisis-line banner above the tap
 *     target as the recommended default for this category.
 */
import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Users,
  ShieldAlert,
  GraduationCap,
  Stethoscope,
  Brain,
  Sparkles,
  MessageCircle,
  CalendarDays,
  Palette,
  Lock,
  Handshake,
  ArrowRight,
  Phone,
  Sparkle,
} from "lucide-react";

import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

// Topic tiles — each maps to an existing route when a Compare share
// exists, and to the intake page when it doesn't. The `comingSoon`
// flag opts a topic out of the router entirely.
const TOPIC_TILES = [
  {
    key: "coparenting",
    label: "Co-Parenting",
    icon: Users,
    fallback: "/companion-assessment",
    ready: (shareId) => (shareId ? `/joint-professional-report?share=${encodeURIComponent(shareId)}` : "/companion-assessment"),
  },
  {
    key: "education",
    label: "Education",
    icon: GraduationCap,
    fallback: "/special-needs-v2/educational-deep-dive",
    ready: (shareId) => (shareId ? `/special-needs-v2/educational-deep-dive/compare/${encodeURIComponent(shareId)}` : "/special-needs-v2/educational-deep-dive"),
  },
  {
    key: "medical",
    label: "Medical",
    icon: Stethoscope,
    fallback: "/special-needs-v2/medical-deep-dive",
    ready: (shareId) => (shareId ? `/special-needs-v2/medical-deep-dive/compare/${encodeURIComponent(shareId)}` : "/special-needs-v2/medical-deep-dive"),
  },
  {
    key: "psychological",
    label: "Psychological / Emotional",
    icon: Brain,
    fallback: "/special-needs-v2/psychological-deep-dive",
    ready: (shareId) => (shareId ? `/special-needs-v2/psychological-deep-dive/compare/${encodeURIComponent(shareId)}` : "/special-needs-v2/psychological-deep-dive"),
  },
  {
    key: "special-needs",
    label: "Special Needs",
    icon: Sparkles,
    fallback: "/special-needs-v2",
    ready: (shareId) => (shareId ? `/special-needs-v2/compare/${encodeURIComponent(shareId)}` : "/special-needs-v2"),
  },
  {
    key: "communication",
    label: "Communication",
    icon: MessageCircle,
    fallback: "/communication/reflection",
    ready: () => "/communication/alignment",
    alwaysStandalone: true,
  },
  {
    key: "schedule",
    label: "Parenting Schedule",
    icon: CalendarDays,
    fallback: "/schedule/reflection",
    ready: () => "/schedule/alignment",
    alwaysStandalone: true,
  },
  {
    key: "activities",
    label: "Activities",
    icon: Palette,
    fallback: "/activities/reflection",
    ready: () => "/activities/alignment",
    alwaysStandalone: true,
  },
];

function PrivateSharedLegend() {
  return (
    <div
      className="card-soft p-4 sm:p-5 flex flex-col sm:flex-row gap-4 sm:items-center bg-gradient-to-r from-[#F5F1FB] to-white border-l-4 border-[#3D1A78]"
      data-testid="joint-picker-legend"
    >
      <div className="flex items-center gap-2 shrink-0">
        <Lock size={16} className="text-[#3D1A78]" />
        <span className="text-sm font-semibold text-[#1A1330]">
          Private Reflection
        </span>
      </div>
      <ArrowRight size={14} className="text-[#6E6787] hidden sm:block shrink-0" />
      <div className="flex items-center gap-2 shrink-0">
        <Handshake size={16} className="text-[#0F7676]" />
        <span className="text-sm font-semibold text-[#1A1330]">
          Shared Alignment
        </span>
      </div>
      <p className="text-xs text-[#4B4567] leading-relaxed">
        Your reflective answers stay private. Only the material you
        intentionally choose for comparison appears in the joint report —
        your co-parent never sees your private notes.
      </p>
    </div>
  );
}

function BigCircle({ to, primary, title, subtitle, icon: Icon, testid, tone }) {
  const isSafety = tone === "safety";
  return (
    <Link
      to={to}
      className={`group relative flex flex-col items-center text-center rounded-3xl border-2 p-6 sm:p-8 transition-all hover:-translate-y-0.5 hover:shadow-xl ${
        isSafety
          ? "border-[#C74A4A] bg-gradient-to-br from-[#FDECEC] to-white hover:bg-[#FBE0E0]"
          : primary
            ? "border-[#3D1A78] bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] text-white hover:from-[#2f1360] hover:to-[#1F8F8F]"
            : "border-[#E5E0EE] bg-white hover:border-[#3D1A78]"
      }`}
      data-testid={testid}
    >
      <div
        className={`w-20 h-20 sm:w-24 sm:h-24 rounded-full grid place-items-center mb-4 ${
          isSafety
            ? "bg-white text-[#A93636]"
            : primary
              ? "bg-white/20 text-white"
              : "bg-[#F1EEF7] text-[#3D1A78]"
        }`}
      >
        <Icon size={36} strokeWidth={2} />
      </div>
      <div
        className={`font-serif text-lg sm:text-xl leading-tight ${
          primary && !isSafety ? "text-white" : "text-[#1A1330]"
        }`}
      >
        {title}
      </div>
      <div
        className={`text-xs mt-1.5 ${
          primary && !isSafety ? "text-white/85" : "text-[#4B4567]"
        }`}
      >
        {subtitle}
      </div>
    </Link>
  );
}

function TopicCircle({ tile, shareId }) {
  const Icon = tile.icon;
  if (tile.comingSoon) {
    return (
      <div
        className="flex flex-col items-center text-center rounded-2xl border border-[#EFECF6] bg-[#FAF8FD] p-4 opacity-70"
        data-testid={`joint-picker-topic-${tile.key}`}
      >
        <div className="w-14 h-14 rounded-full grid place-items-center bg-white text-[#6E6787] mb-2">
          <Icon size={22} strokeWidth={2} />
        </div>
        <div className="text-sm font-semibold text-[#4B4567]">{tile.label}</div>
        <div className="mt-1 text-[10px] uppercase tracking-[0.14em] font-bold text-[#3D1A78] bg-[#EFE9F9] rounded-full px-2 py-0.5">
          Coming soon
        </div>
      </div>
    );
  }
  // Standalone reflection-based topics (Communication, Parenting Schedule,
  // Activities) have their own reflection→alignment flow; they don't need
  // the SNC2 pair-and-compare share id.
  const isStandalone = tile.alwaysStandalone;
  const href = isStandalone
    ? tile.fallback
    : shareId
      ? tile.ready(shareId)
      : tile.fallback;
  const isReady = !isStandalone && Boolean(shareId);
  return (
    <Link
      to={href}
      className="flex flex-col items-center text-center rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:shadow-md transition-all"
      data-testid={`joint-picker-topic-${tile.key}`}
    >
      <div className="w-14 h-14 rounded-full grid place-items-center bg-[#F1EEF7] text-[#3D1A78] mb-2">
        <Icon size={22} strokeWidth={2} />
      </div>
      <div className="text-sm font-semibold text-[#1A1330]">{tile.label}</div>
      <div className="mt-1 text-[10px] uppercase tracking-[0.14em] font-semibold text-[#3D1A78]">
        {isStandalone ? "Start reflection" : isReady ? "Open compare" : "Start"}
      </div>
    </Link>
  );
}

export default function JointReportsPicker() {
  const navigate = useNavigate();
  const [snc, setSnc] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await api.get("/snc2/compare/dashboard/highlights");
        if (!cancelled) setSnc(r.data || null);
      } catch (err) {
        // Non-fatal — the picker still renders with fallback links.
        logError("joint picker highlights failed", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const shareId = snc?.ready && snc?.share_id ? snc.share_id : null;

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* New Front Door nudge — the picker is being superseded by the
            four-circle dashboard root. Keep this route live for parents who
            already bookmarked it, but point them home. */}
        <div
          className="mb-6 rounded-2xl border border-[#D6CFE8] bg-gradient-to-br from-[#F8F7FC] to-[#EFE9F9] p-4 flex items-start sm:items-center gap-3 sm:gap-4 flex-col sm:flex-row"
          data-testid="joint-picker-front-door-nudge"
        >
          <div className="flex-1">
            <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
              New home for co-parenting pathways
            </div>
            <p className="text-[14px] text-[#1A1330] leading-relaxed mt-1 !mb-0">
              We&rsquo;ve moved to a simpler four-pathway front door on your
              dashboard — Co-Parenting, Communication, Family Violence &amp;
              Safety, and Child Needs.
            </p>
          </div>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-4 py-2 text-sm font-semibold hover:bg-[#2A0F5F] transition self-start sm:self-auto"
            data-testid="joint-picker-goto-front-door"
          >
            Try the new front door
            <ArrowRight size={14} />
          </Link>
        </div>

        <div className="mb-8">
          <div className="eyebrow text-[#3D1A78] mb-2">Joint reports</div>
          <h1
            className="font-serif text-3xl sm:text-4xl md:text-5xl text-[#1A1330] leading-tight"
            data-testid="joint-picker-title"
          >
            What do you want to align on?
          </h1>
          <p className="text-[#4B4567] mt-3 max-w-2xl leading-relaxed">
            Pick a full joint report — or focus on one area you're not on the
            same page about yet. Your co-parent uses their own account —{" "}
            <span className="text-[#1A1330] font-medium">
              you never share passwords
            </span>
            .
          </p>
        </div>

        <div className="mb-8">
          <PrivateSharedLegend />
        </div>

        {/* Parent-initiated: send my code to a professional. */}
        <div
          className="mb-6 rounded-2xl border border-[#D6CFE8] bg-white p-4 flex items-start sm:items-center gap-3 sm:gap-4 flex-col sm:flex-row"
          data-testid="joint-picker-send-to-professional"
        >
          <div className="flex-1">
            <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
              Ready to hand this off?
            </div>
            <p className="text-[14px] text-[#1A1330] leading-relaxed mt-1 !mb-0">
              Send your Alignment Code directly to a professional (mediator,
              attorney, therapist, parent facilitator). We&rsquo;ll email
              them the code — you keep your answers private.
            </p>
          </div>
          <Link
            to="/professionals"
            className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-4 py-2 text-sm font-semibold hover:bg-[#2A0F5F] transition self-start sm:self-auto"
            data-testid="joint-picker-goto-professionals"
          >
            Send to a professional
            <ArrowRight size={14} />
          </Link>
        </div>

        {/* Two big circles */}
        <div
          className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6"
          data-testid="joint-picker-primary-circles"
        >
          <BigCircle
            to={shareId ? `/joint-professional-report?share=${encodeURIComponent(shareId)}` : "/special-needs-v2/compare"}
            primary
            title="Complete Co-Parenting Agreement"
            subtitle={
              shareId
                ? "All areas — ready to open and share"
                : "All areas — start the pair-and-compare flow"
            }
            icon={Sparkle}
            testid="joint-picker-complete-circle"
          />
          <BigCircle
            to="/safety"
            title="Family Violence · Communication Safety"
            subtitle="Confidential — separate path"
            icon={ShieldAlert}
            testid="joint-picker-safety-circle"
            tone="safety"
          />
        </div>

        {/* Crisis line — surfaces beneath the Safety circle so parents in
            immediate danger see the hotline without having to enter the
            assessment first. */}
        <div
          className="mt-3 rounded-2xl border border-[#F3D3D3] bg-[#FDF6F6] px-4 py-3 flex items-center gap-3"
          data-testid="joint-picker-crisis-banner"
        >
          <Phone size={16} className="text-[#A93636] shrink-0" />
          <p className="text-xs text-[#4B4567] leading-relaxed">
            If you're in immediate danger, dial <strong>911</strong>. National
            Domestic Violence Hotline:{" "}
            <a
              href="tel:18007997233"
              className="text-[#A93636] font-semibold underline"
              data-testid="joint-picker-crisis-phone"
            >
              1-800-799-7233
            </a>
            {" · "}
            <a
              href="sms:88788?body=START"
              className="text-[#A93636] font-semibold underline"
              data-testid="joint-picker-crisis-text"
            >
              text START to 88788
            </a>
            .
          </p>
        </div>

        <div className="mt-12">
          <div className="text-center mb-6">
            <div className="eyebrow text-[#3D1A78]">Or focus on one area</div>
            <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-1">
              We don't need the whole report. We just disagree about…
            </h2>
          </div>
          <div
            className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4"
            data-testid="joint-picker-topic-grid"
          >
            {TOPIC_TILES.map((t) => (
              <TopicCircle key={t.key} tile={t} shareId={shareId} />
            ))}
          </div>
          {loading ? null : !shareId && (
            <p
              className="mt-4 text-center text-xs text-[#6E6787]"
              data-testid="joint-picker-pair-hint"
            >
              Tiles marked <em>Start</em> begin the pair-and-compare flow.
              You'll invite your co-parent once you're inside the topic.
            </p>
          )}
        </div>

        <div className="mt-10 text-center flex flex-wrap justify-center gap-4">
          <Link
            to="/samples"
            className="text-xs text-[#3D1A78] hover:text-[#2A0F5F] underline underline-offset-2"
            data-testid="joint-picker-samples-link"
          >
            Browse sample PDFs →
          </Link>
          <Link
            to="/dashboard"
            className="text-xs text-[#4B4567] hover:text-[#3D1A78] underline underline-offset-2"
            data-testid="joint-picker-back-to-dashboard"
          >
            ← Back to dashboard
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
