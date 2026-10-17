/**
 * DimensionCompanion — Runs Dimensions 2, 3 & 4 of the four-dimension
 * co-parenting model (Communication, Emotional Regulation, Executive
 * Function) as a single combined mini-flow.
 *
 * Entry point: /companion-assessment
 * Recommended gate: users arrive here only after the Safety Assessment
 * has cleared (level 3 or 4). We do not re-check safety here; the
 * frontend CTA on the safety result page handles the routing.
 *
 * Flow: intro (step 0) → Dim 2 (1) → Dim 3 (2) → Dim 4 (3) → result (4).
 */
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, ArrowRight, CheckCircle2, Download, Loader2, Mail, ShieldCheck } from "lucide-react";
import AppShell from "../components/AppShell";
import BriefingEmailDialog from "../components/BriefingEmailDialog";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const DIM_ORDER = ["communication", "emotional_regulation", "executive_function"];

const TIER_STYLE = {
  strong:    { pill: "bg-[#E6F4EC] text-[#1F5C3B]", bar: "bg-[#1F5C3B]" },
  steady:    { pill: "bg-[#DFF3E5] text-[#2D7A4A]", bar: "bg-[#2D7A4A]" },
  stretched: { pill: "bg-[#FFF6E5] text-[#8A5B00]", bar: "bg-[#AA7428]" },
  strained:  { pill: "bg-[#F8D7D7] text-[#B02A2A]", bar: "bg-[#B02A2A]" },
};

