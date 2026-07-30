/**
 * SpecialNeedsReport.jsx — the individual parent SNC report.
 *
 * Consumes GET /snc/report + POST /snc/report/regenerate + GET /snc/report/pdf,
 * shows the 17-section structured report, and exposes a "last generated · regenerate"
 * affordance backed by the cached-report lifecycle on the backend.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { toast } from "sonner";
import {
  Download,
  RefreshCcw,
  Loader2,
  ShieldAlert,
  FileText,
  ArrowLeft,
  Mail,
  UserPlus,
} from "lucide-react";
import { logError } from "../lib/logger";

const CLS_COLOR = {
  "Established strength": "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
  "Generally supported": "bg-[#EEE9F7] text-[#3D1A78] border-[#D6CFE8]",
  "Coordination opportunity": "bg-[#FBEDDA] text-[#8C5A2C] border-[#EDD5B0]",
  "Significant inconsistency": "bg-[#FBE0D3] text-[#C2481F] border-[#F1BDA1]",
  "Priority concern": "bg-[#F8D7D7] text-[#B02A2A] border-[#EFB4B4]",
  "Not enough data": "bg-[#EEEAF3] text-[#6E6E82] border-[#D6CFE8]",
  "Separate review": "bg-[#EEEAF3] text-[#6E6E82] border-[#D6CFE8]",
};

function Pill({ label }) {
  if (!label) return null;
  const cls = CLS_COLOR[label] || CLS_COLOR["Not enough data"];
  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-semibold border ${cls}`}
      data-testid={`snc-pill-${label.replace(/ /g, "-").toLowerCase()}`}
    >
      {label}
    </span>
  );
}

function BulletList({ items = [], testId }) {
  if (!items || items.length === 0) return <div className="text-sm text-[#8471B3] italic">—</div>;
  return (
    <ul className="list-disc pl-5 text-sm text-[#1A1330] space-y-1" data-testid={testId}>
      {items.map((it, i) => (
        <li key={`${i}-${String(it).slice(0, 30)}`}>{typeof it === "string" ? it : JSON.stringify(it)}</li>
      ))}
    </ul>
  );
}

function FivePartBlock({ id, number, title, block }) {
  if (!block) return null;
  const scoreTxt =
    block.score === null || block.score === undefined
      ? "—"
      : typeof block.score === "number"
      ? block.score.toFixed(2)
      : String(block.score);
  return (
    <section
      className="bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm"
      data-testid={`snc-report-${id}`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <h3 className="font-serif text-xl text-[#1A1330]">
          {number}. {title}
        </h3>
        <div className="flex items-center gap-2">
          <Pill label={block.classification} />
          <span className="text-xs text-[#4B4567]">Score {scoreTxt}</span>
        </div>
      </div>
      <div className="grid gap-3 text-sm">
        {block.finding && (
          <div>
            <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Finding</div>
            <div className="text-[#1A1330]">{block.finding}</div>
          </div>
        )}
        {block.child_impact && (
          <div>
            <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Child impact</div>
            <div className="text-[#1A1330]">{block.child_impact}</div>
          </div>
        )}
        {block.suggested && (
          <div>
            <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Suggested option</div>
            <div className="text-[#1A1330]">{block.suggested}</div>
          </div>
        )}
        {block.action_step && (
          <div>
            <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">First action step</div>
            <div className="text-[#1A1330]">{block.action_step}</div>
          </div>
        )}
      </div>
    </section>
  );
}

function formatWhen(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function SpecialNeedsReport() {
  const [state, setState] = useState({ loading: true, doc: null, status: null });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [rep, st] = await Promise.all([
        api.get("/snc/report"),
        api.get("/snc/report/status"),
      ]);
      setState({ loading: false, doc: rep.data?.report ? rep.data : null, status: st.data });
    } catch (err) {
      logError("snc report load", err);
      setState({ loading: false, doc: null, status: null });
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const regenerate = async () => {
    setBusy(true);
    try {
      await api.post("/snc/report/regenerate");
      await load();
      toast.success("Report regenerated.");
    } catch (err) {
      logError("snc regenerate", err);
      toast.error(err?.response?.data?.detail || "Regenerate failed.");
    } finally {
      setBusy(false);
    }
  };

  const generate = async () => {
    setBusy(true);
    try {
      await api.post("/snc/report/generate");
      await load();
    } catch (err) {
      logError("snc generate", err);
      toast.error(err?.response?.data?.detail || "Could not generate the report.");
    } finally {
      setBusy(false);
    }
  };

  const downloadPdf = async () => {
    setBusy(true);
    try {
      const res = await api.get("/snc/report/pdf", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Special_Needs_Report.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (err) {
      logError("snc pdf", err);
      toast.error(err?.response?.data?.detail || "Could not download the PDF.");
    } finally {
      setBusy(false);
    }
  };

  const emailMe = async () => {
    setBusy(true);
    try {
      const res = await api.post("/snc/report/email");
      if (res.data?.sent) {
        toast.success(`Sent to ${res.data.to || "your email"}.`);
      } else {
        toast.error(res.data?.reason || "Could not email your report.");
      }
      await load();
    } catch (err) {
      logError("snc email", err);
      toast.error(err?.response?.data?.detail || "Could not email your report.");
    } finally {
      setBusy(false);
    }
  };

  if (state.loading) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 py-10 text-[#4B4567]">
          <Loader2 className="animate-spin" /> Loading report…
        </div>
      </AppShell>
    );
  }

  if (!state.doc) {
    return (
      <AppShell>
        <div className="max-w-3xl mx-auto px-4 py-10">
          <h1 className="font-serif text-3xl text-[#1A1330] mb-2">Special Needs Co-Parenting Report</h1>
          <p className="text-sm text-[#4B4567] mb-6">
            No report has been generated yet. Finish (or continue) the assessment,
            then generate your individual parent report.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/special-needs"
              data-testid="snc-report-empty-open-assessment"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110"
            >
              Open the assessment
            </Link>
            {state.status?.has_assessment && (
              <button
                data-testid="snc-report-empty-generate"
                onClick={generate}
                disabled={busy}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7] disabled:opacity-60"
              >
                {busy ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />} Generate report
              </button>
            )}
          </div>
        </div>
      </AppShell>
    );
  }

  const doc = state.doc;
  const report = doc.report || {};
  const status = state.status || {};
  const generatedAt = doc.generated_at;
  const stale = status.stale === true;

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="snc-report-root">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 text-xs text-[#4B4567] underline mb-4"
          data-testid="snc-report-back"
        >
          <ArrowLeft size={12} /> Back to dashboard
        </Link>

        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
          Individual Parent Report
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
          Special Needs Co-Parenting Report
        </h1>
        <p className="text-sm text-[#4B4567] mt-3 max-w-3xl">{report.purpose}</p>

        {/* Cache header */}
        <div
          className="mt-6 rounded-3xl border border-[#E5E0EE] p-4 sm:p-5 bg-white flex flex-wrap items-center justify-between gap-3 shadow-sm"
          data-testid="snc-report-cache-bar"
        >
          <div className="text-xs text-[#4B4567]">
            {stale ? (
              <span className="text-[#B02A2A] font-medium">
                Your answers have changed since this report was generated.
              </span>
            ) : (
              <span>Last generated {formatWhen(generatedAt) || "—"}.</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={downloadPdf}
              disabled={busy}
              data-testid="snc-report-download-pdf"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60"
            >
              <Download size={13} /> Download PDF
            </button>
            <button
              onClick={emailMe}
              disabled={busy}
              data-testid="snc-report-email"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7] disabled:opacity-60"
            >
              <Mail size={13} /> Email me the PDF
            </button>
            <button
              onClick={regenerate}
              disabled={busy}
              data-testid="snc-report-regenerate"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7] disabled:opacity-60"
            >
              {busy ? <Loader2 size={13} className="animate-spin" /> : <RefreshCcw size={13} />} Regenerate
            </button>
            <Link
              to="/special-needs/invite"
              data-testid="snc-report-invite-coparent"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs border border-[#3D1A78] text-[#3D1A78] hover:bg-[#EEE9F7]"
            >
              <UserPlus size={13} /> Invite co-parent
            </Link>
          </div>
        </div>

        {/* At a glance */}
        <section
          className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm"
          data-testid="snc-report-at-a-glance"
        >
          <h2 className="font-serif text-2xl text-[#1A1330] mb-3">1. Report at a Glance</h2>
          <div className="grid sm:grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Child&apos;s identified strengths</div>
              <BulletList items={report.at_a_glance?.child_strengths} testId="snc-glance-strengths" />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Child&apos;s primary needs</div>
              <BulletList items={report.at_a_glance?.child_needs} testId="snc-glance-needs" />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Parent&apos;s highest priorities</div>
              <BulletList items={report.at_a_glance?.parent_priorities} testId="snc-glance-priorities" />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Established strengths</div>
              <BulletList items={report.at_a_glance?.established_strengths} testId="snc-glance-established" />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Areas needing greater coordination</div>
              <BulletList items={report.at_a_glance?.coordination_areas} testId="snc-glance-coordination" />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Priority concerns</div>
              <BulletList items={report.at_a_glance?.priority_concerns} testId="snc-glance-priority" />
            </div>
          </div>
        </section>

        {/* Category summary */}
        <section
          className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm"
          data-testid="snc-report-category-summary"
        >
          <h2 className="font-serif text-2xl text-[#1A1330] mb-3">2. Category Summary</h2>
          <div className="space-y-3">
            {(report.category_summary || []).map((r, i) => (
              <div
                key={`${r.category}-${i}`}
                className="flex flex-wrap items-center justify-between gap-3 py-3 border-b border-[#EEE9F7] last:border-b-0"
                data-testid={`snc-summary-row-${i}`}
              >
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-[#1A1330]">{r.category}</div>
                  {r.primary_finding && (
                    <div className="text-xs text-[#4B4567] mt-0.5">{r.primary_finding}</div>
                  )}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <div className="text-xs text-[#4B4567]">
                    Score{" "}
                    {typeof r.score === "number"
                      ? r.score.toFixed(2)
                      : r.score || "—"}
                  </div>
                  <Pill label={r.classification} />
                </div>
              </div>
            ))}
          </div>
          <div className="text-[11px] italic text-[#8471B3] mt-3">
            Scores reflect the reporting parent&apos;s answers and are not findings of fact.
          </div>
        </section>

        {/* Child profile */}
        {report.child_profile && (
          <section
            className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm"
            data-testid="snc-report-child-profile"
          >
            <h2 className="font-serif text-2xl text-[#1A1330] mb-3">3. Child Profile</h2>
            <div className="grid gap-3 text-sm">
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Age and grade</div>
                <div className="text-[#1A1330]">{report.child_profile.age_grade || "—"}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Diagnosis status</div>
                <div className="text-[#1A1330]">{report.child_profile.diagnosis_status || "—"}</div>
              </div>
              {report.child_profile.identified_needs?.length > 0 && (
                <div>
                  <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Identified areas of need</div>
                  <BulletList items={report.child_profile.identified_needs} testId="snc-child-needs" />
                </div>
              )}
              {report.child_profile.summary && (
                <div className="text-sm text-[#1A1330] italic">{report.child_profile.summary}</div>
              )}
            </div>
          </section>
        )}

        {/* Five-part scored sections */}
        <div className="mt-6 space-y-4">
          <FivePartBlock id="understanding" number={4} title="Understanding and Acceptance" block={report.understanding_acceptance} />
          <FivePartBlock id="medical" number={5} title="Medical and Mental Healthcare" block={report.medical_mental} />
          <FivePartBlock id="school" number={6} title="Kindergarten and Elementary School" block={report.school} />
          <FivePartBlock id="transitions" number={7} title="Transitions, Pickup, and Drop-Off" block={report.transitions} />
          <FivePartBlock id="routines" number={8} title="Daily Routines Across Homes" block={report.daily_routines} />
          <FivePartBlock id="communication" number={9} title="Communication and Information Sharing" block={report.communication} />
          <FivePartBlock
            id="events"
            number={10}
            title="School Events"
            block={report.events_and_extracurricular?.school_events}
          />
          <FivePartBlock
            id="extracurricular"
            number={10}
            title="Extracurricular Activities"
            block={report.events_and_extracurricular?.extracurricular}
          />
          <FivePartBlock id="decisions" number={11} title="Decision-Making and Professional Guidance" block={report.decision_making} />
        </div>

        {/* Safety section */}
        <section
          className="mt-6 bg-white rounded-3xl border-2 border-[#F1BDA1] p-5 sm:p-7 shadow-sm"
          data-testid="snc-report-safety"
        >
          <div className="flex items-start gap-3">
            <ShieldAlert className="text-[#C2481F] shrink-0 mt-1" />
            <div className="flex-1">
              <h2 className="font-serif text-2xl text-[#1A1330] mb-1">12. Family Violence and Communication Safety</h2>
              <p className="text-xs text-[#8471B3] italic mb-3">
                Kept out of every score. Never included automatically in a shared / comparison view.
              </p>
              {report.safety?.redacted ? (
                <div className="text-sm text-[#4B4567] italic">{report.safety.note}</div>
              ) : (
                <>
                  <div className="text-sm text-[#1A1330] font-medium">{report.safety?.screen_result || "—"}</div>
                  {report.safety?.selected_flags?.length > 0 && (
                    <div className="mt-3">
                      <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#C2481F] mb-1">Reported items</div>
                      <BulletList items={report.safety.selected_flags} testId="snc-safety-flags" />
                    </div>
                  )}
                  {report.safety?.recommend_full_family_violence_assessment && (
                    <div className="mt-4 p-3 rounded-2xl bg-[#FBE0D3] text-sm text-[#7A4A2E]" data-testid="snc-safety-referral">
                      <div className="font-semibold mb-1">Next step: Family Violence &amp; Communication Safety Assessment.</div>
                      <Link
                        to="/safety-assessment"
                        className="underline"
                        data-testid="snc-safety-referral-link"
                      >
                        Open the full assessment
                      </Link>
                    </div>
                  )}
                  {report.safety?.note && (
                    <div className="mt-3 text-xs text-[#8471B3] italic">{report.safety.note}</div>
                  )}
                </>
              )}
            </div>
          </div>
        </section>

        {/* Parent capacity */}
        <div className="mt-6">
          <FivePartBlock id="capacity" number={13} title="Parent Capacity and Support" block={report.parent_capacity} />
        </div>

        {/* Goals */}
        {report.goals_concerns && (
          <section
            className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm"
            data-testid="snc-report-goals"
          >
            <h2 className="font-serif text-2xl text-[#1A1330] mb-3">14. Parent&apos;s Goals, Concerns, and Priorities</h2>
            <div className="grid sm:grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Three primary goals</div>
                <BulletList items={report.goals_concerns.goals} testId="snc-goals-goals" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Three primary concerns</div>
                <BulletList items={report.goals_concerns.concerns} testId="snc-goals-concerns" />
              </div>
            </div>
          </section>
        )}

        {/* Action plan */}
        {report.action_plan?.length > 0 && (
          <section
            className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm"
            data-testid="snc-report-action-plan"
          >
            <h2 className="font-serif text-2xl text-[#1A1330] mb-3">15. Recommended Child-Focused Action Plan</h2>
            <div className="space-y-3">
              {report.action_plan.map((row) => (
                <div key={row.priority} className="p-3 rounded-2xl bg-[#F8F5FC] border border-[#EEE9F7]" data-testid={`snc-action-${row.priority}`}>
                  <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">Priority {row.priority}</div>
                  <div className="text-sm text-[#1A1330]">{row.recommended_action}</div>
                  <div className="text-xs text-[#4B4567] mt-1">
                    {row.professional && <>Professional: {row.professional} · </>}
                    Target: {row.target_date}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Questions for other parent */}
        {report.questions_for_other_parent?.length > 0 && (
          <section
            className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm"
            data-testid="snc-report-questions"
          >
            <h2 className="font-serif text-2xl text-[#1A1330] mb-3">16. Questions for the Other Parent or a Professional</h2>
            <BulletList items={report.questions_for_other_parent} testId="snc-questions-list" />
          </section>
        )}

        {/* Closing */}
        {report.closing?.summary_paragraph && (
          <section
            className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm"
            data-testid="snc-report-closing"
          >
            <h2 className="font-serif text-2xl text-[#1A1330] mb-3">17. Closing Summary</h2>
            <p className="text-sm text-[#1A1330]">{report.closing.summary_paragraph}</p>
          </section>
        )}

        {/* Disclaimer */}
        <div className="mt-8 text-xs text-[#8471B3] italic">{report.disclaimer}</div>
      </div>
    </AppShell>
  );
}
