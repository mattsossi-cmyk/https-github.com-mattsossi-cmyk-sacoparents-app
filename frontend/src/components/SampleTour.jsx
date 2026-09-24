import { useEffect, useState } from "react";
import { Compass, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const rectOf = (id) => document.querySelector(`[data-testid="${id}"]`)?.getBoundingClientRect();

export const SampleTour = ({ steps, storageKey, onDone, label = "How this section was filled in", prefix = "tour" }) => {
  const [i, setI] = useState(0);
  const [rect, setRect] = useState(null);
  const step = steps[i];
  useEffect(() => {
    const el = document.querySelector(`[data-testid="${step.id}"]`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
    const update = () => setRect(rectOf(step.id));
    const t = setTimeout(update, 450);
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => { clearTimeout(t); window.removeEventListener("scroll", update); window.removeEventListener("resize", update); };
  }, [step.id]);
  const finish = () => { localStorage.setItem(storageKey, "1"); onDone(); };
  const pad = 8;
  return (
    <div className="fixed inset-0 z-50" data-testid={`${prefix}-overlay`}>
      {rect && <div className="absolute rounded-xl ring-4 ring-brand-purple pointer-events-none transition-all duration-300" style={{ top: rect.top - pad, left: rect.left - pad, width: rect.width + pad * 2, height: rect.height + pad * 2, boxShadow: "0 0 0 9999px rgba(20,10,40,0.6)" }} />}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-xl rounded-xl bg-white p-5 shadow-2xl" data-testid={`${prefix}-card`}>
        <div className="flex items-start justify-between gap-3">
          <div><p className="text-xs font-bold uppercase tracking-widest text-brand-purple" data-testid={`${prefix}-progress`}>Step {i + 1} of {steps.length} · {label}</p><h3 className="text-lg font-bold mt-0.5" data-testid={`${prefix}-title`}>{step.title}</h3></div>
          <button onClick={finish} aria-label="Close tour" className="text-muted-foreground hover:text-foreground" data-testid={`${prefix}-close`}><X className="h-5 w-5" /></button>
        </div>
        <p className="text-sm leading-relaxed mt-2" data-testid={`${prefix}-tip`}>{step.tip}</p>
        <div className="mt-4 flex items-center justify-between gap-2">
          <Button variant="ghost" size="sm" onClick={finish} data-testid={`${prefix}-skip`}>Skip tour</Button>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={i === 0} onClick={() => setI(i - 1)} data-testid={`${prefix}-back`}>Back</Button>
            {i < steps.length - 1 ? <Button size="sm" onClick={() => setI(i + 1)} data-testid={`${prefix}-next`}>Next</Button> : <Button size="sm" onClick={finish} data-testid={`${prefix}-finish`}>Finish</Button>}
          </div>
        </div>
      </div>
    </div>
  );
};

export const useSampleTour = (ready, storageKey) => {
  const [open, setOpen] = useState(false);
  useEffect(() => { if (ready && !localStorage.getItem(storageKey)) setOpen(true); }, [ready, storageKey]);
  return { open, start: () => setOpen(true), close: () => setOpen(false) };
};

export const TourButton = ({ onClick, testId = "tour-start-btn" }) => (
  <Button variant="outline" size="sm" onClick={onClick} data-testid={testId}><Compass className="h-4 w-4 mr-1" /> Start tour</Button>
);

export const FOUNDATION_TOUR = [
  { id: "foundation-section-1", title: "1. Shared Purpose", tip: "The parent's own words on what their child deserves from both parents, regardless of what brought the family here. Written in the parent's voice — never edited by SA CoParents." },
  { id: "foundation-section-2", title: "2. My Vision for My Child", tip: "A child-at-the-center statement of the future the parent wants — how the child should feel and grow. Professionals read this as the parent's stated intent." },
  { id: "foundation-section-3", title: "3–4. Priorities & Understanding My Child", tip: "Priorities are one line each; strengths and current needs describe the child, not the other parent. When both parents share statements, matching priorities become alignment in the Joint Agreement." },
  { id: "foundation-section-5", title: "5–6. Concerns & What My Child May Need", tip: "Concerns are stated without blame and paired with what the child needs. This keeps the statement usable in mediation and in front of a professional." },
  { id: "foundation-section-7", title: "7–8. Commitments & 12-Month Goals", tip: "Concrete personal commitments and goals the parent is making. The professional can later check these against Key Growth Areas at reassessment." },
  { id: "foundation-section-10", title: "9–10. Future & Parent Commitment", tip: "Closing reflection and a one-paragraph Foundation Statement, signed by the parent. It is not a legal agreement and does not replace legal advice or a court order." },
];

export const AGREEMENT_TOUR = [
  { id: "agreement-summary", title: "At a Glance", tip: "Three tallies generated from both parents' private proposals: Areas of Alignment, Specific Agreements (matching follow-up answers), and Issues Still Requiring Resolution (answers that differ)." },
  { id: "agreement-section-foundation", title: "1. Our Child-Focused Foundation", tip: "Each of the 10 sections starts with a Shared Goal, then Current Alignment, Specific Agreements, and open issues. A status badge (Agreed / Partly agreed / Requires resolution) is computed, not chosen." },
  { id: "agreement-section-transitions", title: "2. Parenting-Time Transitions", tip: "Follow-up questions (where, lateness, changes, belongings, contact) become clauses when both parents answered the same way; differing answers are listed for discussion — never decided for them." },
  { id: "agreement-section-communication", title: "3. Communication", tip: "Method, response times, emergencies, tone and boundaries. Matching answers also fill the Communication Method and Decision Process rows used by professionals." },
  { id: "agreement-section-differences", title: "9. Managing Differences", tip: "How the parents agreed to handle future disagreements: written proposal first, SA CoParents tools, a professional, then mediation before court." },
  { id: "agreement-signatures", title: "Signatures & Next Steps", tip: "Open issues are not agreements — they are candidates for conversation, professional consultation or mediation before the document is finalized and signed." },
];
