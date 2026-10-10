import { useEffect } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Phone } from "lucide-react";
import { BrandLogo } from "@/components/Brand";
import POLICIES from "@/content/policies.json";

export const POLICY_VERSION = POLICIES.version;
export const POLICY_STATUS = POLICIES.status;
const BRAND = "#3D1A78";

const useNoIndex = (title) => {
  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex, nofollow";
    meta.dataset.policy = "1";
    document.head.appendChild(meta);
    const prev = document.title;
    document.title = `${title} · SA CoParents Align`;
    return () => { meta.remove(); document.title = prev; };
  }, [title]);
};

const Section = ({ s, slug, i }) => (
  <section aria-labelledby={`${slug}-h-${i}`} className={s.emergency ? "rounded-xl border-l-4 border-red-500 bg-red-50 p-4" : ""} data-testid={`policy-section-${i + 1}`}>
    <h2 id={`${slug}-h-${i}`} className="text-base font-bold md:text-lg" style={{ color: BRAND }}>{s.emergency && <Phone className="mr-1.5 inline h-4 w-4" aria-hidden="true" />}{s.heading}</h2>
    {s.paragraphs?.map((p) => <p key={p} className="mt-2 text-sm leading-relaxed text-slate-700 md:text-base">{p}</p>)}
    {s.bullets && <ul className="mt-2 list-disc space-y-1 pl-6 text-sm text-slate-700 md:text-base">{s.bullets.map((b) => <li key={b}>{b}</li>)}</ul>}
    {s.numbered && <ol className="mt-2 list-decimal space-y-1 pl-6 text-sm text-slate-700 md:text-base">{s.numbered.map((b) => <li key={b}>{b}</li>)}</ol>}
  </section>
);

export default function PolicyPage({ slug }) {
  const p = POLICIES[slug];
  useNoIndex(p.title);
  return (
    <div className="min-h-screen bg-[#f6f3fb] font-jakarta text-slate-900" data-testid={`policy-${slug}-page`}>
      <a href="#policy-main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:rounded focus:bg-white focus:px-3 focus:py-2">Skip to content</a>
      <header className="border-b border-[#3D1A78]/10 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4 sm:px-6">
          <Link to="/" className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900" data-testid="policy-back-link"><ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to SA CoParents</Link>
          <BrandLogo size="text-xl" />
        </div>
      </header>
      <main id="policy-main" className="mx-auto max-w-3xl px-4 py-10 sm:px-6" tabIndex={-1}>
        <p className="text-xs font-bold uppercase tracking-widest" style={{ color: BRAND }}>SA CoParents</p>
        <h1 className="mt-1 text-4xl font-bold tracking-tight sm:text-5xl" style={{ color: BRAND }} data-testid="policy-title">{p.title}</h1>
        <p className="mt-2 inline-block rounded-md border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-900" data-testid="policy-version">Version {POLICY_VERSION} ({POLICY_STATUS})</p>
        <div className="mt-8 space-y-8">{p.sections.map((s, i) => <Section key={s.heading} s={s} slug={slug} i={i} />)}</div>
      </main>
    </div>
  );
}
