/**
 * NDRiskAssessmentResult — post-submission view showing the score
 * breakdown, tier + required interventions, a marked 4×4 heatmap, and
 * a professionally formatted PDF download.
 */
import { useEffect, useState } from "react";
import { useParams, useLocation, Link } from "react-router-dom";
import { ArrowLeft, Download, Loader2, CheckSquare, Square } from "lucide-react";
import AppShell from "../components/AppShell";
import NDRiskTimeline from "../components/NDRiskTimeline";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const TIER_META = {
  low:      { label: "Low",      bg: "bg-[#E6F4EC]", text: "text-[#1F5C3B]", pill: "bg-[#1F5C3B]" },
  medium:   { label: "Medium",   bg: "bg-[#FFF6E5]", text: "text-[#8A5B00]", pill: "bg-[#AA7428]" },
  high:     { label: "High",     bg: "bg-[#F8D7D7]", text: "text-[#B02A2A]", pill: "bg-[#B02A2A]" },
  critical: { label: "Critical", bg: "bg-[#F8D7D7]", text: "text-[#6E1616]", pill: "bg-[#6E1616]" },
};

function tierForProduct(p) {
  if (p <= 3)  return "low";
  if (p <= 8)  return "medium";
  if (p <= 12) return "high";
  return "critical";
}

