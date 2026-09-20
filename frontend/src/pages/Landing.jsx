import React, { useState } from "react";
import { useSafetyLevel } from "../hooks/useSafetyLevel";
import { useJointBridgeCopy } from "../hooks/useJointBridgeCopy";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ArrowDown,
  ArrowUpRight,
  ShieldCheck,
  Facebook,
  Heart,
  MessageCircle,
  Sparkles,
  ClipboardList,
  BookOpen,
  Users,
  Compass,
  Lock,
  FlaskConical,
  LifeBuoy,
  FileText,
  Baby,
  AlertTriangle,
  Scale,
  Handshake,
  Briefcase,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";
import { markOrientationSeen } from "./Orientation";
import EcosystemStrip from "../components/EcosystemStrip";
import CoachDemoSection from "../components/CoachDemoSection";

const FB_URL = process.env.REACT_APP_FACEBOOK_URL;

/* ============================================================
   ENTER-APP CONTEXT
   Multiple entry paths:
     - enterAssessments: scrolls to the situation picker (default primary CTA)
     - enterGuest:       creates guest session + goes straight to /dashboard
                         (skips the intro video)
     - watchIntro:       goes to /watch (public trailer)
     - enterWithFocus:   used by the situation picker — creates guest session,
                         records the user's chosen focus in localStorage so the
                         dashboard can prioritize the right assessment,
                         then navigates to /dashboard with the intro video
                         SKIPPED for safety-oriented picks.
============================================================ */
const EnterAppContext = React.createContext(null);

const FOCUS_STORAGE_KEY = "sac_recommended_focus_v1";

function EnterAppProvider({ children }) {
  const { startGuest } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const enterAssessments = () => {
    // Just scroll to the situation picker. This is the primary CTA.
    scrollToId("situation-picker");
  };

  const watchIntro = () => {
    navigate("/watch");
  };

  const enterGuest = async () => {
    if (loading) return;
    setError(null);
    setLoading(true);
    try {
      await startGuest();
      markOrientationSeen();
      navigate("/dashboard");
    } catch (err) {
      logError("Enter app failed:", err);
      setError(
        err?.response?.data?.detail ||
          "Couldn't open the app right now. Please try again in a moment."
      );
      setLoading(false);
    }
  };

  const enterWithFocus = async ({ focus, route }) => {
    // Focus goes into localStorage so the dashboard can pin the right
    // "Do this next" card. `route` is the target path after guest session.
    if (loading) return;
    setError(null);
    setLoading(true);
    try {
      if (focus) {
        try { localStorage.setItem(FOCUS_STORAGE_KEY, focus); }
        catch (e) { logError("focus localStorage set failed", e); }
      }
      await startGuest();
      markOrientationSeen();
      navigate(route || "/dashboard");
    } catch (err) {
      logError("Enter app with focus failed:", err);
      setError(
        err?.response?.data?.detail ||
          "Couldn't open the app right now. Please try again in a moment."
      );
      setLoading(false);
    }
  };

  return (
    <EnterAppContext.Provider
      value={{ enterAssessments, enterGuest, watchIntro, enterWithFocus, loading, error }}
    >
      {children}
    </EnterAppContext.Provider>
  );
}

function useEnterApp() {
  const ctx = React.useContext(EnterAppContext);
  if (!ctx) throw new Error("useEnterApp outside EnterAppProvider");
  return ctx;
}

/* ============================================================
   SMALL UI PRIMITIVES
============================================================ */
function Eyebrow({ children, color = "text-[#3D1A78]" }) {
  return (
    <div
      className={`text-[11px] tracking-[0.28em] uppercase font-bold ${color} mb-3`}
    >
      {children}
    </div>
  );
}

function PrimaryCTA({ children, testid }) {
  const { enterAssessments } = useEnterApp();
  return (
    <button
      type="button"
      onClick={enterAssessments}
      data-testid={testid}
      className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white font-semibold text-sm shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
    >
      {children}
      <ArrowRight size={16} />
    </button>
  );
}

