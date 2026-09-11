import { useEffect, useState } from "react";
import { X, ChevronLeft, ChevronRight, Compass } from "lucide-react";
import { Button } from "@/components/ui/button";

export const TOUR_STEPS = [
  ["jr-purpose", "Purpose", "Sets the neutral frame: this report compares perspectives — it never recommends custody or judges a parent."],
  ["jr-alignment", "What Both Parents Agree About", "Start every conversation here. Naming shared ground first lowers defensiveness before differences come up."],
  ["jr-differences", "Where They See Things Differently", "Each parent's words appear side by side with a neutral reframe. Read the reframe aloud rather than either parent's quote."],
  ["jr-needs", "Child's Identified Needs", "Pulled from both answers. Keep returning to this list when the discussion drifts toward adult grievances."],
  ["jr-map", "Alignment Map", "Colour-coded at a glance: green = strong, yellow = moderate, blue = different. Use it to choose the order of topics."],
  ["jr-conversation", "Areas for Conversation", "Neutral prompts you can use verbatim to open each topic in session."],
  ["jr-options", "Options and Resources", "Options both parents raised. SA CoParents builds options — it does not decide. Invite the parents to add their own."],
  ["jr-paragraph", "Potential Areas of Alignment", "A short narrative you can read to the parents to summarise where agreement is within reach."],
  ["jr-questions", "Questions for the Parents", "Reflective questions to send home or ask in session; they keep the child at the centre."],
  ["jr-next-steps", "Possible Next Steps", "Concrete, small steps. Close the session by choosing one or two together."],
];

const STORAGE_KEY = "align-sample-tour-done";

export const SampleWalkthrough = ({ active, onStart }) => {
  const [step, setStep] = useState(-1);
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(STORAGE_KEY) === "1");

  useEffect(() => {
    if (step < 0) return;
    const el = document.querySelector(`[data-testid="${TOUR_STEPS[step][0]}"]`);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("tour-highlight");
    return () => el.classList.remove("tour-highlight");
  }, [step]);

  const finish = () => { setStep(-1); localStorage.setItem(STORAGE_KEY, "1"); setDismissed(true); };
  const start = () => { onStart?.(); setTimeout(() => setStep(0), 150); };

  if (!active) return null;

  if (step < 0) {
    return (
      <div className="no-print mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-align-yellow/60 bg-align-yellow/15 px-4 py-3" data-testid="sample-tour-banner">
        <p className="text-sm"><span className="font-semibold">Sample case.</span> {dismissed ? "Take the 10-step tour again any time." : "New here? Take a 2-minute guided tour of the 10 report sections."}</p>
        <Button size="sm" className="gap-1.5" onClick={start} data-testid="sample-tour-start-btn"><Compass className="h-4 w-4" /> Start walkthrough</Button>
      </div>
    );
  }

  const [, title, tip] = TOUR_STEPS[step];
  const last = step === TOUR_STEPS.length - 1;
  return (
    <div className="no-print fixed bottom-4 left-4 right-4 z-50 mx-auto max-w-md rounded-xl border border-border bg-white p-5 shadow-2xl" role="dialog" aria-live="polite" data-testid="sample-tour-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-accent" data-testid="sample-tour-progress">Section {step + 1} of {TOUR_STEPS.length}</p>
          <h3 className="mt-1 font-semibold" data-testid="sample-tour-title">{title}</h3>
        </div>
        <button type="button" onClick={finish} className="text-muted-foreground hover:text-foreground" aria-label="Close walkthrough" data-testid="sample-tour-close-btn"><X className="h-4 w-4" /></button>
      </div>
      <p className="mt-2 text-sm text-muted-foreground leading-relaxed" data-testid="sample-tour-tip">{tip}</p>
      <div className="mt-4 flex items-center justify-between">
        <div className="flex gap-1" aria-hidden="true">
          {TOUR_STEPS.map((_, i) => <span key={i} className={`h-1.5 w-1.5 rounded-full ${i <= step ? "bg-primary" : "bg-border"}`} />)}
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setStep(step - 1)} disabled={step === 0} data-testid="sample-tour-back-btn"><ChevronLeft className="h-4 w-4" /> Back</Button>
          <Button size="sm" onClick={last ? finish : () => setStep(step + 1)} data-testid="sample-tour-next-btn">{last ? "Finish" : "Next"} {!last && <ChevronRight className="h-4 w-4" />}</Button>
        </div>
      </div>
    </div>
  );
};
