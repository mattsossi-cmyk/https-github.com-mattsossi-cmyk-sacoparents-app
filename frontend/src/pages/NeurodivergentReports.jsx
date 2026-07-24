import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, RefreshCw, Loader2, Download, Share2, Copy, Baby, Handshake,
  AlertTriangle, ListChecks, Compass, Table,
} from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import DemoModeBanner from "../components/DemoModeBanner";
import SpecialNeedsScoreDashboard from "../components/SpecialNeedsScoreDashboard";
import { api, API } from "../lib/api";

/**
 * Special Needs Coordination Report — v2, 6-part care plan.
 *
 * Structure:
 *   1. Child Profile           2. Areas of parent agreement
 *   3. Coordination gaps       4. Priority levels
 *   5. Recommended structure   6. Action-plan table
 *
 * Actions: Regenerate · Download PDF · Copy share link.
 */

const PRIORITY_COPY = [
  { key: "immediate",  label: "Immediate",       accent: "text-[#C2481F]", bg: "bg-[#FEF1EC]" },
  { key: "thirty_day", label: "Within 30 days",  accent: "text-[#3D1A78]", bg: "bg-[#EFE9F9]" },
  { key: "longer_term", label: "Longer-term",    accent: "text-[#1F5C3B]", bg: "bg-[#E4F4EC]" },
];

function ReportSection({ icon: Icon, title, testid, children }) {
  return (
    <section
      className="rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8"
      data-testid={testid}
    >
      <div className="flex items-center gap-2 mb-3">
        <div className="w-9 h-9 rounded-full bg-[#F1EBFA] grid place-items-center text-[#3D1A78]">
          <Icon size={16} />
        </div>
        <h3 className="font-serif text-xl text-[#1A1330]">{title}</h3>
      </div>
      {children}
    </section>
  );
}

function BulletList({ items, testid }) {
  if (!items?.length) return <div className="text-sm text-[#857E9C] italic">Nothing to show yet.</div>;
  return (
    <ul className="list-disc pl-5 space-y-1.5 text-sm text-[#1A1330]" data-testid={testid}>
      {items.map((it, i) => (
        <li key={`${String(it).slice(0, 24)}-${i}`}>{it}</li>
      ))}
    </ul>
  );
}

