import React, { useEffect, useMemo, useRef, useState } from "react";
import { ProSeeLink } from "../components/privacy/ProSeeLink";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  ShieldAlert,
  Shield,
  CheckCircle2,
  Download,
  Mail,
  Phone,
  Home,
  FileText,
  AlertTriangle,
  Send,
} from "lucide-react";
import { toast } from "sonner";
import { api, API } from "../lib/api";
import { logError } from "../lib/logger";
import { useAuth } from "../context/AuthContext";
import HighConcernOverlay from "../components/HighConcernOverlay";
import WatchFirstVideo from "../components/WatchFirstVideo";
import SectionCoaching from "../components/SectionCoaching";
import MethodologyCard from "../components/MethodologyCard";
import ReportShareControls, { pdfAbs } from "../components/ReportShareControls";
import BriefingEmailDialog from "../components/BriefingEmailDialog";
import { requestPreShareConsent } from "../components/PreShareConsentDialog";
import DeviceSafetyBanner from "../components/DeviceSafetyBanner";
import ScreenGuardrailPanel from "../components/ScreenGuardrailPanel";
import ReviewerStatusChip from "../components/ReviewerStatusChip";
import PathwayEndCTA from "../components/PathwayEndCTA";
import SafetyAssessmentResultsCard from "../components/safety/SafetyAssessmentResultsCard";
import MediatorEmailDialog from "../components/safety/MediatorEmailDialog";
import {
  StepHeader,
  YNUButton,
  QuestionRow,
  ProgressStrip,
  ExtensionStep,
} from "../components/safety/SafetyAssessmentPrimitives";

// TONE_STYLES lived here before 2026-03-05.  Moved to
// /components/safety/SafetyAssessmentResultsCard.jsx (the only place
// that used it).


function quickExit() {
  try {
    window.location.replace("https://www.google.com");
  } catch (_e) {
    window.location.href = "https://www.google.com";
  }
}


// StepHeader / YNUButton / QuestionRow / ProgressStrip / ExtensionStep /
// SafetyAssessmentResultsCard / MediatorEmailDialog previously lived in
// this file. Extracted 2026-03-05 into /components/safety/* so this
// page can focus on state, scoring, and API orchestration.

