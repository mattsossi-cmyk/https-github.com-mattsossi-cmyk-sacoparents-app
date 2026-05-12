import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import WizardLayout from "../components/WizardLayout";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Sparkles } from "lucide-react";

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

  useEffect(() => {
    api.get("/mediation/prep").then((r) => {
      setCompleted(r.data?.completed || {});
      if (r.data?.comm_style) {
        setAnswers(r.data.comm_style.answers || {});
        setSample(r.data.comm_style.free_text_sample || "");
      }
    }).catch(() => {});
  }, []);

  const handleAnalyze = async () => {
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
      navigate("/prep/readiness");
    } catch {
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
                          ? "bg-[#849D8E]/10 border-[#849D8E]/40 text-[#2A3631]"
                          : "bg-[#F5F3E9] border-transparent text-[#2A3631] hover:bg-[#E8ECE9]"
                      }`}
                    >
                      <span className="flex items-center gap-3">
                        <span
                          className={`w-4 h-4 rounded-full border ${
                            isOn ? "border-[#849D8E] bg-[#849D8E]" : "border-[#8A9A92]"
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
            <textarea
              rows={4}
              value={sample}
              onChange={(e) => setSample(e.target.value)}
              className="input-soft resize-none"
              placeholder="Stays private to your account."
              data-testid="comm-sample-textarea"
            />
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
              <span className="text-xs text-[#8A9A92]">
                Answer the three prompts above to unlock reflection.
              </span>
            )}
          </div>

          {analysis && (
            <div
              className="rounded-2xl p-6 bg-[#849D8E]/8 border border-[#849D8E]/25 space-y-4"
              data-testid="comm-analysis-result"
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-[#849D8E] grid place-items-center text-white">
                  <Sparkles size={16} />
                </div>
                <div>
                  <div className="font-serif text-xl text-[#2A3631]">
                    Style: {analysis.style_label}
                  </div>
                  <div className="text-xs text-[#8A9A92]">
                    Mediation readiness score: {analysis.score}/10
                  </div>
                </div>
              </div>
              <p className="text-[#2A3631]">{analysis.summary}</p>
              {analysis.strengths?.length > 0 && (
                <div>
                  <div className="eyebrow mb-2">Strengths</div>
                  <ul className="list-disc pl-5 space-y-1 text-[#2A3631]">
                    {analysis.strengths.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>
              )}
              {analysis.growth_areas?.length > 0 && (
                <div>
                  <div className="eyebrow mb-2">Growth areas</div>
                  <ul className="list-disc pl-5 space-y-1 text-[#2A3631]">
                    {analysis.growth_areas.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>
              )}
              {analysis.suggestions?.length > 0 && (
                <div>
                  <div className="eyebrow mb-2">Try this</div>
                  <ul className="list-disc pl-5 space-y-1 text-[#2A3631]">
                    {analysis.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </WizardLayout>
    </AppShell>
  );
}
