import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import WizardLayout from "../components/WizardLayout";
import SafetyAlert from "../components/SafetyAlert";
import { api } from "../lib/api";
import { toast } from "sonner";
import { logError } from "../lib/logger";
import { detectSafetyConcern } from "../lib/safety";
import WatchFirstVideo from "../components/WatchFirstVideo";
import SectionCoaching from "../components/SectionCoaching";
import MethodologyCard from "../components/MethodologyCard";
import { Sparkles } from "lucide-react";
import { AiGuardFrame, useAiGuard } from "../components/aiNotice/AiGuard";
import { CommShareCard } from "../components/commStyle/CommShareCard";
import { getCommShare } from "../lib/commShare";

const QUIZ = [
  {
    id: "q1",
    prompt: "When my co-parent texts me about a conflict, my first instinct is to…",
    options: [
      { v: "avoider", label: "Wait days to reply — or not reply." },
      { v: "escalator", label: "Match the intensity and reply quickly." },
      { v: "defensive", label: "Explain why they're wrong before anything else." },
      { v: "over_explainer", label: "Write a long message covering every angle." },
      { v: "passive", label: "Say 'fine' to keep the peace, even if it's not fine." },
      { v: "balanced", label: "Pause, then reply briefly and factually." },
    ],
  },
  {
    id: "q2",
    prompt: "When disagreements arise about our child, I most often…",
    options: [
      { v: "avoider", label: "Disengage and hope it passes." },
      { v: "escalator", label: "Make my point loudly so it lands." },
      { v: "defensive", label: "Justify my parenting decisions." },
      { v: "over_explainer", label: "Send articles, screenshots, and context." },
      { v: "passive", label: "Agree even when I disagree." },
      { v: "balanced", label: "Name the issue and propose options." },
    ],
  },
  {
    id: "q3",
    prompt: "If I had to be honest, the pattern I'd most like to change is…",
    options: [
      { v: "avoider", label: "Avoiding hard conversations." },
      { v: "escalator", label: "Reacting before thinking." },
      { v: "defensive", label: "Defending instead of listening." },
      { v: "over_explainer", label: "Over-explaining instead of being clear." },
      { v: "passive", label: "Going passive when I'm hurt." },
      { v: "balanced", label: "I feel steady; I want to stay that way." },
    ],
  },
];

