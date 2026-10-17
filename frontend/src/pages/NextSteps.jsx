import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, Check, Circle, X, RefreshCw, Loader2,
  Clock, Compass, Sparkles, RotateCcw,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import JointAlignmentPromoCard from "../components/JointAlignmentPromoCard";
import { api } from "../lib/api";

/**
 * "Your Next Three Steps" — end-of-assessment routing page.
 *
 * The parent lands here immediately after finishing an assessment. The
 * backend returns exactly three personalised steps derived (deterministically)
 * from their answers. Each step shows What · Why · How long · a CTA that
 * jumps to the right next surface in the app.
 *
 * URL: /next-steps/:assessment  where assessment ∈
 *      { readiness, comm_style, safety, special_needs }
 */

const ASSESSMENT_META = {
  readiness: {
    title: "Your next three steps after the Readiness Check",
    context: "Based on your Readiness score and the dimension that scored lowest.",
    back_to: "/summary",
    back_label: "Back to the Summary",
  },
  comm_style: {
    title: "Your next three steps after Communication Style",
    context: "Based on the communication pattern you just named.",
    back_to: "/prep/communication",
    back_label: "Back to Communication Style",
  },
  safety: {
    title: "Your next three steps from the Safety Screen",
    context: "Routed by your current safety level. High-concern responses always route to hotlines and parallel-parenting resources first.",
    back_to: "/safety-assessment",
    back_label: "Back to the assessment",
  },
};

const CATEGORY_CHIP = {
  reflection:  "bg-[#E8F2ED] text-[#1F5C3B]",
  preparation: "bg-[#EFE9F9] text-[#3D1A78]",
  review:      "bg-[#FFF6EC] text-[#8C5A2C]",
  safety:      "bg-[#FEF1EC] text-[#8C3A1B]",
};

