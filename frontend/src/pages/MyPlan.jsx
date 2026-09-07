import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, ClipboardCheck, Heart, Shield, Compass, Mail, Send } from "lucide-react";
import AppShell from "../components/AppShell";
import DemoModeBanner from "../components/DemoModeBanner";
import PersonalizedRecommendations from "../components/PersonalizedRecommendations";
import SectionCoaching from "../components/SectionCoaching";
import CertificateCard from "../components/CertificateCard";
import GrowthTracker from "../components/GrowthTracker";
import FoundationStatementShareModal from "../components/foundation/FoundationStatementShareModal";
import FoundationStatementVoicePlayer from "../components/foundation/FoundationStatementVoicePlayer";
import { api } from "../lib/api";

/**
 * MyPlan — the "personalized parent dashboard" surface.
 *
 * Pulls the parent's own prep data + the AI-synthesized summary and lays
 * out a snapshot of everything they've built: progress, foundation, child
 * goals, mediation readiness, plus overall coaching insights (strengths,
 * growth areas, next steps).
 *
 * This page is a *read-only* companion to /dashboard. All edit links point
 * back into the individual module pages, and the coaching card reuses the
 * shared /api/mediation/section-coaching endpoint with section="overall".
 */

const MODULE_LABELS = {
  child_goals: "Child Goals",
  issues: "Issues & Concerns",
  priority: "Priority Agenda",
  comm_style: "Communication Style",
  reflection: "Foundation Statement",
  readiness: "Mediation Readiness",
};

