import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Download, ExternalLink } from "lucide-react";
import api from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { SampleTour, useSampleTour, TourButton, FOUNDATION_TOUR } from "@/components/SampleTour";

const Bullets = ({ items, testId }) => (
  <ul className="space-y-2" data-testid={testId}>{(items || []).map((t, i) => <li key={i} className="relative pl-6 text-sm before:absolute before:left-0.5 before:top-1.5 before:h-2.5 before:w-2.5 before:rounded-full before:bg-teal-600">{t}</li>)}</ul>
);

const Sec = ({ n, title, children }) => (
  <section className="mt-7" data-testid={`foundation-section-${n}`}>
    <div className="flex items-center gap-3"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#4b2a7b] text-sm font-bold text-white">{n}</span><h2 className="font-display text-xl font-bold text-[#2f174f]">{title}</h2></div>
    <div className="my-3 h-px bg-[#ddd7e6]" />
    {children}
  </section>
);

const Focus = ({ label, title, text }) => (
  <div className="rounded-xl border border-[#ddd7e6] bg-gradient-to-br from-[#f8f4fc] to-[#eef9f9] p-5">
    <p className="text-[11px] font-bold uppercase tracking-widest text-teal-600">{label}</p>
    {title && <p className="mt-1 font-display text-lg text-[#4b2a7b]">{title}</p>}
    <p className="mt-2 text-sm leading-relaxed">{text}</p>
  </div>
);

const Banner = ({ right }) => (
  <div className="flex items-center justify-between bg-gradient-to-r from-[#2f174f] to-[#4b2a7b] px-8 py-6 text-white">
    <div className="flex items-center gap-3"><span className="h-12 w-12 rounded-xl bg-white" style={{ background: "linear-gradient(90deg,#4b2a7b 50%,#159a9c 50%)" }} /><div><p className="font-display text-2xl font-bold">SA CoParents</p><p className="text-[10px] uppercase tracking-[2px] opacity-85">Foundation Statement</p></div></div>
    <p className="text-right text-[10px] uppercase tracking-[2px] opacity-90 whitespace-pre-line">{right}</p>
  </div>
);

