import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { FileText, ArrowLeft, ArrowRight, Sparkles } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

function ParentForm({ config, parentLabel, onSubmit, busy }) {
  const [answers, setAnswers] = useState({});
  const [concern, setConcern] = useState("");
  const [goals, setGoals] = useState([]);

  const toggleGoal = (g) => {
    setGoals((prev) => (prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g]));
  };

  const answered = Object.keys(answers).length;
  const total = config.topics.length;

  return (
    <div data-testid={`parent-form-${parentLabel.replace(/\s+/g, "-").toLowerCase()}`}>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-3xl font-semibold">{parentLabel}'s Responses</h2>
        <span className="text-sm text-muted-foreground" data-testid="answers-progress">
          {answered} of {total} answered
        </span>
      </div>

      <div className="space-y-6">
        {config.topics.map((t, i) => (
          <div key={t.key} className="bg-white border border-border rounded-lg p-6" data-testid={`question-${t.key}`}>
            <p className="font-medium mb-1">
              {i + 1}. {t.label}
            </p>
            <p className="text-sm text-muted-foreground mb-4">{t.question}</p>
            <RadioGroup
              value={answers[t.key] || ""}
              onValueChange={(v) => setAnswers((prev) => ({ ...prev, [t.key]: v }))}
              className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2"
              data-testid={`answer-group-${t.key}`}
            >
              {config.scale.map((s) => (
                <label
                  key={s}
                  htmlFor={`${t.key}-${s}`}
                  className={`flex items-center gap-2 border rounded-md px-3 py-2.5 cursor-pointer text-sm transition-colors ${answers[t.key] === s ? "border-primary bg-secondary/60" : "border-border hover:bg-muted"}`}
                  data-testid={`answer-${t.key}-${s.toLowerCase().replace(/[^a-z]+/g, "-")}`}
                >
                  <RadioGroupItem value={s} id={`${t.key}-${s}`} />
                  <span>{s}</span>
                </label>
              ))}
            </RadioGroup>
          </div>
        ))}
      </div>

      <div className="bg-white border border-border rounded-lg p-6 mt-6" data-testid="primary-concern-block">
        <Label htmlFor={`concern-${parentLabel}`} className="font-medium">{parentLabel}'s primary concern</Label>
        <p className="text-sm text-muted-foreground mt-1 mb-3">In one or two sentences, what concerns you most about your child right now?</p>
        <Textarea
          id={`concern-${parentLabel}`}
          value={concern}
          onChange={(e) => setConcern(e.target.value)}
          placeholder="e.g. Difficulty completing homework between households."
          className="min-h-[90px]"
          data-testid="primary-concern-input"
        />
      </div>

      <div className="bg-white border border-border rounded-lg p-6 mt-6" data-testid="shared-goals-block">
        <Label className="font-medium">Shared goals for your child</Label>
        <p className="text-sm text-muted-foreground mt-1 mb-4">Select every goal that matters to you. Shared selections appear on Page 2 of the report.</p>
        <div className="grid sm:grid-cols-2 gap-3">
          {config.shared_goal_options.map((g) => (
            <label key={g} className="flex items-center gap-3 text-sm cursor-pointer" data-testid={`goal-${g.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
              <Checkbox checked={goals.includes(g)} onCheckedChange={() => toggleGoal(g)} />
              <span>{g}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="mt-8 flex justify-end">
        <Button
          size="lg"
          disabled={answered < total || busy}
          onClick={() => onSubmit({ answers, primary_concern: concern, goals })}
          className="gap-2"
          data-testid="submit-responses-btn"
        >
          {busy ? "Saving…" : "Save responses"} <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
      {answered < total && (
        <p className="text-right text-xs text-muted-foreground mt-2" data-testid="answers-required-note">
          Please answer all {total} questions to continue.
        </p>
      )}
    </div>
  );
}

export default function Wizard() {
  const [types, setTypes] = useState([]);
  const [step, setStep] = useState(0);
  const [typeKey, setTypeKey] = useState(null);
  const [config, setConfig] = useState(null);
  const [caseId, setCaseId] = useState(null);
  const [names, setNames] = useState({ child_name: "", parent_a_name: "", parent_b_name: "" });
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    api.get("/assessment-types").then((r) => setTypes(r.data)).catch((e) => toast.error(formatApiError(e)));
  }, []);

  const resumeCase = async (id) => {
    try {
      const { data: c } = await api.get(`/cases/${id}`);
      const { data: cfg } = await api.get(`/assessment-types/${c.type}`);
      setTypeKey(c.type);
      setConfig(cfg);
      setCaseId(c.id);
      setNames({ child_name: c.child_name, parent_a_name: c.parent_a_name, parent_b_name: c.parent_b_name });
      setStep(!c.has_a ? 2 : 3);
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  useEffect(() => {
    const existing = searchParams.get("case");
    if (existing) resumeCase(existing);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectType = async (key) => {
    setTypeKey(key);
    try {
      const { data } = await api.get(`/assessment-types/${key}`);
      setConfig(data);
      setStep(1);
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const createCase = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/cases", { type: typeKey, ...names });
      setCaseId(data.id);
      setStep(2);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const submitResponses = async (parent, payload) => {
    setBusy(true);
    try {
      const { data } = await api.put(`/cases/${caseId}/responses/${parent}`, payload);
      if (parent === "a") {
        setStep(3);
      } else {
        navigate(`/report/${caseId}`);
      }
      return data;
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const fillDemo = async () => {
    setBusy(true);
    try {
      await api.post(`/cases/${caseId}/demo`);
      navigate(`/report/${caseId}`);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const steps = ["Assessment type", "Details", `${names.parent_a_name || "Parent A"}`, `${names.parent_b_name || "Parent B"}`];

  return (
    <div className="min-h-screen bg-background" data-testid="wizard-page">
      <header className="bg-white border-b border-border no-print">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="wizard-back-link">
            <ArrowLeft className="h-4 w-4" /> Dashboard
          </Link>
          <BrandLogo size="text-xl" />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10">
        <div className="flex items-center gap-2 mb-10" data-testid="wizard-progress">
          {steps.map((s, i) => (
            <div key={s} className="flex items-center gap-2 flex-1 last:flex-none">
              <span
                className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold ${i <= step ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}
                data-testid={`step-indicator-${i}`}
              >
                {i + 1}
              </span>
              <span className={`text-xs hidden sm:block ${i === step ? "font-semibold" : "text-muted-foreground"}`}>{s}</span>
              {i < steps.length - 1 && <div className="flex-1 h-px bg-border mx-2" />}
            </div>
          ))}
        </div>

        {step === 0 && (
          <div data-testid="step-type">
            <h1 className="text-4xl font-semibold mb-2">Choose an assessment</h1>
            <p className="text-muted-foreground mb-8">Both parents will answer the same questions. The report combines both perspectives.</p>
            <div className="grid sm:grid-cols-2 gap-4">
              {types.map((t) => (
                <button
                  key={t.key}
                  onClick={() => selectType(t.key)}
                  className="text-left bg-white border border-border rounded-lg p-6 hover:-translate-y-0.5 hover:shadow-md hover:border-primary transition-[transform,box-shadow,border-color] duration-200"
                  data-testid={`type-option-${t.key}`}
                >
                  <p className="font-semibold">{t.title}</p>
                  <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{t.description}</p>
                  <p className="text-xs text-accent font-medium mt-3">{t.topic_count} topics</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 1 && (
          <div data-testid="step-details">
            <h1 className="text-4xl font-semibold mb-2">Who is this assessment for?</h1>
            <p className="text-muted-foreground mb-8">These names appear on the report. Initials or first names are fine.</p>
            <div className="bg-white border border-border rounded-lg p-6 space-y-5">
              <div className="space-y-2">
                <Label htmlFor="child-name">Child's first name (optional)</Label>
                <Input id="child-name" className="h-12" value={names.child_name} onChange={(e) => setNames({ ...names, child_name: e.target.value })} placeholder="e.g. Alex" data-testid="child-name-input" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="parent-a">Parent A name or label</Label>
                <Input id="parent-a" className="h-12" value={names.parent_a_name} onChange={(e) => setNames({ ...names, parent_a_name: e.target.value })} placeholder="Parent A" data-testid="parent-a-name-input" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="parent-b">Parent B name or label</Label>
                <Input id="parent-b" className="h-12" value={names.parent_b_name} onChange={(e) => setNames({ ...names, parent_b_name: e.target.value })} placeholder="Parent B" data-testid="parent-b-name-input" />
              </div>
              <div className="pt-2 flex justify-between items-center">
                <button type="button" onClick={() => setStep(0)} className="text-sm text-muted-foreground hover:text-foreground" data-testid="back-to-types-btn">
                  Back
                </button>
                <Button onClick={createCase} disabled={busy} className="gap-2" data-testid="create-case-btn">
                  {busy ? "Creating…" : "Continue"} <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        )}

        {step === 2 && config && (
          <div data-testid="step-parent-a">
            <div className="bg-secondary/60 border border-border rounded-lg p-4 mb-8 flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm">Exploring the platform? Load realistic sample data instead of answering manually.</p>
              <Button variant="outline" size="sm" className="gap-1.5" onClick={fillDemo} disabled={busy} data-testid="load-demo-btn-a">
                <Sparkles className="h-3.5 w-3.5" /> Load demo data
              </Button>
            </div>
            <ParentForm
              config={config}
              parentLabel={names.parent_a_name || "Parent A"}
              busy={busy}
              onSubmit={(payload) => submitResponses("a", payload)}
            />
          </div>
        )}

        {step === 3 && config && (
          <div data-testid="step-parent-b">
            <div className="bg-secondary/60 border border-border rounded-lg p-4 mb-8 flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm">Skip ahead — load matching sample responses for both parents.</p>
              <Button variant="outline" size="sm" className="gap-1.5" onClick={fillDemo} disabled={busy} data-testid="load-demo-btn-b">
                <Sparkles className="h-3.5 w-3.5" /> Load demo data
              </Button>
            </div>
            <ParentForm
              config={config}
              parentLabel={names.parent_b_name || "Parent B"}
              busy={busy}
              onSubmit={(payload) => submitResponses("b", payload)}
            />
          </div>
        )}
      </main>
    </div>
  );
}
