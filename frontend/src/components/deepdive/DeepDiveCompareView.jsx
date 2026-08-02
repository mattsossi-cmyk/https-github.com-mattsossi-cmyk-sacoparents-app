/**
 * DeepDiveCompareView — reusable side-by-side comparison view for any
 * deep-dive pathway. Accepts a `pathway` prop with API prefix + labels.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import AppShell from "../AppShell";
import { api } from "../../lib/api";
import { toast } from "sonner";
import { ArrowLeft, Download, Loader2, ShieldAlert, Sparkles, TrendingUp, Star, MessageCircle, HelpCircle } from "lucide-react";
import { logError } from "../../lib/logger";
import AlignmentMilestoneCelebration from "./AlignmentMilestoneCelebration";
import ReportReviewNotice from "../ReportReviewNotice";
import ReportProvenanceFooter from "../ReportProvenanceFooter";

const ALIGN_STYLES = {
  aligned:        "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
  both_responded: "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
  close:          "bg-[#EEE9F7] text-[#3D1A78] border-[#D6CFE8]",
  one_only:       "bg-[#FBEDDA] text-[#8C5A2C] border-[#EDD5B0]",
  divergent:      "bg-[#F8D7D7] text-[#B02A2A] border-[#EFB4B4]",
  insufficient:   "bg-[#EEEAF3] text-[#6E6E82] border-[#D6CFE8]",
};

function AlignPill({ alignment, label, testidPrefix }) {
  const cls = ALIGN_STYLES[alignment] || ALIGN_STYLES.insufficient;
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-semibold border ${cls}`}
      data-testid={`${testidPrefix}-align-${alignment}`}>
      {label || alignment}
    </span>
  );
}

function LikertCell({ side }) {
  if (!side) return <span className="text-[#8471B3] italic">—</span>;
  if (side.value === "na") return <span>Not applicable / unknown</span>;
  if (typeof side.value === "number") {
    return <span><span className="font-semibold">{side.value}</span></span>;
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
    return <ul className="list-disc pl-5">{arr.map((v) => <li key={v}>{v}</li>)}</ul>;
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

function AlignmentList({ testid, title, icon, tint, intro, emptyLabel, items, renderRow }) {
  const count = items?.length || 0;
  return (
    <div className={`rounded-3xl border-2 ${tint.border} ${tint.bg} p-5 shadow-sm`} data-testid={testid}>
      <div className={`text-[10px] uppercase tracking-[0.22em] font-bold ${tint.text} flex items-center gap-2`}>
        {icon} {title}
        <span className="ml-auto text-[10px] font-normal opacity-70" data-testid={`${testid}-count`}>{count}</span>
      </div>
      <p className="text-xs text-[#4B4567] italic mt-1 mb-3">{intro}</p>
      {count === 0 ? (
        <div className="text-xs text-[#857E9C] italic" data-testid={`${testid}-empty`}>{emptyLabel}</div>
      ) : (
        <ol className="space-y-2.5" data-testid={`${testid}-list`}>
          {items.map((r) => (
            <li
              key={`${r.section_id}-${r.item_id}`}
              className="bg-white rounded-xl border border-[#EEE9F7] p-3"
              data-testid={`${testid}-item-${r.section_id}-${r.item_id}`}
            >
              {renderRow(r)}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export default function DeepDiveCompareView({ pathway }) {
  // pathway = { testidPrefix, eyebrow, apiPrefix, hubRoute, hubLabel, downloadFilename }
  const { share_id: shareId } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [safetyBlocked, setSafetyBlocked] = useState(false);
  const [data, setData] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const t = pathway.testidPrefix;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSafetyBlocked(false);
    try {
      const res = await api.get(`${pathway.apiPrefix}/${shareId}`);
      setData(res.data);
      // Load timeline (non-blocking — the /view request itself created a
      // snapshot server-side if one was needed).
      try {
        const tl = await api.get(`${pathway.apiPrefix}/${shareId}/timeline`);
        setTimeline(tl.data || null);
      } catch (tlErr) {
        logError(`${t} timeline`, tlErr);
      }
    } catch (err) {
      logError(`${t} view`, err);
      const detail = err?.response?.data?.detail || "Could not load the comparison.";
      if (err?.response?.status === 403 && /safety/i.test(detail)) setSafetyBlocked(true);
      setError(detail);
    } finally {
      setLoading(false);
    }
  }, [shareId, pathway.apiPrefix, t]);

  useEffect(() => { load(); }, [load]);

  const download = async () => {
    setDownloading(true);
    try {
      const res = await api.get(`${pathway.apiPrefix}/${shareId}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url; a.download = pathway.downloadFilename || "DeepDive_Comparison.pdf";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (err) {
      logError(`${t} pdf`, err);
      toast.error(err?.response?.data?.detail || "Could not download the PDF.");
    } finally { setDownloading(false); }
  };

  const parentA = data?.comparison?.parent_a_name || "Parent A";
  const parentB = data?.comparison?.parent_b_name || "Parent B";
  const labels = data?.comparison?.alignment_labels || {};

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid={`${t}-view-root`}>
        <Link to={pathway.hubRoute} className="inline-flex items-center gap-2 text-xs text-[#4B4567] underline mb-4" data-testid={`${t}-view-back`}>
          <ArrowLeft size={12} /> {pathway.hubLabel}
        </Link>
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">{pathway.eyebrow}</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
          {parentA} <span className="text-[#8471B3]">·</span> {parentB}
        </h1>
        <p className="text-sm text-[#4B4567] mt-2 max-w-3xl italic">
          A neutral side-by-side view. Neither parent is labeled correct or wrong.
        </p>

        <ReportReviewNotice variant="comparison" className="mt-5" />

        {safetyBlocked && (
          <div className="mt-5 rounded-2xl border-2 border-[#B02A2A]/40 bg-[#F8D7D7]/40 p-4 sm:p-5" data-testid={`${t}-view-safety-block`}>
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
          <div className="mt-6 rounded-2xl border border-[#E5E0EE] bg-white p-5 text-sm text-[#B02A2A]" data-testid={`${t}-view-error`}>
            {error}
          </div>
        )}

        {!loading && data?.comparison && (
          <>
            <div className="mt-5 rounded-3xl border border-[#E5E0EE] bg-white p-5 shadow-sm flex flex-wrap items-center justify-between gap-3" data-testid={`${t}-summary-bar`}>
              <div className="text-xs text-[#4B4567]">
                <span className="font-semibold text-[#1A1330]">{data.comparison.summary?.total_items || 0}</span> questions compared.
                <span className="mx-2">·</span>
                <span className="text-[#1F5C3B] font-semibold">{data.comparison.summary?.aligned_pct || 0}% aligned</span>
                <span className="mx-2">·</span>
                <span className="text-[#B02A2A] font-semibold">{data.comparison.summary?.divergent_pct || 0}% different views</span>
              </div>
              <button onClick={download} disabled={downloading} data-testid={`${t}-download-pdf`}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60">
                {downloading ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />} Download PDF
              </button>
            </div>

            {timeline && timeline.latest_milestones && timeline.latest_milestones.length > 0 && (
              <AlignmentMilestoneCelebration
                milestone={Math.max(...timeline.latest_milestones)}
                snapshotId={timeline.latest_snapshot_id}
                productLabel={timeline.product_label}
                testidPrefix={t}
              />
            )}

            {timeline && timeline.count > 1 && (
              <section className="mt-5 rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-7 shadow-sm" data-testid={`${t}-timeline`}>
                <div className="flex items-center gap-2 text-[#3D1A78]">
                  <TrendingUp size={16} />
                  <span className="text-[10px] uppercase tracking-[0.22em] font-bold">Alignment over time</span>
                </div>
                <div className="mt-1 flex flex-wrap items-baseline gap-3">
                  <h2 className="font-serif text-2xl text-[#1A1330]" data-testid={`${t}-timeline-headline`}>
                    {timeline.latest_aligned_pct}% aligned today
                  </h2>
                  {timeline.delta_aligned_pct !== 0 && (
                    <span
                      className={`text-sm font-semibold ${timeline.delta_aligned_pct > 0 ? "text-[#1F5C3B]" : "text-[#B02A2A]"}`}
                      data-testid={`${t}-timeline-delta`}
                    >
                      {timeline.delta_aligned_pct > 0 ? "▲" : "▼"} {Math.abs(timeline.delta_aligned_pct)} pts since {new Date(timeline.snapshots[0].created_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
                <p className="text-xs text-[#4B4567] italic mt-1 mb-4">
                  {timeline.count} snapshot{timeline.count === 1 ? "" : "s"} · a new one is captured whenever either parent updates their assessment.
                </p>

                <div className="flex items-end gap-1.5 h-24" data-testid={`${t}-timeline-bars`}>
                  {timeline.series.map((s, i) => {
                    const h = Math.max(6, Math.round((s.aligned_pct || 0) * 0.9));
                    const isLatest = i === timeline.series.length - 1;
                    return (
                      <div key={i} className="flex-1 flex flex-col items-center justify-end" data-testid={`${t}-timeline-bar-${i}`}>
                        <div
                          className={`w-full rounded-t ${isLatest ? "bg-[#3D1A78]" : "bg-[#8471B3]"}`}
                          style={{ height: `${h}%` }}
                          title={`${new Date(s.created_at).toLocaleDateString()} — ${s.aligned_pct}% aligned`}
                        />
                        <div className="text-[9px] text-[#4B4567] mt-1">{s.aligned_pct}%</div>
                      </div>
                    );
                  })}
                </div>

                <ol className="mt-5 space-y-2 max-h-52 overflow-y-auto text-xs" data-testid={`${t}-timeline-list`}>
                  {[...timeline.snapshots].reverse().map((s) => {
                    const summary = s.summary || {};
                    return (
                      <li key={s.snapshot_id} className="flex items-center gap-3 rounded-xl border border-[#EEE9F7] bg-[#FCFBFE] px-3 py-2">
                        <div className="text-[#4B4567] w-28 shrink-0">{new Date(s.created_at).toLocaleDateString()}</div>
                        <div className="text-[#1A1330] font-semibold">{summary.aligned_pct || 0}% aligned</div>
                        <div className="text-[#B02A2A]">{summary.divergent_pct || 0}% different</div>
                        <div className="text-[#857E9C] ml-auto">{summary.total_items || 0} items</div>
                      </li>
                    );
                  })}
                </ol>
              </section>
            )}

            {/* Mediation-ready alignment lists (Shared Priorities / Discussion / Questions) */}
            {(data.comparison.shared_priorities?.length
              || data.comparison.discussion_points?.length
              || data.comparison.mediation_questions?.length) > 0 && (
              <section className="mt-6 grid gap-4 lg:grid-cols-3" data-testid={`${t}-alignment-lists`}>
                <AlignmentList
                  testid={`${t}-shared-priorities`}
                  title="Shared Priorities"
                  icon={<Star size={14} />}
                  tint={{ bg: "bg-[#F1F9F4]", border: "border-[#B5DFC5]", text: "text-[#1F5C3B]" }}
                  emptyLabel="No clear shared priorities yet — a great next step is answering more likert items."
                  intro="What you both already flagged as important."
                  items={data.comparison.shared_priorities || []}
                  renderRow={(r) => (
                    <>
                      <div className="text-[10px] uppercase tracking-[0.14em] text-[#4B4567]">Section {r.section_number} · {r.section_name}</div>
                      <div className="text-sm text-[#1A1330] font-semibold mt-0.5">{r.prompt}</div>
                      <div className="text-xs text-[#1F5C3B] mt-1">{r.reason}</div>
                    </>
                  )}
                />
                <AlignmentList
                  testid={`${t}-discussion-points`}
                  title="Points for Discussion"
                  icon={<MessageCircle size={14} />}
                  tint={{ bg: "bg-[#F5F1FB]", border: "border-[#D6CFE8]", text: "text-[#3D1A78]" }}
                  emptyLabel="No partial-alignment items — either you're perfectly synced or clearly on different pages."
                  intro="Close-but-not-identical items to sync on."
                  items={data.comparison.discussion_points || []}
                  renderRow={(r) => (
                    <>
                      <div className="text-[10px] uppercase tracking-[0.14em] text-[#4B4567]">Section {r.section_number} · {r.section_name}</div>
                      <div className="text-sm text-[#1A1330] font-semibold mt-0.5">{r.prompt}</div>
                      <div className="text-xs text-[#3D1A78] mt-1">{r.reason}</div>
                    </>
                  )}
                />
                <AlignmentList
                  testid={`${t}-mediation-questions`}
                  title="Questions for Mediation"
                  icon={<HelpCircle size={14} />}
                  tint={{ bg: "bg-[#FBEDDA]", border: "border-[#EDD5B0]", text: "text-[#8C5A2C]" }}
                  emptyLabel="No divergent items to escalate — nothing needs a mediator's help right now."
                  intro="Divergent items, neutralized as questions."
                  items={data.comparison.mediation_questions || []}
                  renderRow={(r) => (
                    <>
                      <div className="text-[10px] uppercase tracking-[0.14em] text-[#4B4567]">Section {r.section_number} · {r.section_name}</div>
                      <div className="text-sm text-[#1A1330] mt-0.5 italic">"{r.question}"</div>
                    </>
                  )}
                />
              </section>
            )}

            {(data.comparison.highlights || []).length > 0 && (
              <section className="mt-5 rounded-3xl border border-[#B5DFC5] bg-[#F1F9F4] p-5 sm:p-7 shadow-sm" data-testid={`${t}-highlights`}>
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
                  A neutral snapshot of your strongest shared ground.
                </p>
                <ol className="space-y-3">
                  {(data.comparison.highlights || []).map((h, i) => (
                    <li key={`${h.section_id}-${h.item_id}`}
                      data-testid={`${t}-highlight-${i}`}
                      className="rounded-2xl border border-[#B5DFC5] bg-white p-4">
                      <div className="flex items-start gap-3">
                        <div className="shrink-0 w-7 h-7 rounded-full bg-[#1F5C3B] text-white text-xs font-bold flex items-center justify-center">{i + 1}</div>
                        <div className="flex-1">
                          <div className="text-sm font-semibold text-[#1A1330]">{h.prompt}</div>
                          <div className="text-sm text-[#1F5C3B] mt-1">{h.summary}</div>
                          <div className="text-[10px] uppercase tracking-[0.16em] text-[#4B4567] mt-2">
                            Section {h.section_number} · {h.section_name}
                          </div>
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
            )}

            {(data.comparison.sections || []).map((sec) => (
              <section key={sec.id} className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm" data-testid={`${t}-section-${sec.id}`}>
                <h2 className="font-serif text-2xl text-[#1A1330] mb-1">Section {sec.number}. {sec.name}</h2>
                {sec.purpose && <p className="text-xs text-[#8471B3] italic mb-3">{sec.purpose}</p>}
                <div className="space-y-4">
                  {(sec.items || []).map((item) => (
                    <div key={item.id} className="rounded-2xl border border-[#EEE9F7] bg-[#FCFBFE] p-4" data-testid={`${t}-item-${sec.id}-${item.id}`}>
                      <div className="flex items-start justify-between gap-3 flex-wrap">
                        <div className="text-sm text-[#1A1330] pr-2 flex-1">{item.prompt}</div>
                        <AlignPill alignment={item.alignment} label={labels[item.alignment] || item.alignment} testidPrefix={t} />
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
              </section>
            ))}

            <ReportProvenanceFooter variant="comparison" className="mt-8" />

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
