import { useEffect, useState } from "react";
import { Compass, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const KEY = "sa-lens-sample-tour-seen";
export const TOUR_STEPS = [
  { id: "sample-lens-intro", title: "What This Report Covers", tip: "Static framing text: the 1–10 stability scale, what strengths/gaps mean, and what the report contains. Case Information above it prefills from the case — court, cause number, professional and parent names." },
  { id: "sample-lens-s1", title: "1. Safety First", tip: "Record receipt of each parent's Family Violence screening, then rate four IPV risk categories (Coercive Control, Threats, Hostility, Child Exposure) as Low / Moderate / Moderate-to-High / High with a one-line basis. Write the Takeaway: is an emergency override needed, and is face-to-face negotiation a fit right now? This documents a screening summary — never a verified finding." },
  { id: "sample-lens-s2", title: "2. Individual Breakdown", tip: "For each parent: slide the 1–10 rating, then fill Strengths (what's working), Real-World Example (gaps) and three Key Growth Areas. Strengths/gaps prefill from each parent's own answers (PARENT-REPORTED INFORMATION). The Joint Dynamic rating auto-labels the Operating Dynamic (e.g. Restricted Parallel Parenting Mode)." },
  { id: "sample-lens-s3", title: "3. The 1–10 Scale", tip: "Read-only reference table. The rows matching Parent A, Parent B and the Joint rating are highlighted automatically and named in the Case Placement column — you never edit this table." },
  { id: "sample-lens-s4", title: "4. Roadmap", tip: "Short-term (30–90 days) and long-term (6–12 months) goals, one per line as “Title: concrete action”. Name the responsible parent or provider where it helps (e.g. Transition Promptness Target (Parent B))." },
  { id: "sample-lens-s5", title: "5. Resource & Support Options", tip: "A table of Category → Resource/Specialist → Service focus. Starter rows are prefilled; one click adds a provider from the admin directory (Kelly Bernstein, Kassandra Levay, Brad Craig) with their credentials and contact details." },
  { id: "sample-lens-s6", title: "6. Regular Reassessments", tip: "Choose the check-in interval and the next review date, then state what changes when the score moves up (step down structure) or drops (re-check safety, restrict to app logs, court oversight)." },
  { id: "sample-lens-s7", title: "7. Conflict Resolution Pathways", tip: "Five pathways from Litigation (Levels 1–3) to Direct Collaboration (Level 10). The pathway matching the joint rating is auto-marked as the recommendation; you may select a different one and must write the rationale." },
  { id: "sample-lens-s8", title: "Certification & PDF", tip: "Sign and add your title. Finalizing locks the report and adds an AI-disclosure appendix if any section was AI-assisted; only a finalized report can be included in a frozen court submission. Print / Save as PDF produces the court copy." },
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
