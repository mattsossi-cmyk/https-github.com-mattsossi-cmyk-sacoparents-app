import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Download, Loader2, ArrowUpRight, ExternalLink, Share2, ShieldCheck,
  TrendingUp, AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";

const RATING_CHIP = {
  "Excellent Progress": "text-[#1F5C3B] bg-[#E4F4EC] border-[#B8DDC6]",
  "Building Progress":  "text-[#3D1A78] bg-[#EFE9F9] border-[#CFC1EA]",
  "Early Progress":     "text-[#C2481F] bg-[#FEF1EC] border-[#F0B6A0]",
};

const SAFETY_CHIP = {
  1: "text-[#C2481F] bg-[#FEF1EC] border-[#F0B6A0]",
  2: "text-[#8C5A2C] bg-[#FFF7E3] border-[#F5C147]",
  3: "text-[#3D1A78] bg-[#EFE9F9] border-[#CFC1EA]",
  4: "text-[#1F5C3B] bg-[#E4F4EC] border-[#B8DDC6]",
};

function SafetyBlock({ safety }) {
  if (!safety) return null;
  return (
    <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid="sharedfam-safety">
      <h3 className="font-serif text-xl text-[#1A1330] mb-2 flex items-center gap-2">
        <ShieldCheck size={16} className="text-[#3D1A78]" /> Communication Safety
      </h3>
      <span className={`inline-block text-[10px] font-bold px-2.5 py-1 rounded-full border ${SAFETY_CHIP[safety.level] || SAFETY_CHIP[3]}`}>
        Level {safety.level}: {safety.pathway_title}
      </span>
      {safety.pathway_headline && <div className="text-sm italic text-[#857E9C] mt-2">{safety.pathway_headline}</div>}
      {safety.pathway_summary && <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">{safety.pathway_summary}</p>}
      {(safety.recommendations || []).length > 0 && (
        <div className="mt-4">
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">Recommendations</div>
          <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
            {safety.recommendations.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function AssessmentBlock({ title, block, testid }) {
  if (!block) return null;
  return (
    <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid={testid}>
      <h3 className="font-serif text-xl text-[#1A1330] mb-2">{title}</h3>
      {block.overall_rating && (
        <span className={`inline-block text-[10px] font-bold px-2.5 py-1 rounded-full border ${RATING_CHIP[block.overall_rating] || RATING_CHIP["Building Progress"]}`}>
          {block.overall_rating}
        </span>
      )}
      {block.overall_summary && <p className="text-sm text-[#4B4567] mt-3 leading-relaxed">{block.overall_summary}</p>}
      {(block.strengths || []).length > 0 && (
        <div className="mt-4">
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#1F5C3B] mb-1 flex items-center gap-1"><TrendingUp size={12} /> Strengths</div>
          <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
            {block.strengths.slice(0, 3).map((s) => (
              <li key={s.section_id}><span className="font-semibold">{s.title}</span>{s.detail ? ` — ${s.detail}` : ""}</li>
            ))}
          </ul>
        </div>
      )}
      {(block.growth_areas || []).length > 0 && (
        <div className="mt-4">
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#C2481F] mb-1 flex items-center gap-1"><AlertTriangle size={12} /> Priority focus</div>
          <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
            {block.growth_areas.slice(0, 3).map((g) => (
              <li key={g.section_id}><span className="font-semibold">{g.title}</span>{g.rating ? ` (${g.rating})` : ""}{g.first_step ? ` — ${g.first_step}` : ""}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function SharedFamilyReport() {
  const { token } = useParams();
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const backendUrl = process.env.REACT_APP_BACKEND_URL;
  const pdfUrl = `${backendUrl}/api/family-report/shared/${token}?format=pdf`;

  const load = useCallback(async () => {
    if (!token) return setState({ loading: false, error: "Missing share token.", data: null });
    try {
      const res = await fetch(`${backendUrl}/api/family-report/shared/${token}?format=json`, { credentials: "omit" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        return setState({ loading: false, error: body.detail || "This shared link is no longer valid.", data: null });
      }
      const data = await res.json();
      setState({ loading: false, error: null, data });
    } catch {
      setState({ loading: false, error: "Couldn't load the shared Family Report.", data: null });
    }
  }, [token, backendUrl]);

  useEffect(() => { load(); }, [load]);

  const copyLink = async () => {
    try { await navigator.clipboard.writeText(window.location.href); toast.success("Link copied to clipboard"); }
    catch { toast.error("Couldn't copy — please copy from the address bar."); }
  };

  if (state.loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[#F8F5FF] via-white to-white grid place-items-center px-6" data-testid="sharedfam-loading">
        <div className="flex items-center gap-2 text-[#3D1A78]"><Loader2 size={16} className="animate-spin" /> Loading Family Report…</div>
      </div>
    );
  }
  if (state.error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[#F8F5FF] via-white to-white grid place-items-center px-6" data-testid="sharedfam-error">
        <div className="max-w-md w-full rounded-3xl border border-[#F0B6A0] bg-[#FEF1EC] p-6 text-center">
          <div className="text-[#C2481F] font-bold mb-1">Link unavailable</div>
          <p className="text-sm text-[#4B4567]">{state.error}</p>
          <Link to="/" className="mt-4 inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline"><ArrowUpRight size={14} /> Visit SA CoParents</Link>
        </div>
      </div>
    );
  }

  const { report, shared_by: sharedBy, generated_at: generatedAt } = state.data || {};
  const date = generatedAt ? new Date(generatedAt).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) : null;

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#F8F5FF] via-white to-white">
      <header className="sticky top-0 z-10 bg-white/90 backdrop-blur border-b border-[#E5E0EE]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2" data-testid="sharedfam-brand">
            <img src="/icon-256.png" alt="SA CoParents" className="w-7 h-7 rounded-md" />
            <span className="font-serif text-[15px] text-[#1A1330]">SA CoParents</span>
          </Link>
          <div className="flex items-center gap-2">
            <button onClick={copyLink} className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3D1A78] border border-[#E5E0EE] hover:border-[#3D1A78] rounded-full px-3 py-1.5" data-testid="sharedfam-copy-btn">
              <Share2 size={12} /> Copy link
            </button>
            <a href={pdfUrl} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-[#3D1A78] hover:bg-[#2D0F63] rounded-full px-3 py-1.5" data-testid="sharedfam-pdf-btn">
              <Download size={12} /> PDF
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div className="rounded-3xl border border-[#CFC1EA] bg-[#EFE9F9] p-6 sm:p-8" data-testid="sharedfam-banner">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
            Family Report · {report?.included_sources?.length || 0}/3 sources
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl leading-tight text-[#1A1330]" data-testid="sharedfam-title">
            Your Family Report
          </h1>
          {sharedBy && (
            <p className="text-sm text-[#4B4567] mt-3">
              Shared by <span className="font-semibold text-[#1A1330]" data-testid="sharedfam-sharedby">{sharedBy}</span>
              {date && <> · {date}</>}
            </p>
          )}
        </div>

        {report?.overall_summary && <p className="text-[15px] text-[#1A1330] leading-relaxed">{report.overall_summary}</p>}
        {(report?.missing_sources || []).length > 0 && (
          <div className="text-xs italic text-[#8C5A2C]" data-testid="sharedfam-missing">
            Not yet completed: {report.missing_sources.join(", ")}
          </div>
        )}

        <SafetyBlock safety={report?.safety} />
        <AssessmentBlock title="Co-Parenting Assessment" block={report?.coparenting} testid="sharedfam-cp" />
        <AssessmentBlock title="Special Needs Assessment" block={report?.special_needs} testid="sharedfam-sn" />

        {(report?.combined_next_steps || []).length > 0 && (
          <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid="sharedfam-next-steps">
            <h2 className="font-serif text-xl text-[#1A1330] mb-3">Combined next steps</h2>
            <ul className="space-y-2">
              {report.combined_next_steps.map((s, i) => (
                <li key={i} className="text-sm text-[#1A1330]" data-testid={`sharedfam-step-${i}`}>
                  <span className="inline-block text-[10px] font-bold px-2 py-0.5 rounded-full border border-[#CFC1EA] bg-[#EFE9F9] text-[#3D1A78] mr-2">
                    {s.source}
                  </span>
                  {s.text}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="rounded-3xl bg-[#1A1330] text-white p-6 sm:p-8 mt-6" data-testid="sharedfam-cta">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#CFC1EA] mb-2">Powered by SA CoParents</div>
          <div className="font-serif text-2xl leading-tight">One document. Three assessments. Real clarity.</div>
          <p className="text-sm text-[#CFC1EA] mt-2 max-w-lg">
            Build your own Family Report by completing the Co-Parenting, Special Needs, and Safety assessments — then share a single branded PDF with your co-parent, mediator, or attorney.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#1A1330] bg-white hover:bg-[#EFE9F9] rounded-full px-4 py-2" data-testid="sharedfam-cta-primary">
              Explore SA CoParents <ExternalLink size={12} />
            </Link>
            <Link to="/signup" className="inline-flex items-center gap-1.5 text-sm font-semibold text-white border border-[#CFC1EA] hover:bg-[#3D1A78] rounded-full px-4 py-2" data-testid="sharedfam-cta-signup">
              Take the assessments
            </Link>
          </div>
        </div>

        <p className="text-[11px] text-[#857E9C] italic text-center px-4">{report?.disclaimer || "Educational reflection tool. Not a diagnosis, custody evaluation, or legal advice."}</p>
      </main>
    </div>
  );
}
