import { TrendingUp, AlertTriangle, MessageCircle, ShieldCheck } from "lucide-react";

/**
 * Full-detail Family Report renderer used by both the authenticated
 * FamilyReport.jsx page and the public SharedFamilyReport.jsx viewer.
 * Visual language matches SharedCoParentingReport / SharedSpecialNeedsReport
 * one-to-one so all three reports feel like one product family.
 */

const OVERALL_TONE = {
  "Excellent Progress": { bg: "bg-[#E4F4EC]", text: "text-[#1F5C3B]", border: "border-[#B8DDC6]" },
  "Building Progress":  { bg: "bg-[#EFE9F9]", text: "text-[#3D1A78]", border: "border-[#CFC1EA]" },
  "Early Progress":     { bg: "bg-[#FEF1EC]", text: "text-[#C2481F]", border: "border-[#F0B6A0]" },
};

const SECTION_CHIP = {
  Excellent:           "text-[#1F5C3B] bg-[#E4F4EC] border-[#B8DDC6]",
  Good:                "text-[#3D1A78] bg-[#EFE9F9] border-[#CFC1EA]",
  Fair:                "text-[#8C5A2C] bg-[#FFF7E3] border-[#F5C147]",
  "Needs Improvement": "text-[#C2481F] bg-[#FEF1EC] border-[#F0B6A0]",
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
    <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8" data-testid="famrep-safety">
      <h2 className="font-serif text-xl text-[#1A1330] mb-2 flex items-center gap-2">
        <ShieldCheck size={16} className="text-[#3D1A78]" /> Communication Safety
      </h2>
      <span className={`inline-block text-[10px] font-bold px-2.5 py-1 rounded-full border ${SAFETY_CHIP[safety.level] || SAFETY_CHIP[3]}`}>
        Level {safety.level}: {safety.pathway_title}
      </span>
      {safety.pathway_headline && <div className="text-sm italic text-[#857E9C] mt-2">{safety.pathway_headline}</div>}
      {safety.pathway_summary && <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">{safety.pathway_summary}</p>}
      {(safety.recommendations || []).length > 0 && (
        <div className="mt-4">
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">Recommendations</div>
          <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
            {safety.recommendations.map((r, i) => <li key={i} data-testid={`famrep-safety-rec-${i}`}>{r}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function FullReportBlock({ title, block, unitLabel, testidPrefix }) {
  if (!block || !block.report) return null;
  const r = block.report;
  const tone = OVERALL_TONE[r.overall_rating] || OVERALL_TONE["Building Progress"];

  return (
    <div className="space-y-4" data-testid={`${testidPrefix}-block`}>
      <div className={`rounded-3xl border ${tone.border} ${tone.bg} p-6 sm:p-8`}>
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
          {block.framework || title}
        </div>
        <h2 className={`font-serif text-2xl leading-tight ${tone.text}`} data-testid={`${testidPrefix}-overall`}>
          {r.overall_rating || "Not enough data"}
        </h2>
        {r.overall_summary && <p className="text-sm text-[#1A1330] mt-3 leading-relaxed">{r.overall_summary}</p>}
      </div>

      {(r.strengths || []).length > 0 && (
        <div className="rounded-3xl border border-[#B8DDC6] bg-[#E4F4EC] p-6" data-testid={`${testidPrefix}-strengths`}>
          <div className="flex items-center gap-2 text-[#1F5C3B] font-bold text-xs uppercase tracking-[0.18em] mb-3">
            <TrendingUp size={14} /> Strengths
          </div>
          <ul className="space-y-2.5">
            {r.strengths.map((s) => (
              <li key={s.section_id} className="text-[#1A1330]" data-testid={`${testidPrefix}-strength-${s.section_id}`}>
                <div className="font-semibold">{s.title}</div>
                {s.detail && <div className="text-sm text-[#4B4567]">{s.detail}</div>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {(r.growth_areas || []).length > 0 && (
        <div className="rounded-3xl border border-[#F0B6A0] bg-[#FEF1EC] p-6" data-testid={`${testidPrefix}-growth`}>
          <div className="flex items-center gap-2 text-[#C2481F] font-bold text-xs uppercase tracking-[0.18em] mb-3">
            <AlertTriangle size={14} /> Priority focus areas
          </div>
          <ul className="space-y-3">
            {r.growth_areas.map((g) => (
              <li key={g.section_id} data-testid={`${testidPrefix}-growth-${g.section_id}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-[#1A1330]">{g.title}</span>
                  {g.rating && (
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${SECTION_CHIP[g.rating] || SECTION_CHIP.Fair}`}>
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

      {r.show_communication_toolkit && (r.communication_toolkit || []).length > 0 && (
        <div className="rounded-3xl border border-[#CFC1EA] bg-[#EFE9F9] p-6" data-testid={`${testidPrefix}-toolkit`}>
          <div className="flex items-center gap-2 text-[#3D1A78] font-bold text-xs uppercase tracking-[0.18em] mb-3">
            <MessageCircle size={14} /> Communication toolkit
          </div>
          <ul className="space-y-2.5">
            {r.communication_toolkit.map((tip, i) => (
              <li key={i} className="text-[#1A1330]" data-testid={`${testidPrefix}-tip-${i}`}>
                <div className="font-semibold">{tip.title}</div>
                {tip.detail && <div className="text-sm text-[#4B4567]">{tip.detail}</div>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {(r.sections || []).length > 0 && (
        <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8" data-testid={`${testidPrefix}-sections`}>
          <h3 className="font-serif text-lg text-[#1A1330] mb-4">{unitLabel}-by-{unitLabel.toLowerCase()} detail</h3>
          <div className="space-y-3">
            {r.sections.map((sec) => (
              <div key={sec.id} className="border border-[#E5E0EE] rounded-2xl p-4" data-testid={`${testidPrefix}-sec-${sec.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-0.5">
                      {unitLabel} {sec.number}
                    </div>
                    <div className="font-semibold text-[#1A1330]">{sec.name}</div>
                    {sec.goal && <div className="text-xs text-[#4B4567] mt-0.5">{sec.goal}</div>}
                  </div>
                  <div className="shrink-0 text-right">
                    {sec.rating ? (
                      <span className={`inline-block text-[10px] font-bold px-2.5 py-1 rounded-full border ${SECTION_CHIP[sec.rating] || SECTION_CHIP.Fair}`} data-testid={`${testidPrefix}-rating-${sec.id}`}>
                        {sec.rating}
                      </span>
                    ) : (
                      <span className="text-xs italic text-[#857E9C]">Not answered</span>
                    )}
                    {typeof sec.avg === "number" && <div className="text-[11px] text-[#857E9C] mt-1">Avg {sec.avg} / 4</div>}
                  </div>
                </div>
                {(sec.findings || []).length > 0 && (
                  <div className="mt-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">Findings</div>
                    <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
                      {sec.findings.map((f, i) => <li key={i}>{f}</li>)}
                    </ul>
                  </div>
                )}
                {(sec.recommendations || []).length > 0 && (
                  <div className="mt-3">
                    <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">Recommendations</div>
                    <ul className="text-sm text-[#1A1330] list-disc pl-4 space-y-0.5">
                      {sec.recommendations.map((f, i) => <li key={i}>{f}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {(r.next_steps || []).length > 0 && (
        <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid={`${testidPrefix}-next-steps`}>
          <h3 className="font-serif text-lg text-[#1A1330] mb-3">Recommended next steps</h3>
          <ol className="list-decimal pl-5 space-y-1.5 text-[#1A1330]">
            {r.next_steps.map((s, i) => <li key={i}>{s}</li>)}
          </ol>
        </div>
      )}
    </div>
  );
}

export function FamilyReportBody({ report }) {
  if (!report) return null;
  return (
    <div className="space-y-8" data-testid="famrep-body">
      <div className="rounded-3xl border border-[#E5E0EE] bg-[#F8F5FF] p-6 sm:p-8">
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
          Family Report · {report.included_sources?.length || 0}/3 sources
        </div>
        <h2 className="font-serif text-2xl text-[#1A1330]" data-testid="famrep-overall">
          {report.prepared_by ? `Prepared for ${report.prepared_by}` : "Your Family Report"}
        </h2>
        {report.overall_summary && <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">{report.overall_summary}</p>}
        {(report.missing_sources || []).length > 0 && (
          <div className="mt-3 text-xs italic text-[#8C5A2C]" data-testid="famrep-missing">
            Not yet completed: {report.missing_sources.join(", ")}
          </div>
        )}
      </div>

      <SafetyBlock safety={report.safety} />
      <FullReportBlock title="Co-Parenting Assessment" block={report.coparenting} unitLabel="Section" testidPrefix="famrep-cp" />
      <FullReportBlock title="Special Needs Co-Parenting Assessment" block={report.special_needs} unitLabel="Section" testidPrefix="famrep-sn" />

      {(report.combined_next_steps || []).length > 0 && (
        <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6" data-testid="famrep-combined-next-steps">
          <h2 className="font-serif text-xl text-[#1A1330] mb-3">Combined next steps across your assessments</h2>
          <ul className="space-y-2">
            {report.combined_next_steps.map((s, i) => (
              <li key={i} className="text-sm text-[#1A1330]" data-testid={`famrep-step-${i}`}>
                <span className="inline-block text-[10px] font-bold px-2 py-0.5 rounded-full border border-[#CFC1EA] bg-[#EFE9F9] text-[#3D1A78] mr-2">
                  {s.source}
                </span>
                {s.text}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-[11px] text-[#857E9C] italic text-center px-4">{report.disclaimer}</p>
    </div>
  );
}