function LikertRow({ q, likert, value, onChange }) {
  return (
    <div
      className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5"
      data-testid={`companion-q-${q.id}`}
    >
      <div className="text-sm text-[#1A1330] leading-relaxed mb-3">
        {q.text}
      </div>
      <div className="grid grid-cols-5 gap-1.5">
        {likert.map((lb) => {
          const selected = value === lb.value;
          return (
            <button
              key={lb.value}
              type="button"
              onClick={() => onChange(lb.value)}
              className={`text-[0.6875rem] py-2 px-1 rounded-lg border transition ${
                selected
                  ? "bg-[#3D1A78] text-white border-[#3D1A78] font-bold"
                  : "bg-white text-[#4B4567] border-[#E5E0EE] hover:border-[#3D1A78]"
              }`}
              data-testid={`companion-q-${q.id}-choice-${lb.value}`}
              aria-pressed={selected}
            >
              <div className="text-base font-bold">{lb.value}</div>
              <div className="hidden sm:block text-[0.625rem] leading-tight mt-0.5">
                {lb.label.split(" / ")[0]}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function DimStep({ dim, likert, answers, setAnswer }) {
  return (
    <div className="fade-up" data-testid={`companion-dim-${dim.key}`}>
      <div className="mb-6">
        <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
          Dimension {dim.number}
        </div>
        <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] mt-1">
          {dim.label}
        </h2>
        <p className="text-sm text-[#4B4567] mt-1">{dim.hint}</p>
      </div>
      <div className="space-y-3">
        {dim.questions.map((q) => (
          <LikertRow
            key={q.id}
            q={q}
            likert={likert}
            value={answers[q.id]}
            onChange={(v) => setAnswer(q.id, v)}
          />
        ))}
      </div>
    </div>
  );
}

function DimensionResultCard({ dim }) {
  const style = TIER_STYLE[dim.tier] || TIER_STYLE.steady;
  const pctToStrained = (Math.min(5, Math.max(1, dim.score)) - 1) / 4; // 0..1
  return (
    <div
      className="rounded-2xl border border-[#E5E0EE] bg-white p-5"
      data-testid={`companion-result-${dim.dimension}`}
    >
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div className="text-[0.625rem] uppercase tracking-[0.2em] font-bold text-[#3D1A78]">
            Dimension {dim.dimension_num}
          </div>
          <div className="font-serif text-lg text-[#1A1330] mt-0.5">{dim.label}</div>
        </div>
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[0.6875rem] font-bold ${style.pill}`}
          data-testid={`companion-result-${dim.dimension}-tier`}
        >
          {dim.tier_label}
        </span>
      </div>

      {/* Concern bar (1..5) — visual gauge */}
      <div className="mt-3">
        <div className="h-2 w-full rounded-full bg-[#F0EEF8] overflow-hidden">
          <div
            className={`h-full ${style.bar}`}
            style={{ width: `${Math.max(4, pctToStrained * 100)}%` }}
          />
        </div>
        <div className="text-[0.6875rem] text-[#6A5799] mt-1">
          Concern level {dim.score.toFixed(2)} / 5 (lower is better)
        </div>
      </div>

      <p className="text-sm text-[#4B4567] mt-3">{dim.summary}</p>

      <div className="mt-3">
        <div className="text-[0.625rem] uppercase tracking-[0.2em] font-bold text-[#3D1A78] mb-2">
          Recommended supports
        </div>
        <ul className="space-y-1.5">
          {dim.interventions.map((iv, i) => (
            <li
              key={`${dim.dimension}-iv-${i}`}
              className="text-sm text-[#1A1330] flex items-start gap-2"
              data-testid={`companion-result-${dim.dimension}-intervention-${i}`}
            >
              <CheckCircle2 size={14} className="text-[#3D1A78] shrink-0 mt-0.5" />
              <span>{iv}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default function DimensionCompanion() {
  const navigate = useNavigate();
  const [bundle, setBundle] = useState(null);
  const [step, setStep] = useState(0); // 0 intro, 1..3 dims, 4 result
  const [answers, setAnswers] = useState({
    communication: {},
    emotional_regulation: {},
    executive_function: {},
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [downloadingBriefing, setDownloadingBriefing] = useState(false);
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [emailSending, setEmailSending] = useState(false);

  const sendBriefingEmail = async (payload) => {
    setEmailSending(true);
    try {
      const r = await api.post("/dimension-companion/four-dimension-briefing/email", payload);
      toast.success(`Briefing sent to ${r.data.emailed_to}.`);
      setEmailDialogOpen(false);
    } catch (err) {
      logError("Briefing email failed", err);
      const detail = err?.response?.data?.detail;
      const status = err?.response?.status;
      if (status === 400 && /save your work|real email/i.test(detail || "")) {
        toast.error(detail || "Save your work first — add a real email to your account.");
      } else if (status === 503) {
        toast.error(detail || "Email service isn't available right now.");
      } else {
        toast.error(detail || "Couldn't send the briefing. Please try again.");
      }
    } finally {
      setEmailSending(false);
    }
  };

  const downloadBriefing = async () => {
    setDownloadingBriefing(true);
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
      toast.error("Couldn't download the briefing. Please try again.");
    } finally {
      setDownloadingBriefing(false);
    }
  };

  useEffect(() => {
    api
      .get("/dimension-companion/questions")
      .then((r) => setBundle(r.data))
      .catch((err) => {
        logError("Failed to load companion questions", err);
        toast.error("Couldn't load the assessment. Please refresh.");
      });
  }, []);

  const dims = useMemo(() => {
    if (!bundle) return null;
    return Object.fromEntries(bundle.dimensions.map((d) => [d.key, d]));
  }, [bundle]);

  const currentDimKey = step >= 1 && step <= 3 ? DIM_ORDER[step - 1] : null;

  const setAnswer = (dimKey) => (qid, value) => {
    setAnswers((prev) => ({
      ...prev,
      [dimKey]: { ...prev[dimKey], [qid]: value },
    }));
  };

  const currentComplete = useMemo(() => {
    if (!currentDimKey || !dims) return false;
    const qs = dims[currentDimKey].questions;
    return qs.every((q) => answers[currentDimKey][q.id]);
  }, [currentDimKey, dims, answers]);

  const submit = async () => {
    setSubmitting(true);
    try {
      const r = await api.post("/dimension-companion", { answers });
      setResult(r.data);
      setStep(4);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      logError("Companion submit failed", err);
      toast.error("Couldn't submit. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (!bundle) {
    return (
      <AppShell>
        <div className="p-10 inline-flex items-center gap-2 text-sm text-[#4B4567]">
          <Loader2 size={14} className="animate-spin" /> Loading…
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="dimension-companion">
        <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] hover:text-[#3D1A78] mb-4">
          <ArrowLeft size={12} /> Back to dashboard
        </Link>

        {/* Step progress */}
        {step >= 1 && step <= 3 && (
          <div className="mb-6" data-testid="companion-progress">
            <div className="flex items-center justify-between text-[0.6875rem] text-[#6A5799] mb-1">
              <span>Step {step} of 3 · Dimension {bundle.dimensions[step - 1].number}</span>
              <span>{Math.round((step / 3) * 100)}%</span>
            </div>
            <div className="h-1.5 bg-[#F0EEF8] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] transition-all"
                style={{ width: `${(step / 3) * 100}%` }}
              />
            </div>
          </div>
        )}

        {step === 0 && (
          <div className="fade-up" data-testid="companion-intro">
            <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Companion assessment
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-1">
              Dimensions 2, 3 &amp; 4
            </h1>
            <p className="text-[#4B4567] mt-3 leading-relaxed">
              You&rsquo;ve completed the Safety screen. This companion covers the
              other three dimensions of co-parenting: <strong>Communication</strong>,
              <strong> Emotional Regulation</strong>, and <strong>Executive Function</strong>.
              Together they give you the full four-dimension picture in a
              single sitting.
            </p>

            <div className="mt-6 rounded-2xl border border-[#E5E0EE] bg-[#F8F5FF] p-5">
              <div className="flex items-center gap-2 mb-2 text-[0.6875rem] uppercase tracking-[0.2em] font-bold text-[#3D1A78]">
                <ShieldCheck size={13} /> Why the Safety firewall matters
              </div>
              <p className="text-sm text-[#4B4567] leading-relaxed">
                Safety (Dim 1) is scored on its own so a genuine safety
                concern is never diluted by communication-difference answers.
                Because your safety result cleared, it is safe to score the
                remaining three dimensions together.
              </p>
            </div>

            <ul className="mt-5 text-sm text-[#4B4567] space-y-2">
              <li className="flex items-start gap-2"><CheckCircle2 size={16} className="shrink-0 mt-0.5 text-[#3D1A78]" /><span>5 questions per dimension — 15 total, ~7 minutes.</span></li>
              <li className="flex items-start gap-2"><CheckCircle2 size={16} className="shrink-0 mt-0.5 text-[#3D1A78]" /><span>Answers are Likert-scale (Never → Always).</span></li>
              <li className="flex items-start gap-2"><CheckCircle2 size={16} className="shrink-0 mt-0.5 text-[#3D1A78]" /><span>Results show per-dimension tier + targeted supports.</span></li>
            </ul>

            <div className="mt-7">
              <button
                type="button"
                onClick={() => setStep(1)}
                data-testid="companion-start-button"
                className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-3 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
              >
                Start companion assessment <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {step >= 1 && step <= 3 && dims && (
          <>
            <DimStep
              dim={dims[currentDimKey]}
              likert={bundle.likert_labels}
              answers={answers[currentDimKey]}
              setAnswer={setAnswer(currentDimKey)}
            />
            <div className="mt-8 flex flex-wrap gap-3 justify-between">
              <button
                type="button"
                onClick={() => setStep(step - 1)}
                data-testid="companion-back-button"
                className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-5 py-3 text-sm font-semibold hover:bg-[#F8F7FC]"
              >
                <ArrowLeft size={14} /> Back
              </button>
              {step < 3 ? (
                <button
                  type="button"
                  onClick={() => setStep(step + 1)}
                  disabled={!currentComplete}
                  data-testid="companion-next-button"
                  className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-6 py-3 text-sm font-semibold disabled:opacity-50"
                >
                  Next dimension <ArrowRight size={14} />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={submit}
                  disabled={!currentComplete || submitting}
                  data-testid="companion-submit-button"
                  className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-3 text-sm font-semibold disabled:opacity-50"
                >
                  {submitting ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                  {submitting ? "Scoring…" : "See your combined results"}
                </button>
              )}
            </div>
          </>
        )}

        {step === 4 && result && (
          <div className="fade-up" data-testid="companion-result">
            <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Companion result
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-1">
              Your Dimensions 2, 3 &amp; 4
            </h1>
            <div className="mt-3 rounded-2xl border border-[#E5E0EE] bg-[#F8F5FF] p-5">
              <div className="text-[0.6875rem] uppercase tracking-[0.2em] font-bold text-[#3D1A78] mb-1">
                Focus first on
              </div>
              <p className="text-sm text-[#1A1330]" data-testid="companion-result-overall">
                {result.scoring.overall_note}
              </p>
            </div>

            <div className="mt-6 space-y-4">
              {DIM_ORDER.map((k) => (
                <DimensionResultCard key={k} dim={result.scoring.dimensions[k]} />
              ))}
            </div>

            <div className="mt-8 flex flex-wrap gap-3 justify-center">
              <button
                type="button"
                onClick={() => setEmailDialogOpen(true)}
                data-testid="companion-briefing-email-button"
                className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-6 py-3 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
              >
                <Mail size={14} /> Email 4-Dimension Briefing
              </button>
              <button
                type="button"
                onClick={downloadBriefing}
                disabled={downloadingBriefing}
                data-testid="companion-briefing-pdf-button"
                className="inline-flex items-center gap-2 rounded-full bg-white border-2 border-[#3D1A78] text-[#3D1A78] px-5 py-3 text-sm font-semibold hover:bg-[#F1EBFA] disabled:opacity-60"
              >
                {downloadingBriefing ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                {downloadingBriefing ? "Preparing PDF…" : "Download PDF"}
              </button>
              <button
                type="button"
                onClick={() => navigate("/dashboard")}
                data-testid="companion-done-button"
                className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-6 py-3 text-sm font-semibold"
              >
                Back to dashboard <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      <BriefingEmailDialog
        open={emailDialogOpen}
        onClose={() => { if (!emailSending) setEmailDialogOpen(false); }}
        onSend={sendBriefingEmail}
        sending={emailSending}
      />
    </AppShell>
  );
}
