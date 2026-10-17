import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Download, Loader2, AlertTriangle, TrendingUp, MessageCircle,
  ShieldCheck, ArrowUpRight, ExternalLink, Share2,
} from "lucide-react";
import { toast } from "sonner";

/**
 * Public shared Co-Parenting report viewer.
 * Reads the SIGNED share token (no auth required) and renders a branded page.
 * Matches the same visual language as the in-app SpecialNeedsV3 results page.
 */

const RATING_TONE = {
  "Excellent Progress": { bg: "bg-[#E4F4EC]", text: "text-[#1F5C3B]", border: "border-[#B8DDC6]", chip: "text-[#1F5C3B] bg-[#E4F4EC] border-[#B8DDC6]" },
  "Building Progress":  { bg: "bg-[#EFE9F9]", text: "text-[#3D1A78]", border: "border-[#CFC1EA]", chip: "text-[#3D1A78] bg-[#EFE9F9] border-[#CFC1EA]" },
  "Early Progress":     { bg: "bg-[#FEF1EC]", text: "text-[#C2481F]", border: "border-[#F0B6A0]", chip: "text-[#C2481F] bg-[#FEF1EC] border-[#F0B6A0]" },
};

const SECTION_TONE = {
  Excellent:           { chip: "text-[#1F5C3B] bg-[#E4F4EC] border-[#B8DDC6]" },
  Good:                { chip: "text-[#3D1A78] bg-[#EFE9F9] border-[#CFC1EA]" },
  Fair:                { chip: "text-[#8C5A2C] bg-[#FFF7E3] border-[#F5C147]" },
  "Needs Improvement": { chip: "text-[#C2481F] bg-[#FEF1EC] border-[#F0B6A0]" },
};

function Banner({ overall, sharedBy, generatedAt }) {
  const tone = RATING_TONE[overall] || RATING_TONE["Building Progress"];
  const date = generatedAt ? new Date(generatedAt).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) : null;
  return (
    <div className={`rounded-3xl border ${tone.border} ${tone.bg} p-6 sm:p-8`} data-testid="sharedcp-banner">
      <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
        Co-Parenting Assessment · shared report
      </div>
      <h1 className={`font-serif text-3xl sm:text-4xl leading-tight ${tone.text}`} data-testid="sharedcp-overall">
        {overall || "Not enough data"}
      </h1>
      {sharedBy && (
        <p className="text-sm text-[#4B4567] mt-3">
          Shared by <span className="font-semibold text-[#1A1330]" data-testid="sharedcp-sharedby">{sharedBy}</span>
          {date && <> · {date}</>}
        </p>
      )}
    </div>
  );
}

function EmptyBlockNotice({ label }) {
  return (
    <div className="text-xs italic text-[#6E6787]">
      {label} isn&apos;t included in this shared view.
    </div>
  );
}

