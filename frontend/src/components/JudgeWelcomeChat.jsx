import { Gavel, Heart, Bot } from "lucide-react";

export const JudgeWelcomeChat = ({ onEnter }) => (
  <div className="mb-6 flex gap-3" data-testid="judge-welcome-chat">
    <span className="mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-purple text-white"><Bot className="h-5 w-5" /></span>
    <div className="relative min-w-0 flex-1 rounded-2xl rounded-tl-sm border border-brand-purple/20 bg-[#f3edfb] px-4 py-3 text-sm leading-relaxed animate-in fade-in slide-in-from-left-2 duration-300">
      <p className="font-semibold text-brand-purple" data-testid="judge-welcome-title">Welcome to SA CoParents Alignment! 👋</p>
      <p className="mt-2">Thank you so much for volunteering your time and expertise to support healthy co-parenting outcomes. Your role as a judge is vital to helping families build aligned, child-centered foundations.</p>
      <p className="mt-2">Whenever you're ready, you can step into your evaluator space below:</p>
      <button type="button" onClick={onEnter} className="mt-3 inline-flex items-center gap-2 rounded-full bg-brand-blue px-4 py-2 text-sm font-semibold text-white transition-transform hover:scale-[1.02]" data-testid="judge-welcome-enter-btn">
        <Heart className="h-4 w-4 fill-current" /> Enter Your Judges Portal <Gavel className="h-4 w-4" />
      </button>
      <p className="mt-3 text-xs text-muted-foreground" data-testid="judge-welcome-hint">First time here? Don't worry—our portal guides you step-by-step through every review.</p>
    </div>
  </div>
);