export default function SafetyAssessment() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [questions, setQuestions] = useState(null);
  const [step, setStep] = useState(0); // 0 intro, 1 section 1, 2 section 2, 3 results
  const [answersS1, setAnswersS1] = useState({});
  const [answersS2, setAnswersS2] = useState({});
  const [answersPattern, setAnswersPattern] = useState({});
  const [answersTrauma, setAnswersTrauma] = useState({});
  const [answersChild, setAnswersChild] = useState({});
  const [skippedExt, setSkippedExt] = useState({
    pattern_context: false,
    trauma_impact: false,
    child_experience: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [showHighConcern, setShowHighConcern] = useState(false);
  const [pendingHighId, setPendingHighId] = useState(null);
  const [emailing, setEmailing] = useState(false);
  const [mediatorDialogOpen, setMediatorDialogOpen] = useState(false);
  const [mediatorSending, setMediatorSending] = useState(false);
  const [briefingEmailOpen, setBriefingEmailOpen] = useState(false);
  const [briefingSending, setBriefingSending] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [missingIds, setMissingIds] = useState({ section_1: [], section_2: [] });
  const flashedRef = useRef(new Set());

  const isAdmin = Boolean(
    user?.email && user.email.toLowerCase() === "mattsossi@bsossi.com"
  );

  useEffect(() => {
    api
      .get("/safety-assessment/questions")
      .then((r) => setQuestions(r.data))
      .catch((err) => {
        logError("Failed to load questions:", err);
        toast.error("Couldn’t load the assessment. Please refresh.");
      });
  }, []);

  const highConcernIds = useMemo(
    () => new Set(questions?.high_concern_ids || []),
    [questions]
  );

  const onS1Change = (qid) => (value) => {
    setAnswersS1((prev) => ({ ...prev, [qid]: value }));
    setMissingIds((prev) =>
      prev.section_1.includes(qid)
        ? { ...prev, section_1: prev.section_1.filter((id) => id !== qid) }
        : prev
    );
    if (value === "yes" && highConcernIds.has(qid) && !flashedRef.current.has(qid)) {
      flashedRef.current.add(qid);
      setPendingHighId(qid);
      setShowHighConcern(true);
    }
  };
  const onS2Change = (qid) => (value) => {
    setAnswersS2((prev) => ({ ...prev, [qid]: value }));
    setMissingIds((prev) =>
      prev.section_2.includes(qid)
        ? { ...prev, section_2: prev.section_2.filter((id) => id !== qid) }
        : prev
    );
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      const r = await api.post("/safety-assessment", {
        section_1: answersS1,
        section_2: answersS2,
        pattern_context: skippedExt.pattern_context ? {} : answersPattern,
        trauma_impact: skippedExt.trauma_impact ? {} : answersTrauma,
        child_experience: skippedExt.child_experience ? {} : answersChild,
      });
      setResult(r.data);
      setMissingIds({ section_1: [], section_2: [] });
      setStep(6);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      logError("Submit failed:", err);
      const detail = err?.response?.data?.detail;
      // Server-side "all-answered" guard responds with a structured
      // { message, missing: { section_1, section_2 } } payload — flag
      // the missing rows in the UI and jump to the section that has
      // the earliest unanswered item.
      if (
        err?.response?.status === 400 &&
        detail &&
        typeof detail === "object" &&
        detail.missing
      ) {
        const miss = {
          section_1: detail.missing.section_1 || [],
          section_2: detail.missing.section_2 || [],
        };
        setMissingIds(miss);
        if (miss.section_1.length > 0) {
          setStep(1);
        } else if (miss.section_2.length > 0) {
          setStep(2);
        }
        toast.error(
          detail.message ||
            "Please answer every question before submitting.",
        );
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else {
        toast.error("Couldn’t submit your assessment. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const downloadPdf = () => {
    if (!result) return;
    const url = `${API}/safety-assessment/${result.assessment_id}/pdf`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const [downloadingCourt, setDownloadingCourt] = useState(false);
  const downloadCourtReport = () => {
    if (!result) return;
    setDownloadingCourt(true);
    const url = `${API}/safety-assessment/${result.assessment_id}/court-report`;
    try {
      window.open(url, "_blank", "noopener,noreferrer");
    } finally {
      setTimeout(() => setDownloadingCourt(false), 1200);
    }
  };

  const downloadOnePager = () => {
    if (!result) return;
    const url = `${API}/safety-assessment/${result.assessment_id}/one-pager`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const [cosignModal, setCosignModal] = useState(null);
  const prepareCoSign = async () => {
    if (!result?.assessment_id) return;
    // HB 300 + Privacy Policy pre-share gate — the QR link exposes the
    // court report to whoever scans it, so the six "YOU CONTROL THIS
    // REPORT" bullets must be shown before the token is minted.
    const consented = await requestPreShareConsent(
      "the reviewer Co-Sign QR link for your Family Violence & Communication Safety Screen"
    );
    if (!consented) return;
    try {
      const r = await api.post(
        `/safety-assessment/${result.assessment_id}/prepare-cosign`,
      );
      setCosignModal(r.data);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(detail || "Couldn't prepare the co-sign QR right now.");
    }
  };
  const copyCoSignLink = async () => {
    if (!cosignModal?.verify_url) return;
    try {
      await navigator.clipboard.writeText(cosignModal.verify_url);
      toast.success("Link copied to clipboard.");
    } catch {
      toast.error("Copy failed — long-press the link to copy manually.");
    }
  };

  const emailMe = async () => {
    if (!result) return;
    setEmailing(true);
    try {
      await api.post(`/safety-assessment/${result.assessment_id}/email`);
      toast.success("Sent! Check your inbox for the PDF.");
    } catch (err) {
      logError("Email failed:", err);
      const detail = err?.response?.data?.detail;
      if (err?.response?.status === 400 && /save your work|real email/i.test(detail || "")) {
        toast.error(detail, {
          action: { label: "Save my work", onClick: () => navigate("/claim") },
        });
      } else {
        toast.error(detail || "Couldn’t email the report right now.");
      }
    } finally {
      setEmailing(false);
    }
  };

  const openMediatorDialog = () => {
    if (!result) return;
    setMediatorDialogOpen(true);
  };

  const sendToMediator = async (payload) => {
    if (!result) return;
    setMediatorSending(true);
    try {
      await api.post(
        `/safety-assessment/${result.assessment_id}/email-mediator`,
        payload,
      );
      toast.success("Sent to your mediator.");
      setMediatorDialogOpen(false);
    } catch (err) {
      logError("Mediator email failed:", err);
      const detail = err?.response?.data?.detail;
      if (err?.response?.status === 400 && /save your work|real email/i.test(detail || "")) {
        toast.error(detail, {
          action: { label: "Save my work", onClick: () => navigate("/claim") },
        });
      } else {
        toast.error(detail || "Couldn’t send to your mediator right now.");
      }
    } finally {
      setMediatorSending(false);
    }
  };

  const regenerateSummaries = async () => {
    if (!result?.assessment_id) return;
    setRegenerating(true);
    try {
      await api.post(
        `/safety-assessment/${result.assessment_id}/regenerate-summaries`,
      );
      toast.success(
        "AI summaries regenerated. Your next PDF download will include the fresh copy.",
      );
    } catch (err) {
      logError("Regenerate summaries failed:", err);
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 429) {
        toast.error(detail || "Please wait a bit before regenerating again.");
      } else if (status === 503) {
        toast.error(
          detail ||
            "AI summary service is temporarily unavailable. Please try again shortly.",
        );
      } else {
        toast.error(detail || "Couldn't regenerate the summaries right now.");
      }
    } finally {
      setRegenerating(false);
    }
  };

  const allAnsweredS1 = useMemo(() => {
    if (!questions) return false;
    return questions.section_1.every((q) => answersS1[q.id]);
  }, [answersS1, questions]);
  const allAnsweredS2 = useMemo(() => {
    if (!questions) return false;
    return questions.section_2.every((q) => answersS2[q.id]);
  }, [answersS2, questions]);
  const answeredCountS1 = useMemo(() => {
    if (!questions) return 0;
    return questions.section_1.filter((q) => answersS1[q.id]).length;
  }, [answersS1, questions]);
  const answeredCountS2 = useMemo(() => {
    if (!questions) return 0;
    return questions.section_2.filter((q) => answersS2[q.id]).length;
  }, [answersS2, questions]);
  const missingS1Set = useMemo(
    () => new Set(missingIds.section_1 || []),
    [missingIds]
  );
  const missingS2Set = useMemo(
    () => new Set(missingIds.section_2 || []),
    [missingIds]
  );

  if (!questions) {
    return (
      <div className="min-h-screen grid place-items-center text-[#4B4567]">
        <div className="animate-pulse text-sm tracking-[0.2em] uppercase">Loading</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gentle-bg" data-testid="safety-assessment-page">
      {/* Top safety bar */}
      <div className="sticky top-0 z-40 backdrop-blur-md bg-[#C28771]/10 border-b border-[#C28771]/25">
        <div className="max-w-3xl mx-auto px-6 py-3 flex items-center justify-between gap-3">
          <Link
            to="/safety"
            className="inline-flex items-center gap-2 text-sm text-[#4B4567] hover:text-[#1A1330]"
            data-testid="assessment-back-link"
          >
            <ArrowLeft size={14} />
            Back to Safety
          </Link>
          <button
            type="button"
            onClick={quickExit}
            className="inline-flex items-center gap-2 rounded-full bg-[#C28771] hover:bg-[#a87560] text-white px-4 py-2 text-sm font-medium shadow-sm"
            data-testid="assessment-quick-exit"
            aria-label="Quick exit"
          >
            <Home size={14} />
            Quick exit
          </button>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {step === 0 && (
          <div className="card-soft p-6 sm:p-10 fade-up" data-testid="assessment-intro">
            <DeviceSafetyBanner />

            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-[#C28771]/15 text-[#C28771] grid place-items-center">
                <ShieldAlert size={18} />
              </div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold">
                SA CoParents
              </div>
            </div>
            <h1 className="font-bold text-3xl sm:text-4xl text-[#1A1330] tracking-tight mb-1">
              Family Safety and Functioning Reflection
            </h1>
            <p className="text-sm text-[#4B4567] mb-3">
              Family Violence and Communication Safety Screen
              <span className="text-[#3D1A78] font-semibold"> · TISFL</span>
            </p>
            <div className="mb-4">
              <ReviewerStatusChip />
            </div>

            <MethodologyCard id="safety" defaultOpen={false} />

            <p className="text-[#4B4567] leading-relaxed mb-4">
              This is a <strong className="text-[#1A1330]">reflection screen</strong> — not
              a clinical assessment — to help you notice patterns of family
              violence, coercive control, intimidation, stalking, or safety
              concerns before deciding how (or whether) to communicate with
              your co-parent. Several items are informed by the Danger
              Assessment (Campbell) domains most predictive of severe harm,
              but this tool is <strong className="text-[#1A1330]">not the
              Danger Assessment, MASIC-S, or HITS</strong>, and it has not
              been independently validated in custody or mediation
              populations. A trained professional should be involved in any
              high-risk situation.
            </p>

            <div
              className="rounded-2xl bg-[#F5F1FB] border border-[#3D1A78]/25 text-[#1A1330] p-4 sm:p-5 mb-4"
              data-testid="self-reflection-disclaimer"
            >
              <div className="flex items-center gap-2 mb-2">
                <FileText size={14} className="text-[#3D1A78]" />
                <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
                  What this assessment is (and is not)
                </div>
              </div>
              <p className="text-sm leading-relaxed">
                This assessment is a <strong>guided self-reflection and
                preparation resource</strong>. It is <strong>not a clinical,
                forensic, legal, or professional evaluation</strong>. Its
                results are intended to help you identify concerns, organize
                your thinking, and prepare questions for an appropriate
                professional.
              </p>
            </div>

            <div className="rounded-2xl bg-[#FCE3DC] border border-[#9A3A23]/25 text-[#9A3A23] p-4 sm:p-5 mb-6">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle size={14} />
                <div className="text-[11px] uppercase tracking-[0.18em] font-bold">
                  Important safety notice
                </div>
              </div>
              <p className="text-sm leading-relaxed">
                In addition to the disclaimer above: if there is immediate
                danger, call{" "}
                <a href="tel:911" className="underline font-bold">911</a>.
                If communication with the other parent creates fear, danger,
                or retaliation, direct communication may not be appropriate.
              </p>
              <a
                href="tel:18007997233"
                data-testid="intro-call-ndv"
                className="mt-3 inline-flex items-center gap-2 rounded-full bg-[#9A3A23] text-white px-4 py-2 text-xs font-bold hover:bg-[#7e2e1c]"
              >
                <Phone size={12} />
                Call 800-799-7233 · National DV Hotline
              </a>
            </div>

            {/* Family Safety and Functioning Reflection — procedural safeguards */}
            <div
              className="rounded-2xl border border-[#3D1A78]/20 bg-[#F5F1FB] p-5 sm:p-6 mb-6"
              data-testid="tisfl-safeguards"
            >
              <div className="flex items-center gap-2 mb-3">
                <ShieldAlert size={14} className="text-[#3D1A78]" />
                <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                  Procedural safeguards · Trauma-Informed Lens
                </div>
              </div>
              <ul className="text-sm text-[#1A1330] space-y-2">
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                  <span>You complete this <strong>separately</strong> from your co-parent. Your answers are private and are never shared with them unless you choose to.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                  <span>You can <strong>pause any time</strong>. If a question raises a strong reaction, step away, breathe, and return when you&rsquo;re ready.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                  <span>This tool <strong>does not diagnose</strong> and does not label either parent. It reflects behaviour and safety signals — not personality or worth.</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 size={14} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                  <span>Safety information stays walled off from the Compare view. Your co-parent only sees the parenting-plan implications, never your pattern or trauma details.</span>
                </li>
              </ul>
              <div className="mt-4 rounded-xl border border-[#3D1A78]/20 bg-white p-3 text-xs text-[#4B4567] leading-relaxed">
                <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1.5">
                  Two interpretation rules
                </div>
                <ol className="list-decimal list-inside space-y-1">
                  <li>Trauma symptoms are not evidence that a parent is unreliable, unfit, or responsible for the violence.</li>
                  <li>A history of trauma does not excuse coercion, intimidation, child maltreatment, or other harmful parenting behavior.</li>
                </ol>
              </div>
            </div>

            {/* 4-dimension clinical model — Safety is one of four separate lenses */}
            <div className="rounded-2xl border border-[#E5E0EE] bg-[#F8F5FF] p-5 sm:p-6 mb-6" data-testid="four-dimension-model">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-full bg-[#3D1A78]/12 grid place-items-center text-[#3D1A78] text-[10px] font-bold">
                  1/4
                </div>
                <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                  Where this assessment sits in the bigger picture
                </div>
              </div>
              <p className="text-sm text-[#4B4567] leading-relaxed mb-4">
                We evaluate co-parenting on four separate dimensions, so that a
                communication difference (for example, from autism or ADHD) is
                never confused with a genuine safety concern. This
                assessment focuses on the first one — <strong>Safety</strong>.
              </p>
              <div className="grid sm:grid-cols-2 gap-3">
                <div className="rounded-xl border-2 border-[#C28771] bg-white p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#C28771] mb-1">
                    Dimension 1 · Safety <span className="text-[#857E9C]">(you are here)</span>
                  </div>
                  <div className="text-sm text-[#1A1330] font-semibold mb-1">Family violence, coercive control, fear</div>
                  <div className="text-xs text-[#4B4567]">→ Safety recommendations &amp; safer pathways</div>
                </div>
                <div className="rounded-xl border border-[#E5E0EE] bg-white p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">
                    Dimension 2 · Communication
                  </div>
                  <div className="text-sm text-[#1A1330] font-semibold mb-1">Communication profile</div>
                  <div className="text-xs text-[#4B4567]">→ Communication strategies</div>
                </div>
                <div className="rounded-xl border border-[#E5E0EE] bg-white p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">
                    Dimension 3 · Emotional regulation
                  </div>
                  <div className="text-sm text-[#1A1330] font-semibold mb-1">Stress &amp; conflict response</div>
                  <div className="text-xs text-[#4B4567]">→ Regulation tools</div>
                </div>
                <div className="rounded-xl border border-[#E5E0EE] bg-white p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">
                    Dimension 4 · Executive function
                  </div>
                  <div className="text-sm text-[#1A1330] font-semibold mb-1">Organisation, planning, follow-through</div>
                  <div className="text-xs text-[#4B4567]">→ Practical supports</div>
                </div>
              </div>
              <p className="text-xs text-[#4B4567] mt-4">
                Dimensions 2, 3 &amp; 4 can be scored together in a single
                companion assessment once your safety screen clears.
              </p>
            </div>

            <ul className="text-sm text-[#4B4567] space-y-2 mb-7">
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                <span>Takes about 5 minutes.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                <span>Your answers are stored privately on your account.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                <span>You can download or email yourself a PDF copy at the end.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 size={16} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                <span>
                  Nothing is sent to anyone unless you choose to.{" "}
                  <ProSeeLink testid="safety-intro-pros-see-link" area="safety-check" />
                </span>
              </li>
            </ul>

            <div className="mb-7">
              <WatchFirstVideo
                videoSrc="/videos/ipv-assessment-intro.mp4"
                posterSrc="/images/ipv-assessment-poster.png"
                label="Watch First · Family Violence and Communication Safety Screen for Co-Parents"
                subtitle="Safety First. Informed Choices. Better Outcomes for Your Children."
                testid="safety-assessment-watch"
              />
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => setStep(1)}
                data-testid="intro-start-button"
                className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-3 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
              >
                Start the assessment
                <ArrowRight size={14} />
              </button>
              <Link
                to="/safety"
                data-testid="intro-cancel-link"
                className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-5 py-3 text-sm font-semibold hover:bg-[#F8F7FC]"
              >
                Not now
              </Link>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="fade-up" data-testid="assessment-section-1">
            <StepHeader
              step={0}
              total={3}
              title="Section 1 · Immediate Safety Screen"
              subtitle="In the past 12 months, has the other parent…"
            />
            <ProgressStrip
              answered={answeredCountS1}
              total={questions.section_1.length}
              testid="s1-progress"
            />
            <div className="space-y-3 mb-8">
              {questions.section_1.map((q, idx) => (
                <QuestionRow
                  key={q.id}
                  idx={idx}
                  question={q}
                  value={answersS1[q.id]}
                  onChange={onS1Change(q.id)}
                  highConcern={highConcernIds.has(q.id)}
                  missing={missingS1Set.has(q.id)}
                />
              ))}
            </div>
            <div className="flex flex-wrap gap-3 justify-between">
              <button
                type="button"
                onClick={() => setStep(0)}
                className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
                data-testid="s1-back-button"
              >
                <ArrowLeft size={14} /> Back
              </button>
              <button
                type="button"
                onClick={() => {
                  setStep(2);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                disabled={!allAnsweredS1}
                className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-2.5 text-sm font-semibold shadow-md disabled:opacity-50"
                data-testid="s1-next-button"
              >
                Continue to readiness
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="fade-up" data-testid="assessment-section-2">
            <StepHeader
              step={1}
              total={3}
              title="Section 2 · Communication Readiness"
              subtitle="These reflect your own readiness right now. The other parent should complete this separately to get their own private result."
            />
            <ProgressStrip
              answered={answeredCountS2}
              total={questions.section_2.length}
              testid="s2-progress"
            />
            <div className="space-y-3 mb-8">
              {questions.section_2.map((q, idx) => (
                <QuestionRow
                  key={q.id}
                  idx={idx}
                  question={q}
                  value={answersS2[q.id]}
                  onChange={onS2Change(q.id)}
                  highConcern={false}
                  missing={missingS2Set.has(q.id)}
                />
              ))}
            </div>
            <div className="flex flex-wrap gap-3 justify-between">
              <button
                type="button"
                onClick={() => {
                  setStep(1);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
                data-testid="s2-back-button"
              >
                <ArrowLeft size={14} /> Back
              </button>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setSkippedExt({
                      pattern_context: true,
                      trauma_impact: true,
                      child_experience: true,
                    });
                    submit();
                  }}
                  disabled={!allAnsweredS2 || submitting}
                  className="inline-flex items-center gap-2 rounded-full bg-white border border-[#3D1A78]/30 text-[#3D1A78] px-5 py-2.5 text-sm font-semibold hover:bg-[#F5F1FB] disabled:opacity-50"
                  data-testid="s2-skip-depth-button"
                >
                  See my pathway now (skip optional depth)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setStep(3);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  disabled={!allAnsweredS2}
                  className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-2.5 text-sm font-semibold shadow-md disabled:opacity-50"
                  data-testid="s2-continue-button"
                >
                  {submitting ? "Scoring…" : "Continue to optional depth"}
                  <ArrowRight size={14} />
                </button>
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <ExtensionStep
            testid="assessment-section-pattern"
            title="Pattern & Context (optional)"
            subtitle="These items help distinguish coercive-control from situational or separation-instigated conflict. This is optional — skip freely if any question is too much."
            leadNote="Trauma-informed pacing: skip any question or the whole section. Nothing is required here."
            questions={questions.pattern_context || []}
            answers={answersPattern}
            setAnswers={setAnswersPattern}
            onBack={() => { setStep(2); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            onContinue={() => { setStep(4); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            onSkip={() => {
              setSkippedExt((p) => ({ ...p, pattern_context: true }));
              setStep(4);
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        )}

        {step === 4 && (
          <ExtensionStep
            testid="assessment-section-trauma"
            title="Trauma Impact (optional, non-diagnostic)"
            subtitle="These items describe common behavioural responses to danger and stress. They do not diagnose anything. They help Finding 2 reflect your reality rather than assume it."
            leadNote="If any question triggers a strong response, step away, breathe, and come back — or skip the whole section."
            questions={questions.trauma_impact || []}
            answers={answersTrauma}
            setAnswers={setAnswersTrauma}
            onBack={() => { setStep(3); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            onContinue={() => { setStep(5); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            onSkip={() => {
              setSkippedExt((p) => ({ ...p, trauma_impact: true }));
              setStep(5);
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        )}

        {step === 5 && (
          <ExtensionStep
            testid="assessment-section-child"
            title="Child Experience — your account (optional)"
            subtitle="Your account of how the children are experiencing all of this. This tool never asks the child directly. A qualified child specialist should conduct any direct assessment of the child."
            leadNote="Skip freely. You know your child better than any form. This section produces Finding 4 when completed."
            questions={questions.child_experience || []}
            answers={answersChild}
            setAnswers={setAnswersChild}
            onBack={() => { setStep(4); window.scrollTo({ top: 0, behavior: "smooth" }); }}
            onContinue={submit}
            onContinueLabel="See my pathway"
            onSkip={() => {
              setSkippedExt((p) => ({ ...p, child_experience: true }));
              submit();
            }}
            submitting={submitting}
          />
        )}

        {cosignModal && (
          <div
            className="fixed inset-0 bg-black/60 grid place-items-center z-50 p-4"
            data-testid="cosign-modal"
            onClick={() => setCosignModal(null)}
          >
            <div
              className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#3D1A78] font-bold mb-2">
                Reviewer co-sign QR
              </div>
              <h3 className="text-xl font-bold text-[#1A1330] mb-3">
                Give this to your professional
              </h3>
              <p className="text-sm text-[#4B4567] leading-relaxed mb-4">
                Your mediator, DV advocate, or family counsellor scans this QR (or clicks the link) to add their printed name, role, and optional notes to your court report — no regeneration required on your side.
              </p>
              <div className="grid place-items-center bg-[#FAF9FD] rounded-2xl border border-[#E5E0EE] p-4 mb-4">
                <img
                  src={cosignModal.qr_png_data_url}
                  alt="Reviewer co-sign QR code"
                  className="w-56 h-56"
                  data-testid="cosign-modal-qr"
                />
              </div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-[#857E9C] font-bold mb-1">Link</div>
              <div className="text-xs break-all text-[#4B4567] mb-3" data-testid="cosign-modal-url">
                {cosignModal.verify_url}
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={copyCoSignLink}
                  data-testid="cosign-modal-copy"
                  className="rounded-full bg-[#3D1A78] text-white px-4 py-2 text-xs font-semibold hover:bg-[#2a1155]"
                >
                  Copy link
                </button>
                <button
                  type="button"
                  onClick={() => setCosignModal(null)}
                  data-testid="cosign-modal-close"
                  className="rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-4 py-2 text-xs font-semibold hover:bg-[#F8F7FC]"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        )}


        {step === 6 && result && (
          <div className="fade-up" data-testid="assessment-results">
            <div className="mb-5 text-xs uppercase tracking-[0.2em] text-[#857E9C]">
              Your result · {new Date(result.created_at).toLocaleDateString()}
            </div>
            <SafetyAssessmentResultsCard
              assessment={result}
              onDownload={downloadPdf}
              onDownloadCourt={downloadCourtReport}
              onDownloadOnePager={downloadOnePager}
              onPrepareCoSign={prepareCoSign}
              downloadingCourt={downloadingCourt}
              onEmail={emailMe}
              onEmailMediator={openMediatorDialog}
              onRegenerate={regenerateSummaries}
              regenerating={regenerating}
              isAdmin={isAdmin}
              sending={emailing}
            />

            {result?.assessment_id && (
              <div className="mt-6">
                <ReportShareControls
                  reportType="safety"
                  pdfUrl={pdfAbs(`/safety-assessment/${result.assessment_id}/pdf`)}
                  shareUrl={`/safety-assessment/${result.assessment_id}/share-link`}
                  visibilityUrl={`/safety-assessment/${result.assessment_id}/visibility`}
                  initialExcluded={result?.visibility?.excluded || []}
                  filename={`safety-assessment-${result.assessment_id}.pdf`}
                  testIdPrefix="safety-share"
                />
              </div>
            )}

            {/* Post-result guardrail — makes explicit what this screen
                does NOT decide, plus an anti-mutualization block for
                Level 1/2 (highest concern) results. */}
            <ScreenGuardrailPanel level={result?.result?.level} />

            {/* AI communication coaching is SUPPRESSED for Level 1 & 2 to
                avoid mutualizing abuse — coaching a survivor to
                communicate "better" with a coercive co-parent shifts
                responsibility onto the person experiencing harm. */}
            {result?.result?.level >= 3 && (
              <div className="mt-6">
                <SectionCoaching
                  section="safety"
                  ready={Boolean(result?.result)}
                  data={{
                    level: result?.result?.level,
                    pathway_tone: result?.result?.pathway_tone,
                    pathway_title: result?.result?.pathway_title,
                    pathway_summary: result?.result?.pathway_summary,
                    recommendations: result?.result?.recommendations || [],
                  }}
                />
              </div>
            )}

            <div className="mt-6 flex justify-center">
              <Link
                to="/next-steps/safety"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-[#3D1A78] text-white font-semibold hover:bg-[#2D0F63]"
                data-testid="safety-next-steps-cta"
              >
                See your Next Three Steps <ArrowRight size={14} />
              </Link>
            </div>

            {/* Companion 4-dimension CTA — only offered when Safety cleared
                (level 3 or 4). We do not surface this for levels 1/2 so
                parents can prioritise safety planning without being pulled
                into communication/regulation questions that may be
                misinterpreted under coercion. */}
            {result?.result?.level >= 3 && (
              <div
                className="mt-6 rounded-3xl border-2 border-[#3D1A78] bg-gradient-to-br from-[#F8F5FF] to-white p-6 sm:p-8"
                data-testid="safety-companion-cta"
              >
                <div
                  className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2"
                  data-testid="safety-companion-cta-eyebrow"
                >
                  When you&rsquo;re ready to go further &mdash; no concerns about family violence
                </div>
                <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] mb-2">
                  Your safety result cleared — want to run the other three
                  dimensions in one sitting?
                </h3>
                <p className="text-sm text-[#4B4567] leading-relaxed mb-4">
                  Communication, Emotional Regulation, and Executive Function
                  are the three remaining lenses in the four-dimension model.
                  Because your safety screen cleared, they can now be scored
                  together in a single ~7-minute companion assessment.
                </p>
                <div className="flex flex-wrap gap-3">
                  <Link
                    to="/companion-assessment"
                    data-testid="safety-companion-cta-link"
                    className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-3 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
                  >
                    Start companion assessment <ArrowRight size={14} />
                  </Link>
                  <button
                    type="button"
                    onClick={() => setBriefingEmailOpen(true)}
                    data-testid="safety-briefing-email-button"
                    className="inline-flex items-center gap-2 rounded-full bg-white border-2 border-[#3D1A78] text-[#3D1A78] px-5 py-3 text-sm font-semibold hover:bg-[#F1EBFA]"
                  >
                    <Mail size={14} /> Email Briefing
                  </button>
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        const res = await api.get("/dimension-companion/four-dimension-briefing/pdf", {
                          params: { sign: true },
                          responseType: "blob",
                        });
                        const blob = new Blob([res.data], { type: "application/pdf" });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = "four-dimension-briefing.pdf";
                        a.click();
                        URL.revokeObjectURL(url);
                      } catch (err) {
                        logError("Briefing download failed", err);
                        toast.error("Couldn't download the briefing.");
                      }
                    }}
                    data-testid="safety-briefing-pdf-button"
                    className="inline-flex items-center gap-2 rounded-full bg-white border-2 border-[#3D1A78] text-[#3D1A78] px-5 py-3 text-sm font-semibold hover:bg-[#F1EBFA]"
                  >
                    <Download size={14} /> Download PDF
                  </button>
                </div>
                <p className="text-[11px] text-[#8471B3] mt-3 italic">
                  Briefing includes Safety + whichever companion dimensions you've
                  completed — designed for a mediator, parent facilitator ad litem,
                  or trial court.
                </p>
              </div>
            )}

            {/* Iter199 · Concerned-variant CTA — level 1/2 result. We
                deliberately do NOT surface joint tools here; the parent
                needs individual, private, safe paths first. Mirrors the
                Landing bridge "safe-path-card" and shares the same
                eyebrow copy so both surfaces speak the same language. */}
            {result?.result?.level != null && result.result.level < 3 && (
              <div
                className="mt-6 rounded-3xl border-2 border-[#B45F13]/40 bg-[#FFF6EA] p-6 sm:p-8"
                data-testid="safety-concerned-cta"
              >
                <div
                  className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#B45F13] mb-2"
                  data-testid="safety-concerned-cta-eyebrow"
                >
                  When you&rsquo;re ready, on your own timeline &mdash; safe paths for when family violence is present
                </div>
                <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] mb-2">
                  Keep working on your own &mdash; safely, at your pace.
                </h3>
                <p className="text-sm text-[#4B4567] leading-relaxed mb-4">
                  Joint tools aren&rsquo;t the next step for you right now.
                  Continue building your private reflection, keep a
                  co-parenting journal, and connect with a
                  domestic-violence advocate whenever it feels right.
                </p>
                <div className="flex flex-wrap gap-3">
                  <Link
                    to="/safety"
                    data-testid="safety-concerned-cta-safety-link"
                    className="inline-flex items-center gap-2 rounded-full bg-[#B45F13] hover:bg-[#8A4610] text-white px-5 py-2.5 text-sm font-semibold transition-colors"
                  >
                    Open my safety plan <ArrowRight size={14} />
                  </Link>
                  <Link
                    to="/journal"
                    data-testid="safety-concerned-cta-journal-link"
                    className="inline-flex items-center gap-2 rounded-full bg-white border-2 border-[#B45F13] text-[#B45F13] hover:bg-[#FFEEDA] px-5 py-2.5 text-sm font-semibold"
                  >
                    Open my private journal
                  </Link>
                </div>
              </div>
            )}

            {/* Important Advisory — legally-worded post-assessment disclaimer */}
            <div
              className="mt-6 rounded-2xl bg-[#FFF7E6] border-2 border-[#E8A628] p-5 sm:p-7 text-[#1A1330]"
              data-testid="safety-important-advisory"
            >
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] font-bold text-[#B8891C] mb-3">
                <Shield size={13} /> Important Advisory
              </div>
              <p className="leading-relaxed mb-3">
                The SA CoParents Family Violence and Communication Safety
                Screen is designed to help you reflect on your parenting
                and communication situation. It is <strong>not intended to
                diagnose domestic violence, determine legal rights, predict
                future behavior, or replace professional advice</strong>.
              </p>
              <p className="leading-relaxed mb-3">
                Your responses are based solely on the information you provide
                and may not reflect the complete circumstances of your family.
              </p>
              <p className="leading-relaxed mb-4">
                If your assessment suggests concerns about intimidation,
                coercive control, threats, stalking, harassment, or violence,
                we strongly encourage you to seek additional guidance before
                making parenting or communication decisions.
              </p>
              <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-2">
                Consider consulting with
              </div>
              <ul className="space-y-2 text-sm mb-4">
                <li className="flex gap-2">
                  <span className="text-[#B8891C] mt-1">•</span>
                  A qualified <strong>family law attorney</strong> to
                  understand your legal rights and available protections.
                </li>
                <li className="flex gap-2">
                  <span className="text-[#B8891C] mt-1">•</span>
                  A licensed <strong>therapist or domestic violence
                  professional</strong> experienced in intimate partner
                  violence.
                </li>
                <li className="flex gap-2">
                  <span className="text-[#B8891C] mt-1">•</span>
                  Your local <strong>domestic violence advocacy
                  organization</strong> or victim assistance program.
                </li>
                <li className="flex gap-2">
                  <span className="text-[#B8891C] mt-1">•</span>
                  <strong>Law enforcement or emergency services immediately</strong>{" "}
                  if you believe you or your child are in immediate danger.
                </li>
              </ul>
              <p className="text-sm font-semibold text-[#1A1330] mb-2">
                The safety of you and your child should always come before
                attempts to improve communication or co-parenting.
              </p>
              <p className="text-xs text-[#6B6580] italic leading-relaxed">
                This assessment is intended to support informed decision-making
                — not to replace professional legal, therapeutic, or safety
                planning services.
              </p>
            </div>

            <div className="mt-6 rounded-2xl bg-[#F8F7FC] border border-[#E5E0EE] p-4 sm:p-5 text-sm text-[#4B4567] leading-relaxed">
              <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-2">
                Texas resources
              </div>
              <p>
                National Domestic Violence Hotline:{" "}
                <a href="tel:18007997233" className="underline font-bold text-[#1A1330]">800-799-7233</a>{" "}
                · text <strong>START</strong> to <strong>88788</strong>. Trained
                advocates provide crisis intervention, safety planning,
                education, advocacy, and referrals to shelters and local
                resources. If there is immediate danger, call{" "}
                <a href="tel:911" className="underline font-bold text-[#1A1330]">911</a>.
              </p>
            </div>

            {/* One clear ending — a warm handoff to a mediator/attorney.
                This is the founder-mandated single next action for the
                safety pathway. */}
            <PathwayEndCTA
              eyebrow="Safety pathway"
              title="Send your case to a mediator instead"
              description="A DV-informed mediator can handle the outreach so you never have to send a direct invitation. Only the fields you approve are shared."
              primary={{
                label: "Send my case to a mediator",
                onClick: openMediatorDialog,
              }}
              tone="amber"
              icon={ShieldAlert}
              testId="safety-assessment-end-cta"
            />

            <div className="mt-6 flex flex-wrap gap-3 justify-between">
              <Link
                to="/safety"
                className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
                data-testid="results-back-to-safety"
              >
                <ArrowLeft size={14} /> Back to Safety
              </Link>
              <button
                type="button"
                onClick={() => {
                  setAnswersS1({});
                  setAnswersS2({});
                  setAnswersPattern({});
                  setAnswersTrauma({});
                  setAnswersChild({});
                  setSkippedExt({
                    pattern_context: false,
                    trauma_impact: false,
                    child_experience: false,
                  });
                  setResult(null);
                  flashedRef.current = new Set();
                  setStep(0);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
                data-testid="results-retake-button"
              >
                Retake assessment
              </button>
            </div>
          </div>
        )}
      </div>

      <HighConcernOverlay
        open={showHighConcern}
        onContinue={() => {
          setShowHighConcern(false);
          setPendingHighId(null);
        }}
        onClose={() => {
          if (pendingHighId) {
            setAnswersS1((prev) => {
              const next = { ...prev };
              delete next[pendingHighId];
              return next;
            });
            flashedRef.current.delete(pendingHighId);
          }
          setShowHighConcern(false);
          setPendingHighId(null);
        }}
      />

      <MediatorEmailDialog
        open={mediatorDialogOpen}
        onClose={() => {
          if (!mediatorSending) setMediatorDialogOpen(false);
        }}
        onSend={sendToMediator}
        sending={mediatorSending}
      />

      <BriefingEmailDialog
        open={briefingEmailOpen}
        onClose={() => { if (!briefingSending) setBriefingEmailOpen(false); }}
        onSend={async (payload) => {
          setBriefingSending(true);
          try {
            const r = await api.post("/dimension-companion/four-dimension-briefing/email", payload);
            toast.success(`Briefing sent to ${r.data.emailed_to}.`);
            setBriefingEmailOpen(false);
          } catch (err) {
            logError("Briefing email failed", err);
            const detail = err?.response?.data?.detail;
            const status = err?.response?.status;
            if (status === 400 && /save your work|real email/i.test(detail || "")) {
              toast.error(detail, {
                action: { label: "Save my work", onClick: () => navigate("/claim") },
              });
            } else if (status === 503) {
              toast.error(detail || "Email service isn't available right now.");
            } else {
              toast.error(detail || "Couldn't send the briefing. Please try again.");
            }
          } finally {
            setBriefingSending(false);
          }
        }}
        sending={briefingSending}
      />
    </div>
  );
}