function scrollToId(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ============================================================
   HEADER + FOOTER
============================================================ */
function MarketingHeader() {
  return (
    <header className="absolute top-0 left-0 right-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-5 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5" data-testid="header-logo">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] grid place-items-center text-white shadow-sm">
            <Heart size={16} strokeWidth={2.4} />
          </div>
          <div className="font-serif text-[#1A1330] text-lg leading-none">
            SA CoParents
          </div>
        </Link>
        <div className="flex items-center gap-4">
          {FB_URL && (
            <a
              href={FB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="w-9 h-9 rounded-full grid place-items-center text-[#3D1A78] hover:bg-white/50 transition-colors"
              data-testid="header-facebook-link"
              aria-label="Facebook"
            >
              <Facebook size={18} />
            </a>
          )}
        </div>
      </div>
    </header>
  );
}

function MarketingFooter() {
  return (
    <footer className="bg-[#1A1330] text-white/80 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] grid place-items-center">
              <Heart size={18} strokeWidth={2.4} />
            </div>
            <div>
              <div className="font-serif text-white text-lg leading-none">
                SA CoParents
              </div>
              <div className="text-xs text-white/60 mt-1" data-testid="footer-tagline">
                Build Alignment. Create Better Agreements.
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs">
            <Link to="/for-professionals" className="hover:text-white" data-testid="footer-for-professionals-link">
              For professionals
            </Link>
            <Link to="/samples" className="hover:text-white" data-testid="footer-samples-link">
              Sample library
            </Link>
            <Link to="/terms" className="hover:text-white" data-testid="footer-terms-link">
              Terms
            </Link>
            <Link to="/privacy" className="hover:text-white" data-testid="footer-privacy-link">
              Privacy
            </Link>
            <Link to="/data-retention" className="hover:text-white" data-testid="footer-data-retention-link">
              Data retention
            </Link>
            <Link to="/methodology" className="hover:text-white" data-testid="footer-methodology-link">
              Methodology
            </Link>
            <Link to="/accessibility" className="hover:text-white" data-testid="footer-accessibility-link">
              Accessibility
            </Link>
            {FB_URL && (
              <a
                href={FB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-white inline-flex items-center gap-1.5"
                data-testid="footer-facebook-link"
              >
                <Facebook size={14} /> facebook.com/SACoparent
              </a>
            )}
          </div>
        </div>
        <div className="text-[11px] text-white/40 mt-8 leading-relaxed max-w-2xl">
          SA CoParents is an educational and preparation tool. It is not legal
          advice, therapy, or a substitute for professional mediation. Always
          consult qualified family-law and mental-health professionals for your
          situation.
        </div>
      </div>
    </footer>
  );
}

/* ============================================================
   SECTION 1 — HERO
============================================================ */
/* ============================================================
   SITUATION-FIRST OPENING
   Iteration 203 — collapsed 6 flat choices into 4 parent-needs
   groups. High-conflict + communication-is-difficult now share a
   single "Communication" tile but expand to a sub-choice card so
   the underlying clinical routing (safety-adjacent path for
   high-conflict) is fully preserved. "Preparing for mediation or
   court" moved out of the tile grid entirely — now a destination
   link rendered beneath the picker so it reads as a process
   choice, not a fifth substantive assessment category.

   Coercive-control / safety pickers still go DIRECTLY to the
   Safety Screen with NO cooperation messaging shown first.
============================================================ */

// Leaf definitions — the 6 original routes preserved verbatim so
// no downstream analytics / focus keys break. UI now composes
// these into the 4 group tiles below.
const SITUATION_LEAVES = {
  cooperate: {
    key: "cooperate",
    label: "We generally cooperate",
    icon: <Handshake />,
    focus: "mediation",
    route: "/dashboard",
    result: {
      title: "Start with the Mediation Readiness Assessment.",
      body: "You have a foundation to build on. This assessment turns your existing goodwill into a concrete, child-focused agenda you can bring to any co-parenting conversation.",
      cta: "Start the readiness assessment",
      tone: "cooperative",
      icon: <Scale size={20} />,
    },
  },
  difficult: {
    key: "difficult",
    label: "Communication is difficult",
    icon: <MessageCircle />,
    focus: "mediation",
    route: "/dashboard",
    result: {
      title: "Start with the Mediation Readiness Assessment.",
      body: "The Readiness Assessment includes a communication-clarity dimension. It will name what's breaking down and give you scripts for the highest-leverage conversations.",
      cta: "Start the readiness assessment",
      tone: "warn",
      icon: <MessageCircle size={20} />,
    },
  },
  "high-conflict": {
    key: "high-conflict",
    label: "We experience ongoing high conflict",
    icon: <AlertTriangle />,
    focus: "safety",
    route: "/safety-assessment",
    result: {
      title: "First a quick safety check — then we'll suggest a communication or mediation pathway.",
      body: "High conflict isn't the same as family violence, and we don't assume it is. Before recommending a communication or mediation pathway, we'll run a short private safety check. If nothing concerning surfaces, you'll go straight into the co-parenting-agreement flow — with structure to keep the temperature down.",
      cta: "Run the private safety check first",
      tone: "urgent",
      icon: <ShieldCheck size={20} />,
      safetyBanner: "If you are in immediate danger, call 911. Suicide & Crisis Lifeline: 988. National Domestic Violence Hotline: 1-800-799-SAFE.",
    },
  },
  safety: {
    key: "safety",
    label: "I have safety or family-violence concerns",
    icon: <ShieldCheck />,
    focus: "safety",
    route: "/safety-assessment",
    result: {
      title: "Start with the Family Violence and Communication Safety Screen.",
      body: "Your safety and your child's safety come first. This is a private screen that never asks you to cooperate with the other parent. It recommends the safest communication pathway (including no-direct-contact) and includes Texas crisis hotlines.",
      cta: "Start the safety screen",
      tone: "urgent",
      icon: <ShieldCheck size={20} />,
      safetyBanner: "If you are in immediate danger, call 911. Suicide & Crisis Lifeline: 988. National Domestic Violence Hotline: 1-800-799-SAFE.",
    },
  },
  "special-needs": {
    key: "special-needs",
    label: "Our child has unique educational, psychological or medical needs",
    icon: <Baby />,
    focus: "special-needs",
    route: "/special-needs-v2",
    result: {
      title: "Start with the Special Needs Co-Parenting Assessment.",
      body: "Children's needs don't always fit one category. You'll pick every area that applies — medical, educational, psychological, or interconnected — and walk through a coordinated eight-step assessment that ends in an individualized action plan you can share with your co-parent, mediator, or provider.",
      cta: "Start the Special Needs assessment",
      tone: "cooperative",
      icon: <Baby size={20} />,
    },
  },
  mediation: {
    key: "mediation",
    label: "I am preparing for mediation or court",
    icon: <Scale />,
    focus: "mediation",
    route: "/dashboard",
    result: {
      title: "Start with the Mediation Readiness Assessment.",
      body: "You'll build a child-focused agenda, name your priorities and flexibility areas, and download a Mediation Summary PDF ready to hand to your mediator.",
      cta: "Start the readiness assessment",
      tone: "cooperative",
      icon: <Scale size={20} />,
    },
  },
};

// Four parent-needs groups. `subChoices` lets Communication open a
// two-option card so we don't merge the high-conflict clinical
// path with the ordinary communication-is-difficult path.
const SITUATION_GROUPS = [
  {
    key: "co-parenting",
    label: "Co-Parenting",
    sublabel: "How are we parenting together?",
    icon: <Handshake />,
    leaf: SITUATION_LEAVES.cooperate,
  },
  {
    key: "communication",
    label: "Communication",
    sublabel: "How can we communicate more effectively?",
    icon: <MessageCircle />,
    subChoices: [
      SITUATION_LEAVES.difficult,
      SITUATION_LEAVES["high-conflict"],
    ],
  },
  {
    key: "child-needs",
    label: "My Child's Needs",
    sublabel: "Educational · Medical · Psychological",
    icon: <Baby />,
    leaf: SITUATION_LEAVES["special-needs"],
  },
  {
    key: "safety",
    label: "Safety",
    sublabel: "Do I need a different communication or parenting pathway?",
    icon: <ShieldCheck />,
    leaf: SITUATION_LEAVES.safety,
  },
];

// Mediation is a destination/process choice, not a substantive
// assessment category — pulled out of the tile grid and rendered
// as a distinct link below the picker.
const MEDIATION_DESTINATION = SITUATION_LEAVES.mediation;

const TONE_STYLES = {
  cooperative: { border: "border-[#3D1A78]/25", bg: "bg-white", chipBg: "bg-[#EFE9F9]", chipText: "text-[#3D1A78]", cta: "bg-[#3D1A78] hover:bg-[#2D0F63]" },
  warn:        { border: "border-[#F5C147]/40", bg: "bg-[#FFFAEC]", chipBg: "bg-[#FFF3D1]", chipText: "text-[#B27700]", cta: "bg-[#B27700] hover:bg-[#8F6100]" },
  urgent:      { border: "border-[#B85B00]/40", bg: "bg-[#FFF3E9]", chipBg: "bg-[#FFDFC4]", chipText: "text-[#8F4600]", cta: "bg-[#B85B00] hover:bg-[#8F4600]" },
};

function SituationPicker() {
  const { enterWithFocus, loading } = useEnterApp();
  const [expandedGroup, setExpandedGroup] = useState(null); // group with subChoices open
  const [picked, setPicked] = useState(null);                // final leaf chosen

  const chooseGroup = (g) => {
    if (g.leaf) {
      setPicked(g.leaf);
      setExpandedGroup(null);
      return;
    }
    setExpandedGroup(g);
  };
  const chooseLeaf = (leaf) => {
    setPicked(leaf);
    setExpandedGroup(null);
  };
  const resetAll = () => {
    setPicked(null);
    setExpandedGroup(null);
  };
  const proceed = () => {
    if (!picked) return;
    enterWithFocus({ focus: picked.focus, route: picked.route });
  };
  const proceedMediation = () => {
    enterWithFocus({
      focus: MEDIATION_DESTINATION.focus,
      route: MEDIATION_DESTINATION.route,
    });
  };

  // STATE 1 — a group is expanded (sub-choice card shown).
  if (expandedGroup) {
    return (
      <div
        id="situation-picker"
        className="rounded-3xl border border-[#E5E0EE] bg-white/85 backdrop-blur-sm p-6 sm:p-8 shadow-sm max-w-3xl mx-auto fade-up"
        data-testid={`situation-group-${expandedGroup.key}-subchoices`}
      >
        <button
          onClick={() => setExpandedGroup(null)}
          className="text-xs font-semibold text-[#3D1A78] hover:underline mb-3"
          data-testid="situation-subchoice-back"
        >
          ← Back to all situations
        </button>
        <div className="flex items-center gap-3 mb-2">
          <div className="shrink-0 w-11 h-11 rounded-full bg-[#EFE9F9] text-[#3D1A78] flex items-center justify-center">
            {expandedGroup.icon}
          </div>
          <div>
            <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-snug">
              {expandedGroup.label}
            </h2>
            <p className="text-sm text-[#4B4567] leading-snug">
              {expandedGroup.sublabel}
            </p>
          </div>
        </div>
        <p className="text-sm text-[#4B4567] mt-3">
          Which of these fits your current situation more closely? The
          routing behind each option is different — high conflict starts
          with a private safety check first.
        </p>
        <div className="mt-5 grid sm:grid-cols-2 gap-2.5">
          {expandedGroup.subChoices.map((leaf) => (
            <button
              key={leaf.key}
              onClick={() => chooseLeaf(leaf)}
              className="group text-left rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:bg-[#F7F4FC] transition-colors flex items-center gap-3"
              data-testid={`situation-${leaf.key}`}
            >
              <div className="shrink-0 w-9 h-9 rounded-full bg-[#EFE9F9] text-[#3D1A78] flex items-center justify-center group-hover:bg-[#3D1A78] group-hover:text-white transition-colors">
                {leaf.icon}
              </div>
              <span className="text-sm sm:text-[15px] text-[#1A1330] leading-snug">
                {leaf.label}
              </span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // STATE 2 — initial 4-tile group picker.
  if (!picked) {
    return (
      <div
        id="situation-picker"
        className="rounded-3xl border border-[#E5E0EE] bg-white/85 backdrop-blur-sm p-6 sm:p-8 shadow-sm max-w-3xl mx-auto"
        data-testid="situation-picker"
      >
        <div className="text-[11px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-2">
          Step 1
        </div>
        <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-snug">
          What best describes your situation?
        </h2>
        <p className="text-sm text-[#4B4567] mt-2">
          There are no wrong answers. Your choice helps us route you to the
          safest and most relevant starting point.
        </p>
        <div className="mt-5 grid sm:grid-cols-2 gap-2.5">
          {SITUATION_GROUPS.map((g) => (
            <button
              key={g.key}
              onClick={() => chooseGroup(g)}
              className="group text-left rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:bg-[#F7F4FC] transition-colors flex items-start gap-3"
              data-testid={`situation-group-${g.key}`}
            >
              <div className="shrink-0 w-9 h-9 rounded-full bg-[#EFE9F9] text-[#3D1A78] flex items-center justify-center group-hover:bg-[#3D1A78] group-hover:text-white transition-colors">
                {g.icon}
              </div>
              <div className="min-w-0">
                <div className="text-[15px] font-semibold text-[#1A1330] leading-snug">
                  {g.label}
                </div>
                <div className="text-xs sm:text-[13px] text-[#4B4567] leading-snug mt-0.5">
                  {g.sublabel}
                </div>
              </div>
            </button>
          ))}
        </div>
        {/* Mediation is a destination, not a substantive category —
            rendered as a distinct link below the tile grid. */}
        <div className="mt-5 pt-5 border-t border-[#E5E0EE] text-center">
          <p className="text-xs uppercase tracking-[0.16em] font-bold text-[#857E9C] mb-1.5">
            Preparing for mediation or court?
          </p>
          <button
            onClick={proceedMediation}
            disabled={loading}
            className="inline-flex items-center gap-1 text-sm font-semibold text-[#3D1A78] hover:underline disabled:opacity-60"
            data-testid="situation-mediation-destination"
          >
            Start the Mediation Readiness Assessment
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    );
  }

  // STATE 3 — leaf picked, show the routed result card.
  const tone = TONE_STYLES[picked.result.tone] || TONE_STYLES.cooperative;
  return (
    <div
      id="situation-picker"
      className={`rounded-3xl border-2 ${tone.border} ${tone.bg} p-6 sm:p-8 shadow-sm max-w-3xl mx-auto fade-up`}
      data-testid="situation-picker-result"
    >
      {picked.result.safetyBanner && (
        <div
          className="rounded-2xl border border-[#B85B00]/40 bg-[#FFF3E9] p-3 mb-5 text-xs sm:text-sm text-[#8F4600] leading-relaxed"
          data-testid="situation-picker-safety-banner"
        >
          <strong>Your safety comes first.</strong> {picked.result.safetyBanner}
        </div>
      )}
      <div className="flex items-center gap-3 mb-3">
        <div className={`shrink-0 inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${tone.chipBg} ${tone.chipText}`}>
          {picked.result.icon}
          {picked.label}
        </div>
      </div>
      <h3 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-snug" data-testid="situation-picker-result-title">
        {picked.result.title}
      </h3>
      <p className="text-sm sm:text-base text-[#4B4567] mt-3 leading-relaxed">
        {picked.result.body}
      </p>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          onClick={proceed}
          disabled={loading}
          className={`inline-flex items-center gap-2 text-white font-semibold px-6 py-3 rounded-full text-sm sm:text-base transition-colors ${tone.cta} disabled:opacity-60`}
          data-testid="situation-picker-cta"
        >
          {loading ? "Opening…" : picked.result.cta}
          {!loading && <ArrowRight size={16} />}
        </button>
        <button
          onClick={resetAll}
          className="text-sm text-[#4B4567] hover:text-[#3D1A78] hover:underline"
          data-testid="situation-picker-reset"
        >
          Change my answer
        </button>
      </div>
    </div>
  );
}

/* ============================================================
   SECTION 1 — HERO (tagline + situation picker embedded)
============================================================ */
function PathBInvitedCard() {
  const [expanded, setExpanded] = useState(false);
  const [code, setCode] = useState("");
  const [warning, setWarning] = useState(null);

  // Format-only validation (regex against the visible SA-XXXXXX
  // shape). Backend `/joint-alignment/manual-code` is JWT-required,
  // so we can't do a true live lookup here without exposing an
  // unauthenticated case-enumeration endpoint — the strict backend
  // check runs after login on the /join page. This is best-effort
  // "don't dead-end them at submit" UX, not a security guarantee.
  const validateOnBlur = () => {
    const trimmed = code.trim().toUpperCase();
    if (!trimmed) { setWarning(null); return; }
    if (!/^SA-[A-Z0-9]{4,10}$/.test(trimmed)) {
      setWarning(
        "Alignment codes usually look like SA-ABC123. We'll still try — it's checked properly after you sign in.",
      );
    } else {
      setWarning(null);
    }
  };

  const submit = (e) => {
    e.preventDefault();
    const trimmed = code.trim().toUpperCase();
    if (trimmed) {
      window.location.href = `/join?code=${encodeURIComponent(trimmed)}`;
    } else {
      window.location.href = "/join";
    }
  };

  if (!expanded) {
    return (
      <div
        className="text-left rounded-3xl bg-white border-2 border-[#D6CFE8] hover:border-[#3D1A78] p-5 sm:p-6 transition shadow-sm"
        data-testid="hero-invited-cta-wrap"
      >
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="w-full text-left"
          data-testid="hero-invited-cta"
        >
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Path B
          </div>
          <div className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-1 leading-tight">
            I was invited by a professional
          </div>
          <div className="text-[13px] text-[#4B4567] mt-2 leading-relaxed">
            Open the link your mediator or attorney emailed you — or
            paste the code they gave you. We&rsquo;ll auto-connect the
            rest.
          </div>
          <div className="mt-3 inline-flex items-center gap-1 text-[13px] font-semibold text-[#3D1A78] group-hover:underline">
            Continue your invitation →
          </div>
        </button>
        <div className="mt-3 pt-3 border-t border-[#EFE9F9]">
          <Link
            to="/join/sample-preview"
            className="text-[11px] text-[#857E9C] hover:text-[#3D1A78] hover:underline"
            data-testid="hero-invited-sample-link"
          >
            See a sample invited screen →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div
      className="text-left rounded-3xl bg-white border-2 border-[#3D1A78] p-5 sm:p-6 shadow-sm"
      data-testid="hero-invited-expanded"
    >
      <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
        Path B
      </div>
      <div className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-1 leading-tight">
        I was invited by a professional
      </div>
      <div className="mt-4 space-y-3">
        <div className="rounded-2xl bg-[#F5F1FB] border border-[#D6CFE8] p-3">
          <div className="text-[12px] font-semibold text-[#3D1A78] mb-1">
            I have a link from my email
          </div>
          <div className="text-[12px] text-[#4B4567] leading-relaxed">
            Open the link your professional sent you — it auto-connects
            everything.
          </div>
        </div>
        <form onSubmit={submit} className="space-y-2">
          <label
            htmlFor="hero-path-b-code"
            className="block text-[12px] font-semibold text-[#3D1A78]"
          >
            I have an Alignment Code
          </label>
          <div className="flex flex-wrap gap-2">
            <input
              id="hero-path-b-code"
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onBlur={validateOnBlur}
              placeholder="SA-ABC123"
              autoCapitalize="characters"
              autoCorrect="off"
              spellCheck="false"
              className="flex-1 min-w-[120px] rounded-full border border-[#D6CFE8] bg-white px-4 py-2 text-sm focus:border-[#3D1A78] focus:outline-none font-mono uppercase"
              data-testid="hero-path-b-code-input"
            />
            <button
              type="submit"
              className="inline-flex items-center gap-1 rounded-full bg-[#3D1A78] hover:bg-[#2A0F5F] text-white px-4 py-2 text-sm font-semibold"
              data-testid="hero-path-b-continue"
            >
              Continue →
            </button>
          </div>
          {warning && (
            <div
              className="text-[11px] text-[#8A5B00] bg-[#FFF6E5] border border-[#F0D9A1] rounded-lg px-2.5 py-1.5"
              data-testid="hero-path-b-code-warning"
            >
              {warning}
            </div>
          )}
        </form>
        <button
          type="button"
          onClick={() => { setExpanded(false); setCode(""); setWarning(null); }}
          className="text-[11px] text-[#857E9C] hover:text-[#1A1330] hover:underline"
          data-testid="hero-path-b-collapse"
        >
          ← Back
        </button>
      </div>
    </div>
  );
}

function HeroTop() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-[#F8F7FC] via-[#EFE9F9] to-[#E4F1F1] pt-28 sm:pt-32 pb-10 sm:pb-14">
      <div className="absolute -top-32 -left-32 w-[28rem] h-[28rem] rounded-full bg-[#D4C5F0]/40 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-32 w-[30rem] h-[30rem] rounded-full bg-[#A8DCDC]/40 blur-3xl pointer-events-none" />

      {/* "Free App" badge — parents shouldn't have to guess at pricing. */}
      <div
        className="absolute top-24 right-4 sm:top-28 sm:right-8 lg:right-12 z-10 rotate-[8deg]"
        aria-hidden="false"
        data-testid="hero-free-app-badge"
      >
        <div className="relative">
          <div className="absolute inset-0 rounded-full bg-[#3D1A78]/25 blur-lg" />
          <div className="relative h-24 w-24 sm:h-28 sm:w-28 rounded-full bg-gradient-to-br from-[#3D1A78] to-[#5A2FA0] text-white grid place-items-center shadow-xl border-4 border-white">
            <div className="text-center leading-tight">
              <div className="text-[10px] uppercase tracking-[0.24em] font-bold opacity-90">Free</div>
              <div className="font-serif text-lg sm:text-xl font-bold">App</div>
            </div>
          </div>
        </div>
      </div>

      <div className="relative max-w-5xl mx-auto px-4 sm:px-6 text-center fade-up">
        <Eyebrow>The SA CoParents App</Eyebrow>
        <h1
          className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-[1.15] tracking-[0.02em] uppercase"
          data-testid="hero-headline"
        >
          With <span className="text-[#3D1A78]">Reflection.</span>
          <br />
          Build <span className="text-[#3D1A78]">Alignment.</span>
          <br />
          Create Better <span className="text-[#3D1A78]">Agreements.</span>
        </h1>
      </div>
    </section>
  );
}


function HeroBottom() {
  const { enterGuest, loading: guestLoading, watchIntro } = useEnterApp();
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-[#E4F1F1] via-[#EFE9F9] to-[#F8F7FC] pt-10 sm:pt-14 pb-16 sm:pb-20">
      <div className="absolute -top-24 -right-32 w-[24rem] h-[24rem] rounded-full bg-[#A8DCDC]/30 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -left-32 w-[28rem] h-[28rem] rounded-full bg-[#D4C5F0]/40 blur-3xl pointer-events-none" />

      <div className="relative max-w-5xl mx-auto px-4 sm:px-6 text-center fade-up">
        <p
          className="max-w-2xl mx-auto text-base sm:text-lg text-[#4B4567] leading-relaxed"
          data-testid="hero-supporting-copy"
        >
          SA CoParents helps parents independently identify their child&rsquo;s
          needs, concerns and parenting priorities, discover areas of shared
          understanding, identify differences without assigning blame, and
          explore options and resources for moving forward.
        </p>

        {/* Primary path chooser — replaces a single generic CTA with
            two clear parent journeys. "Starting on my own" reveals
            the situation picker below (existing solo flow). "Invited
            by a professional" expands inline: either open the email
            link, or paste the visible SA-XXXXXX Alignment Code and
            we auto-forward to `/join?code=...` so the code is
            pre-filled after login. */}
        <div
          className="mt-10 grid gap-3 sm:grid-cols-2 max-w-3xl mx-auto"
          data-testid="hero-dual-entry"
        >
          <button
            type="button"
            onClick={() => {
              const el = document.getElementById("situation-picker");
              if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
            className="group text-left rounded-3xl bg-white border-2 border-[#D6CFE8] hover:border-[#3D1A78] p-5 sm:p-6 transition shadow-sm"
            data-testid="hero-solo-cta"
          >
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Path A
            </div>
            <div className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-1 leading-tight">
              I&rsquo;m starting on my own
            </div>
            <div className="text-[13px] text-[#4B4567] mt-2 leading-relaxed">
              Reflect independently, at your own pace. Build a Foundation
              Statement you can share when you&rsquo;re ready.
            </div>
            <div className="mt-3 inline-flex items-center gap-1 text-[13px] font-semibold text-[#3D1A78] group-hover:underline">
              Choose your situation →
            </div>
          </button>

          <PathBInvitedCard />
        </div>

        {/* Path A body — SituationPicker is the existing solo flow.
            It sits under an anchor so the "starting on my own" CTA
            above can scroll into view. */}
        <div id="situation-picker" className="mt-10 scroll-mt-24">
          <SituationPicker />
        </div>

        {/* Supporting reassurance — one concise strip, no visual noise. */}
        <p
          className="mt-6 text-xs sm:text-sm text-[#4B4567] max-w-2xl mx-auto"
          data-testid="hero-reassurance"
        >
          Private guest access · No payment required · About 10 minutes
        </p>

        {/* Secondary paths — kept but demoted to text links so the one
            primary action ("Choose your situation" above) stays the
            visual centre of gravity. */}
        <div className="mt-4 flex flex-col sm:flex-row items-center justify-center gap-2 sm:gap-5 text-sm">
          <button
            type="button"
            onClick={watchIntro}
            data-testid="hero-watch-cta"
            className="text-[#3D1A78] hover:underline font-medium"
          >
            Watch how it works
          </button>
          <span className="hidden sm:inline text-[#D6CFE8]">·</span>
          <button
            type="button"
            onClick={enterGuest}
            disabled={guestLoading}
            data-testid="hero-guest-cta"
            className="text-[#4B4567] hover:text-[#3D1A78] hover:underline disabled:opacity-60"
          >
            {guestLoading ? "Opening…" : "Or explore as a guest →"}
          </button>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   THREE REPORTS STRIP — Iteration 203: made the report hierarchy
   explicit. Two labeled tiers:
     Tier 1 — CORE REPORTS every parent gets
     Tier 2 — WHEN YOUR CHILD NEEDS MORE SUPPORT
              (Educational / Medical / Psychological / Special Needs)
   Reason: on the previous single-tier layout parents wondered
   whether "Child Needs Statement" and "Special Needs Assessment"
   were the same thing. Splitting them into two labeled tiers
   fixes that ambiguity.
============================================================ */
function ThreeReportsStrip() {
  const focusedAssessments = [
    {
      key: "educational",
      label: "Educational",
      body: "IEP · school communication · academic goals",
      route: "/special-needs-v2/educational-deep-dive",
      sampleHref: "/api/insights/samples/deep-dive-educational.pdf",
      accent: "#2563EB",
    },
    {
      key: "medical",
      label: "Medical",
      body: "Diagnoses · medication · care coordination",
      route: "/special-needs-v2/medical-deep-dive",
      sampleHref: "/api/insights/samples/deep-dive-medical.pdf",
      accent: "#DC2626",
    },
    {
      key: "psychological",
      label: "Psychological",
      body: "Therapy · anxiety · behavioural support",
      route: "/special-needs-v2/psychological-deep-dive",
      sampleHref: "/api/insights/samples/deep-dive-psychological.pdf",
      accent: "#7C3AED",
    },
    {
      key: "special-needs",
      label: "Special Needs (7-domain)",
      body: "Multi-domain evaluation with consistency-between-homes score",
      route: "/special-needs-v2",
      sampleHref: null, // 7-domain sample is handled by the SpecialNeedsV2 page itself
      accent: "#B85B00",
    },
  ];

  return (
    <section id="three-reports" className="relative py-14 sm:py-16 bg-white border-y border-[#EFE9F9]">
      {/* ---------- Tier 1 · CORE REPORTS ---------- */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 text-center">
        <Eyebrow>Core Reports · Individual Journey</Eyebrow>
        <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight mt-2">
          Every parent can create three core reports.
        </h2>
        <p className="text-sm sm:text-base text-[#4B4567] mt-3 max-w-3xl mx-auto">
          Complete them on your own, at your own pace. These three anchor
          your reflection and stay with you across the whole journey.
        </p>
      </div>
      <div className="mt-8 grid md:grid-cols-3 gap-4 max-w-6xl mx-auto px-4 sm:px-6">
        <ThreeReportsCover
          testid="three-reports-situation"
          number="1"
          title="Co-Parenting Assessment Report"
          body="A private snapshot of how you and the other parent are actually communicating today — with concrete next steps."
          accent="#3D1A78"
          sampleHref="/api/insights/samples/sacoparents-coparenting-report.pdf"
          sampleLabel="View sample (PDF)"
        />
        <ThreeReportsCover
          testid="three-reports-foundation"
          number="2"
          title="Foundation Statement"
          body="A one-page statement of your child-focused goals — the anchor you can return to whenever things get emotionally hot."
          accent="#2DB5B5"
          sampleHref="/api/insights/samples/sacoparents-foundation-statement.pdf"
          sampleLabel="View sample (PDF)"
        />
        <ThreeReportsCover
          testid="three-reports-child-needs"
          number="3"
          title="Child Needs Statement"
          body="A structured, child-focused agenda you can bring straight into your mediation session or attorney meeting."
          accent="#B85B00"
        />
      </div>

      {/* ---------- Tier 2 · FOCUSED ASSESSMENTS ---------- */}
      <div className="mt-16 max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-3xl mx-auto">
          <Eyebrow>When Your Child Needs More Support</Eyebrow>
          <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-tight mt-2">
            Focused assessments for specific needs.
          </h3>
          <p className="text-sm sm:text-base text-[#4B4567] mt-3">
            Use these alongside the three core reports when a specific
            area of your child's life needs deeper attention. Each one
            produces its own individual and (when both parents complete
            it) joint alignment report.
          </p>
        </div>
        <div
          className="mt-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-4"
          data-testid="focused-assessments-tier"
        >
          {focusedAssessments.map((fa) => (
            <div
              key={fa.key}
              className="group rounded-2xl border border-[#E5E0EE] bg-white p-5 hover:border-[#3D1A78] hover:shadow-md transition-all flex flex-col"
              data-testid={`focused-assessment-${fa.key}`}
            >
              <Link to={fa.route} className="flex-1 block">
                <div
                  className="text-[11px] uppercase tracking-[0.18em] font-bold mb-2"
                  style={{ color: fa.accent }}
                >
                  {fa.label}
                </div>
                <p className="text-sm text-[#4B4567] leading-snug">
                  {fa.body}
                </p>
                <div className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-[#3D1A78] group-hover:underline">
                  Learn more <ArrowRight size={12} />
                </div>
              </Link>
              {fa.sampleHref && (
                <a
                  href={fa.sampleHref}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-[#3D1A78]/80 hover:text-[#3D1A78] hover:underline self-start"
                  data-testid={`focused-assessment-${fa.key}-sample`}
                >
                  View sample (PDF) <ArrowUpRight size={11} />
                </a>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   NOT-A-VERDICT STATEMENT — a single, prominent visual block
   that captures the philosophy of the entire product. Pulled up
   out of Step 6's body copy (previously buried on the six-step
   grid) so it reads as a first-class principle, not a footnote.

   Reasoning: parents and referring professionals sometimes fear
   the tool will "score" one parent against the other. This block
   says out loud that it doesn't — and separates the parent app
   conceptually from a custody evaluation.
============================================================ */
function NotAVerdictStatement() {
  return (
    <section
      id="not-a-verdict"
      className="relative py-16 sm:py-20 bg-gradient-to-br from-[#1A1330] via-[#2A0F5F] to-[#3D1A78]"
      data-testid="not-a-verdict-statement"
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6 text-center">
        <div className="inline-flex w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-white/10 backdrop-blur border border-white/20 items-center justify-center mb-6">
          <Scale size={26} className="text-white" strokeWidth={1.75} />
        </div>
        <p
          className="font-serif text-2xl sm:text-3xl lg:text-4xl text-white leading-snug"
          data-testid="not-a-verdict-headline"
        >
          SA CoParents doesn't decide which parent is right.
        </p>
        <p className="mt-5 text-base sm:text-lg text-white/85 leading-relaxed max-w-2xl mx-auto">
          It helps identify what the child needs, where parents align,
          where they see things differently, and what options may help
          them move forward.
        </p>
      </div>
    </section>
  );
}

/* ============================================================
   INDIVIDUAL → JOINT BRIDGE — the pivot moment. Signals clearly
   that everything above is the solo path, and everything below
   is what unlocks when a co-parent or professional connects.
============================================================ */
function IndividualToJointBridge() {
  // Iter199 · personalise the bridge copy by the parent's most recent
  // Safety Assessment level, and A/B-track impressions + clicks so
  // ops can compare CTR of the new "no concerns"/"safe paths" copy
  // vs the baseline. Both variants are ADMIN-editable via
  // /admin/nudge-copy (see nudge_copy_routes._KEY_JOINT_BRIDGE).
  const { status } = useSafetyLevel();
  const { copy, trackImpression, trackClick } = useJointBridgeCopy();
  // Neutral default when we don't know the parent's level (guest,
  // never taken the screen, endpoint 5xx) is the CLEARED variant —
  // the historical baseline. "concerned" is only shown when we're
  // confident, so a false positive never hides joint tools from a
  // safe parent.
  const variantKey = status === "concerned" ? "concerned" : "cleared";
  const variant = copy[variantKey];

  React.useEffect(() => {
    trackImpression(variantKey);
  }, [variantKey, trackImpression]);

  return (
    <section
      id="individual-to-joint-bridge"
      className="relative py-16 sm:py-20 bg-gradient-to-b from-white via-[#F5F1FB] to-white"
      data-testid="individual-to-joint-bridge"
      data-variant={variantKey}
    >
      <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
        <div
          className="text-[11px] uppercase tracking-[0.28em] font-bold text-[#3D1A78] mb-3"
          data-testid="joint-bridge-eyebrow"
        >
          {variant.eyebrow}
        </div>
        <h2
          className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-snug"
          data-testid="joint-bridge-headline"
        >
          {variant.headline}
        </h2>
        <p
          className="mt-3 text-sm sm:text-base text-[#4B4567] leading-relaxed"
          data-testid="joint-bridge-body"
        >
          {variant.body}
        </p>
        <div className="mt-6 flex justify-center text-[#3D1A78]" aria-hidden>
          <ArrowDown size={24} strokeWidth={2.2} />
        </div>

        {variantKey === "cleared" ? (
          <div
            className="mt-6 rounded-3xl border-2 border-[#2DB5B5]/30 bg-white p-6 sm:p-8 text-left shadow-sm"
            data-testid="joint-journey-card"
          >
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#0E7A7A]">
              Joint Journey
            </div>
            <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-2 leading-tight">
              Joint Assessment → Joint Alignment Report
            </h3>
            <p className="text-sm sm:text-base text-[#4B4567] mt-3 leading-relaxed">
              Once both parents complete their reflections, the app (or a
              connected professional using{" "}
              <span className="font-semibold text-[#0E7A7A]">SA CoParents Align</span>)
              can generate a Joint Alignment Report — a side-by-side view
              of shared understanding, differences worth discussing, and
              options for moving forward.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Link
                to="/samples/joint-alignment-preview"
                onClick={() => trackClick(variantKey, "sample-joint-preview")}
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#0E7A7A] hover:underline"
                data-testid="joint-journey-see-sample"
              >
                {variant.cta_label} <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        ) : (
          // Safety-concerned variant — the joint journey is intentionally
          // NOT shown. Route the parent to individual-only safe paths
          // (safety plan, journal, resources) instead so we never
          // pressure a parent who screened concerned into cooperative
          // tools they aren't ready for.
          <div
            className="mt-6 rounded-3xl border-2 border-[#B45F13]/40 bg-[#FFF6EA] p-6 sm:p-8 text-left shadow-sm"
            data-testid="safe-path-card"
          >
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#B45F13]">
              Safe Paths
            </div>
            <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-2 leading-tight">
              Individual-only tools that don&rsquo;t require the other parent
            </h3>
            <p className="text-sm sm:text-base text-[#4B4567] mt-3 leading-relaxed">
              Continue your private reflection, keep a co-parenting journal,
              build a safety plan, and connect with a domestic-violence
              advocate. Joint tools remain here for whenever &mdash; and only
              if &mdash; it&rsquo;s ever safe to invite the other parent.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link
                to={variant.cta_route || "/safety"}
                onClick={() => trackClick(variantKey, "safe-individual-paths")}
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#B45F13] hover:underline"
                data-testid="safe-path-cta"
              >
                {variant.cta_label} <ArrowRight size={14} />
              </Link>
              <Link
                to="/journal"
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#3D1A78] hover:underline"
                data-testid="safe-path-journal"
              >
                Open my private journal <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function ThreeReportsCover({ testid, number, title, body, accent, sampleHref, sampleLabel }) {
  return (
    <article
      data-testid={testid}
      className="rounded-2xl border border-[#E5E0EE] bg-gradient-to-br from-white to-[#F7F4FC] p-6 sm:p-7 relative overflow-hidden hover:shadow-md transition-shadow flex flex-col"
    >
      <div
        className="absolute top-4 right-4 w-9 h-9 rounded-full flex items-center justify-center font-serif text-lg font-semibold text-white"
        style={{ backgroundColor: accent }}
      >
        {number}
      </div>
      <div className="mb-3">
        <FileText size={20} style={{ color: accent }} />
      </div>
      <h3 className="font-serif text-lg text-[#1A1330] leading-snug pr-10">
        {title}
      </h3>
      <p className="text-sm text-[#4B4567] mt-3 leading-relaxed">{body}</p>
      <div className="mt-4 text-[11px] uppercase tracking-[0.14em] font-bold" style={{ color: accent }}>
        Downloadable PDF · shareable
      </div>
      <div className="mt-auto pt-4">
        {sampleHref ? (
          <a
            data-testid={`${testid}-sample-link`}
            href={sampleHref}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm font-semibold rounded-full px-3.5 py-1.5 border transition-colors"
            style={{ color: accent, borderColor: accent, backgroundColor: "rgba(255,255,255,0.6)" }}
          >
            {sampleLabel}
            <span aria-hidden>→</span>
          </a>
        ) : (
          <span
            data-testid={`${testid}-sample-placeholder`}
            className="inline-flex items-center gap-1.5 text-xs italic text-[#857E9C]"
          >
            {sampleLabel}
          </span>
        )}
      </div>
    </article>
  );
}

/* ============================================================
   SECTION — HOW IT WORKS
============================================================ */
function Step5CoparentCtas() {
  // Detect the invited-parent state: either the /join flow has
  // stashed the professional name in sessionStorage, or the URL
  // carries ?prof=NAME (readable link for professionals to share).
  const [profName, setProfName] = React.useState(null);
  React.useEffect(() => {
    try {
      const stored = window.sessionStorage?.getItem("invited_professional_name");
      const qs = new URLSearchParams(window.location.search).get("prof");
      const name = (qs || stored || "").trim();
      if (name) setProfName(name);
    } catch { /* noop */ }
  }, []);

  if (profName) {
    return (
      <div
        className="mt-4 rounded-2xl border border-[#B7DEC6] bg-[#E1F3E8] p-3 text-[13px] text-[#186142]"
        data-testid="how-step-5-invited-banner"
      >
        <div className="font-semibold flex items-center gap-1.5 mb-0.5">
          ✓ Connected to {profName}
        </div>
        <div className="text-[12px] leading-relaxed">
          Complete your reflection at your own pace — your professional
          will use the completed assessments to generate a Joint
          Alignment Report.
        </div>
      </div>
    );
  }
  return (
    <div className="mt-4 flex flex-wrap gap-2" data-testid="how-step-5-ctas">
      <a
        href="/dashboard"
        className="inline-flex items-center gap-1 rounded-full bg-[#3D1A78] hover:bg-[#2A0F5F] text-white px-3.5 py-1.5 text-[12px] font-semibold"
        data-testid="how-step-5-invite-coparent"
      >
        Invite my co-parent →
      </a>
      <a
        href="/join"
        className="inline-flex items-center gap-1 rounded-full bg-white border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-3.5 py-1.5 text-[12px] font-semibold"
        data-testid="how-step-5-connect-professional"
      >
        Connect with a professional →
      </a>
    </div>
  );
}

function HowItWorks() {
  // Parent-friendly language on top, formal terminology as a small
  // subtitle for attorneys/mediators/therapists reviewing the same page.
  const steps = [
    {
      n: "1",
      title: "What's Going On?",
      subtitle: "Tell Us About Your Family",
      icon: ClipboardList,
      body: "Tell us a little about your current parenting situation. There are no wrong answers.",
    },
    {
      n: "2",
      title: "How Is Co-Parenting Going Right Now?",
      subtitle: "Co-Parenting Relationship Assessment",
      icon: MessageCircle,
      body: "A short reflection on how the two of you exchange information, share decisions, and manage handoffs.",
    },
    {
      n: "3",
      title: "What Does Your Child Need Most?",
      subtitle: "Child Needs Assessment",
      icon: Baby,
      body: "Think about your child's routines, relationships, education, health, activities and emotional needs.",
    },
    {
      n: "4",
      title: "What Matters Most to You as a Parent?",
      subtitle: "Foundation Statement",
      icon: Compass,
      body: "We'll organize what you've told us into a clear Foundation Statement — your starting point in your own words.",
      sampleHref: "/foundation/demo",
      sampleLabel: "See what one looks like",
    },
    {
      n: "5",
      title: "Where Do We See Things the Same — and Differently?",
      subtitle: "Two Parents. Two Perspectives.",
      icon: Users,
      body: "Each parent completes their assessment separately. When appropriate, the perspectives can then be compared to identify areas of alignment and differences that need discussion. If you're working with a professional, your professional can invite both parents and use the completed assessments to generate a Joint Alignment Report.",
      step5Ctas: true,
    },
    {
      n: "6",
      title: "Your Family's Next-Step Guide",
      subtitle: "Joint Alignment Report",
      icon: FileText,
      body: "Options, resources, and questions you can take into mediation or a conversation with a professional.",
    },
  ];
  return (
    <section
      id="how-it-works"
      className="relative py-24 sm:py-28 bg-[#F8F7FC] scroll-mt-16"
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto fade-up">
          <Eyebrow>Your Six-Step Parent Journey</Eyebrow>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight">
            Six plain-language steps toward
            <br className="hidden sm:block" /> a healthier plan for your child.
          </h2>
          <p className="mt-5 text-sm sm:text-base text-[#4B4567] leading-relaxed">
            Each step is written for parents first. The formal terminology
            (used by attorneys, mediators, and therapists) appears in
            smaller text underneath so the professionals reviewing your
            reports can find the same information.
          </p>
        </div>

        <div className="mt-14 grid md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-7">
          {steps.map((s) => (
            <div
              key={s.n}
              className="card-soft p-6 sm:p-7 relative"
              data-testid={`how-step-${s.n}`}
            >
              <div className="absolute -top-4 -left-1 font-serif text-[4.5rem] leading-none text-[#3D1A78]/8 select-none">
                {s.n}
              </div>
              <div className="relative">
                <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] grid place-items-center text-white shadow-sm mb-4">
                  <s.icon size={18} strokeWidth={2.2} />
                </div>
                <div className="text-[10px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold mb-1">
                  Step {s.n}
                </div>
                <h3 className="font-serif text-[1.35rem] sm:text-2xl text-[#1A1330] leading-tight mb-1.5">
                  {s.title}
                </h3>
                <div
                  className="text-[11px] uppercase tracking-[0.16em] text-[#857E9C] font-semibold mb-3"
                  data-testid={`how-step-${s.n}-formal-subtitle`}
                >
                  {s.subtitle}
                </div>
                <p className="text-sm sm:text-[15px] text-[#4B4567] leading-relaxed">
                  {s.body}
                </p>
                {s.sampleHref && (
                  <Link
                    to={s.sampleHref}
                    className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-[#3D1A78] hover:underline"
                    data-testid={`how-step-${s.n}-sample-link`}
                  >
                    {s.sampleLabel || "See a sample"} →
                  </Link>
                )}
                {s.step5Ctas && <Step5CoparentCtas />}
              </div>
            </div>
          ))}
        </div>

        {/* Prominent sample CTA — sits below the six-step grid so
            visitors leave with a way to peek at a real artefact without
            signing up. Links to the public Foundation Statement demo. */}
        <div className="mt-10 flex justify-center">
          <Link
            to="/foundation/demo"
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#3D1A78] text-[#3D1A78] px-6 py-3 text-sm font-semibold shadow-sm hover:bg-[#F5F1FB] hover:shadow-md transition-all"
            data-testid="how-it-works-foundation-sample-cta"
          >
            See a sample Foundation Statement →
          </Link>
        </div>

        <p className="text-center text-sm sm:text-base text-[#4B4567] mt-14 max-w-xl mx-auto">
          Every step is designed to help you make better decisions for
          your child — not to decide which parent has the better answer.
        </p>
      </div>
    </section>
  );
}


/* ============================================================
   PROFESSIONAL CONNECTION — sits directly after the six-step
   parent journey so the ecosystem hand-off is explicit right
   where a parent is deciding what to do next. Two clear CTAs:
     - "I have a professional invitation"  → /join
     - "Learn about SA CoParents Align"    → sacoparentsalign.com
============================================================ */
function ProfessionalConnection() {
  return (
    <section
      id="professional-connection"
      className="relative py-20 sm:py-24 bg-white border-t border-[#EFE9F9]"
      data-testid="professional-connection"
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        <div
          className="rounded-3xl border-2 border-[#2DB5B5]/30 bg-gradient-to-br from-white to-[#EEF6F6] p-6 sm:p-10"
          data-testid="professional-connection-card"
        >
          <div className="flex items-start gap-3 mb-4">
            <div className="shrink-0 w-11 h-11 rounded-2xl bg-[#2DB5B5]/15 grid place-items-center text-[#0E7A7A]">
              <Briefcase size={20} strokeWidth={2.2} />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#0E7A7A]">
                The Ecosystem Hand-off
              </div>
              <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-snug mt-1">
                Working with a mediator, attorney, therapist, or parenting professional?
              </h2>
            </div>
          </div>

          <p className="text-sm sm:text-base text-[#4B4567] leading-relaxed">
            Your professional can invite you to connect your completed
            SA CoParents reflections with{" "}
            <span className="font-semibold text-[#0E7A7A]">SA CoParents Align</span>.
            Your individual reflection remains yours. Align helps the
            professional identify areas of shared understanding and
            differences that may need discussion.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/join"
              className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] hover:bg-[#2A0F5F] text-white px-6 py-3 text-sm font-semibold shadow-sm transition-colors"
              data-testid="professional-connection-invitation-cta"
            >
              I have a professional invitation
              <ArrowRight size={16} />
            </Link>
            <a
              href="https://sacoparentsalign.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-full bg-white border-2 border-[#0E7A7A] text-[#0E7A7A] hover:bg-[#EEF6F6] px-6 py-3 text-sm font-semibold transition-colors"
              data-testid="professional-connection-align-cta"
            >
              Learn about SA CoParents Align
              <ArrowUpRight size={16} />
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   ECOSYSTEM FLOW — Iteration 203. A single vertical diagram that
   tells the whole SA CoParents story end-to-end. Sits between the
   professional-connection card and the alignment-philosophy strip
   so the reader has just been told they can connect to Align —
   this section shows exactly what that connection looks like.

   Four stacked tiers:
     1. INDIVIDUAL PARENT   — Assessment → Foundation → Child Needs
     2. TWO PARENTS         — Joint Alignment Report (the bridge)
     3. PROFESSIONAL        — Review → Options & Resources → Report
     4. NEXT STEP           — Mediation / Agreement / Therapy / etc.

   Each tier connects to the next with a downward arrow so parents
   read this as a sequence, not four unrelated boxes.
============================================================ */
function EcosystemFlow() {
  const tiers = [
    {
      key: "individual",
      eyebrow: "Individual Parent",
      title: "Private reflection, in your own words.",
      chips: ["Assessment", "Foundation Statement", "Child Needs"],
      accent: "#3D1A78",
      bg: "bg-[#F7F4FC]",
      border: "border-[#3D1A78]/20",
    },
    {
      key: "two-parents",
      eyebrow: "Two Parents",
      title: "Joint Alignment Report.",
      chips: [
        "Where you align",
        "Where you see things differently",
        "Questions worth discussing",
      ],
      accent: "#2DB5B5",
      bg: "bg-[#EEF6F6]",
      border: "border-[#2DB5B5]/30",
    },
    {
      key: "professional",
      eyebrow: "Professional",
      title: "SA CoParents Align — Professional Review.",
      chips: [
        "Interpret through a professional lens",
        "Options & Resources",
        "Professional Report",
      ],
      accent: "#0E7A7A",
      bg: "bg-[#E6F0F7]",
      border: "border-[#0E7A7A]/30",
    },
    {
      key: "next-step",
      eyebrow: "Next Step",
      title: "A concrete, child-focused pathway.",
      chips: [
        "Child-focused mediation",
        "Co-parenting agreement",
        "Therapeutic support",
        "Educational / medical / psychological resource",
        "Other appropriate process",
      ],
      accent: "#B85B00",
      bg: "bg-[#FFF6EA]",
      border: "border-[#B85B00]/30",
    },
  ];

  return (
    <section
      id="full-ecosystem-flow"
      className="relative py-24 sm:py-28 bg-white"
      data-testid="full-ecosystem-flow"
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <Eyebrow>The Full Ecosystem</Eyebrow>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight mt-2">
            From private reflection to a concrete next step.
          </h2>
          <p className="mt-5 text-sm sm:text-base text-[#4B4567] leading-relaxed">
            SA CoParents and SA CoParents Align are sibling tools. The
            individual reflection stays with each parent. Align is where a
            professional (with consent) helps interpret shared and different
            perspectives into practical options and resources.
          </p>
        </div>

        <div className="space-y-3">
          {tiers.map((tier, i) => (
            <React.Fragment key={tier.key}>
              <div
                className={`rounded-2xl border-2 ${tier.border} ${tier.bg} p-5 sm:p-7`}
                data-testid={`ecosystem-tier-${tier.key}`}
              >
                <div
                  className="text-[10px] uppercase tracking-[0.22em] font-bold"
                  style={{ color: tier.accent }}
                >
                  {tier.eyebrow}
                </div>
                <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-snug mt-1">
                  {tier.title}
                </h3>
                <div className="mt-4 flex flex-wrap gap-2">
                  {tier.chips.map((chip) => (
                    <span
                      key={chip}
                      className="inline-flex items-center rounded-full bg-white border border-[#E5E0EE] px-3 py-1 text-[12px] sm:text-[13px] font-semibold text-[#1A1330]"
                    >
                      {chip}
                    </span>
                  ))}
                </div>
              </div>
              {i < tiers.length - 1 && (
                <div
                  className="flex justify-center py-1"
                  aria-hidden="true"
                  data-testid={`full-ecosystem-flow-arrow-${i}`}
                >
                  <ArrowDown size={22} className="text-[#3D1A78]/40" />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>

        <p className="text-center text-xs sm:text-sm text-[#857E9C] mt-10 max-w-xl mx-auto leading-relaxed">
          Not a verdict on which parent is right — a structured way to
          identify what your child needs and what options may help you
          move forward together, separately, or with professional support.
        </p>
      </div>
    </section>
  );
}

/* ============================================================
   ALIGNMENT BEFORE AGREEMENT — the parent philosophy strip.
   Sits between "How it works" and the trust signals so the reader
   understands the guiding idea before they see the credentials.
============================================================ */
function AlignmentPhilosophy() {
  const shared = [
    "Our child needs consistency.",
    "Our child needs a meaningful relationship with both parents.",
    "School needs to become more stable.",
    "Transitions are difficult for our child.",
    "We need a better way to exchange information.",
  ];
  return (
    <section
      id="alignment-philosophy"
      className="relative py-24 sm:py-28 bg-gradient-to-br from-[#3D1A78] via-[#4A2288] to-[#2DB5B5] text-white overflow-hidden"
      data-testid="alignment-philosophy"
    >
      <div className="absolute -top-40 -left-40 w-[32rem] h-[32rem] rounded-full bg-white/8 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-[32rem] h-[32rem] rounded-full bg-white/8 blur-3xl pointer-events-none" />
      <div className="relative max-w-5xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-3xl mx-auto">
          <div className="text-[10px] uppercase tracking-[0.28em] font-bold text-[#E8DEFA] mb-3">
            The Parent Philosophy
          </div>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl leading-tight">
            Start With Alignment.
            <br />
            <span className="text-[#A8DCDC]">Build Toward Agreement.</span>
          </h2>
          <p
            className="mt-6 text-base sm:text-lg text-white/90 leading-relaxed"
            data-testid="alignment-tagline"
          >
            Alignment does not mean agreement. Two parents may disagree
            about schedules, schools, activities, medical treatment or
            communication — and still become aligned around something
            more fundamental.
          </p>
        </div>

        <div
          className="mt-12 rounded-3xl bg-white/10 backdrop-blur-sm border border-white/20 p-6 sm:p-8"
          data-testid="alignment-shared-concerns"
        >
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#A8DCDC] mb-4 text-center">
            Shared concerns often sound like this
          </div>
          <ul className="grid sm:grid-cols-2 gap-3 sm:gap-4">
            {shared.map((s) => (
              <li
                key={s}
                className="flex items-start gap-3 rounded-2xl bg-white/10 px-4 py-3"
              >
                <Handshake size={16} className="mt-0.5 shrink-0 text-[#A8DCDC]" />
                <span className="font-serif text-[15px] sm:text-base italic leading-relaxed">
                  &ldquo;{s}&rdquo;
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-6 text-center text-sm sm:text-base text-white/85 leading-relaxed max-w-2xl mx-auto">
            Once the app identifies those shared concerns, negotiations
            become much easier — even between parents who can&rsquo;t
            agree on the details.
          </p>
        </div>

        <div
          className="mt-10 rounded-3xl border-2 border-white/30 p-6 sm:p-8 text-center"
          data-testid="alignment-child-value"
        >
          <p className="font-serif text-xl sm:text-2xl leading-relaxed italic">
            &ldquo;We value the parenting system by how well it supports
            the child, not by how friendly the adults appear.&rdquo;
          </p>
          <p className="mt-4 text-sm text-white/75 max-w-2xl mx-auto leading-relaxed">
            Successful co-parenting doesn&rsquo;t require former partners
            to become friends. Sometimes clear boundaries, limited
            communication and predictable structure are healthier than
            trying to create an artificially friendly relationship.
          </p>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   TRUST SIGNALS — "Why parents trust SA CoParents"
============================================================ */
function TrustSignals() {
  return (
    <section id="trust" className="relative py-20 sm:py-24 bg-gradient-to-br from-[#F8F7FC] via-white to-[#EEF6F6]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center mb-14">
          <Eyebrow>Why parents trust SA CoParents</Eyebrow>
          <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight mt-3">
            Built with care. Honest about limits.
          </h2>
          <p className="text-sm sm:text-base text-[#4B4567] mt-3 max-w-2xl mx-auto">
            Every assessment, PDF, and coaching prompt was designed with two
            beliefs in mind: parents deserve tools that respect their
            intelligence, and children deserve outcomes that come from real
            preparation — not a black box.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-5">
          <article className="rounded-3xl border border-[#E5E0EE] bg-white p-7 flex gap-4" data-testid="trust-created-by">
            <div className="shrink-0 w-14 h-14 rounded-full bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] flex items-center justify-center text-white">
              <Users size={22} />
            </div>
            <div className="min-w-0">
              <div className="eyebrow mb-1">Created by</div>
              <h3 className="font-serif text-xl text-[#1A1330]">Matt Sossi · Founder, SA CoParents</h3>
              <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
                Built in San Antonio, Texas — because too many parents were
                walking into mediation reactive, unprepared, and afraid.
                Our mission is to move families from emotionally reactive
                to child-focused, one conversation at a time.
              </p>
              <div className="text-xs text-[#857E9C] mt-3">
                <a href="mailto:mattsossi@bsossi.com" className="text-[#3D1A78] hover:underline">mattsossi@bsossi.com</a>
                {" · "}
                <a href="tel:2102241667" className="text-[#3D1A78] hover:underline">210-224-1667</a>
              </div>
            </div>
          </article>

          <article className="rounded-3xl border border-[#E5E0EE] bg-white p-7 flex gap-4" data-testid="trust-data">
            <div className="shrink-0 w-14 h-14 rounded-full bg-[#3D1A78]/10 flex items-center justify-center text-[#3D1A78]">
              <Lock size={22} />
            </div>
            <div className="min-w-0">
              <div className="eyebrow mb-1">Your data is protected</div>
              <h3 className="font-serif text-xl text-[#1A1330]">Yours to keep. Yours to delete.</h3>
              <ul className="text-sm text-[#4B4567] mt-2 space-y-1.5 leading-relaxed list-disc pl-4">
                <li>Your answers are never sold or used to train AI models.</li>
                <li>Delete your account and all data any time — deletion is complete within 30 days.</li>
                <li>Share links you create can be revoked. Locked safety sections stay in every shared PDF.</li>
              </ul>
              <div className="text-xs mt-3 flex flex-wrap gap-x-4 gap-y-1">
                <Link to="/privacy" className="text-[#3D1A78] hover:underline">Privacy policy</Link>
                <Link to="/data-retention" className="text-[#3D1A78] hover:underline">Data retention</Link>
              </div>
            </div>
          </article>

          <article className="rounded-3xl border border-[#E5E0EE] bg-white p-7 flex gap-4" data-testid="trust-methodology">
            <div className="shrink-0 w-14 h-14 rounded-full bg-[#2DB5B5]/15 flex items-center justify-center text-[#0E7A7A]">
              <FlaskConical size={22} />
            </div>
            <div className="min-w-0">
              <div className="eyebrow mb-1">What this tool can and can&rsquo;t do</div>
              <h3 className="font-serif text-xl text-[#1A1330]">Preparation, not diagnosis.</h3>
              <div className="text-sm text-[#4B4567] mt-2 leading-relaxed space-y-2">
                <p>
                  <strong className="text-[#0E7A7A]">Can do:</strong> Help you name goals, structure your thinking, and generate reports child-focused enough to hand a mediator or pediatrician.
                </p>
                <p>
                  <strong className="text-[#B85B00]">Can&rsquo;t do:</strong> Replace a lawyer, therapist, mediator, or physician. Every score is a conversation starter — never the last word.
                </p>
              </div>
              <div className="text-xs mt-3">
                <Link to="/methodology" className="text-[#3D1A78] hover:underline">See how each score is calculated</Link>
              </div>
            </div>
          </article>

          <article className="rounded-3xl border border-[#E5E0EE] bg-white p-7 flex gap-4" data-testid="trust-professional-help">
            <div className="shrink-0 w-14 h-14 rounded-full bg-[#B85B00]/12 flex items-center justify-center text-[#B85B00]">
              <LifeBuoy size={22} />
            </div>
            <div className="min-w-0">
              <div className="eyebrow mb-1">When to seek professional help</div>
              <h3 className="font-serif text-xl text-[#1A1330]">If safety is a question, call a human.</h3>
              <ul className="text-sm text-[#4B4567] mt-2 leading-relaxed space-y-1.5">
                <li><strong>988</strong> — Suicide & Crisis Lifeline (call or text)</li>
                <li><strong>1-800-799-SAFE</strong> — National Domestic Violence Hotline</li>
                <li><strong>911</strong> — Immediate danger</li>
                <li>Consult a family law attorney before any custody agreement is signed.</li>
                <li>A licensed therapist can support your child through transition — this app can&rsquo;t.</li>
              </ul>
              <div className="text-xs mt-3">
                <Link to="/safety" className="text-[#3D1A78] hover:underline">See our crisis-resource page</Link>
              </div>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   HOMEPAGE FAQ — compact 4-question strip that surfaces the last
   trust doubts a hesitant parent still carries just before the
   final CTA. Uses native <details>/<summary> so there's no JS
   state to manage and each question is independently expandable.
============================================================ */
const HOMEPAGE_FAQ = [
  {
    id: "solo",
    q: "Do I need my co-parent to participate?",
    a: (
      <>
        No. You can complete every assessment, generate every report, and
        follow every pathway on your own. The comparison views become
        available if and when your co-parent chooses to join — never before.
      </>
    ),
  },
  {
    id: "privacy",
    q: "Will my co-parent see what I write?",
    a: (
      <>
        Your answers are private to you until you explicitly hit{" "}
        <strong>Share</strong> on a specific report. Even then, only the
        report content is shared — not your raw answers. You can revoke
        any share link at any time.
      </>
    ),
  },
  {
    id: "professional",
    q: "Is this a substitute for a mediator, therapist, or attorney?",
    a: (
      <>
        No — and it&rsquo;s not meant to be. SA CoParents helps you arrive
        at those conversations <em>prepared</em>, with a clear agenda and
        the right questions. It is preparation and communication support,
        not legal or clinical advice.
      </>
    ),
  },
  {
    id: "safety",
    q: "What if my situation involves conflict or safety concerns?",
    a: (
      <>
        Pick the situation that fits — the app will route you to a
        structured-written pathway and Texas crisis resources instead of
        a joint-mediation pathway. Safety comes before every other
        recommendation, always.
      </>
    ),
  },
];

function HomepageFAQ() {
  return (
    <section
      id="homepage-faq"
      className="relative py-20 sm:py-24 bg-white border-t border-[#EFE9F9]"
      data-testid="homepage-faq"
    >
      <div className="max-w-3xl mx-auto px-4 sm:px-6">
        <div className="text-center">
          <Eyebrow>Still deciding?</Eyebrow>
          <h2 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-3">
            Answers to the last four questions parents ask.
          </h2>
        </div>
        <ul className="mt-10 space-y-3">
          {HOMEPAGE_FAQ.map((item) => (
            <li key={item.id}>
              <details
                className="group rounded-2xl border border-[#E5E0EE] bg-[#FCFBFE] px-5 py-4 open:bg-white open:shadow-sm transition-colors"
                data-testid={`homepage-faq-${item.id}`}
              >
                <summary
                  className="cursor-pointer list-none flex items-start justify-between gap-3 text-left"
                  data-testid={`homepage-faq-${item.id}-summary`}
                >
                  <span className="font-serif text-lg text-[#1A1330] leading-snug">
                    {item.q}
                  </span>
                  <span className="shrink-0 mt-1 w-6 h-6 rounded-full border border-[#D6CFE8] text-[#3D1A78] grid place-items-center text-lg font-light group-open:rotate-45 transition-transform">
                    +
                  </span>
                </summary>
                <p
                  className="mt-3 text-sm sm:text-base text-[#4B4567] leading-relaxed"
                  data-testid={`homepage-faq-${item.id}-answer`}
                >
                  {item.a}
                </p>
              </details>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ============================================================
   SECTION — FINAL CTA
============================================================ */
function FinalCTA() {
  return (
    <section className="relative py-24 sm:py-32 bg-gradient-to-br from-[#F8F7FC] via-[#EFE9F9] to-[#E4F1F1] overflow-hidden">
      <div className="absolute -top-32 -right-32 w-[28rem] h-[28rem] rounded-full bg-[#D4C5F0]/30 blur-3xl" />
      <div className="absolute -bottom-40 -left-32 w-[30rem] h-[30rem] rounded-full bg-[#A8DCDC]/30 blur-3xl" />

      <div className="relative max-w-4xl mx-auto px-4 sm:px-6 text-center">
        <Eyebrow>Take the First Step</Eyebrow>
        <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl text-[#1A1330] leading-tight">
          Your Children Deserve Parents
          <br className="hidden sm:block" /> Who Can Work Together
        </h2>
        <p className="text-base text-[#4B4567] mt-6 max-w-2xl mx-auto leading-relaxed">
          Every step toward healthier communication creates a stronger
          foundation for your children.
        </p>

        <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-10 leading-snug">
          Discover Your Co-Parenting Strengths and Growth Opportunities
        </h3>
        <p className="text-sm sm:text-base text-[#4B4567] mt-3 max-w-xl mx-auto">
          Take the first step toward healthier communication, stronger
          cooperation, and better outcomes for your children.
        </p>

        {/* Single primary action — one recommendation, one next action.
            The prior secondary "Learn more" scrolled to a section that
            no longer exists post-iter80; the new FAQ above this CTA
            covers that job. */}
        <div className="mt-9 flex items-center justify-center">
          <PrimaryCTA testid="final-primary-cta">Let&rsquo;s Start With You And Your Children</PrimaryCTA>
        </div>

        <div className="mt-16 inline-flex items-center gap-2 text-xs text-[#3D1A78] font-medium tracking-wide">
          <Sparkles size={14} />
          <span>
            From Conflict to Cooperation. From Disagreement to Understanding.
            From Parenting Apart to Raising Children Together.
          </span>
        </div>
      </div>
    </section>
  );
}

/* ============================================================
   PAGE
============================================================ */
export default function Landing() {
  return (
    <EnterAppProvider>
      <div className="min-h-screen bg-[#F8F7FC]">
        <MarketingHeader />
        {/* Iteration 80 → refined:
            1. Hero + situation picker + Path B card
            2. EcosystemFlow — 3-node strip showing the two-site
               relationship (sacoparentsapp ↔ sacoparentsalign) and
               the child-focused result.
            3. ThreeReportsStrip — "Individual Journey" trio: the
               Co-Parenting Assessment Report, Foundation Statement,
               and Child Needs Statement.
            4. IndividualToJointBridge — pivot from solo → joint,
               previewing the Joint Assessment / Joint Alignment
               Report path.
            5. HowItWorks — the six-step parent journey.
            6. ProfessionalConnection — explicit hand-off card sitting
               right after Step 6, with two CTAs: "I have a professional
               invitation" (→ /join) and "Learn about SA CoParents
               Align" (→ sacoparentsalign.com).
            7. AlignmentPhilosophy → TrustSignals → HomepageFAQ →
               FinalCTA close the page. */}
        <HeroTop />
        <CoachDemoSection />
        <HeroBottom />
        <EcosystemStrip />
        <ThreeReportsStrip />
        <NotAVerdictStatement />
        <IndividualToJointBridge />
        <HowItWorks />
        <ProfessionalConnection />
        <EcosystemFlow />
        <AlignmentPhilosophy />
        <TrustSignals />
        <HomepageFAQ />
        <FinalCTA />
        <MarketingFooter />
      </div>
    </EnterAppProvider>
  );
}
