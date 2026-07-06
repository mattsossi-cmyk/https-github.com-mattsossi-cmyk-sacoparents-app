import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  ShieldAlert,
  CheckCircle2,
  Download,
  Mail,
  Phone,
  Home,
  FileText,
  AlertTriangle,
  Lightbulb,
  Send,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { api, API } from "../lib/api";
import { logError } from "../lib/logger";
import { useAuth } from "../context/AuthContext";
import HighConcernOverlay from "../components/HighConcernOverlay";
import WatchFirstVideo from "../components/WatchFirstVideo";

const TONE_STYLES = {
  danger: {
    chip: "bg-[#FCE3DC] text-[#9A3A23] border-[#9A3A23]/25",
    badge: "bg-[#9A3A23] text-white",
    card: "border-[#9A3A23]/30",
  },
  warning: {
    chip: "bg-[#FFF1D6] text-[#7A4A05] border-[#7A4A05]/25",
    badge: "bg-[#A05C1E] text-white",
    card: "border-[#A05C1E]/30",
  },
  info: {
    chip: "bg-[#E5EAF7] text-[#1B3D8F] border-[#1B3D8F]/25",
    badge: "bg-[#3C598A] text-white",
    card: "border-[#3C598A]/30",
  },
  ok: {
    chip: "bg-[#DCEEDF] text-[#1F5C3B] border-[#1F5C3B]/25",
    badge: "bg-[#3C7858] text-white",
    card: "border-[#3C7858]/30",
  },
};


function quickExit() {
  try {
    window.location.replace("https://www.google.com");
  } catch (_e) {
    window.location.href = "https://www.google.com";
  }
}


