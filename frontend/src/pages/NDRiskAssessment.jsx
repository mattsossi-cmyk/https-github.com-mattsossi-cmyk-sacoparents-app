/**
 * NDRiskAssessment — intake form for the Neurodivergent Coparenting
 * Risk Assessment. Six 1-4 ratings across two axes (Threat + Vulnerability),
 * an optional notes field, and a coparent name.
 *
 * On submit we POST to /api/nd-risk/assessment and navigate to the
 * result page carrying the response inline (so the result page never
 * needs a second network round-trip for the just-completed record).
 */
import { useMemo, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, ShieldAlert, Loader2 } from "lucide-react";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const RATING_LABELS = ["Never / not at all", "Sometimes", "Often", "Constantly / severe"];

const AXES = [
  {
    key: "threat",
    title: "Threat axis — the coparent's behaviour",
    hint: "Rate 1-4 based on the last 90 days. 1 = never; 4 = constant / severe.",
    items: [
      { key: "threat_scheduling_disruption", label: "Scheduling disruption",
        hint: "Last-minute changes, no-shows, or calendar chaos used as leverage." },
      { key: "threat_gaslighting", label: "Memory manipulation / gaslighting",
        hint: "Denying agreed events, rewriting history, distorting what was said." },
      { key: "threat_sensory_overload", label: "Intentional sensory overload",
        hint: "Volume, environment, or timing used to overwhelm you deliberately." },
    ],
  },
  {
    key: "vuln",
    title: "Vulnerability axis — your current state",
    hint: "Rate 1-4 honestly. Your safety plan depends on this being accurate.",
    items: [
      { key: "vuln_executive_burnout", label: "Executive burnout",
        hint: "Capacity for planning, task-switching, and follow-through is depleted." },
      { key: "vuln_memory_fragmentation", label: "Memory fragmentation",
        hint: "Recall of recent exchanges is patchy or dissociative under stress." },
      { key: "vuln_communication_bottleneck", label: "Communication bottleneck",
        hint: "You struggle to formulate a reply in real time under pressure." },
    ],
  },
];

export default function NDRiskAssessment() {
  const nav = useNavigate();
  const [coparentName, setCoparentName] = useState("");
  const [notes, setNotes] = useState("");
  const [scores, setScores] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const totalQuestions = AXES.reduce((n, a) => n + a.items.length, 0);
  const answered = Object.keys(scores).length;
  const canSubmit = coparentName.trim().length > 0 && answered === totalQuestions;

  const summaryPreview = useMemo(() => {
    if (answered === 0) return null;
    const t = Math.max(scores.threat_scheduling_disruption || 0, scores.threat_gaslighting || 0, scores.threat_sensory_overload || 0);
    const v = Math.max(scores.vuln_executive_burnout || 0, scores.vuln_memory_fragmentation || 0, scores.vuln_communication_bottleneck || 0);
    return { threat: t, vuln: v, total: t * v };
  }, [scores, answered]);

  const submit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      const { data } = await api.post("/nd-risk/assessment", {
        coparent_name: coparentName.trim(),
        matrix: scores,
        notes: notes.trim() || undefined,
      });
      nav(`/nd-risk-assessment/result/${data.assessment_id}`, { state: { assessment: data } });
    } catch (err) {
      logError("ND risk submit failed", err);
      toast.error(err?.response?.data?.detail || "Couldn't submit the assessment. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="nd-risk-intake">
        <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] hover:text-[#3D1A78] mb-4">
          <ArrowLeft size={12} /> Back to dashboard
        </Link>

        <header>
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Family Violence · Assessment
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-1 leading-tight">
            Neurodivergent Coparenting Risk Assessment
          </h1>
          <p className="mt-3 text-sm text-[#4B4567] leading-relaxed">
            This assessment filters coparenting risk through a neurodivergent
            vulnerability lens. Six honest 1-4 ratings produce a court-ready
            tier + required interventions plan. All answers are private to you.
          </p>
        </header>

        <div className="mt-6 rounded-2xl border border-[#EFB4B4] bg-[#F8D7D7] p-4 flex items-start gap-3">
          <ShieldAlert size={16} className="text-[#B02A2A] shrink-0 mt-0.5" />
          <p className="text-xs text-[#B02A2A]">
            If you are in immediate danger, close this page and call{" "}
            <strong>911</strong> or the National DV Hotline at{" "}
            <strong>1-800-799-SAFE</strong>. This tool is not an emergency service.
          </p>
        </div>

        <section className="mt-8 space-y-3">
          <label className="block text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
            Named coparent (for the report header)
          </label>
          <input
            type="text"
            value={coparentName}
            onChange={(e) => setCoparentName(e.target.value)}
            className="w-full border border-[#E5E0EE] rounded-xl px-4 py-2.5 text-sm"
            placeholder="e.g. Alex Rivera"
            data-testid="nd-risk-coparent-name"
          />
        </section>

        {AXES.map((axis) => (
          <section key={axis.key} className="mt-8" data-testid={`nd-risk-axis-${axis.key}`}>
            <h2 className="font-serif text-xl text-[#1A1330]">{axis.title}</h2>
            <p className="text-xs text-[#8471B3] italic mt-1">{axis.hint}</p>
            <ul className="mt-4 space-y-3">
              {axis.items.map((item) => (
                <li key={item.key} className="rounded-2xl border border-[#E5E0EE] bg-white p-4">
                  <div className="text-sm font-semibold text-[#1A1330]">{item.label}</div>
                  <div className="text-xs text-[#4B4567] mt-0.5">{item.hint}</div>
                  <div className="mt-3 flex flex-wrap gap-2" role="radiogroup" aria-label={item.label}>
                    {[1, 2, 3, 4].map((n) => {
                      const active = scores[item.key] === n;
                      return (
                        <button
                          key={n}
                          type="button"
                          role="radio"
                          aria-checked={active}
                          onClick={() => setScores((s) => ({ ...s, [item.key]: n }))}
                          data-testid={`nd-risk-${item.key}-${n}`}
                          className={`min-w-[54px] px-3 py-2 rounded-full text-xs font-semibold border transition-colors ${
                            active
                              ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                              : "bg-white text-[#3D1A78] border-[#D6CFE8] hover:bg-[#F5F1FB]"
                          }`}
                        >
                          {n} · {RATING_LABELS[n - 1].split(" ")[0]}
                        </button>
                      );
                    })}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))}

        <section className="mt-8">
          <label className="block text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-2">
            Notes for the court report (optional)
          </label>
          <textarea
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={1000}
            className="w-full border border-[#E5E0EE] rounded-xl px-4 py-3 text-sm"
            placeholder="Specific recent examples that support these ratings…"
            data-testid="nd-risk-notes"
          />
          <div className="text-[10px] text-[#8471B3] mt-1">{notes.length} / 1000</div>
        </section>

        <div className="mt-8 rounded-2xl border border-[#E5E0EE] bg-[#FCFBFE] p-4 flex items-center justify-between gap-3 flex-wrap">
          <div className="text-xs text-[#4B4567]">
            <strong>{answered}</strong> / {totalQuestions} answered
            {summaryPreview && (
              <> · preview total: <strong className="text-[#1A1330]">{summaryPreview.total}</strong> / 16</>
            )}
          </div>
          <button
            type="button"
            onClick={submit}
            disabled={!canSubmit || submitting}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-semibold disabled:opacity-60"
            data-testid="nd-risk-submit"
          >
            {submitting ? <Loader2 size={14} className="animate-spin" /> : null}
            {submitting ? "Scoring…" : "Submit assessment"}
          </button>
        </div>
      </div>
    </AppShell>
  );
}
