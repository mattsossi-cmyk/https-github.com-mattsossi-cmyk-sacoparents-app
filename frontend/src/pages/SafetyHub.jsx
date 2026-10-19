import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ShieldCheck, MessageSquareText, HeartHandshake, Phone } from "lucide-react";
import api from "@/lib/api";
import { QuickExitBar } from "@/components/QuickExit";
import { CrisisResourcesButton } from "@/components/CrisisResources";
import { Button } from "@/components/ui/button";

const CARDS = [
  { key: "safety", icon: ShieldCheck, title: "Private Safety & Power Dynamics", body: "Screens for coercive control, boundary violations, physical or emotional safety risks, and conflict history.", cta: "Start Private Screening", to: "safety-screening" },
  { key: "communication", icon: MessageSquareText, title: "Communication Readiness", body: "Helps identify the communication approach that feels safest for your family, such as direct messaging, written-only, or structured third-party communication.", cta: "Check Communication Readiness", to: "communication-readiness" },
  { key: "inclusive", icon: HeartHandshake, title: "Inclusive Family Support", body: "Behavior-focused screening that honors all family structures.", cta: "View Inclusive Care", to: "safety-screening" },
];
const EMERGENCY = [["Immediate danger?", "Call 911"], ["National DV Hotline", "1-800-799-SAFE (7233)"], ["Text", "START to 88788"], ["Crisis Lifeline", "988"]];

export default function SafetyHub() {
  const { id } = useParams();
  const [st, setSt] = useState(null);
  useEffect(() => { api.get(`/joint/reports/${id}/safety-screening`).then((r) => setSt(r.data)).catch(() => setSt({})); }, [id]);
  const mine = st?.my_role ? st.roles?.[st.my_role] : null;
  return (
    <div className="min-h-screen bg-[#f6f3fb] font-jakarta text-slate-900 motion-reduce:transition-none" data-testid="safety-hub">
      <QuickExitBar variant="red" label="Confidential Assessment Area" />
      <header className="border-b border-[#3D1A78]/10 bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-4 sm:px-6">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#3D1A78] text-white" aria-hidden="true"><HeartHandshake className="h-6 w-6" /></span>
          <div><p className="text-lg font-bold leading-tight text-[#3D1A78]" data-testid="hub-brand">SA CoParents</p><p className="text-xs text-slate-600" data-testid="hub-subtitle">Safety &amp; Communication Readiness Assessment</p></div>
          <CrisisResourcesButton version={mine?.version} className="ml-auto" />
          <Link to={`/joint/${id}`} className="text-xs font-semibold text-[#3D1A78] underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#3D1A78]" data-testid="hub-back">Back to case</Link>
        </div>
      </header>
      <main className="mx-auto max-w-5xl space-y-8 px-4 py-8 sm:px-6">
        <section className="rounded-2xl border border-[#3D1A78]/15 bg-white p-5 shadow-sm" data-testid="hub-banner" aria-label="Inclusive support">
          <p className="text-base font-bold text-[#3D1A78] md:text-lg" data-testid="hub-banner-heading">Designed for All Co-Parents</p>
          <p className="mt-1 text-sm text-slate-700" data-testid="hub-banner-text">Private, behavior-focused safety questions for every family structure, including non-binary and LGBTQ+ co-parents.</p>
        </section>
        <section>
          <h1 className="text-4xl font-bold tracking-tight text-[#3D1A78] sm:text-5xl" data-testid="hub-title">Family Safety &amp; Readiness</h1>
          <p className="mt-2 text-base text-slate-600 md:text-lg" data-testid="hub-title-sub">Assessments are completed individually and kept strictly confidential.</p>
        </section>
        <section className="grid grid-cols-1 gap-5 md:grid-cols-3" data-testid="hub-cards" aria-label="Assessments">
          {CARDS.map((c) => {
            const done = c.key === "communication" ? mine?.communication_received : mine?.received;
            return (
              <article key={c.key} className="flex flex-col rounded-2xl border border-[#3D1A78]/15 bg-white p-6 shadow-sm transition-transform duration-200 hover:-translate-y-0.5 motion-reduce:transform-none" data-testid={`hub-card-${c.key}`}>
                <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#3D1A78]/10 text-[#3D1A78]" aria-hidden="true"><c.icon className="h-6 w-6" /></span>
                <h2 className="mt-4 text-base font-bold text-slate-900 md:text-lg">{c.title}</h2>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600">{c.body}</p>
                {done && <p className="mt-3 text-xs font-semibold text-emerald-700" data-testid={`hub-card-${c.key}-done`}>Received privately — you can review or update any time.</p>}
                <Link to={`/joint/${id}/${c.to}`} className="mt-5 focus-visible:outline-none"><Button className="w-full bg-[#3D1A78] hover:bg-[#2f1460] focus-visible:ring-2 focus-visible:ring-[#3D1A78] focus-visible:ring-offset-2" data-testid={`hub-card-${c.key}-btn`}>{c.cta}</Button></Link>
              </article>
            );
          })}
        </section>
        <section className="text-center">
          <Link to={`/joint/${id}/safety-screening`}><Button size="lg" className="h-auto min-h-12 w-full max-w-md whitespace-normal rounded-full bg-[#3D1A78] px-6 py-3 text-base font-bold leading-snug hover:bg-[#2f1460] focus-visible:ring-2 focus-visible:ring-[#3D1A78] focus-visible:ring-offset-2 sm:w-auto sm:px-8" data-testid="hub-begin-btn">Begin Confidential Safety Assessment</Button></Link>
          <p className="mt-3 text-sm text-slate-600" data-testid="hub-privacy-line">Your answers are never shown to the other parent and are shared only with the professionals assigned to your case.</p>
        </section>
        <section className="rounded-2xl bg-red-700 p-5 text-white" data-testid="hub-emergency" aria-label="Emergency resources">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {EMERGENCY.map(([k, v]) => <p key={k} className="flex items-center gap-2 text-sm"><Phone className="h-4 w-4 shrink-0" aria-hidden="true" /><span><span className="font-semibold">{k}:</span> {v}</span></p>)}
          </div>
        </section>
      </main>
    </div>
  );
}
