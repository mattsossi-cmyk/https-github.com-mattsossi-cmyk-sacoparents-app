import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, ArrowRight, Download } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { ConfidentialityNotice } from "@/components/ConfidentialityNotice";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export default function JointAssessment() {
  const { id } = useParams();
  const [config, setConfig] = useState(null);
  const [detail, setDetail] = useState(null);
  const [answers, setAnswers] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [link, setLink] = useState(null);
  const [linkCode, setLinkCode] = useState("");
  const [foundation, setFoundation] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/external/link").then((r) => setLink(r.data)).catch(() => setLink({ linked: false }));
  }, []);

  const doLink = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/external/link", { code: linkCode });
      setLink({ linked: true, external_email: data.external_email });
      toast.success("Accounts linked");
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const doImport = async () => {
    setBusy(true);
    try {
      await api.post(`/joint/reports/${id}/import`);
      toast.success("Assessment imported — your side is complete.");
      navigate(`/joint/${id}`);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const doFoundation = async () => {
    setBusy(true);
    try {
      const { data } = await api.get("/external/assessments");
      const stmts = data.statements || [];
      if (!stmts.length) {
        toast.error("No Foundation Statements found on your sacoparentsapp.online account");
      } else {
        setFoundation(stmts);
        toast.success(`${stmts.length} Foundation Statement${stmts.length > 1 ? "s" : ""} ready to merge into the agreement`);
      }
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    Promise.all([api.get("/joint/config"), api.get(`/joint/reports/${id}`)])
      .then(([c, d]) => {
        setConfig(c.data);
        setDetail(d.data);
        if (d.data.my_answers) {
          navigate(`/joint/${id}`, { replace: true });
        } else if (!d.data.my_role || !d.data.participants[d.data.my_role]?.accepted) {
          setError("Only invited parents can complete this assessment.");
        }
      })
      .catch((e) => setError(formatApiError(e)));
  }, [id, navigate]);

  const questionList = detail?.kind === "agreement" ? config?.agreement_areas || [] : config?.questions || [];
  const answered = questionList.filter((q) => (answers[q.key] || "").trim()).length;
  const total = questionList.length;

  const submit = async () => {
    setBusy(true);
    try {
      await api.put(`/joint/reports/${id}/responses`, { answers, ...(foundation ? { foundation } : {}) });
      toast.success("Your responses are saved — they remain private until both parents finish.");
      navigate(`/joint/${id}`);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-6" data-testid="joint-assess-error">
        <div className="max-w-md text-center">
          <p className="text-lg font-medium">{error}</p>
          <Link to="/dashboard" className="inline-block mt-6">
            <Button variant="outline" data-testid="joint-assess-error-back-btn">Back to dashboard</Button>
          </Link>
        </div>
      </div>
    );
  }

  if (!config || !detail) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center" data-testid="joint-assess-loading">
        <p className="text-muted-foreground text-sm">Loading…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background" data-testid="joint-assessment-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="assess-back-link">
            <ArrowLeft className="h-4 w-4" /> Dashboard
          </Link>
          <BrandLogo size="text-xl" />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10">
        <p className="text-xs uppercase tracking-widest text-accent font-semibold" data-testid="assess-subject">{detail.subject_label}</p>
        <h1 className="text-4xl font-semibold mt-1 mb-2" data-testid="assess-heading">{detail.kind === "agreement" ? "Your Proposed Agreement Terms" : "Your Independent Reflection"}</h1>
        <p className="text-muted-foreground mb-2">
          Regarding <strong>{detail.child_name}</strong>. {detail.kind === "agreement" ? "Propose an arrangement for each area — the other parent does the same independently, and neither of you sees the other's proposals." : "Answer honestly — the other parent cannot see your answers."}
        </p>
        <p className="text-sm text-muted-foreground mb-8" data-testid="assess-progress">{answered} of {total} answered</p>

        {detail.is_safety && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-5 mb-8" data-testid="safety-confidentiality">
            <p className="font-semibold text-red-800">Confidentiality</p>
            <p className="text-sm text-red-800/80 mt-1">
              Your responses will not be shared between the parties. This report is prepared for review
              with a third-party mediator{detail.professional_name ? ` (${detail.professional_name})` : ""}.
              Only the completed comparison is provided to the mediator.
            </p>
          </div>
        )}

        <div className="bg-secondary/50 border border-border rounded-lg p-5 mb-8" data-testid="import-card">
          <p className="font-semibold">Already completed an assessment on sacoparentsapp.online?</p>
          <p className="text-sm text-muted-foreground mt-1 mb-4">
            Import it instead of answering these questions again. Your imported material is used as-is for the comparison.
          </p>
          {link === null ? null : link.linked ? (
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-sm text-muted-foreground" data-testid="linked-email">Linked: {link.external_email}</span>
              <Button onClick={doImport} disabled={busy} className="gap-2" data-testid="import-assessment-btn">
                <Download className="h-4 w-4" /> {busy ? "Importing…" : "Import My Assessment"}
              </Button>
            </div>
          ) : (
            <div className="flex gap-2 max-w-lg items-center">
              <Input
                value={linkCode}
                onChange={(e) => setLinkCode(e.target.value.toUpperCase())}
                placeholder="Link code from sacoparentsapp.online"
                className="h-11 uppercase tracking-widest"
                data-testid="link-code-input"
              />
              <Button variant="outline" onClick={doLink} disabled={!linkCode.trim() || busy} className="h-11" data-testid="link-accounts-btn">
                Link Accounts
              </Button>
            </div>
          )}
        </div>

        {detail.kind === "agreement" && (
          <div className="bg-white border-2 border-brand-green rounded-lg p-5 mb-8" data-testid="foundation-card">
            <p className="font-semibold text-brand-green">Foundation Statements</p>
            <p className="text-sm text-muted-foreground mt-1 mb-4">
              Your Foundation Statement from sacoparentsapp.online will be merged into the co-parenting agreement alongside your proposed terms.
            </p>
            {foundation ? (
              <div data-testid="foundation-loaded">
                <p className="text-sm font-medium mb-2">{foundation.length} statement{foundation.length > 1 ? "s" : ""} will be included:</p>
                <ul className="list-disc pl-5 space-y-1">
                  {foundation.map((s, i) => (
                    <li key={i} className="text-sm text-muted-foreground">{s.title || `Statement ${i + 1}`}</li>
                  ))}
                </ul>
              </div>
            ) : link?.linked ? (
              <Button variant="outline" onClick={doFoundation} disabled={busy} className="gap-2" data-testid="pull-foundation-btn">
                <Download className="h-4 w-4" /> {busy ? "Loading…" : "Pull in my Foundation Statements"}
              </Button>
            ) : (
              <p className="text-sm text-muted-foreground" data-testid="foundation-link-hint">Link your sacoparentsapp.online account above to include your Foundation Statement.</p>
            )}
          </div>
        )}

        <div className="space-y-6">
          {questionList.map((q, i) => (
            <div key={q.key} className="bg-white border border-border rounded-lg p-6" data-testid={`assess-question-${q.key}`}>
              {q.label && <p className="text-xs uppercase tracking-widest text-accent font-semibold mb-1">{q.label}</p>}
              <Label htmlFor={`q-${q.key}`} className="font-medium">{i + 1}. {q.question}</Label>
              <Textarea
                id={`q-${q.key}`}
                className="mt-3 min-h-[90px]"
                value={answers[q.key] || ""}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [q.key]: e.target.value }))}
                data-testid={`assess-answer-${q.key}`}
              />
            </div>
          ))}
        </div>

        <div className="mt-8">
          <ConfidentialityNotice />
        </div>

        <div className="mt-8 flex justify-end">
          <Button size="lg" className="gap-2" disabled={answered < total || busy} onClick={submit} data-testid="assess-submit-btn">
            {busy ? "Saving…" : "Submit My Responses"} <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
        {answered < total && (
          <p className="text-right text-xs text-muted-foreground mt-2" data-testid="assess-required-note">
            Please answer all {total} questions to continue.
          </p>
        )}
      </main>
    </div>
  );
}