function StepHeader({ step, total, title, subtitle }) {
  const pct = Math.round(((step + 1) / total) * 100);
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-[#857E9C] mb-2">
        <span>Step {step + 1} of {total}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 bg-[#EFE9F9] rounded-full overflow-hidden mb-5">
        <div
          className="h-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <h1 className="font-bold text-2xl sm:text-3xl text-[#1A1330] tracking-tight mb-2">{title}</h1>
      {subtitle && <p className="text-sm text-[#4B4567] leading-relaxed">{subtitle}</p>}
    </div>
  );
}


function YNUButton({ value, current, label, onClick, testid }) {
  const active = current === value;
  const palette = {
    yes: active ? "bg-[#9A3A23] text-white border-[#9A3A23]" : "bg-white text-[#1A1330] border-[#E5E0EE] hover:border-[#9A3A23]",
    no: active ? "bg-[#3C7858] text-white border-[#3C7858]" : "bg-white text-[#1A1330] border-[#E5E0EE] hover:border-[#3C7858]",
    unsure: active ? "bg-[#857E9C] text-white border-[#857E9C]" : "bg-white text-[#1A1330] border-[#E5E0EE] hover:border-[#857E9C]",
  };
  return (
    <button
      type="button"
      onClick={() => onClick(value)}
      data-testid={testid}
      className={`flex-1 px-3 py-2 rounded-full border text-xs sm:text-sm font-semibold transition-colors ${palette[value]}`}
    >
      {label}
    </button>
  );
}


function QuestionRow({ idx, question, value, onChange, highConcern }) {
  return (
    <div
      className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5"
      data-testid={`question-${question.id}`}
    >
      <div className="flex items-start gap-3 mb-3">
        <div
          className={`shrink-0 w-7 h-7 rounded-full grid place-items-center text-xs font-bold ${
            highConcern ? "bg-[#FCE3DC] text-[#9A3A23]" : "bg-[#EFE9F9] text-[#3D1A78]"
          }`}
        >
          {idx + 1}
        </div>
        <div className="flex-1">
          <p className="text-sm sm:text-base text-[#1A1330] leading-relaxed">{question.text}</p>
          {highConcern && (
            <div className="mt-1.5 inline-flex items-center gap-1 text-[10px] uppercase tracking-[0.18em] text-[#9A3A23] font-bold">
              <ShieldAlert size={11} />
              High safety concern
            </div>
          )}
        </div>
      </div>
      <div className="flex items-stretch gap-2">
        <YNUButton value="yes" current={value} label="Yes" onClick={onChange} testid={`${question.id}-yes`} />
        <YNUButton value="no" current={value} label="No" onClick={onChange} testid={`${question.id}-no`} />
        <YNUButton value="unsure" current={value} label="Unsure" onClick={onChange} testid={`${question.id}-unsure`} />
      </div>
    </div>
  );
}


function ResultsCard({ assessment, onDownload, onEmail, onEmailMediator, sending }) {
  const result = assessment?.result || {};
  const tone = TONE_STYLES[result.pathway_tone] || TONE_STYLES.info;
  const level = result.level || 4;
  return (
    <div
      className={`rounded-3xl border-2 ${tone.card} bg-white shadow-sm overflow-hidden`}
      data-testid="results-card"
    >
      <div className={`${tone.badge} px-6 sm:px-8 py-3 flex items-center justify-between gap-3`}>
        <div className="text-[11px] uppercase tracking-[0.22em] font-bold">Level {level} pathway</div>
        <div className="text-[11px] uppercase tracking-[0.18em] opacity-90">{result.pathway_tone}</div>
      </div>
      <div className="p-6 sm:p-8">
        <h2 className="font-bold text-2xl sm:text-3xl text-[#1A1330] mb-3" data-testid="results-pathway-title">
          {result.pathway_title}
        </h2>
        <p className="text-sm sm:text-base text-[#4B4567] leading-relaxed mb-6">{result.pathway_summary}</p>

        <div className="mb-6">
          <div className="text-[11px] uppercase tracking-[0.2em] text-[#857E9C] font-bold mb-3">
            Recommended pathway
          </div>
          <ul className="space-y-2">
            {(result.recommendations || []).map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-[#1A1330]">
                <CheckCircle2 size={16} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl bg-[#F8F7FC] border border-[#E5E0EE] p-4 sm:p-5 mb-6">
          <div className="flex items-center gap-2 text-[#3D1A78] mb-2">
            <Lightbulb size={14} />
            <div className="text-[11px] uppercase tracking-[0.18em] font-bold">Note about your co-parent</div>
          </div>
          <p className="text-sm text-[#4B4567] leading-relaxed">
            This assessment reflects only your responses. The other parent should
            complete this assessment separately so each of you has your own private
            result. Forcing or pressuring the other parent to take it is not
            recommended.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={onDownload}
            data-testid="results-download-pdf"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
          >
            <Download size={14} />
            Download PDF
          </button>
          <button
            type="button"
            onClick={onEmail}
            disabled={sending}
            data-testid="results-email-button"
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC] disabled:opacity-60"
          >
            <Mail size={14} />
            {sending ? "Sending…" : "Email me a copy"}
          </button>
          <button
            type="button"
            onClick={onEmailMediator}
            data-testid="results-email-mediator-button"
            className="inline-flex items-center gap-2 rounded-full bg-[#1A1330] hover:bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold shadow-md transition-colors"
          >
            <Send size={14} />
            Email my pathway to my mediator
          </button>
          <Link
            to="/problem-solving"
            data-testid="results-problem-solving-link"
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
          >
            <FileText size={14} />
            Open the Problem-Solving Worksheet
          </Link>
        </div>
      </div>
    </div>
  );
}


function MediatorEmailDialog({ open, onClose, onSend, sending }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");

  if (!open) return null;

  const emailOk = /\S+@\S+\.\S+/.test(email.trim());

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/45 backdrop-blur-sm px-4"
      data-testid="mediator-email-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="mediator-dialog-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-3xl bg-white shadow-2xl border border-[#E5E0EE] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 px-6 sm:px-7 pt-6">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold mb-1">
              Send to your mediator
            </div>
            <h3
              id="mediator-dialog-title"
              className="font-bold text-xl text-[#1A1330] leading-tight"
            >
              Email your safety pathway
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="mediator-email-close"
            aria-label="Close"
            className="w-9 h-9 rounded-full grid place-items-center bg-[#F8F7FC] hover:bg-[#EFE9F9] text-[#4B4567]"
          >
            <X size={16} />
          </button>
        </div>
        <div className="px-6 sm:px-7 py-5 space-y-4">
          <p className="text-sm text-[#4B4567] leading-relaxed">
            We&rsquo;ll send your mediator a short summary of your recommended
            pathway with the full PDF attached. They can reply directly to your
            email address.
          </p>
          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Mediator email <span aria-hidden="true" className="text-[#9A3A23]">*</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="mediator@example.com"
              data-testid="mediator-email-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
              autoComplete="email"
              required
            />
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Mediator name <span className="text-[#857E9C] font-normal normal-case tracking-normal">· optional</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Jamie Rivera"
              data-testid="mediator-name-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
            />
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Message to your mediator <span className="text-[#857E9C] font-normal normal-case tracking-normal">· optional</span>
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Anything you want your mediator to know before our session…"
              rows={3}
              data-testid="mediator-message-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30 resize-none"
            />
          </div>
        </div>
        <div className="px-6 sm:px-7 pb-6 flex flex-wrap gap-3 justify-end">
          <button
            type="button"
            onClick={onClose}
            data-testid="mediator-email-cancel"
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() =>
              onSend({
                mediator_email: email.trim(),
                mediator_name: name.trim(),
                parent_message: message.trim(),
              })
            }
            disabled={!emailOk || sending}
            data-testid="mediator-email-send"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold shadow-md disabled:opacity-50"
          >
            <Send size={14} />
            {sending ? "Sending…" : "Send to my mediator"}
          </button>
        </div>
      </div>
    </div>
  );
}


export default function SafetyAssessment() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [questions, setQuestions] = useState(null);
  const [step, setStep] = useState(0); // 0 intro, 1 section 1, 2 section 2, 3 results
  const [answersS1, setAnswersS1] = useState({});
  const [answersS2, setAnswersS2] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [showHighConcern, setShowHighConcern] = useState(false);
  const [pendingHighId, setPendingHighId] = useState(null);
  const [emailing, setEmailing] = useState(false);
  const [mediatorDialogOpen, setMediatorDialogOpen] = useState(false);
  const [mediatorSending, setMediatorSending] = useState(false);
  const flashedRef = useRef(new Set());

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
    if (value === "yes" && highConcernIds.has(qid) && !flashedRef.current.has(qid)) {
      flashedRef.current.add(qid);
      setPendingHighId(qid);
      setShowHighConcern(true);
    }
  };
  const onS2Change = (qid) => (value) => {
    setAnswersS2((prev) => ({ ...prev, [qid]: value }));
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      const r = await api.post("/safety-assessment", {
        section_1: answersS1,
        section_2: answersS2,
      });
      setResult(r.data);
      setStep(3);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      logError("Submit failed:", err);
      toast.error("Couldn’t submit your assessment. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const downloadPdf = () => {
    if (!result) return;
    const url = `${API}/safety-assessment/${result.assessment_id}/pdf`;
    window.open(url, "_blank", "noopener,noreferrer");
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

  const allAnsweredS1 = useMemo(() => {
    if (!questions) return false;
    return questions.section_1.every((q) => answersS1[q.id]);
  }, [answersS1, questions]);
  const allAnsweredS2 = useMemo(() => {
    if (!questions) return false;
    return questions.section_2.every((q) => answersS2[q.id]);
  }, [answersS2, questions]);

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
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-[#C28771]/15 text-[#C28771] grid place-items-center">
                <ShieldAlert size={18} />
              </div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold">
                SA Coparents
              </div>
            </div>
            <h1 className="font-bold text-3xl sm:text-4xl text-[#1A1330] tracking-tight mb-3">
              IPV Communication Safety Assessment
            </h1>
            <p className="text-[#4B4567] leading-relaxed mb-4">
              This assessment helps identify whether co-parenting communication
              should be direct, structured, assisted, or restricted because of
              family violence, coercive control, intimidation, stalking,
              harassment, or safety concerns.
            </p>

            <div className="rounded-2xl bg-[#FCE3DC] border border-[#9A3A23]/25 text-[#9A3A23] p-4 sm:p-5 mb-6">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle size={14} />
                <div className="text-[11px] uppercase tracking-[0.18em] font-bold">
                  Important safety notice
                </div>
              </div>
              <p className="text-sm leading-relaxed">
                This assessment is not a diagnosis, legal advice, or a substitute
                for a family violence evaluation. If there is immediate danger,
                call <a href="tel:911" className="underline font-bold">911</a>.
                If communication with the other parent creates fear, danger, or
                retaliation, direct communication may not be appropriate.
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
            </ul>

            <div className="mb-7">
              <WatchFirstVideo
                videoSrc="/videos/safety-assessment-reflection.mp4"
                label="Watch First · Family Violence Assessment"
                subtitle="Intimate Partner Violence — watch before you begin"
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
            <div className="space-y-3 mb-8">
              {questions.section_1.map((q, idx) => (
                <QuestionRow
                  key={q.id}
                  idx={idx}
                  question={q}
                  value={answersS1[q.id]}
                  onChange={onS1Change(q.id)}
                  highConcern={highConcernIds.has(q.id)}
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
            <div className="space-y-3 mb-8">
              {questions.section_2.map((q, idx) => (
                <QuestionRow
                  key={q.id}
                  idx={idx}
                  question={q}
                  value={answersS2[q.id]}
                  onChange={onS2Change(q.id)}
                  highConcern={false}
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
              <button
                type="button"
                onClick={submit}
                disabled={!allAnsweredS2 || submitting}
                className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-2.5 text-sm font-semibold shadow-md disabled:opacity-50"
                data-testid="s2-submit-button"
              >
                {submitting ? "Scoring…" : "See my pathway"}
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {step === 3 && result && (
          <div className="fade-up" data-testid="assessment-results">
            <div className="mb-5 text-xs uppercase tracking-[0.2em] text-[#857E9C]">
              Your result · {new Date(result.created_at).toLocaleDateString()}
            </div>
            <ResultsCard
              assessment={result}
              onDownload={downloadPdf}
              onEmail={emailMe}
              onEmailMediator={openMediatorDialog}
              sending={emailing}
            />

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
    </div>
  );
}