export default function SampleFoundationStatement() {
  const [d, setD] = useState(null);
  const [error, setError] = useState("");
  const tour = useSampleTour(!!d, "sa-foundation-sample-tour-seen");
  useEffect(() => { api.get("/joint/sample-foundation-statement").then(({ data }) => setD(data)).catch(() => setError("The sample statement could not be loaded.")); }, []);
  const pdf = `${process.env.REACT_APP_BACKEND_URL}/api/joint/sample-foundation-statement/pdf`;
  return (
    <div className="min-h-screen bg-[#f5f5f7]" data-testid="sample-foundation-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-3">
          <Link to="/samples" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="sample-foundation-back-link"><ArrowLeft className="h-4 w-4" /> Samples</Link>
          <span className="hidden sm:block"><BrandLogo size="text-xl" /></span>
          <div className="flex flex-wrap gap-2">
            <TourButton onClick={tour.start} testId="foundation-tour-start-btn" />
            <Button variant="outline" size="sm" asChild data-testid="sample-foundation-viewpdf-link"><a href={`${pdf}?inline=1`} target="_blank" rel="noopener noreferrer"><ExternalLink className="h-4 w-4 mr-1" /> View PDF</a></Button>
            <Button size="sm" asChild data-testid="sample-foundation-pdf-link"><a href={pdf} download><Download className="h-4 w-4 mr-1" /> Download PDF</a></Button>
          </div>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-10 text-[#2d2d34]">
        <div className="mb-6 rounded-lg border border-[#4b2a7b]/30 bg-[#4b2a7b]/5 p-4 text-sm" data-testid="sample-foundation-banner"><strong className="text-[#4b2a7b]">Sample — fictional data.</strong> A parent's Child-Focused Foundation Statement as written in the SA CoParents parent app and imported into Align's joint Co-Parenting Agreement.</div>
        {error && <p className="text-sm text-red-700" data-testid="sample-foundation-error">{error}</p>}
        {tour.open && d && <SampleTour steps={FOUNDATION_TOUR} storageKey="sa-foundation-sample-tour-seen" onDone={tour.close} label="How a parent writes this" prefix="foundation-tour" />}
        {d && (
          <div className="overflow-hidden rounded-lg bg-white shadow-lg" data-testid="foundation-document">
            <Banner right={"Child-Focused\nParent Report"} />
            <div className="border-b border-[#ddd7e6] px-8 py-7">
              <p className="text-[11px] font-bold uppercase tracking-[2px] text-teal-600">SA CoParents Parent Report</p>
              <h1 className="mt-1 font-display text-3xl sm:text-4xl font-bold text-[#2f174f]" data-testid="foundation-title">Child-Focused Foundation Statement</h1>
              <p className="mt-1 text-[#6d6875]">A parent's statement of goals, priorities, concerns and commitments for their child.</p>
            </div>
            <div className="grid gap-3 px-8 py-5 sm:grid-cols-3">
              {[["Parent", d.parent_name], ["Child", d.child_name], ["Statement Date", d.statement_date]].map(([l, v]) => <div key={l} className="rounded-lg border border-[#eee7f5] bg-[#f4f0fa] p-4"><p className="text-[9px] font-bold uppercase tracking-widest text-[#4b2a7b]">{l}</p><p className="mt-1 font-display text-lg">{v}</p></div>)}
            </div>
            <div className="mx-8 mb-6 rounded-md border-l-4 border-teal-600 bg-[#eaf7f7] p-4 text-sm"><strong className="text-teal-800">Purpose of This Statement</strong><br />{d.purpose}</div>
            <div className="px-8 pb-10">
              <Sec n={1} title="Shared Purpose"><div className="rounded-lg border border-[#ddd7e6] bg-[#faf9fc] p-4 text-sm leading-relaxed">{d.shared_purpose}</div></Sec>
              <Sec n={2} title="My Vision for My Child"><Focus label="Child at the Center" title={`The future I want for ${d.child_short}`} text={d.vision} /></Sec>
              <Sec n={3} title="Parenting Priorities"><Bullets items={d.priorities} testId="foundation-priorities" /></Sec>
              <Sec n={4} title="Understanding My Child">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="rounded-lg border border-[#ddd7e6] p-4"><p className="font-display font-bold text-[#4b2a7b]">My Child's Strengths</p><p className="mt-2 text-sm leading-relaxed">{d.strengths}</p></div>
                  <div className="rounded-lg border border-[#ddd7e6] p-4"><p className="font-display font-bold text-[#4b2a7b]">My Child's Current Needs</p><div className="mt-2"><Bullets items={d.needs} /></div></div>
                </div>
              </Sec>
              <Sec n={5} title="Areas of Concern"><div className="rounded-lg border border-[#ddd7e6] bg-[#faf9fc] p-4"><Bullets items={d.concerns} /></div></Sec>
              <Sec n={6} title="Wellness, Phones & Social Media"><div className="rounded-lg border border-[#ddd7e6] bg-[#faf9fc] p-4"><Bullets items={d.wellness_tech} testId="foundation-wellness-tech" /></div></Sec>
              <Sec n={7} title="What My Child May Need"><Focus label="Child-Focused Reflection" text={d.child_may_need} /></Sec>
              <Sec n={8} title="Commitments I Am Making"><div className="rounded-md border-l-4 border-[#4b2a7b] bg-[#f8f6fb] p-4"><Bullets items={d.commitments} /></div></Sec>
              <Sec n={9} title="Goals for the Next 12 Months"><Bullets items={d.goals} /></Sec>
              <Sec n={10} title="My Child's Future"><Focus label="Looking Forward" text={d.future} /></Sec>
              <Sec n={11} title="Parent Commitment"><div className="rounded-md border-l-4 border-[#4b2a7b] bg-[#f8f6fb] p-4 text-sm"><strong>My Foundation Statement</strong><p className="mt-2 leading-relaxed">{d.parent_commitment}</p></div></Sec>
              <div className="mt-12 grid gap-10 sm:grid-cols-2">{["Parent Signature", "Date"].map((l) => <div key={l} className="border-t border-[#444] pt-2 text-[9px] uppercase tracking-widest text-[#6d6875]">{l}</div>)}</div>
              <div className="mt-10 grid gap-6 border-t border-[#ddd7e6] pt-4 text-[10px] text-[#6d6875] sm:grid-cols-[1fr_1.4fr]">
                <div><p className="text-xs font-bold text-[#4b2a7b]">{d.contact[0]}</p>{d.contact.slice(1).map((c) => <p key={c}>{c}</p>)}</div>
                <p className="italic">{d.disclaimer}</p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
