import { Gavel, Heart, Bot, Briefcase, Compass } from "lucide-react";

const COPY = {
  judge: {
    title: "Welcome to SA CoParents Alignment! 👋", greet: (n) => `Welcome back, Judge ${n}! 👋`,
    body: "Thank you so much for volunteering your time and expertise to support healthy co-parenting outcomes. Your role as a judge is vital to helping families build aligned, child-centered foundations.",
    lead: "Whenever you're ready, you can step into your evaluator space below:",
    cta: "Enter Your Judges Portal", Icon: Gavel,
    hint: "First time here? Don't worry—our portal guides you step-by-step through every review.",
  },
  professional: {
    title: "Welcome to SA CoParents Alignment! 👋", greet: (n) => `Welcome back, ${n}! 👋`,
    body: "Thank you for bringing your expertise to families in transition. As a mediator, attorney, therapist or facilitator, you turn two parents' perspectives into one child-focused picture.",
    lead: "Whenever you're ready, set up your professional space below:",
    cta: "Enter Your Professional Portal", Icon: Briefcase,
    hint: "First time here? Our dashboard walks you through inviting parents, reviewing the Joint Report and building your Professional Report.",
  },
  parent: {
    title: "Welcome to SA CoParents Alignment! 👋", greet: (n) => `Welcome back, ${n}! 👋`,
    body: "Thank you for taking this step for your child. Your professional has invited you to share your own perspective — privately. Your answers are never shown to the other parent; SA CoParents only compares the two completed assessments to find where you align and where the child's needs deserve attention.",
    lead: "Whenever you're ready, accept the invitation below and begin at your own pace:",
    cta: "Begin My Parent Assessment", Icon: Heart,
    hint: "First time here? Each question comes with a short explanation, and you can pause and return any time.",
  },
};

const firstName = (name) => { const parts = (name || "").trim().split(/\s+/).filter((p) => !/^(judge|hon\.?|honorable|the)$/i.test(p)); return (parts[0] || "").replace(/,$/, ""); };

export const JudgeWelcomeChat = ({ onEnter, onTour, kind = "judge", name, className = "mb-6" }) => {
  const c = COPY[kind] || COPY.judge;
  const first = firstName(name);
  return (
    <div className={`flex gap-3 ${className}`} data-testid={`${kind}-welcome-chat`}>
      <span className="mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-purple text-white"><Bot className="h-5 w-5" /></span>
      <div className="relative min-w-0 flex-1 rounded-2xl rounded-tl-sm border border-brand-purple/20 bg-[#f3edfb] px-4 py-3 text-sm leading-relaxed animate-in fade-in slide-in-from-left-2 duration-300">
        <p className="font-semibold text-brand-purple" data-testid={`${kind}-welcome-title`}>{first ? c.greet(first) : c.title}</p>
        <p className="mt-2">{c.body}</p>
        <p className="mt-2">{c.lead}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button type="button" onClick={onEnter} className="inline-flex items-center gap-2 rounded-full bg-brand-blue px-4 py-2 text-sm font-semibold text-white transition-transform hover:scale-[1.02]" data-testid={`${kind}-welcome-enter-btn`}>
            <Heart className="h-4 w-4 fill-current" /> {c.cta} <c.Icon className="h-4 w-4" />
          </button>
          {onTour && (
            <button type="button" onClick={onTour} className="inline-flex items-center gap-1.5 rounded-full border border-brand-purple/40 bg-white px-3 py-2 text-xs font-semibold text-brand-purple transition-colors hover:bg-brand-purple/5" data-testid={`${kind}-welcome-tour-btn`}>
              <Compass className="h-3.5 w-3.5" /> Take a 1-Minute Portal Tour
            </button>
          )}
        </div>
        <p className="mt-3 text-xs text-muted-foreground" data-testid={`${kind}-welcome-hint`}>{c.hint}</p>
      </div>
    </div>
  );
};
