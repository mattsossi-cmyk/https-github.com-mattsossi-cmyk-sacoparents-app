/**
 * SpecialNeedsV2CompareView.jsx — Neutral side-by-side comparison.
 *
 * Category filter chips (All / Medical / Educational / Psychological) restrict
 * the visible pathways. Each item shows both parents' answers and a neutral
 * alignment pill.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { toast } from "sonner";
import { ArrowLeft, Download, Loader2, ShieldAlert, Sparkles } from "lucide-react";
import { logError } from "../lib/logger";
import ReportReviewNotice from "../components/ReportReviewNotice";

const ALIGN_STYLES = {
  aligned:        "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
  both_responded: "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
  close:          "bg-[#EEE9F7] text-[#3D1A78] border-[#D6CFE8]",
  one_only:       "bg-[#FBEDDA] text-[#8C5A2C] border-[#EDD5B0]",
  divergent:      "bg-[#F8D7D7] text-[#B02A2A] border-[#EFB4B4]",
  insufficient:   "bg-[#EEEAF3] text-[#6E6E82] border-[#D6CFE8]",
};

function AlignPill({ alignment, label }) {
  const cls = ALIGN_STYLES[alignment] || ALIGN_STYLES.insufficient;
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-semibold border ${cls}`}
      data-testid={`snc2-align-${alignment}`}>
      {label || alignment}
    </span>
  );
}

function LikertCell({ side }) {
  if (!side) return <span className="text-[#8471B3] italic">—</span>;
  if (side.value === "na") return <span>Not applicable / unknown</span>;
  if (typeof side.value === "number") {
    return <span><span className="font-semibold">{side.value}</span> — {side.label}</span>;
  }
  return <span className="text-[#8471B3] italic">—</span>;
}

function ValueCell({ item, side }) {
  const type = item.type;
  const sideObj = item[side] || {};
  if (type === "likert") return <LikertCell side={sideObj} />;
  if (type === "single") return <span>{sideObj.value || <span className="text-[#8471B3] italic">—</span>}</span>;
  if (type === "multi") {
    const arr = sideObj.value || [];
    if (!arr.length) return <span className="text-[#8471B3] italic">—</span>;
    return <ul className="list-disc pl-5">{arr.map((v, i) => <li key={i}>{v}</li>)}</ul>;
  }
  const v = sideObj.value || "";
  return v ? <span className="whitespace-pre-wrap">{v}</span> : <span className="text-[#8471B3] italic">—</span>;
}

function MultiBreakdown({ item, parentA, parentB }) {
  return (
    <div className="mt-2 text-xs space-y-1">
      {(item.both || []).length > 0 && (
        <div><span className="font-semibold text-[#1F5C3B]">Both selected:</span> {(item.both || []).join(", ")}</div>
      )}
      {(item.only_parent_a || []).length > 0 && (
        <div><span className="font-semibold text-[#8C5A2C]">Only {parentA}:</span> {(item.only_parent_a || []).join(", ")}</div>
      )}
      {(item.only_parent_b || []).length > 0 && (
        <div><span className="font-semibold text-[#8C5A2C]">Only {parentB}:</span> {(item.only_parent_b || []).join(", ")}</div>
      )}
    </div>
  );
}

export default function SpecialNeedsV2CompareView() {
  const { share_id: shareId } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [safetyBlocked, setSafetyBlocked] = useState(false);
  const [data, setData] = useState(null);
  const [category, setCategory] = useState(null); // null = All
  const [downloading, setDownloading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSafetyBlocked(false);
    try {
      const params = category ? { category } : {};
      const res = await api.get(`/snc2/compare/${shareId}`, { params });
      setData(res.data);
    } catch (err) {
      logError("snc2 compare view", err);
      const detail = err?.response?.data?.detail || "Could not load the comparison.";
      if (err?.response?.status === 403 && /safety/i.test(detail)) setSafetyBlocked(true);
      setError(detail);
    } finally {
      setLoading(false);
    }
  }, [shareId, category]);

  useEffect(() => { load(); }, [load]);

  const download = async () => {
    setDownloading(true);
    try {
      const params = category ? { category } : {};
      const res = await api.get(`/snc2/compare/${shareId}/pdf`, { responseType: "blob", params });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url; a.download = "SNC_Comparison.pdf";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (err) {
      logError("snc2 compare pdf", err);
      toast.error(err?.response?.data?.detail || "Could not download the PDF.");
    } finally { setDownloading(false); }
  };

  const availableCategories = useMemo(() => data?.comparison?.shared_pathways || [], [data]);
  const parentA = data?.comparison?.parent_a_name || "Parent A";
  const parentB = data?.comparison?.parent_b_name || "Parent B";
  const labels = data?.comparison?.alignment_labels || {};

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="snc2-compare-view-root">
        <Link to="/special-needs-v2/compare" className="inline-flex items-center gap-2 text-xs text-[#4B4567] underline mb-4" data-testid="snc2-compare-view-back">
          <ArrowLeft size={12} /> Back to comparisons
        </Link>
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">Co-Parent Comparison</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
          {parentA} <span className="text-[#8471B3]">·</span> {parentB}
        </h1>
        <p className="text-sm text-[#4B4567] mt-2 max-w-3xl italic">
          A neutral side-by-side view. Neither parent is labeled correct or wrong.
        </p>

        <ReportReviewNotice variant="comparison" className="mt-5" />

        {safetyBlocked && (
          <div className="mt-5 rounded-2xl border-2 border-[#B02A2A]/40 bg-[#F8D7D7]/40 p-4 sm:p-5" data-testid="snc2-compare-view-safety-block">
            <div className="flex items-start gap-3">
              <ShieldAlert className="text-[#B02A2A] shrink-0 mt-0.5" size={18} />
              <div className="text-sm text-[#4B4567]">
                Your Safety Assessment recommends a limited-contact pathway. Access to the comparison is paused.
                <div className="mt-2">
                  <Link to="/safety-assessment" className="underline text-[#B02A2A] font-semibold">Review Safety Assessment</Link>
                </div>
              </div>
            </div>
          </div>
        )}

        {loading && <div className="mt-6 text-sm text-[#4B4567]"><Loader2 className="animate-spin inline" size={14} /> Loading comparison…</div>}

        {!loading && error && !safetyBlocked && (
          <div className="mt-6 rounded-2xl border border-[#E5E0EE] bg-white p-5 text-sm text-[#B02A2A]" data-testid="snc2-compare-view-error">
            {error}
          </div>
        )}

        {!loading && data?.comparison && (
          <>
            <div className="mt-5 rounded-3xl border border-[#E5E0EE] bg-white p-5 shadow-sm flex flex-wrap items-center justify-between gap-3" data-testid="snc2-compare-summary-bar">
              <div className="text-xs text-[#4B4567]">
                <span className="font-semibold text-[#1A1330]">{data.comparison.summary?.total_items || 0}</span> questions compared.
                <span className="mx-2">·</span>
                <span className="text-[#1F5C3B] font-semibold">{data.comparison.summary?.aligned_pct || 0}% aligned</span>
                <span className="mx-2">·</span>
                <span className="text-[#B02A2A] font-semibold">{data.comparison.summary?.divergent_pct || 0}% different views</span>
              </div>
              <button onClick={download} disabled={downloading} data-testid="snc2-compare-download-pdf"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60">
                {downloading ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />} Download PDF
              </button>
            </div>

            {(data.comparison.highlights || []).length > 0 && (
              <section className="mt-5 rounded-3xl border border-[#B5DFC5] bg-[#F1F9F4] p-5 sm:p-7 shadow-sm" data-testid="snc2-compare-highlights">
                <div className="flex items-center gap-2 text-[#1F5C3B]">
                  <Sparkles size={16} />
                  <span className="text-[10px] uppercase tracking-[0.22em] font-bold">Where you already agree</span>
                </div>
                <h2 className="font-serif text-2xl text-[#1A1330] mt-1 mb-1">
                  {(data.comparison.highlights || []).length === 1
                    ? "1 thing you already agree on"
                    : `${(data.comparison.highlights || []).length} things you already agree on`}
                </h2>
                <p className="text-xs text-[#4B4567] mb-4 italic">
                  A neutral snapshot of your strongest shared ground. Consider starting your co-parent conversation here.
                </p>
                <ol className="space-y-3">
                  {(data.comparison.highlights || []).map((h, i) => (
                    <li key={`${h.step_id}-${h.pathway_id}-${h.item_id}`}
                      data-testid={`snc2-compare-highlight-${i}`}
                      className="rounded-2xl border border-[#B5DFC5] bg-white p-4">
                      <div className="flex items-start gap-3">
                        <div className="shrink-0 w-7 h-7 rounded-full bg-[#1F5C3B] text-white text-xs font-bold flex items-center justify-center">{i + 1}</div>
                        <div className="flex-1">
                          <div className="text-sm font-semibold text-[#1A1330]">{h.prompt}</div>
                          <div className="text-sm text-[#1F5C3B] mt-1">{h.summary}</div>
                          <div className="text-[10px] uppercase tracking-[0.16em] text-[#4B4567] mt-2">
                            Step {h.step_number} · {h.step_name} · {h.pathway_name}
                          </div>
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
            )}

            {/* Category filter */}
            <div className="mt-4 flex flex-wrap items-center gap-2" data-testid="snc2-compare-category-filter">
              <span className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mr-2">Filter</span>
              {[
                { id: null, label: "All shared" },
                { id: "medical", label: "Medical" },
                { id: "educational", label: "Educational" },
                { id: "psychological", label: "Psychological" },
              ].map((c) => {
                const enabled = c.id === null || availableCategories.includes(c.id);
                const active = category === c.id;
                return (
                  <button key={c.id || "all"} onClick={() => enabled && setCategory(c.id)} disabled={!enabled}
                    data-testid={`snc2-compare-filter-${c.id || "all"}`}
                    className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${
                      active
                        ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                        : enabled
                          ? "bg-white text-[#3D1A78] border-[#E5E0EE] hover:bg-[#EEE9F7]"
                          : "bg-[#F5F3FA] text-[#B5AEC7] border-[#EEEAF3] cursor-not-allowed"
                    }`}>
                    {c.label}
                  </button>
                );
              })}
            </div>

            {/* Steps */}
            {(data.comparison.steps || []).map((step) => {
              const hasContent = (step.pathways || []).some((p) => (p.items || []).length > 0);
              if (!hasContent) return null;
              return (
                <section key={step.id} className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm" data-testid={`snc2-compare-step-${step.id}`}>
                  <h2 className="font-serif text-2xl text-[#1A1330] mb-3">Step {step.number}. {step.name}</h2>
                  {(step.pathways || []).map((path) => (
                    <div key={path.id} className="mt-4">
                      <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-2">{path.name}</div>
                      <div className="space-y-4">
                        {(path.items || []).map((item) => (
                          <div key={item.id} className="rounded-2xl border border-[#EEE9F7] bg-[#FCFBFE] p-4" data-testid={`snc2-compare-item-${step.id}-${path.id}-${item.id}`}>
                            <div className="flex items-start justify-between gap-3 flex-wrap">
                              <div className="text-sm text-[#1A1330] pr-2 flex-1">{item.prompt}</div>
                              <AlignPill alignment={item.alignment} label={labels[item.alignment] || item.alignment} />
                            </div>
                            <div className="mt-3 grid sm:grid-cols-2 gap-3">
                              <div>
                                <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">{parentA}</div>
                                <div className="text-sm text-[#1A1330]"><ValueCell item={item} side="parent_a" /></div>
                              </div>
                              <div>
                                <div className="text-[10px] uppercase tracking-[0.18em] font-semibold text-[#3D1A78] mb-1">{parentB}</div>
                                <div className="text-sm text-[#1A1330]"><ValueCell item={item} side="parent_b" /></div>
                              </div>
                            </div>
                            {item.type === "multi" && (
                              <MultiBreakdown item={item} parentA={parentA} parentB={parentB} />
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </section>
              );
            })}

            <p className="text-[11px] text-[#4B4567] mt-8 italic max-w-3xl">
              This comparison is neutral and does not determine parental fitness, provide legal advice,
              or diagnose. Either parent can revoke consent at any time from the Comparisons hub.
            </p>
          </>
        )}
      </div>
    </AppShell>
  );
}