function StepCard({ step, index, onDone, onDismiss, onUndo }) {
  const chipClass = CATEGORY_CHIP[step.category] || CATEGORY_CHIP.preparation;
  const isDone = !!step.done;
  const isDismissed = !!step.dismissed;
  return (
    <div
      className={`rounded-3xl border p-6 sm:p-8 transition-all ${
        isDone
          ? "bg-[#F4FAF7] border-[#C6DECF] opacity-80"
          : isDismissed
          ? "bg-[#F5F2FA] border-[#E5E0EE] opacity-60"
          : "bg-white border-[#E5E0EE] shadow-sm"
      }`}
      data-testid={`next-step-card-${step.step_id}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="shrink-0 w-9 h-9 rounded-full bg-[#3D1A78] text-white grid place-items-center font-bold text-sm">
            {index + 1}
          </div>
          <span className={`text-[10px] uppercase tracking-[0.16em] font-bold px-2 py-0.5 rounded-full ${chipClass}`}>
            {step.category}
          </span>
          {isDone && (
            <span className="inline-flex items-center gap-1 text-xs font-bold text-[#1F5C3B]">
              <Check size={12} /> Done
            </span>
          )}
          {isDismissed && (
            <span className="inline-flex items-center gap-1 text-xs font-bold text-[#6E6787]">
              <X size={12} /> Dismissed
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 text-xs text-[#6E6787]">
          <Clock size={12} /> {step.how_long}
        </div>
      </div>

      <h3
        className={`font-serif text-2xl mt-4 leading-tight ${
          isDone || isDismissed ? "line-through text-[#6E6787]" : "text-[#1A1330]"
        }`}
        data-testid={`next-step-what-${step.step_id}`}
      >
        {step.what}
      </h3>
      <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">{step.why}</p>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        {!isDone && !isDismissed && (
          <Link
            to={step.cta_path}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2D0F63]"
            data-testid={`next-step-cta-${step.step_id}`}
          >
            {step.cta_label} <ArrowRight size={14} />
          </Link>
        )}
        {!isDone && !isDismissed && (
          <>
            <button
              type="button"
              onClick={() => onDone(step.step_id)}
              className="inline-flex items-center gap-1.5 text-xs border border-[#C6DECF] text-[#1F5C3B] hover:bg-[#E8F2ED] rounded-full px-3 py-1.5"
              data-testid={`next-step-done-${step.step_id}`}
            >
              <Check size={12} /> Mark done
            </button>
            <button
              type="button"
              onClick={() => onDismiss(step.step_id)}
              className="inline-flex items-center gap-1.5 text-xs border border-[#E5E0EE] text-[#6E6787] hover:bg-[#F5F2FA] rounded-full px-3 py-1.5"
              data-testid={`next-step-dismiss-${step.step_id}`}
            >
              <X size={12} /> Not right now
            </button>
          </>
        )}
        {(isDone || isDismissed) && (
          <button
            type="button"
            onClick={() => onUndo(step.step_id)}
            className="inline-flex items-center gap-1.5 text-xs border border-[#E5E0EE] text-[#3D1A78] hover:bg-[#F5F2FA] rounded-full px-3 py-1.5"
            data-testid={`next-step-undo-${step.step_id}`}
          >
            <RotateCcw size={12} /> Bring it back
          </button>
        )}
      </div>
    </div>
  );
}

export default function NextSteps() {
  const { assessment } = useParams();
  const navigate = useNavigate();
  const meta = useMemo(() => ASSESSMENT_META[assessment] || null, [assessment]);
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!meta) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.get(`/next-steps/${assessment}`);
      setDoc(data);
    } catch {
      toast.error("Couldn't load your next steps.");
    } finally {
      setLoading(false);
    }
  }, [assessment, meta]);

  useEffect(() => {
    load();
  }, [load]);

  const regenerate = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/next-steps/${assessment}/generate`);
      setDoc(data);
      toast.success("Fresh steps generated.");
    } catch {
      toast.error("Couldn't regenerate the steps.");
    } finally {
      setBusy(false);
    }
  };

  const act = async (stepId, action) => {
    try {
      const { data } = await api.post(
        `/next-steps/${assessment}/${stepId}/action`,
        { action }
      );
      setDoc(data);
    } catch {
      toast.error("Couldn't update the step.");
    }
  };

  if (!meta) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10 text-[#6E6787]">
          Unknown assessment.
          <div className="mt-4">
            <Link to="/dashboard" className="text-[#3D1A78] hover:underline">Back to Dashboard</Link>
          </div>
        </div>
      </AppShell>
    );
  }

  const steps = doc?.steps || [];

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        <Link
          to={meta.back_to}
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="next-steps-back-link"
        >
          <ArrowLeft size={14} /> {meta.back_label}
        </Link>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="eyebrow text-[#3D1A78] flex items-center gap-1.5">
              <Compass size={12} /> Your next three steps
            </div>
            <h1
              className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-1"
              data-testid="next-steps-title"
            >
              {meta.title}
            </h1>
            <p className="text-[#4B4567] mt-2 max-w-2xl">{meta.context}</p>
          </div>
          <button
            onClick={regenerate}
            disabled={busy || loading}
            className="inline-flex items-center gap-2 text-sm border border-[#E5E0EE] text-[#3D1A78] hover:bg-[#F5F2FA] rounded-full px-4 py-2 font-semibold disabled:opacity-60"
            data-testid="next-steps-regenerate-btn"
          >
            {busy ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Regenerate
          </button>
        </div>

        {/* Unmistakable next-action card — Co-Parenting Agreement promo.
            Flips between "Invite Co-Parent" (waiting) and
            "Your Co-Parenting Agreement is ready" (ready) automatically. */}
        <div className="mt-8">
          <JointAlignmentPromoCard testidPrefix="next-steps-joint-promo" />
        </div>

        {loading ? (
          <div className="mt-8 text-[#6E6787] flex items-center gap-2" data-testid="next-steps-loading">
            <Loader2 size={14} className="animate-spin" /> Personalising your next moves…
          </div>
        ) : (
          <div className="mt-8 space-y-4" data-testid="next-steps-list">
            {steps.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-[#C1B4E0] bg-white p-8 text-center">
                <p className="text-[#1A1330]">
                  We couldn&apos;t generate any next steps yet. Complete more
                  of the assessment and come back.
                </p>
              </div>
            ) : (
              steps.map((s, i) => (
                <StepCard
                  key={s.step_id}
                  step={s}
                  index={i}
                  onDone={(id) => act(id, "done")}
                  onDismiss={(id) => act(id, "dismiss")}
                  onUndo={(id) => act(id, "undo")}
                />
              ))
            )}
          </div>
        )}

        <div className="mt-10 flex items-center gap-3">
          <button
            onClick={() => navigate("/dashboard")}
            className="text-sm text-[#3D1A78] hover:underline font-semibold"
            data-testid="next-steps-continue-btn"
          >
            <ArrowRight size={14} className="inline mr-1" />
            Back to your Dashboard
          </button>
        </div>
      </div>
    </AppShell>
  );
}