function Card({ title, icon: Icon, children, editHref, testid }) {
  return (
    <section
      className="card-soft p-6"
      data-testid={testid}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {Icon && <Icon size={16} className="text-[#3D1A78]" />}
          <h3 className="font-serif text-lg text-[#1A1330]">{title}</h3>
        </div>
        {editHref && (
          <Link
            to={editHref}
            className="text-xs text-[#3D1A78] hover:underline"
            data-testid={`${testid}-edit`}
          >
            Edit
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}

function Empty({ text, to, cta }) {
  return (
    <div className="text-sm text-[#857E9C]">
      {text}{" "}
      {to && (
        <Link to={to} className="text-[#3D1A78] hover:underline font-medium">
          {cta || "Start"} →
        </Link>
      )}
    </div>
  );
}

export default function MyPlan() {
  const [prep, setPrep] = useState({ completed: {}, data: {} });
  const [summary, setSummary] = useState(null);
  const [gmail, setGmail] = useState({ connected: false });
  const [loading, setLoading] = useState(true);
  const [shareOpen, setShareOpen] = useState(false);
  // Highlights the section currently being read aloud (see the
  // `FoundationStatementVoicePlayer` `onSectionChange` callback).
  const [activeVoiceSection, setActiveVoiceSection] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.get("/mediation/prep").catch(() => ({ data: {} })),
      api.get("/mediation/summaries").catch(() => ({ data: [] })),
      api.get("/gmail/status").catch(() => ({ data: { connected: false } })),
    ]).then(([p, s, g]) => {
      if (cancelled) return;
      setPrep(p.data || { completed: {} });
      // Latest summary = first entry (backend returns newest first)
      const list = Array.isArray(s?.data) ? s.data : s?.data?.summaries || [];
      setSummary(list.length > 0 ? list[0] : null);
      setGmail(g.data || { connected: false });
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const completed = prep.completed || {};
  // The /api/mediation/prep endpoint returns the parent's saved state
  // at the TOP level (`reflection`, `child_goals`, `comm_style`, etc.);
  // there is no nested `.data` envelope. Reading `prep.data` used to
  // yield `{}` here, silently emptying every card on this page.
  const data = prep;
  const doneCount = Object.values(completed).filter(Boolean).length;
  const totalModules = Object.keys(MODULE_LABELS).length;

  const goals = data.child_goals?.selected_goals || data.child_goals?.goals || [];
  // Foundation Statement is composed from the four Reflection prompts —
  // Reflection.jsx saves them as `child_lens` / `own_part` /
  // `best_outcome` / `coparent_feedback` on the reflection dict, NOT
  // as a single `text`/`foundation` field. Legacy prompt keys are
  // included so pre-2026 reflections continue to render. If a very
  // old row happened to save a monolithic `text`/`foundation` string
  // we still surface it as a final fallback.
  const foundationSections = (() => {
    const r = data.reflection || {};
    const canonical = [
      { key: "child_lens", label: "Through your child's eyes" },
      { key: "own_part", label: "Your own part" },
      { key: "best_outcome", label: "Your best-case outcome" },
      { key: "coparent_feedback", label: "Through your co-parent's eyes" },
    ];
    const parts = canonical
      .map((s) => ({
        label: s.label,
        text: typeof r[s.key] === "string" ? r[s.key].trim() : "",
      }))
      .filter((s) => s.text.length > 0);
    if (parts.length > 0) return parts;
    // Legacy fallbacks — older prompt keys or a monolithic string.
    const legacy = ["worry", "triggers", "calm_strategy", "appreciation", "release", "text", "foundation"]
      .map((k) => (typeof r[k] === "string" ? r[k].trim() : ""))
      .filter(Boolean);
    return legacy.length > 0
      ? [{ label: "", text: legacy.join("\n\n") }]
      : [];
  })();
  const foundation = foundationSections.map((s) => s.text).join("\n\n");
  const summaryReady = Boolean(summary?.summary_id || summary?.readiness_score !== undefined);

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="my-plan-back-link"
        >
          <ArrowLeft size={14} /> Back to Dashboard
        </Link>
        <h1 className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight" data-testid="my-plan-title">
          Your Plan
        </h1>
        <p className="text-[#4B4567] mt-2 max-w-2xl">
          A snapshot of everything you&apos;ve built — your progress, your goals, and
          what to focus on next.
        </p>

        <div className="mt-6">
          <DemoModeBanner />
        </div>

        {loading ? (
          <div className="mt-10 text-[#857E9C]" data-testid="my-plan-loading">Loading your plan…</div>
        ) : (
          <div className="mt-8 grid gap-5 md:grid-cols-2">
            {/* Progress + Assessments Completed (combined) */}
            <Card title="Assessments Completed" icon={ClipboardCheck} testid="myplan-progress">
              <div className="text-3xl font-serif text-[#1A1330]">
                {doneCount}
                <span className="text-lg text-[#857E9C]"> / {totalModules}</span>
              </div>
              <ul className="mt-3 space-y-1.5 text-sm">
                {Object.entries(MODULE_LABELS).map(([k, label]) => (
                  <li key={k} className="flex items-center gap-2">
                    <span
                      className={
                        completed[k]
                          ? "text-[#3D1A78] font-semibold"
                          : "text-[#857E9C]"
                      }
                    >
                      {completed[k] ? "✓" : "◻"}
                    </span>
                    <span className={completed[k] ? "text-[#1A1330]" : "text-[#4B4567]"}>
                      {label}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>

            {/* Foundation Statement */}
            <Card
              title="Foundation Statement"
              icon={Heart}
              editHref="/reflection"
              testid="myplan-foundation"
            >
              {foundation ? (
                <div className="space-y-3 text-sm text-[#1A1330] leading-relaxed">
                  {foundationSections.length > 1 || foundationSections[0]?.label ? (
                    foundationSections.map((s, i) => {
                      // Find the raw prompt key so we can highlight the
                      // section currently being spoken aloud by the
                      // voice player.
                      const promptKey = (
                        s.label === "Through your child's eyes" ? "child_lens"
                        : s.label === "Your own part" ? "own_part"
                        : s.label === "Your best-case outcome" ? "best_outcome"
                        : s.label === "Through your co-parent's eyes" ? "coparent_feedback"
                        : null
                      );
                      const active = promptKey && promptKey === activeVoiceSection;
                      return (
                        <div
                          key={i}
                          data-testid={`myplan-foundation-section-${i}`}
                          data-voice-active={active ? "true" : undefined}
                          className={
                            active
                              ? "rounded-xl bg-[#EFE9F9] px-3 py-2 -mx-3 transition-colors"
                              : "transition-colors"
                          }
                        >
                          {s.label && (
                            <div className="text-[10px] uppercase tracking-[0.15em] font-bold text-[#3D1A78] mb-1">
                              {s.label}
                            </div>
                          )}
                          <p className="whitespace-pre-wrap line-clamp-3">{s.text}</p>
                        </div>
                      );
                    })
                  ) : (
                    <p className="whitespace-pre-wrap line-clamp-6">
                      {foundation}
                    </p>
                  )}
                  <div className="pt-1 flex flex-wrap items-center gap-2">
                    <FoundationStatementVoicePlayer
                      variant="inline"
                      compact
                      onSectionChange={setActiveVoiceSection}
                    />
                    <button
                      type="button"
                      onClick={() => setShareOpen(true)}
                      className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-3 py-1.5 text-xs font-semibold transition-colors"
                      data-testid="myplan-foundation-share"
                    >
                      <Send size={12} /> Send to co-parent or mediator
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <Empty
                    text="You haven't written your Foundation Statement yet."
                    to="/reflection"
                    cta="Write it"
                  />
                  <Link
                    to="/foundation/demo"
                    className="inline-flex items-center gap-1 text-xs text-[#3D1A78] hover:underline font-medium"
                    data-testid="myplan-foundation-see-example"
                  >
                    See what one looks like →
                  </Link>
                </div>
              )}
            </Card>

            {/* Child Goals */}
            <Card
              title="Child Goals"
              icon={Heart}
              editHref="/prep/child-goals"
              testid="myplan-child-goals"
            >
              {goals.length > 0 ? (
                <ul className="space-y-1.5 text-sm text-[#1A1330]">
                  {goals.slice(0, 5).map((g) => (
                    <li key={typeof g === "string" ? g : g.id} className="flex items-start gap-2">
                      <span className="text-[#3D1A78] mt-1">•</span>
                      <span>{typeof g === "string" ? g : g.label || g.id}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty text="You haven't selected child goals yet." to="/prep/child-goals" />
              )}
            </Card>

            {/* Mediation Preparation status */}
            <Card
              title="Mediation Preparation"
              icon={Shield}
              testid="myplan-mediation"
            >
              {summaryReady ? (
                <>
                  <div className="text-sm text-[#1A1330]">
                    Your Mediation Prep Summary is ready.
                    {summary?.readiness_label && (
                      <span className="text-[#857E9C]"> · {summary.readiness_label}</span>
                    )}
                  </div>
                  <Link
                    to="/summary"
                    className="inline-flex items-center gap-1 text-sm text-[#3D1A78] hover:underline mt-3 font-medium"
                    data-testid="myplan-open-summary"
                  >
                    Open your summary →
                  </Link>
                </>
              ) : (
                <Empty
                  text="Complete all sections to generate your Mediation Prep Summary."
                  to="/dashboard"
                  cta="Continue"
                />
              )}
            </Card>

            {/* Gmail connection */}
            <Card title="Gmail" icon={Mail} testid="myplan-gmail">
              {gmail.connected ? (
                <>
                  <div className="text-sm text-[#1A1330]">
                    Connected as <span className="font-semibold">{gmail.google_email || "your Google account"}</span>.
                  </div>
                  <Link
                    to="/gmail"
                    className="inline-flex items-center gap-1 text-sm text-[#3D1A78] hover:underline mt-3 font-medium"
                    data-testid="myplan-open-gmail"
                  >
                    Open inbox →
                  </Link>
                </>
              ) : (
                <>
                  <p className="text-sm text-[#4B4567]">
                    Read, search, and send co-parenting emails without leaving the app.
                  </p>
                  <Link
                    to="/gmail"
                    className="inline-flex items-center gap-1 text-sm text-[#3D1A78] hover:underline mt-3 font-medium"
                    data-testid="myplan-connect-gmail"
                  >
                    Connect Gmail →
                  </Link>
                </>
              )}
            </Card>

            {/* Recommended Next Steps — reuses Summary's component */}
            {summary && (
              <div className="md:col-span-2">
                <PersonalizedRecommendations summary={summary} />
              </div>
            )}

            {/* Longitudinal growth tracking — timeline of readiness snapshots
                with 30/60/90-day comparisons and coach insights. */}
            <div className="md:col-span-2" id="growth">
              <GrowthTracker />
            </div>

            {/* Certificate of Completion — locked state until 5+ core steps
                are done, or always available to demo users for preview. */}
            <div className="md:col-span-2" id="certificate">
              <CertificateCard />
            </div>

            {/* Overall coaching (Strengths + Growth Areas + One Next Step) */}
            {summary && (
              <div className="md:col-span-2">
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
                  <Compass size={12} /> Coach&apos;s view of your journey
                </div>
                <SectionCoaching
                  section="overall"
                  ready={true}
                  testid="myplan-overall-coaching"
                  data={{
                    modules_completed: doneCount,
                    modules_total: totalModules,
                    child_goals: goals,
                    foundation_excerpt: (foundation || "").slice(0, 400),
                    readiness_score: summary.readiness_score,
                    readiness_label: summary.readiness_label,
                    top_concerns: summary.top_concerns,
                    priority_agenda: summary.priority_agenda,
                    communication_goals: summary.communication_goals,
                    flexibility_areas: summary.flexibility_areas,
                  }}
                />
              </div>
            )}
          </div>
        )}
      </div>
      <FoundationStatementShareModal
        open={shareOpen}
        onClose={() => setShareOpen(false)}
      />
      {foundation && (
        <FoundationStatementVoicePlayer
          variant="floating"
          onSectionChange={setActiveVoiceSection}
        />
      )}
    </AppShell>
  );
}