export default function CommStyle() {
  const navigate = useNavigate();
  const [completed, setCompleted] = useState({});
  const [answers, setAnswers] = useState({});
  const [sample, setSample] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [askShare, setAskShare] = useState(false);

  useEffect(() => {
    api
      .get("/mediation/prep")
      .then((r) => {
        setCompleted(r.data?.completed || {});
        if (r.data?.comm_style) {
          setAnswers(r.data.comm_style.answers || {});
          setSample(r.data.comm_style.free_text_sample || "");
        }
      })
      .catch((err) => logError("Failed to load prep:", err));
  }, []);

  // The sample is also saved to the account, so the box stays editable; the AI notice and check run on the AI button.
  const aiGuard = useAiGuard("comm_style", sample);
  const handleAnalyze = async () => {
    if (!(await aiGuard.confirmSend(sample))) return;
    setAnalyzing(true);
    try {
      const res = await api.post("/mediation/analyze-communication", {
        text: sample,
        answers,
      });
      setAnalysis(res.data);
      toast.success("Reflection ready.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not analyze right now.");
    } finally {
      setAnalyzing(false);
    }
  };

  const onNext = async () => {
    setSaving(true);
    try {
      await api.put("/mediation/comm-style", {
        answers,
        free_text_sample: sample,
      });
      toast.success("Saved.");
      // Ask once (only parents linked to Align); after that the Account page switch changes it.
      const linked = await api.get("/integrations/align-link").then((r) => Boolean(r.data?.linked), () => false);
      const choice = linked ? await getCommShare().catch(() => "unknown") : "unknown";
      if (choice === null) setAskShare(true);
      else navigate("/next-steps/comm_style");
    } catch (err) {
      logError("Save comm-style failed:", err);
      toast.error("Could not save.");
    } finally {
      setSaving(false);
    }
  };

  const allAnswered = QUIZ.every((q) => answers[q.id]);

  return (
    <AppShell>
      <WizardLayout
        currentKey="communication"
        eyebrow="Step 4 of 5"
        title="Notice your patterns — gently."
        description="Awareness, not judgement. A short quiz, then optional AI-coached reflection."
        completed={completed}
        saving={saving}
        onNext={onNext}
      >
        <div className="space-y-8">
          <MethodologyCard id="comm_style" />
          <WatchFirstVideo
            videoSrc="/videos/comm-style-reflection.mp4"
            subtitle="Understand Your Co-Parenting Relationship — watch before you answer"
            testid="comm-style-watch"
          />
          {QUIZ.map((q) => (
            <div key={q.id}>
              <div className="eyebrow mb-2">{q.prompt}</div>
              <div className="space-y-2">
                {q.options.map((opt) => {
                  const isOn = answers[q.id] === opt.v;
                  return (
                    <button
                      key={opt.v}
                      type="button"
                      onClick={() => setAnswers({ ...answers, [q.id]: opt.v })}
                      data-testid={`comm-${q.id}-${opt.v}`}
                      className={`w-full text-left rounded-2xl px-4 py-3 border transition-all ${
                        isOn
                          ? "bg-[#3D1A78]/10 border-[#3D1A78]/40 text-[#1A1330]"
                          : "bg-[#EFE9F9] border-transparent text-[#1A1330] hover:bg-[#E5E0EE]"
                      }`}
                    >
                      <span className="flex items-center gap-3">
                        <span
                          className={`w-4 h-4 rounded-full border ${
                            isOn ? "border-[#3D1A78] bg-[#3D1A78]" : "border-[#857E9C]"
                          }`}
                        />
                        {opt.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}

          <div>
            <label className="eyebrow block mb-2">
              Optional: paste a recent message you sent (it will be reframed gently)
            </label>
            <AiGuardFrame tp="comm-sample" guard={aiGuard}>
              <textarea
                rows={4}
                value={sample}
                onChange={(e) => setSample(e.target.value)}
                className="input-soft resize-none"
                placeholder="Private to your account unless you choose to share it with your assigned professional on Align."
                data-testid="comm-sample-textarea"
              />
            </AiGuardFrame>
            <CommSafety sample={sample} />
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleAnalyze}
              disabled={!allAnswered || analyzing}
              className="btn-sage inline-flex items-center gap-2"
              data-testid="comm-analyze-button"
            >
              <Sparkles size={16} />
              {analyzing ? "Reflecting…" : "Get AI reflection"}
            </button>
            {!allAnswered && (
              <span className="text-xs text-[#6E6787]">
                Answer the three prompts above to unlock reflection.
              </span>
            )}
          </div>

          {analysis && (
            <div
              className="rounded-2xl p-6 bg-[#3D1A78]/8 border border-[#3D1A78]/25 space-y-4"
              data-testid="comm-analysis-result"
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-[#3D1A78] grid place-items-center text-white">
                  <Sparkles size={16} />
                </div>
                <div>
                  <div className="font-serif text-xl text-[#1A1330]">
                    Style: {analysis.style_label}
                  </div>
                  <div className="text-xs text-[#6E6787]">
                    Mediation readiness score: {analysis.score}/10
                  </div>
                </div>
              </div>
              <p className="text-[#1A1330]">{analysis.summary}</p>
              {analysis.strengths?.length > 0 && (
                <div>
                  <div className="eyebrow mb-2">Strengths</div>
                  <ul className="list-disc pl-5 space-y-1 text-[#1A1330]">
                    {analysis.strengths.map((s) => <li key={s}>{s}</li>)}
                  </ul>
                </div>
              )}
              {analysis.growth_areas?.length > 0 && (
                <div>
                  <div className="eyebrow mb-2">Growth areas</div>
                  <ul className="list-disc pl-5 space-y-1 text-[#1A1330]">
                    {analysis.growth_areas.map((s) => <li key={s}>{s}</li>)}
                  </ul>
                </div>
              )}
              {analysis.suggestions?.length > 0 && (
                <div>
                  <div className="eyebrow mb-2">Try this</div>
                  <ul className="list-disc pl-5 space-y-1 text-[#1A1330]">
                    {analysis.suggestions.map((s) => <li key={s}>{s}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}

          <SectionCoaching
            section="comm-style"
            ready={Boolean(analysis)}
            data={analysis || {}}
          />
        </div>
      </WizardLayout>
      <CommShareCard open={askShare} hasSample={Boolean(sample.trim())} onDone={() => navigate("/next-steps/comm_style")} />
    </AppShell>
  );
}

function CommSafety({ sample }) {
  const [dismissed, setDismissed] = useState(false);
  const level = useMemo(() => detectSafetyConcern(sample), [sample]);
  if (!level || dismissed) return null;
  return <SafetyAlert level={level} onDismiss={() => setDismissed(true)} />;
}
