/**
 * SA CoParents — Self Journey (multi-page guided experience), from the user's SelfJourney.jsx.
 *
 * App fit (SelfJourneyPage.jsx passes these in):
 *  - Safety: the Family check-in lives on SACOparentsAlign (checkinHref). The parent then picks
 *    "clear" or "concern" themselves; that pick is never printed, shared or sent to Align. The Journey Guide
 *    receives it only to keep its replies safe (no direct contact / joint sessions on "concern").
 *  - Self-Assessment, Co-Parenting Assessment and Child's Needs open the app's existing ones (panel props).
 *  - The approved Foundation Statement is saved into the existing Foundation Statement (onApproveFoundation).
 *  - Help uses the app's AI coach (onAskAssistant), behind the AI notice.
 */

import React, { useEffect, useRef, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

import { ArrowLeft, Hand } from "lucide-react";

import { useAiGuard } from "../../components/aiNotice/AiGuard";
import Disclaimer from "../../components/Disclaimer";
import { AwardModal, useMilestoneAwards } from "./Awards";
import { CheckInCard, CheckInDialog, isCheckInDue } from "./CheckIn";
import {
  CONFLICT_LEVELS, PathCard, PathNote, RecommendedBadge, StagePicker, StepComplete,
  conflictLevel, hidesWorkingTogether, isRecommended,
} from "./Path";
import GuideAvatar from "./GuideAvatar";
import { readyQuestions } from "../selfJourneyGuide/guideAnswers";
import ListenButton, { stopReading } from "../selfJourneyGuide/ListenButton";
import "./selfJourney.css";

/* ------------------------------------------------------------------ */
/* Step configuration                                                  */
/* ------------------------------------------------------------------ */

export const STEPS = [
  {
    slug: "safety",
    short: "Safety",
    kicker: "Start here",
    title: "Your Safety Comes First",
    intro:
      "Every family's situation is different. Before beginning your Self Journey, SA CoParents wants to help you determine whether this pathway is appropriate for your circumstances.",
    minutes: 2,
    cta: "Begin My Self Journey",
    chat:
      "This first step checks whether this pathway fits your family. I can walk you through what each part of the check-in means.",
    suggestions: ["Why is this first?", "Who sees my answers?"],
  },
  {
    slug: "situation",
    short: "Situation",
    kicker: "Step 1 · Your situation",
    title: "Understanding Where You Are Today",
    intro: "Take a moment to describe where things stand. There are no right answers.",
    minutes: 5,
    cta: "Continue to Self Assessment",
    chat:
      "Welcome to your Self Journey. You do not have to solve everything today. Let's begin by understanding your situation and what matters most to your child.",
    suggestions: ["Help me get started", "What should I include?"],
  },
  {
    slug: "self-assessment",
    short: "Self",
    kicker: "Step 2 · About you",
    title: "Understanding Yourself as a Parent",
    intro: "Reflect on where you are today with your Self-Assessment. It's just for you, and you can revisit it anytime.",
    minutes: 5,
    cta: "Explore My Co-Parenting Relationship",
    chat:
      "Understanding yourself can help you make thoughtful decisions for your child. Let's explore your strengths, challenges, and what you hope to improve.",
    suggestions: ["What does emotional readiness mean?", "How is this used?"],
  },
  {
    slug: "coparenting",
    short: "Co-parenting",
    kicker: "Step 3 · Your relationship",
    title: "Understanding Your Co-Parenting Relationship",
    intro:
      "Look at how decisions, communication and boundaries work today, and what might work better.",
    minutes: 6,
    cta: "Identify My Child's Needs",
    chat:
      "Parents do not have to agree about everything to identify what their child needs. Let's explore the parenting arrangements and communication approaches that may work best for your situation.",
    suggestions: ["What is parallel parenting?", "Setting boundaries"],
  },
  {
    slug: "child-needs",
    short: "Child",
    kicker: "Step 4 · Your child",
    title: "Understanding Your Child's Needs",
    intro:
      "Shift the focus to your child. Open the areas where they may need support, stability or extra resources.",
    minutes: 6,
    cta: "Create My Foundation Statement",
    chat:
      "Every child has different needs. Let's identify the areas where your child may need support, stability, encouragement, or additional resources.",
    suggestions: ["Which areas should I open?", "Signs my child needs support"],
  },
  {
    slug: "foundation",
    short: "Foundation",
    kicker: "Step 5 · Your foundation",
    title: "Building Your Parenting Foundation",
    intro:
      "Name the principles that will guide your decisions. We'll turn your answers into a draft you can edit.",
    minutes: 8,
    cta: "Prepare for Mediation",
    chat:
      "Your Foundation Statement is an opportunity to identify what matters most to your child and how your own actions can support those needs.",
    suggestions: ["Show me an example", "Help me phrase this"],
  },
  {
    slug: "mediation",
    short: "Mediation",
    kicker: "Step 6 · Next conversations",
    title: "Preparing for Child-Focused Mediation",
    intro: "Organize your issues, interests and possible solutions so you walk in prepared.",
    minutes: 8,
    cta: "View My Journey Summary",
    chat:
      "Mediation preparation is not about winning an argument. It is about understanding your concerns, identifying your child's needs, and considering possible solutions.",
    suggestions: ["What happens in mediation?", "Is mediation right for me?"],
  },
  {
    slug: "summary",
    short: "Summary",
    kicker: "Your journey",
    title: "Your SA CoParents Self Journey",
    intro: "Here is everything you've worked through. Review, edit any section, or download it to share.",
    minutes: 3,
    cta: "Save My Journey",
    chat: "This summary brings your work together. I can help you decide what to share and with whom.",
    suggestions: ["What should I bring to mediation?", "Who can I share this with?"],
  },
];

const SITUATION_QUESTIONS = [
  ["currentSituation", "What is your current parenting situation?"],
  ["topConcerns", "What concerns are most important to you?"],
  ["workingWell", "What is working well for your child?"],
  ["toImprove", "What would you like to improve?"],
];

// The parent's own pick after the Family check-in (same wording as the Journey page).
const SAFETY_PICKS = [
  { id: "clear", name: "No · lower conflict", desc: "No safety concerns right now." },
  { id: "concern", name: "Yes · there are safety concerns", desc: "Your journey will skip anything that needs direct contact with the other parent." },
];

const APPROACHES = [
  { id: "cooperative", name: "Working together", desc: "Shared decisions and regular communication." },
  { id: "parallel", name: "Parallel parenting", desc: "Each parent runs their own time, with minimal, structured contact." },
  { id: "unsure", name: "Not sure yet", desc: "That's okay. The assistant can help you think it through." },
];

const CHILD_AREAS = [
  ["educational", "Educational needs", "School routines, learning support and staying on track across two homes."],
  ["medical", "Medical needs", "Ongoing care, medications and how health decisions are shared."],
  ["emotional", "Emotional & psychological needs", "How your child is coping, and the stability and reassurance that help."],
  ["developmental", "Developmental & special needs", "Milestones, therapies and supports that need consistency."],
];

const FOUNDATION_QUESTIONS = [
  ["childNeedsMost", "What does your child need most from you?"],
  ["values", "What parenting values matter most?"],
  ["stability", "What can you do to create greater stability?"],
  ["commitments", "What commitments are within your control?"],
  ["success", "What would successful parenting arrangements look like?"],
];

const MEDIATION_FIELDS = [
  ["issues", "Issues to address"],
  ["childConcerns", "Child-focused concerns"],
  ["options", "Possible parenting options"],
  ["flexibility", "Where I can be flexible"],
  ["questions", "Questions for a mediator or professional"],
  ["boundaries", "Communication boundaries & safeguards"],
];

const DEFAULT_RESOURCES = [
  { label: "In immediate danger", detail: "Call 911", href: "tel:911" },
  {
    label: "National Domestic Violence Hotline",
    detail: "1-800-799-7233 or text START to 88788",
    href: "tel:18007997233",
  },
];

export const EMPTY_PROGRESS = {
  maxStepReached: 0,
  stage: null, // "separated" | "planning" | "communication" | "ongoing" | "highConflict" (Path.jsx STAGES)
  safety: { status: "none" }, // "none" | "clear" | "concern"
  situation: {},
  coparenting: { approach: null, agree: "", disagree: "" },
  childNeeds: { opened: [] },
  foundation: { answers: {}, draft: "", approved: false, approvedAt: null },
  mediation: {},
  checkIns: [], // [{ date, hardest, wentWell, helpNext, planFits }] — private, never printed or shared
  awards: {}, // { selfAssessment, coparenting, foundation, journey }: date each award was earned
  updatedAt: null,
};

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

export default function SelfJourney({
  initialProgress,
  onSave,
  checkinHref,
  SelfAssessmentPanel,
  selfAssessmentCount = 0,
  CoParentingPanel,
  ChildNeedsPanels = {},
  onApproveFoundation,
  onAskAssistant,
  safetyResources = DEFAULT_RESOURCES,
  onDownloadPdf,
  onShare,
  onQuickExit,
  logoSrc,
  calm = false,
  homeHref = "/journey",
  coparentingDone = false,
  lastSelfAssessmentAt = null,
  awardsPaused = false,
  awardLogoSrc,
  onDownloadCertificate,
  onRetakeSelfAssessment,
  checkInDays = 30,
}) {
  const { step: slug } = useParams();
  const navigate = useNavigate();
  const [progress, setProgress] = useState(() => ({ ...EMPTY_PROGRESS, ...(initialProgress || {}) }));
  const [chatOpen, setChatOpen] = useState(false);
  const [checkInOpen, setCheckInOpen] = useState(false);
  const [checkInHidden, setCheckInHidden] = useState(false);
  const [justCompleted, setJustCompleted] = useState(null); // step number (1–6) whose green arrow was just pressed
  const [toast, setToast] = useState("");
  const contentRef = useRef(null);
  const dirty = useRef(false);
  const saveRef = useRef(onSave);
  saveRef.current = onSave;

  const index = STEPS.findIndex((s) => s.slug === slug);
  const step = STEPS[index];
  const concern = progress.safety.status === "concern";
  const level = conflictLevel(progress);

  const [award, setAward] = useMilestoneAwards({
    progress, setProgress, saveRef,
    earned: { selfAssessment: selfAssessmentCount > 0, coparenting: coparentingDone, foundation: progress.foundation.approved },
    // Never over the Safety page; awards wait until the parent has moved on.
    paused: awardsPaused || chatOpen || checkInOpen || index <= 0 || index > progress.maxStepReached,
  });

  // Scroll to top and close the assistant whenever the page changes
  useEffect(() => {
    setChatOpen(false);
    window.scrollTo?.(0, 0);
  }, [slug]);

  // Answers save quietly a moment after the parent stops typing or picking.
  useEffect(() => {
    if (!dirty.current) return undefined;
    const t = setTimeout(() => {
      dirty.current = false;
      Promise.resolve(saveRef.current?.(progress)).catch(() => {});
    }, 1200);
    return () => clearTimeout(t);
  }, [progress]);

  // Unknown slug, or a page the parent hasn't reached yet → send them to their furthest page
  if (index === -1 || index > progress.maxStepReached) {
    return <Navigate to={`/self-journey/guided/${STEPS[progress.maxStepReached].slug}`} replace />;
  }

  const update = (section, patch) => {
    dirty.current = true;
    setProgress((p) => ({ ...p, [section]: { ...p[section], ...patch } }));
  };

  const flash = (message) => {
    setToast(message);
    setTimeout(() => setToast(""), 2600);
  };

  const persist = async (next = progress, message = "Progress saved. You can pick up right here anytime.") => {
    dirty.current = false;
    const stamped = { ...next, updatedAt: new Date().toISOString() };
    setProgress(stamped);
    try {
      await onSave?.(stamped);
      if (message) flash(message);
    } catch (e) {
      flash("We couldn't save just now. Please try again.");
    }
  };

  const checkInDue =
    index > 0 && !checkInHidden && isCheckInDue({ checkIns: progress.checkIns, lastSelfAssessmentAt, checkInDays });

  const saveCheckIn = async (entry, message = "Check-in saved. See you next month.") => {
    setCheckInOpen(false);
    setCheckInHidden(true);
    await persist({ ...progress, checkIns: [...progress.checkIns, entry].slice(-60) }, message);
  };

  // Only the safety step is required before moving on
  const canContinue = index !== 0 || progress.safety.status !== "none";

  const goTo = (i) => {
    if (i > progress.maxStepReached) return;
    setJustCompleted(null);
    navigate(`/self-journey/guided/${STEPS[i].slug}`);
  };

  const handleNext = async () => {
    if (!canContinue) return;
    if (index === STEPS.length - 1) {
      const first = !progress.awards?.journey;
      const next = first ? { ...progress, awards: { ...progress.awards, journey: new Date().toISOString() } } : progress;
      await persist(next, "Your Self Journey is saved.");
      if (first) setAward("journey");
      return;
    }
    const next = { ...progress, maxStepReached: Math.max(progress.maxStepReached, index + 1) };
    await persist(next, index === 0 ? "Progress saved." : null);
    setJustCompleted(index === 0 ? null : index);
    navigate(`/self-journey/guided/${STEPS[index + 1].slug}`);
  };

  const approveFoundation = async (draft) => {
    try {
      await onApproveFoundation?.(draft);
      const foundation = { ...progress.foundation, draft, approved: true, approvedAt: new Date().toISOString() };
      await persist({ ...progress, foundation }, "Saved as your Foundation Statement.");
    } catch {
      flash("We couldn't save your Foundation Statement just now. Please try again.");
    }
  };

  const ctaLabel = index === 0 && concern ? "Continue on My Safety Pathway" : step.cta;
  const isLast = index === STEPS.length - 1;

  return (
    <div className={`sj${calm ? " is-calm-mode" : ""}`} data-testid="self-journey" data-step={step.slug}>
      <header className="sj-header">
        <Link to={homeHref} className="sj-brand" data-testid="sj-home-link" aria-label="SA CoParents, back to your Journey">
          <GuideAvatar size={34} logoSrc={logoSrc} calm={index === 0} decorative testid="sj-header-avatar" />
          <span className="sj-brand-name">SA CoParents</span>
        </Link>
        <div className="sj-header-actions">
          <button type="button" className="sj-link-btn" onClick={() => persist()} data-testid="sj-save-later">
            <SaveIcon /> Save &amp; finish later
          </button>
          <button type="button" className="sj-exit-btn" onClick={onQuickExit} data-testid="sj-quick-exit">
            Quick Exit
          </button>
        </div>
      </header>

      <ProgressBar index={index} max={progress.maxStepReached} onJump={goTo} />

      <main className="sj-content" ref={contentRef}>
        <Link to={homeHref} className="sj-back-link" data-testid="sj-back-to-journey">
          <ArrowLeft size={16} aria-hidden="true" /> Back to the Journey page
        </Link>
        {/* Live region stays mounted across pages so the "Step complete" message is announced. */}
        <div role="status" aria-live="polite" className="sj-step-done-region">
          {justCompleted && justCompleted === index - 1 && (
            <StepComplete number={justCompleted} next={step} onDismiss={() => setJustCompleted(null)} />
          )}
        </div>
        <p className="sj-kicker">{step.kicker}</p>
        {isRecommended(progress.stage, step.slug) && <RecommendedBadge />}
        <h1 className="sj-title" data-testid="sj-title">{step.title}</h1>
        <p className="sj-intro">{step.intro}</p>

        {checkInDue && <CheckInCard onStart={() => setCheckInOpen(true)} onLater={() => setCheckInHidden(true)} />}

        {step.slug === "safety" && (
          <SafetyPage
            status={progress.safety.status}
            checkinHref={checkinHref}
            setSafety={(status) => {
              update("safety", { status, completedAt: new Date().toISOString() });
              // Cooperative approach is not offered on the safety pathway
              if (status === "concern" && progress.coparenting.approach === "cooperative") {
                update("coparenting", { approach: null });
              }
            }}
            resources={safetyResources}
          />
        )}
        {step.slug === "situation" && (
          <SituationPage
            values={progress.situation}
            onChange={(k, v) => update("situation", { [k]: v })}
            stage={progress.stage}
            onStage={(stage) => {
              dirty.current = true;
              setProgress((p) => {
                const next = { ...p, stage };
                // "Working together" is not offered on the high and safety paths
                return hidesWorkingTogether(conflictLevel(next)) && p.coparenting.approach === "cooperative"
                  ? { ...next, coparenting: { ...p.coparenting, approach: null } }
                  : next;
              });
            }}
          />
        )}
        {step.slug === "self-assessment" && (
          SelfAssessmentPanel ? <SelfAssessmentPanel /> : <Placeholder>[Existing Self-Assessment opens here]</Placeholder>
        )}
        {step.slug === "coparenting" && (
          <CoParentingPage
            data={progress.coparenting}
            concern={concern}
            level={level}
            onChange={(patch) => update("coparenting", patch)}
            CoParentingPanel={CoParentingPanel}
          />
        )}
        {step.slug === "child-needs" && (
          <ChildNeedsPage
            explored={progress.childNeeds.opened}
            onExplore={(key) => {
              const o = progress.childNeeds.opened;
              if (!o.includes(key)) update("childNeeds", { opened: [...o, key] });
            }}
            panels={ChildNeedsPanels}
          />
        )}
        {step.slug === "foundation" && (
          <FoundationPage
            data={progress.foundation}
            onChange={(patch) => update("foundation", patch)}
            onApprove={approveFoundation}
          />
        )}
        {step.slug === "mediation" && (
          <MediationPage values={progress.mediation} level={level} onChange={(k, v) => update("mediation", { [k]: v })} />
        )}
        {step.slug === "summary" && (
          <SummaryPage
            progress={progress}
            concern={concern}
            level={level}
            selfAssessmentCount={selfAssessmentCount}
            onEdit={(i) => goTo(i)}
            onDownloadPdf={() => onDownloadPdf?.(progress)}
            onShare={() => onShare?.(progress)}
            onCheckIn={() => setCheckInOpen(true)}
            onCertificate={progress.awards?.journey ? onDownloadCertificate : null}
            resources={safetyResources}
          />
        )}
        <Disclaimer style={{ marginTop: 20 }} />
      </main>

      {!chatOpen && (
        <button type="button" className="sj-help-btn" onClick={() => setChatOpen(true)} data-testid="sj-help-open">
          <GuideAvatar size={28} logoSrc={logoSrc} calm={index === 0} decorative /> Need help with this step?
        </button>
      )}

      <footer className="sj-footer">
        <button type="button" className="sj-back" onClick={() => goTo(index - 1)} disabled={index === 0} data-testid="sj-back">
          Back
        </button>
        <button type="button" className="sj-next" onClick={handleNext} disabled={!canContinue} data-testid="sj-next">
          {ctaLabel} {!isLast && <span aria-hidden="true">→</span>}
        </button>
      </footer>

      {chatOpen && (
        <AssistantSheet
          step={step}
          isSafetyStep={index === 0}
          path={{ safety: progress.safety.status, stage: progress.stage, level }}
          onClose={() => setChatOpen(false)}
          onAsk={onAskAssistant}
          logoSrc={logoSrc}
        />
      )}

      {checkInOpen && (
        <CheckInDialog
          onClose={() => setCheckInOpen(false)}
          onSave={(entry) => saveCheckIn(entry)}
          onRetake={async (entry) => {
            await saveCheckIn(entry, "Check-in saved. Your last answers show as dotted outlines.");
            onRetakeSelfAssessment?.();
          }}
          onUpdateSituation={async (entry) => {
            await saveCheckIn(entry, "Check-in saved. Update where things stand today.");
            navigate(`/self-journey/guided/${STEPS[1].slug}`);
          }}
        />
      )}

      {award && (
        <AwardModal award={award} logoSrc={awardLogoSrc} calm={calm} onClose={() => setAward(null)} onCertificate={onDownloadCertificate} />
      )}

      {toast && (
        <div className="sj-toast" role="status" data-testid="sj-toast">
          {toast}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Shared pieces                                                       */
/* ------------------------------------------------------------------ */

function ProgressBar({ index, max, onJump }) {
  const step = STEPS[index];
  return (
    <div className="sj-progress" data-testid="sj-progress">
      <div className="sj-progress-meta">
        <strong>{index === 0 ? "Before you begin" : `Step ${index} of 7 · ${step.short}`}</strong>
        <span>About {step.minutes} min</span>
      </div>
      <div className="sj-progress-track">
        {STEPS.map((s, i) => (
          <button
            key={s.slug}
            type="button"
            className="sj-progress-seg"
            onClick={() => onJump(i)}
            disabled={i > max}
            aria-current={i === index ? "step" : undefined}
            aria-label={`Step ${i + 1} of 8: ${s.short}${i > max ? " (not yet reached)" : ""}`}
            data-testid={`sj-progress-${s.slug}`}
          >
            <span className={i === index ? "is-current" : i <= max ? "is-done" : ""} />
          </button>
        ))}
      </div>
    </div>
  );
}

function TextField({ id, label, value, onChange, rows = 3, optional }) {
  return (
    <div className="sj-field">
      <label htmlFor={id}>
        {label} {optional && <span className="sj-muted">(optional)</span>}
      </label>
      <textarea id={id} rows={rows} value={value || ""} onChange={(e) => onChange(e.target.value)} data-testid={id} maxLength={3000} />
    </div>
  );
}

function Notice({ tone = "info", children, testid }) {
  return <div className={`sj-notice sj-notice-${tone}`} data-testid={testid}>{children}</div>;
}

function Placeholder({ children }) {
  return <div className="sj-placeholder">{children}</div>;
}

function ChoiceList({ label, options, value, onPick, testid }) {
  return (
    <div className="sj-choice-list" role="radiogroup" aria-label={label}>
      {options.map((a) => (
        <button
          key={a.id}
          type="button"
          role="radio"
          aria-checked={value === a.id}
          className={`sj-choice ${value === a.id ? "is-on" : ""}`}
          onClick={() => onPick(a.id)}
          data-testid={`${testid}-${a.id}`}
        >
          <strong>{a.name}</strong>
          <span>{a.desc}</span>
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Pages                                                               */
/* ------------------------------------------------------------------ */

function SafetyPage({ status, checkinHref, setSafety, resources }) {
  return (
    <>
      <section className="sj-card">
        <h2 className="sj-card-title">Your private Safety First</h2>
        <p className="sj-small" style={{ marginTop: 0 }}>
          The check-in happens on SACOparentsAlign. Your co-parent never sees your answers, and they don&apos;t come back
          to this app.
        </p>
        <a
          href={checkinHref || undefined}
          aria-disabled={!checkinHref}
          target="_blank"
          rel="noopener noreferrer"
          className="sj-open-btn"
          style={{ marginTop: 10, width: "100%" }}
          data-testid="sj-open-checkin"
        >
          Open Safety First <span aria-hidden="true">↗</span>
          <span className="sj-sr-only"> (opens SACOparentsAlign in a new tab)</span>
        </a>
      </section>

      <h2 className="sj-subhead">After your check-in, are there safety concerns?</h2>
      <ChoiceList label="Are there safety concerns?" options={SAFETY_PICKS} value={status} onPick={setSafety} testid="sj-safety" />
      <p className="sj-small">
        Only you see this choice. It isn&apos;t shared, printed or sent to SACOparentsAlign. It shapes the steps that
        follow and keeps the Journey Guide&apos;s suggestions safe for you. You can change it anytime.
      </p>

      {status === "clear" && (
        <Notice tone="success" testid="sj-safety-notice-clear">
          You&apos;re ready to begin. If anything changes, you can return to this check at any time.
        </Notice>
      )}

      {status === "concern" && (
        <Notice tone="warning" testid="sj-safety-notice-concern">
          <strong>Help is available right now</strong>
          <ul className="sj-resource-list">
            {resources.map((r) => (
              <li key={r.label}>
                {r.label}:{" "}
                {r.href ? <a href={r.href}>{r.detail}</a> : r.detail}
              </li>
            ))}
          </ul>
          <p>
            You can still continue. Your journey will skip anything that requires direct contact or joint sessions
            with the other parent.
          </p>
        </Notice>
      )}
    </>
  );
}

function SituationPage({ values, onChange, stage, onStage }) {
  return (
    <>
      <StagePicker value={stage} onPick={onStage} />
      <Notice>All questions are optional. Share only what you&apos;re comfortable with. Only you see these answers.</Notice>
      {SITUATION_QUESTIONS.map(([key, label]) => (
        <TextField key={key} id={`sit-${key}`} label={label} value={values[key]} onChange={(v) => onChange(key, v)} />
      ))}
    </>
  );
}

function CoParentingPage({ data, concern, level, onChange, CoParentingPanel }) {
  const options = hidesWorkingTogether(level) ? APPROACHES.filter((a) => a.id !== "cooperative") : APPROACHES;
  return (
    <>
      <PathNote level={level} page="coparenting" />
      {CoParentingPanel ? (
        <section className="sj-card">
          <CoParentingPanel concern={concern} />
        </section>
      ) : (
        <Placeholder>[Existing Co-Parenting Assessment opens here]</Placeholder>
      )}

      <h2 className="sj-subhead">Which approach feels closest to right for now?</h2>
      <ChoiceList label="Co-parenting approach" options={options} value={data.approach} onPick={(id) => onChange({ approach: id })} testid="sj-approach" />

      <TextField id="cp-agree" label="Where do you already agree?" rows={2} optional value={data.agree} onChange={(v) => onChange({ agree: v })} />
      <TextField id="cp-disagree" label="Where do you disagree most?" rows={2} optional value={data.disagree} onChange={(v) => onChange({ disagree: v })} />
    </>
  );
}

// "Explored" (saved, counted on the Summary) stays once an area has been opened; collapsing only folds it.
function ChildNeedsPage({ explored, onExplore, panels }) {
  const [expanded, setExpanded] = useState([]);
  const toggle = (key) => {
    onExplore(key);
    setExpanded((e) => (e.includes(key) ? e.filter((x) => x !== key) : [...e, key]));
  };
  return (
    <>
      {CHILD_AREAS.map(([key, name, desc]) => {
        const open = expanded.includes(key);
        const Panel = panels[key];
        return (
          <section key={key} className="sj-accordion">
            <button
              type="button"
              className="sj-accordion-head"
              aria-expanded={open}
              aria-controls={`need-${key}`}
              onClick={() => toggle(key)}
              data-testid={`sj-need-${key}`}
            >
              <span>
                <strong>{name}</strong>
                <span className="sj-muted">{explored.includes(key) ? "Explored" : "Optional"}</span>
              </span>
              <ChevronIcon open={open} />
            </button>
            {open && (
              <div id={`need-${key}`} className="sj-accordion-body">
                <p>{desc}</p>
                {Panel ? <Panel /> : <Placeholder>[Existing {name.toLowerCase()} form opens here]</Placeholder>}
              </div>
            )}
          </section>
        );
      })}
      <p className="sj-small">
        Open only the areas that matter for your child. You don&apos;t need to include names, school details or medical
        records here.
      </p>
    </>
  );
}

function buildDraftStatement(a) {
  // Simple template. The parent still edits and approves it.
  const parts = [];
  if (a.childNeedsMost) parts.push(`My child needs ${a.childNeedsMost.trim().replace(/\.$/, "")}.`);
  if (a.values) parts.push(`The values that guide my parenting are ${a.values.trim().replace(/\.$/, "")}.`);
  if (a.stability) parts.push(`To create stability, I will ${a.stability.trim().replace(/\.$/, "")}.`);
  if (a.commitments) parts.push(`Within my control, I commit to ${a.commitments.trim().replace(/\.$/, "")}.`);
  if (a.success) parts.push(`Success for our family looks like ${a.success.trim().replace(/\.$/, "")}.`);
  return parts.join(" ") || "Write your Foundation Statement here.";
}

function FoundationPage({ data, onChange, onApprove }) {
  const hasDraft = Boolean(data.draft);
  const toggleApproved = () =>
    data.approved ? onChange({ approved: false, approvedAt: null }) : onApprove(data.draft);
  return (
    <>
      {FOUNDATION_QUESTIONS.map(([key, label]) => (
        <TextField
          key={key}
          id={`fd-${key}`}
          label={label}
          rows={2}
          value={data.answers[key]}
          onChange={(v) => onChange({ answers: { ...data.answers, [key]: v } })}
        />
      ))}

      {!hasDraft ? (
        <button
          type="button"
          className="sj-outline-btn"
          onClick={() => onChange({ draft: buildDraftStatement(data.answers), approved: false })}
          data-testid="sj-draft-foundation"
        >
          Draft my Foundation Statement
        </button>
      ) : (
        <section className="sj-card sj-draft">
          <label htmlFor="fd-draft" className="sj-card-title">Your draft — edit any word</label>
          <textarea
            id="fd-draft"
            rows={7}
            maxLength={3000}
            value={data.draft}
            onChange={(e) => onChange({ draft: e.target.value, approved: false, approvedAt: null })}
            data-testid="fd-draft"
          />
          <div className="sj-row">
            <button
              type="button"
              className="sj-text-btn"
              onClick={() => onChange({ draft: buildDraftStatement(data.answers), approved: false, approvedAt: null })}
              data-testid="sj-rebuild-foundation"
            >
              Rebuild from my answers
            </button>
            <button
              type="button"
              className={data.approved ? "sj-approved-btn" : "sj-primary-btn"}
              onClick={toggleApproved}
              data-testid="sj-approve-foundation"
            >
              {data.approved ? "Approved ✓" : "I approve this statement"}
            </button>
          </div>
          <p className="sj-small">Approving saves it as your Foundation Statement in SA CoParents.</p>
        </section>
      )}
    </>
  );
}

function MediationPage({ values, level, onChange }) {
  return (
    <>
      <PathNote level={level} page="mediation" />
      <Notice>Mediation isn&apos;t right for every family. Use this page to get organized, whatever path you choose.</Notice>
      {MEDIATION_FIELDS.map(([key, label]) => (
        <TextField key={key} id={`md-${key}`} label={label} rows={2} value={values[key]} onChange={(v) => onChange(key, v)} />
      ))}
    </>
  );
}

function SummaryPage({ progress, concern, level, selfAssessmentCount, onEdit, onDownloadPdf, onShare, onCheckIn, onCertificate, resources }) {
  const filled = (obj) => Object.values(obj || {}).some((v) => typeof v === "string" && v.trim());
  const approach = APPROACHES.find((a) => a.id === progress.coparenting.approach);
  const mediationDone = filled(progress.mediation) ? "Completed" : "Not started";

  const sections = [
    { name: "Parenting Situation Overview", step: 1, status: filled(progress.situation) ? "Completed" : "Not started" },
    {
      name: "Self Assessment Reflections",
      step: 2,
      status: selfAssessmentCount ? `${selfAssessmentCount} dated reflection(s)` : "Not started",
    },
    { name: "Co-Parenting Relationship", step: 3, status: approach ? `Approach: ${approach.name}` : "Not started" },
    {
      name: "Child's Identified Needs",
      step: 4,
      status: progress.childNeeds.opened.length ? `${progress.childNeeds.opened.length} area(s) explored` : "Not started",
    },
    {
      name: "Foundation Statement",
      step: 5,
      status: progress.foundation.approved ? "Approved by you" : progress.foundation.draft ? "Draft — needs your approval" : "Not started",
    },
    {
      name: "Mediation Preparation & Options",
      step: 6,
      // The safety pick never prints: on paper this row shows only whether the page was filled in.
      status: concern ? (
        <>
          <span className="sj-no-print">Safety pathway options</span>
          <span className="hidden print:inline">{mediationDone}</span>
        </>
      ) : mediationDone,
    },
  ];

  return (
    <>
      <PathCard stage={progress.stage} level={level} onChange={() => onEdit(1)} />
      <div className="sj-summary" data-testid="sj-summary">
        {sections.map((s) => (
          <div key={s.name} className="sj-summary-row">
            <div>
              <strong>{s.name}</strong>
              <span className="sj-muted">{s.status}</span>
            </div>
            <button
              type="button"
              className="sj-text-btn sj-no-print"
              onClick={() => onEdit(s.step)}
              aria-label={`Edit ${s.name}`}
              data-testid={`sj-edit-${s.step}`}
            >
              Edit
            </button>
          </div>
        ))}
      </div>

      {progress.foundation.approved && (
        <section className="sj-card">
          <h2 className="sj-card-title">Your Foundation Statement</h2>
          <p className="sj-statement" data-testid="sj-summary-statement">{progress.foundation.draft}</p>
        </section>
      )}

      <section className="sj-card">
        <h2 className="sj-card-title">Next Steps &amp; Available Resources</h2>
        <ul className="sj-resource-list">
          {concern && resources.map((r) => (
            <li key={r.label} className="sj-no-print">
              {r.label}: {r.href ? <a href={r.href}>{r.detail}</a> : r.detail}
            </li>
          ))}
          <li data-testid="sj-level-next-step">{CONFLICT_LEVELS[level].nextStep}</li>
          <li>Bring this summary to your mediator, attorney or counselor.</li>
          <li>Revisit your Self Assessment in a few weeks to see how things have changed.</li>
        </ul>
      </section>

      <div className="sj-row">
        <button type="button" className="sj-outline-btn" onClick={onDownloadPdf} data-testid="sj-download-pdf">Download PDF</button>
        <button type="button" className="sj-outline-btn" onClick={onShare} data-testid="sj-share">Share with a professional</button>
      </div>
      <div className="sj-row">
        <button type="button" className="sj-outline-btn" onClick={onCheckIn} data-testid="sj-checkin-now">Check in now</button>
        {onCertificate && (
          <button type="button" className="sj-outline-btn" onClick={onCertificate} data-testid="sj-certificate">Download my certificate</button>
        )}
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Assistant                                                           */
/* ------------------------------------------------------------------ */

const WAVED_KEY = "sj-guide-waved";

// The small waving hand shows once per device, the first time Help opens.
function useOneTimeWave() {
  const [wave] = useState(() => {
    try {
      if (localStorage.getItem(WAVED_KEY)) return false;
      localStorage.setItem(WAVED_KEY, new Date().toISOString());
      return true;
    } catch {
      return false;
    }
  });
  const [show, setShow] = useState(wave);
  useEffect(() => {
    if (!wave) return undefined;
    const t = setTimeout(() => setShow(false), 2800);
    return () => clearTimeout(t);
  }, [wave]);
  return show;
}

function AssistantSheet({ step, isSafetyStep, path, onClose, onAsk, logoSrc }) {
  const opening = [{ role: "assistant", text: step.chat }];
  if (isSafetyStep) {
    opening.push({
      role: "assistant",
      text: "I can explain how this check works, but I can't decide whether you're safe. Your check-in on SACOparentsAlign and a trained professional can help with that.",
    });
  }
  const [messages, setMessages] = useState(opening);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [asked, setAsked] = useState([]);
  const listRef = useRef(null);
  const guard = useAiGuard("journey_guide", input);
  const waving = useOneTimeWave();
  // Same ready-made path answers as the reading Self Journey; answered on the device, nothing is sent.
  const pathQuestions = readyQuestions({
    steps: STEPS,
    stepId: isSafetyStep ? "safety-first" : step.slug,
    noun: "steps",
    safetyConcern: path?.safety === "concern" || path?.level === "safety",
  }).filter((r) => !asked.includes(r.id));
  const askReady = (r) => {
    setAsked((a) => [...a, r.id]);
    setMessages((m) => [...m, { role: "user", text: r.q }, { role: "assistant", text: r.a }]);
  };

  useEffect(() => stopReading, []);

  useEffect(() => {
    listRef.current?.scrollTo?.(0, listRef.current.scrollHeight);
  }, [messages]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const send = async (text) => {
    const q = text.trim();
    if (!q || busy) return;
    if (!(await guard.confirmSend(q))) return;
    const history = [...messages, { role: "user", text: q }];
    setMessages(history);
    setInput("");
    if (!onAsk) return;
    setBusy(true);
    try {
      const reply = await onAsk(step.slug, q, history, path);
      setMessages((m) => [...m, { role: "assistant", text: reply }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", text: "Sorry, I couldn't respond just now. Please try again." }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="sj-scrim" onClick={onClose} aria-hidden="true" />
      <div className="sj-sheet" role="dialog" aria-modal="true" aria-labelledby="sj-sheet-title" data-testid="sj-assistant">
        <div className="sj-sheet-head">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className="sj-avatar-wrap">
              <GuideAvatar size={44} logoSrc={logoSrc} calm={isSafetyStep} speaking={busy} decorative testid="sj-guide-avatar" />
              {waving && (
                <span className="sj-wave" aria-hidden="true" data-testid="sj-guide-wave">
                  <Hand size={14} strokeWidth={2.4} />
                </span>
              )}
            </span>
            <div>
              <h2 id="sj-sheet-title">Journey Guide</h2>
              <span className="sj-muted">Helping with: {step.short}</span>
            </div>
          </div>
          <button type="button" className="sj-icon-btn" onClick={onClose} aria-label="Close help" data-testid="sj-assistant-close">
            <CloseIcon />
          </button>
        </div>
        <div className="sj-sheet-body" ref={listRef} aria-live="polite">
          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="sj-bubble is-user" data-testid="sj-bubble-user">{m.text}</div>
            ) : (
              <div key={i} className="sj-bubble-row">
                <GuideAvatar size={26} logoSrc={logoSrc} calm={isSafetyStep} decorative />
                <div className="sj-bubble" data-testid="sj-bubble-assistant">
                  {m.text}
                  <ListenButton text={m.text} testid={`sj-listen-${i}`} />
                </div>
              </div>
            )
          )}
          {busy && (
            <div className="sj-bubble-row">
              <GuideAvatar size={26} logoSrc={logoSrc} calm={isSafetyStep} speaking decorative />
              <div className="sj-bubble sj-muted" data-testid="sj-assistant-thinking">Thinking…</div>
            </div>
          )}
          {messages.length <= 2 && (
            <div className="sj-suggestions">
              {step.suggestions.map((s, i) => (
                <button key={s} type="button" onClick={() => send(s)} data-testid={`sj-suggestion-${i}`}>
                  {s}
                </button>
              ))}
            </div>
          )}
          {pathQuestions.length > 0 && (
            <div className="sj-path-qs" data-testid="sj-path-questions">
              <p className="sj-path-qs-label">Questions about the paths</p>
              <div className="sj-suggestions">
                {pathQuestions.map((r) => (
                  <button key={r.id} type="button" onClick={() => askReady(r)} data-testid={`sj-path-q-${r.id}`}>
                    {r.q}
                  </button>
                ))}
              </div>
              <p className="sj-path-qs-note">These answers stay on your device. Nothing you tap here is sent anywhere.</p>
            </div>
          )}
        </div>
        <form
          className="sj-sheet-input"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <label htmlFor="sj-chat-input" className="sj-sr-only">Ask the Journey Guide</label>
          <input
            id="sj-chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question…"
            maxLength={1000}
            data-testid="sj-chat-input"
            {...guard.inputProps}
          />
          <button type="submit" className="sj-send" aria-label="Send" disabled={busy} data-testid="sj-chat-send">
            <ArrowIcon />
          </button>
        </form>
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Icons                                                               */
/* ------------------------------------------------------------------ */

const svg = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };
const SaveIcon = () => (<svg {...svg}><path d="M5 3h11l3 3v15H5z" /><path d="M8 3v5h8V3" /><path d="M8 21v-7h8v7" /></svg>);
const CloseIcon = () => (<svg {...svg}><path d="M6 6l12 12M18 6L6 18" /></svg>);
const ArrowIcon = () => (<svg {...svg}><path d="M5 12h14M13 6l6 6-6 6" /></svg>);
const ChevronIcon = ({ open }) => (
  <svg {...svg} width={20} height={20} style={{ transform: `rotate(${open ? 180 : 0}deg)`, transition: "transform .2s", color: "var(--sj-purple)" }}>
    <path d="M6 9l6 6 6-6" />
  </svg>
);