function SharedCoParentingReport() {
  const { token } = useParams();
  const [state, setState] = useState({ loading: true, error: null, data: null });

  const backendUrl = process.env.REACT_APP_BACKEND_URL;
  const pdfUrl = `${backendUrl}/api/coparenting/report/shared/${token}?format=pdf`;

  const load = useCallback(async () => {
    if (!token) {
      setState({ loading: false, error: "Missing share token.", data: null });
      return;
    }
    try {
      const res = await fetch(`${backendUrl}/api/coparenting/report/shared/${token}?format=json`, {
        method: "GET",
        credentials: "omit",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setState({ loading: false, error: body.detail || "This shared link is no longer valid.", data: null });
        return;
      }
      const data = await res.json();
      setState({ loading: false, error: null, data });
    } catch {
      setState({ loading: false, error: "Couldn't load the shared report. Please try again.", data: null });
    }
  }, [token, backendUrl]);

  useEffect(() => { load(); }, [load]);

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      toast.success("Link copied to clipboard");
    } catch {
      toast.error("Couldn't copy — please copy from the address bar.");
    }
  };

  if (state.loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[#F8F5FF] via-white to-white grid place-items-center px-6" data-testid="sharedcp-loading">
        <div className="flex items-center gap-2 text-[#3D1A78]">
          <Loader2 size={16} className="animate-spin" /> Loading shared report…
        </div>
      </div>
    );
  }

  if (state.error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[#F8F5FF] via-white to-white grid place-items-center px-6" data-testid="sharedcp-error">
        <div className="max-w-md w-full rounded-3xl border border-[#F0B6A0] bg-[#FEF1EC] p-6 text-center">
          <div className="text-[#C2481F] font-bold mb-1">Link unavailable</div>
          <p className="text-sm text-[#4B4567]">{state.error}</p>
          <Link
            to="/"
            className="mt-4 inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline"
            data-testid="sharedcp-home-link"
          >
            <ArrowUpRight size={14} /> Visit SA CoParents
          </Link>
        </div>
      </div>
    );
  }

  const { report, scores, shared_by: sharedBy, generated_at: generatedAt, excluded_sections: excluded = [] } = state.data || {};
  const ex = new Set(excluded);
  const hasSections = (report?.sections || []).length > 0;

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#F8F5FF] via-white to-white">
      {/* Top bar — thin brand strip so the shared page feels like a product */}
      <header className="sticky top-0 z-10 bg-white/90 backdrop-blur border-b border-[#E5E0EE]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2" data-testid="sharedcp-brand">
            <img src="/icon-256.png" alt="SA CoParents" className="w-7 h-7 rounded-md" />
            <span className="font-serif text-[15px] text-[#1A1330]">SA CoParents</span>
          </Link>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={copyLink}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3D1A78] border border-[#E5E0EE] hover:border-[#3D1A78] rounded-full px-3 py-1.5"
              data-testid="sharedcp-copy-btn"
            >
              <Share2 size={12} /> Copy link
            </button>
            <a
              href={pdfUrl}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-[#3D1A78] hover:bg-[#2D0F63] rounded-full px-3 py-1.5"
              data-testid="sharedcp-pdf-btn"
            >
              <Download size={12} /> PDF
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {!ex.has("overall") ? (
          <Banner overall={report?.overall_rating} sharedBy={sharedBy} generatedAt={generatedAt} />
        ) : (
          <EmptyBlockNotice label="Overall rating" />
        )}

        {!ex.has("overall") && report?.overall_summary && (
          <p className="text-[15px] text-[#1A1330] leading-relaxed">{report.overall_summary}</p>
        )}

        {/* Strengths */}
        {!ex.has("strengths") && (report?.strengths || []).length > 0 && (
          <div className="rounded-3xl border border-[#B8DDC6] bg-[#E4F4EC] p-6" data-testid="sharedcp-strengths">
            <div className="flex items-center gap-2 text-[#1F5C3B] font-bold text-xs uppercase tracking-[0.18em] mb-3">
              <TrendingUp size={14} /> Strengths
            </div>
            <ul className="space-y-2.5">
              {report.strengths.map((s) => (
                <li key={s.section_id} className="text-[#1A1330]" data-testid={`sharedcp-strength-${s.section_id}`}>
                  <div className="font-semibold">{s.title}</div>
                  {s.detail && <div className="text-sm text-[#4B4567]">{s.detail}</div>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Growth areas */}
        {!ex.has("growth_areas") && (report?.growth_areas || []).length > 0 && (
          <div className="rounded-3xl border border-[#F0B6A0] bg-[#FEF1EC] p-6" data-testid="sharedcp-growth">
            <div className="flex items-center gap-2 text-[#C2481F] font-bold text-xs uppercase tracking-[0.18em] mb-3">
              <AlertTriangle size={14} /> Priority focus areas
            </div>
            <ul className="space-y-3">
              {report.growth_areas.map((g) => (
                <li key={g.section_id} data-testid={`sharedcp-growth-${g.section_id}`}>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-[#1A1330]">{g.title}</span>
                    {g.rating && (
                      <span className={`text-[0.625rem] font-bold px-2 py-0.5 rounded-full border ${(SECTION_TONE[g.rating] || SECTION_TONE.Fair).chip}`}>
                        {g.rating}
                      </span>
                    )}
                  </div>
                  {g.why_it_matters && <div className="text-sm text-[#4B4567] mt-1"><span className="font-semibold text-[#1A1330]">Why:</span> {g.why_it_matters}</div>}
                  {g.first_step && <div className="text-sm text-[#4B4567] mt-0.5"><span className="font-semibold text-[#1A1330]">First step:</span> {g.first_step}</div>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Communication toolkit */}
        {!ex.has("communication_toolkit") && (report?.communication_toolkit || []).length > 0 && (
          <div className="rounded-3xl border border-[#CFC1EA] bg-[#EFE9F9] p-6" data-testid="sharedcp-toolkit">
            <div className="flex items-center gap-2 text-[#3D1A78] font-bold text-xs uppercase tracking-[0.18em] mb-3">
              <MessageCircle size={14} /> Communication toolkit
            </div>
            <ul className="space-y-2.5">
              {report.communication_toolkit.map((tip, i) => (
                <li key={`tip-${i}-${(tip || "").slice(0, 30)}`} className="text-[#1A1330]" data-testid={`sharedcp-tip-${i}`}>
                  <div className="font-semibold">{tip.title}</div>
                  {tip.detail && <div className="text-sm text-[#4B4567]">{tip.detail}</div>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Section-by-section detail */}
        {!ex.has("sections") && hasSections && (
          <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8" data-testid="sharedcp-sections">
            <h2 className="font-serif text-xl text-[#1A1330] mb-4">Section-by-section detail</h2>
            <div className="space-y-3">
              {report.sections.map((sec) => {
                const tone = SECTION_TONE[sec.rating] || SECTION_TONE.Fair;
                return (
                  <div key={sec.id} className="border border-[#E5E0EE] rounded-2xl p-4" data-testid={`sharedcp-sec-${sec.id}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-0.5">
                          Section {sec.number}
                        </div>
                        <div className="font-semibold text-[#1A1330]">{sec.name}</div>
                        {sec.goal && <div className="text-xs text-[#4B4567] mt-0.5">{sec.goal}</div>}
                      </div>
                      <div className="shrink-0 text-right">
                        {sec.rating ? (
                          <span className={`inline-block text-[0.625rem] font-bold px-2.5 py-1 rounded-full border ${tone.chip}`} data-testid={`sharedcp-rating-${sec.id}`}>
                            {sec.rating}
                          </span>
                        ) : (
                          <span className="text-xs italic text-[#6E6787]">Not answered</span>
                        )}
                        {typeof sec.avg === "number" && (
                          <div className="text-[0.6875rem] text-[#6E6787] mt-1">Avg {sec.avg} / 4</div>
                        )}
                      </div>
                    </div>
                    {(sec.findings || []).length > 0 && (
                      <div className="mt-3">
                        <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">Findings</div>
                        <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
                          {sec.findings.map((f, i) => <li key={`f-${i}-${(f || "").slice(0, 30)}`}>{f}</li>)}
                        </ul>
                      </div>
                    )}
                    {(sec.recommendations || []).length > 0 && (
                      <div className="mt-3">
                        <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">Recommendations</div>
                        <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
                          {sec.recommendations.map((f, i) => <li key={`r-${i}-${(f || "").slice(0, 30)}`}>{f}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Next steps */}
        {!ex.has("next_steps") && (report?.next_steps || []).length > 0 && (
          <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid="sharedcp-next-steps">
            <h2 className="font-serif text-xl text-[#1A1330] mb-3">Recommended next steps</h2>
            <ol className="list-decimal pl-5 space-y-1.5 text-[#1A1330]">
              {report.next_steps.map((s, i) => (
                <li key={`step-${i}-${(s || "").slice(0, 30)}`} data-testid={`sharedcp-step-${i}`}>{s}</li>
              ))}
            </ol>
          </div>
        )}

        {/* Aggregate score summary (small strip, if not everything hidden) */}
        {!ex.has("sections") && scores && (
          <div className="rounded-3xl bg-[#F8F5FF] border border-[#E5E0EE] p-4 text-xs text-[#4B4567] flex items-center gap-2" data-testid="sharedcp-progress">
            <ShieldCheck size={14} className="text-[#3D1A78]" />
            Based on {scores.answered_count || 0} of {scores.total_count || 67} answered questions.
          </div>
        )}

        {/* CTA back to app */}
        <div className="rounded-3xl bg-[#1A1330] text-white p-6 sm:p-8 mt-6" data-testid="sharedcp-cta">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#CFC1EA] mb-2">
            Powered by SA CoParents
          </div>
          <div className="font-serif text-2xl leading-tight">
            Prepare for co-parenting decisions with clarity.
          </div>
          <p className="text-sm text-[#CFC1EA] mt-2 max-w-lg">
            Take the assessment yourself, prepare for mediation, and get a
            child-focused, deterministic report you can share with your co-parent,
            mediator, or Parenting Facilitator.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#1A1330] bg-white hover:bg-[#EFE9F9] rounded-full px-4 py-2"
              data-testid="sharedcp-cta-primary"
            >
              Explore SA CoParents <ExternalLink size={12} />
            </Link>
            <Link
              to="/signup"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-white border border-[#CFC1EA] hover:bg-[#3D1A78] rounded-full px-4 py-2"
              data-testid="sharedcp-cta-signup"
            >
              Take the assessment
            </Link>
          </div>
        </div>

        <p className="text-[0.6875rem] text-[#6E6787] italic text-center px-4">
          {report?.disclaimer || "Educational reflection tool. Not a diagnosis, custody evaluation, or legal advice."}
        </p>
      </main>
    </div>
  );
}

export default SharedCoParentingReport;
