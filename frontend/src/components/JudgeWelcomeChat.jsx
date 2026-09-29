import { Gavel, Heart, Bot, Briefcase } from "lucide-react";

const COPY = {
  judge: {
    title: "Welcome to SA CoParents Alignment! 👋",
    body: "Thank you so much for volunteering your time and expertise to support healthy co-parenting outcomes. Your role as a judge is vital to helping families build aligned, child-centered foundations.",
    lead: "Whenever you're ready, you can step into your evaluator space below:",
    cta: "Enter Your Judges Portal", Icon: Gavel,
    hint: "First time here? Don't worry—our portal guides you step-by-step through every review.",
  },
  professional: {
    title: "Welcome to SA CoParents Alignment! 👋",
    body: "Thank you for bringing your expertise to families in transition. As a mediator, attorney, therapist or facilitator, you turn two parents' perspectives into one child-focused picture.",
    lead: "Whenever you're ready, set up your professional space below:",
    cta: "Enter Your Professional Portal", Icon: Briefcase,
    hint: "First time here? Our dashboard walks you through inviting parents, reviewing the Joint Report and building your Professional Report.",
  },
};

export const JudgeWelcomeChat = ({ onEnter, kind = "judge" }) => {
  const c = COPY[kind] || COPY.judge;
  return (
    <div className="mb-6 flex gap-3" data-testid={`${kind}-welcome-chat`}>
      <span className="mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-purple text-white"><Bot className="h-5 w-5" /></span>
      <div className="relative min-w-0 flex-1 rounded-2xl rounded-tl-sm border border-brand-purple/20 bg-[#f3edfb] px-4 py-3 text-sm leading-relaxed animate-in fade-in slide-in-from-left-2 duration-300">
        <p className="font-semibold text-brand-purple" data-testid={`${kind}-welcome-title`}>{c.title}</p>
        <p className="mt-2">{c.body}</p>
        <p className="mt-2">{c.lead}</p>
        <button type="button" onClick={onEnter} className="mt-3 inline-flex items-center gap-2 rounded-full bg-brand-blue px-4 py-2 text-sm font-semibold text-white transition-transform hover:scale-[1.02]" data-testid={`${kind}-welcome-enter-btn`}>
          <Heart className="h-4 w-4 fill-current" /> {c.cta} <c.Icon className="h-4 w-4" />
        </button>
        <p className="mt-3 text-xs text-muted-foreground" data-testid={`${kind}-welcome-hint`}>{c.hint}</p>
      </div>
    </div>
  );
};