function ObjectBullets({ items, testid }) {
  if (!items?.length) return <div className="text-sm text-[#857E9C] italic">None flagged.</div>;
  return (
    <ul className="space-y-2 text-sm text-[#1A1330]" data-testid={testid}>
      {items.map((it, i) => (
        <li key={`${(it.title || "").slice(0, 24)}-${i}`} className="flex gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#3D1A78] shrink-0 mt-2" />
          <div>
            <span className="font-semibold text-[#1A1330]">{it.title}</span>
            {it.title && it.detail && " — "}
            <span className="text-[#4B4567]">{it.detail}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function ActionTable({ rows }) {
  if (!rows?.length) {
    return <div className="text-sm text-[#857E9C] italic">No action rows yet.</div>;
  }
  return (
    <div className="overflow-x-auto" data-testid="sn-action-table">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left border-b border-[#E5E0EE]">
            <th className="py-2 pr-3 font-bold text-[#3D1A78] text-xs uppercase tracking-[0.14em]">Child&apos;s need</th>
            <th className="py-2 pr-3 font-bold text-[#3D1A78] text-xs uppercase tracking-[0.14em]">Agreed action</th>
            <th className="py-2 pr-3 font-bold text-[#3D1A78] text-xs uppercase tracking-[0.14em]">Responsible</th>
            <th className="py-2 pr-3 font-bold text-[#3D1A78] text-xs uppercase tracking-[0.14em]">Info shared by</th>
            <th className="py-2 font-bold text-[#3D1A78] text-xs uppercase tracking-[0.14em]">Review date</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-[#F0EBF7] align-top">
              <td className="py-3 pr-3 text-[#1A1330] font-semibold">{r.need}</td>
              <td className="py-3 pr-3 text-[#4B4567]">{r.action}</td>
              <td className="py-3 pr-3 text-[#4B4567]">{r.responsible}</td>
              <td className="py-3 pr-3 text-[#4B4567]">{r.channel}</td>
              <td className="py-3 text-[#4B4567]">{r.review}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function NeurodivergentReports() {
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/neurodivergent/report");
      setDoc(data?.report_id ? data : null);
    } catch {
      setDoc(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const generate = async (isRegen) => {
    if (isRegen && !window.confirm("Regenerate the report from your current answers?")) return;
    setBusy(true);
    try {
      const { data } = await api.post("/neurodivergent/report/generate");
      setDoc(data);
      toast.success(isRegen ? "Report refreshed." : "Report ready.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not generate the report.");
    } finally {
      setBusy(false);
    }
  };

  const downloadPdf = async () => {
    try {
      const res = await fetch(`${API}/neurodivergent/report/pdf`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("pdf failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `SN_Care_Plan_${doc?.child_name || "child"}.pdf`.replace(/[^\w.-]/g, "_");
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Couldn't download the PDF. Please try again.");
    }
  };

  const copyShareLink = async () => {
    if (!doc?.report_id) return;
    try {
      const { data } = await api.post(`/neurodivergent/report/${doc.report_id}/share-link`);
      const full = `${window.location.origin}${data.path}`;
      await navigator.clipboard.writeText(full);
      toast.success("Shareable PDF link copied.");
    } catch {
      toast.error("Couldn't create the share link.");
    }
  };

  const r = doc?.report || null;

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
        <Link
          to="/neurodivergent"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="nd-reports-back-link"
        >
          <ArrowLeft size={14} /> Back to the questions
        </Link>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="eyebrow text-[#3D1A78]">Special Needs Coordination Report</div>
            <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-1" data-testid="nd-reports-title">
              A care plan for {doc?.child_name || "your child"}
            </h1>
            <p className="text-[#4B4567] mt-2 max-w-2xl">
              Six-part care plan built from your answers. Share it with your
              pediatrician, therapist, school team, mediator, or attorney.
              Not diagnostic. Not legal advice.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {doc && (
              <>
                <button
                  onClick={downloadPdf}
                  className="inline-flex items-center gap-2 text-sm border border-[#E5E0EE] rounded-full px-4 py-2 hover:bg-[#F5F2FA] text-[#3D1A78] font-semibold"
                  data-testid="nd-download-pdf-btn"
                >
                  <Download size={14} /> Download PDF
                </button>
                <button
                  onClick={copyShareLink}
                  className="inline-flex items-center gap-2 text-sm border border-[#E5E0EE] rounded-full px-4 py-2 hover:bg-[#F5F2FA] text-[#3D1A78] font-semibold"
                  data-testid="nd-share-link-btn"
                >
                  <Share2 size={14} /> Copy share link
                </button>
              </>
            )}
            <button
              onClick={() => generate(!!doc)}
              disabled={busy}
              className="inline-flex items-center gap-2 text-sm bg-[#3D1A78] text-white rounded-full px-4 py-2 hover:bg-[#2D0F63] disabled:opacity-60"
              data-testid="nd-regenerate-btn"
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              {doc ? (busy ? "Regenerating…" : "Regenerate") : (busy ? "Generating…" : "Generate report")}
            </button>
          </div>
        </div>

        <div className="mt-6">
          <DemoModeBanner />
        </div>

        <div className="mt-8">
          <SpecialNeedsScoreDashboard />
        </div>

        {loading ? (
          <div className="mt-10 text-[#857E9C]" data-testid="nd-reports-loading">Loading…</div>
        ) : !r ? (
          <div
            className="mt-10 rounded-3xl border border-dashed border-[#C1B4E0] bg-white p-8 text-center"
            data-testid="nd-reports-empty"
          >
            <p className="text-[#1A1330] font-medium">
              No report yet. Once you&apos;ve answered the assessment, generate your
              6-part care plan.
            </p>
            <button
              onClick={() => generate(false)}
              disabled={busy}
              className="inline-flex items-center gap-2 mt-5 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-medium hover:bg-[#2A1256] disabled:opacity-60"
              data-testid="nd-generate-first-btn"
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              Generate the report
            </button>
          </div>
        ) : (
          <div className="mt-8 space-y-6">
            <ReportSection icon={Baby} title="1. Child profile" testid="nd-sec-profile">
              {r.child_profile?.summary && (
                <p className="text-sm text-[#1A1330] leading-relaxed mb-3">{r.child_profile.summary}</p>
              )}
              {r.child_profile?.strengths?.length > 0 && (
                <>
                  <div className="text-xs uppercase tracking-[0.14em] font-bold text-[#3D1A78] mt-3 mb-1">Strengths &amp; interests</div>
                  <BulletList items={r.child_profile.strengths} testid="nd-strengths" />
                </>
              )}
              {r.child_profile?.what_helps?.length > 0 && (
                <>
                  <div className="text-xs uppercase tracking-[0.14em] font-bold text-[#3D1A78] mt-3 mb-1">What helps them feel safe and successful</div>
                  <BulletList items={r.child_profile.what_helps} testid="nd-what-helps" />
                </>
              )}
              {r.child_profile?.support_needs?.length > 0 && (
                <>
                  <div className="text-xs uppercase tracking-[0.14em] font-bold text-[#3D1A78] mt-3 mb-1">Support needs</div>
                  <BulletList items={r.child_profile.support_needs} testid="nd-support-needs" />
                </>
              )}
            </ReportSection>

            <ReportSection icon={Handshake} title="2. Areas of parent agreement" testid="nd-sec-agreement">
              <ObjectBullets items={r.agreement_areas} testid="nd-agreement-list" />
            </ReportSection>

            <ReportSection icon={AlertTriangle} title="3. Coordination gaps" testid="nd-sec-gaps">
              <ObjectBullets items={r.coordination_gaps} testid="nd-gaps-list" />
            </ReportSection>

            <ReportSection icon={ListChecks} title="4. Priority levels" testid="nd-sec-priorities">
              <div className="grid gap-3 sm:grid-cols-3">
                {PRIORITY_COPY.map((p) => (
                  <div key={p.key} className={`rounded-2xl ${p.bg} p-4`}>
                    <div className={`text-xs uppercase tracking-[0.14em] font-bold ${p.accent} mb-2`}>{p.label}</div>
                    <BulletList items={r.priorities?.[p.key] || []} testid={`nd-prio-${p.key}`} />
                  </div>
                ))}
              </div>
            </ReportSection>

            <ReportSection icon={Compass} title="5. Recommended co-parenting structure" testid="nd-sec-structure">
              <p className="text-sm text-[#1A1330] leading-relaxed">{r.structure_reasoning}</p>
            </ReportSection>

            <ReportSection icon={Table} title="6. Special Needs parenting-plan worksheet" testid="nd-sec-action-plan">
              <ActionTable rows={r.action_plan} />
            </ReportSection>

            <p className="text-xs text-[#857E9C] italic text-center px-6">{r.disclaimer}</p>
          </div>
        )}
      </div>
    </AppShell>
  );
}