function Heatmap({ threat, vuln }) {
  const rows = [1, 2, 3, 4];
  return (
    <div className="inline-block" data-testid="nd-risk-heatmap">
      <div className="grid grid-cols-[max-content_repeat(4,_44px)] gap-1 items-center">
        <div />
        {rows.map((c) => (
          <div key={`col-${c}`} className="text-[10px] text-center text-[#6A5799] font-bold">V{c}</div>
        ))}
        {rows.map((r) => (
          <>
            <div key={`row-${r}`} className="text-[10px] text-right text-[#6A5799] font-bold pr-1">T{r}</div>
            {rows.map((c) => {
              const p = r * c;
              const tier = tierForProduct(p);
              const isCase = r === threat && c === vuln;
              const meta = TIER_META[tier];
              return (
                <div
                  key={`cell-${r}-${c}`}
                  data-testid={`nd-risk-heatmap-${r}-${c}`}
                  data-case={isCase ? "1" : "0"}
                  className={`w-11 h-11 rounded-md flex items-center justify-center text-xs font-bold border ${
                    isCase
                      ? `${meta.pill} text-white border-black/20 ring-2 ring-offset-2 ring-[#3D1A78]`
                      : `${meta.bg} ${meta.text} border-[#E5E0EE]`
                  }`}
                  title={`Threat ${r} × Vulnerability ${c} = ${p}`}
                >
                  {p}
                </div>
              );
            })}
          </>
        ))}
      </div>
      <div className="flex flex-wrap gap-2 mt-3 text-[10px]">
        <span className="px-2 py-0.5 rounded-full bg-[#E6F4EC] text-[#1F5C3B] font-semibold">1-3 Low</span>
        <span className="px-2 py-0.5 rounded-full bg-[#FFF6E5] text-[#8A5B00] font-semibold">4-8 Medium</span>
        <span className="px-2 py-0.5 rounded-full bg-[#F8D7D7] text-[#B02A2A] font-semibold">9-12 High</span>
        <span className="px-2 py-0.5 rounded-full bg-[#F8D7D7] text-[#6E1616] font-semibold">13-16 Critical</span>
      </div>
    </div>
  );
}

export default function NDRiskAssessmentResult() {
  const { aid } = useParams();
  const location = useLocation();
  const [assessment, setAssessment] = useState(location.state?.assessment || null);
  const [loading, setLoading] = useState(!assessment);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (assessment) return;
    (async () => {
      try {
        const { data } = await api.get(`/nd-risk/assessment/${aid}`);
        setAssessment(data);
      } catch (err) {
        logError("Could not load assessment", err);
      } finally {
        setLoading(false);
      }
    })();
  }, [aid, assessment]);

  const download = async () => {
    if (!aid) return;
    setDownloading(true);
    try {
      const res = await api.get(`/nd-risk/assessment/${aid}/pdf`, {
        params: { sign: true },
        responseType: "blob",
      });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `nd-risk-assessment-${aid.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      logError("PDF download failed", err);
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return <AppShell><div className="p-10 text-sm text-[#4B4567] inline-flex items-center gap-2"><Loader2 className="animate-spin" size={14} /> Loading…</div></AppShell>;
  }
  if (!assessment) {
    return <AppShell><div className="p-10 text-sm text-[#B02A2A]">Assessment not found.</div></AppShell>;
  }

  const s = assessment.scoring || {};
  const tier = TIER_META[s.tier] || TIER_META.low;

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="nd-risk-result">
        <Link to="/dashboard" className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] hover:text-[#3D1A78] mb-4">
          <ArrowLeft size={12} /> Back to dashboard
        </Link>

        <header className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              ND Risk · Result
            </div>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mt-1">
              {assessment.target_name} × {assessment.coparent_name}
            </h1>
            <div className="text-xs text-[#6A5799] mt-1">
              Assessed {new Date(assessment.created_at).toLocaleString()} · ID {assessment.assessment_id}
            </div>
          </div>
          <button
            type="button"
            onClick={download}
            disabled={downloading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#3D1A78] text-white text-sm font-semibold disabled:opacity-60"
            data-testid="nd-risk-download-pdf"
          >
            {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            {downloading ? "Preparing…" : "Download PDF report"}
          </button>
        </header>

        <section className={`mt-6 rounded-3xl border-2 ${tier.bg} p-6`} data-testid="nd-risk-result-tier">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Overall risk tier
          </div>
          <div className="flex items-baseline gap-4 flex-wrap mt-1">
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full ${tier.pill} text-white text-sm font-bold`}
              data-testid="nd-risk-result-tier-pill"
            >
              {tier.label}
            </span>
            <span className={`text-2xl font-bold ${tier.text}`}>
              {s.total_score} / 16
            </span>
            <span className="text-xs text-[#4B4567]">
              Threat {s.threat_score} × Vulnerability {s.vulnerability_score}
            </span>
          </div>
        </section>

        <section className="mt-6 grid md:grid-cols-2 gap-6">
          <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Risk matrix
            </div>
            <div className="font-serif text-lg text-[#1A1330] mt-1 mb-3">
              Your case on the 4×4 grid
            </div>
            <Heatmap threat={s.threat_score} vuln={s.vulnerability_score} />
          </div>

          <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid="nd-risk-interventions">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              Required interventions
            </div>
            <div className="font-serif text-lg text-[#1A1330] mt-1 mb-3">
              For your {tier.label.toLowerCase()} tier
            </div>
            <ul className="space-y-2">
              {(s.interventions || []).map((item, i) => (
                <li
                  key={`iv-${i}-${item.slice(0, 20)}`}
                  className="flex items-start gap-2 text-sm text-[#1A1330]"
                  data-testid={`nd-risk-intervention-${i}`}
                >
                  <Square size={14} className="text-[#3D1A78] shrink-0 mt-0.5" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="mt-8" data-testid="nd-risk-timeline-section" id="timeline">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Assessment timeline
          </div>
          <div className="font-serif text-2xl text-[#1A1330] mt-1 mb-4">
            How your tier has changed over time
          </div>
          <NDRiskTimeline highlightId={assessment.assessment_id} />
        </section>

        <p className="mt-8 text-[11px] text-[#6A5799] italic">
          This report is informational preparation support only. It is not legal
          advice, medical diagnosis, or a substitute for a licensed professional.
          The PDF is designed to be brought to your mediator,
          attorney, or clinician — not to replace them.
        </p>
      </div>
    </AppShell>
  );
}
