import { useEffect, useState } from "react";
import { Compass, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const KEY = "sa-lens-sample-tour-seen";
export const TOUR_STEPS = [
  { id: "sample-lens-s1", title: "1. Case & Assessment Overview", tip: "Identifies the case, the professional reviewer, which assessments were completed and when, the sources considered — and the IPV / coercive-control safety screening (receipt of each parent's Family Violence screening, four risk categories, joint-process appropriateness, takeaway). A screening summary, never a verified finding." },
  { id: "sample-lens-s2", title: "2. Individual Parent Perspectives", tip: "Parent A and Parent B separately and neutrally: strengths, gaps, three Key Growth Areas (with met-at-reassessment tracking) and PARENT-REPORTED notes. Each parent's 1–10 placement table sits directly under their perspective — read-only, highlighted automatically." },
  { id: "sample-lens-joint", title: "3. Joint Assessment Findings", tip: "Compares the parents' responses: areas of alignment, partial alignment, differing perspectives, shared concerns and issues needing further attention. The joint rating auto-labels the Operating Dynamic and highlights the Joint table row." },
  { id: "sample-lens-s4", title: "4. Child-Focused Issues", tip: "A checklist of nine child-focused categories (educational, medical, psychological, developmental, routines, relationships, communication, transitions, special needs) with an optional neutral note each; the Joint Report pre-ticks likely categories for review." },
  { id: "sample-lens-s5", title: "5. Options & Resources", tip: "Practical tools: BIFF, OurFamilyWizard / tone tools, the SA CoParents Communication Coach, Children in the Middle, parenting education, counseling and subject-matter consultation. One click adds a provider from the admin directory with contact details." },
  { id: "sample-lens-s7", title: "6. Conflict Resolution Pathways", tip: "Twelve pathways from direct structured discussion to court determination — multi-select. The level suggestion is only a hint; the professional must explain why the chosen pathways fit the type of conflict (communication-based, defined disagreement, subject-matter, persistent high conflict, safety)." },
  { id: "sample-lens-s8", title: "7. Professional Statement", tip: "The professional's own judgment — distinct from parent-reported information and AI/system summaries — plus short/long-term goals, reassessment interval and certification. Finalizing locks the report; only a finalized report can be included in a frozen court submission." },
  { id: "sample-lens-s9", title: "8. Concise Court / Referral Summary", tip: "A 1–3 paragraph summary for the court, referring professional or mediator — the only narrative that travels into the judge's frozen-submission summary alongside the ratings, pathways and child-focused issues. Certification, signature lines and the disclaimer follow." },
];

const rectOf = (id) => document.querySelector(`[data-testid="${id}"]`)?.getBoundingClientRect();

export const SampleLensTour = ({ onDone }) => {
  const [i, setI] = useState(0);
  const [rect, setRect] = useState(null);
  const step = TOUR_STEPS[i];

  useEffect(() => {
    const el = document.querySelector(`[data-testid="${step.id}"]`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
    const update = () => setRect(rectOf(step.id));
    const t = setTimeout(update, 450);
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => { clearTimeout(t); window.removeEventListener("scroll", update); window.removeEventListener("resize", update); };
  }, [step.id]);

  const finish = () => { localStorage.setItem(KEY, "1"); onDone(); };
  const pad = 8;
  return (
    <div className="fixed inset-0 z-50" data-testid="lens-tour-overlay">
      {rect && <div className="absolute rounded-xl ring-4 ring-brand-purple pointer-events-none transition-all duration-300"
        style={{ top: rect.top - pad, left: rect.left - pad, width: rect.width + pad * 2, height: rect.height + pad * 2, boxShadow: "0 0 0 9999px rgba(20,10,40,0.6)" }} />}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-xl rounded-xl bg-white p-5 shadow-2xl" data-testid="lens-tour-card">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-brand-purple" data-testid="lens-tour-progress">Step {i + 1} of {TOUR_STEPS.length} · How this section was filled in</p>
            <h3 className="text-lg font-bold mt-0.5" data-testid="lens-tour-title">{step.title}</h3>
          </div>
          <button onClick={finish} aria-label="Close tour" className="text-muted-foreground hover:text-foreground" data-testid="lens-tour-close"><X className="h-5 w-5" /></button>
        </div>
        <p className="text-sm leading-relaxed mt-2" data-testid="lens-tour-tip">{step.tip}</p>
        <div className="mt-4 flex items-center justify-between gap-2">
          <Button variant="ghost" size="sm" onClick={finish} data-testid="lens-tour-skip">Skip tour</Button>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={i === 0} onClick={() => setI(i - 1)} data-testid="lens-tour-back">Back</Button>
            {i < TOUR_STEPS.length - 1
              ? <Button size="sm" onClick={() => setI(i + 1)} data-testid="lens-tour-next">Next</Button>
              : <Button size="sm" onClick={finish} data-testid="lens-tour-finish">Finish</Button>}
          </div>
        </div>
      </div>
    </div>
  );
};

export const useSampleLensTour = (ready) => {
  const [open, setOpen] = useState(false);
  useEffect(() => { if (ready && !localStorage.getItem(KEY)) setOpen(true); }, [ready]);
  return { open, start: () => setOpen(true), close: () => setOpen(false) };
};

export const StartTourButton = ({ onClick }) => (
  <Button variant="outline" size="sm" onClick={onClick} data-testid="lens-tour-start-btn"><Compass className="h-4 w-4 mr-1" /> Start tour</Button>
);
