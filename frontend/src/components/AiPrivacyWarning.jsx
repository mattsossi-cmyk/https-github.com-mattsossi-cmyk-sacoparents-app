import { ShieldAlert } from "lucide-react";

// Owner-approved text (2026-10-12). Edit strings here only. Shown EVERY time, above the input — no one-time hide, no storage.
export const AI_PRIVACY_WARNING = {
  headingBuilder: "SA CoParents Communication Builder — Privacy Warning",
  heading: "Privacy Warning",
  p1: "SA CoParents is committed to protecting your personal information and your child's privacy.",
  p2: "When using an AI-assisted communication tool, information you enter may be processed by external technology providers and could be disclosed to third parties depending on the platform's privacy practices and safeguards.",
  p3: "Please speak in general terms. Do not provide names or identifying details; upload assessments or reports; disclose sensitive medical, mental health, psychological or educational information; or enter confidential legal communications or details concerning family violence or personal safety.",
  highlight: "You can improve communication without sharing private family details.",
  tagline: "SA CoParents — Start with Safety. Protect Your Privacy. Focus on Your Child.",
};
export const AI_PRIVACY_ONE_LINER = "Privacy Warning: speak in general terms — no names, identifying details, reports, health, legal or safety information. Text you enter may be processed by external AI providers.";

export const AiPrivacyWarning = ({ builder = false, compact = false, testId = "ai-privacy-warning" }) => {
  const w = AI_PRIVACY_WARNING;
  if (compact) {
    return (
      <p role="note" className="mb-2 flex items-start gap-2 rounded-md border border-[#3D1A78]/25 bg-[#3D1A78]/5 px-3 py-2 font-jakarta text-xs leading-snug text-[#3D1A78]" data-testid={testId}>
        <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" /><span>{AI_PRIVACY_ONE_LINER}</span>
      </p>
    );
  }
  return (
    <section role="note" aria-label={builder ? w.headingBuilder : w.heading} className="mb-3 rounded-xl border border-[#3D1A78]/25 bg-[#3D1A78]/5 p-4 font-jakarta text-[#2d2d34]" data-testid={testId}>
      <p className="flex items-center gap-2 text-sm font-bold text-[#3D1A78] md:text-base"><ShieldAlert className="h-4 w-4 shrink-0" aria-hidden="true" />{builder ? w.headingBuilder : w.heading}</p>
      <p className="mt-2 text-sm leading-relaxed">{w.p1}</p>
      <p className="mt-2 text-sm leading-relaxed">{w.p2}</p>
      <p className="mt-2 text-sm leading-relaxed">{w.p3}</p>
      <p className="mt-3 text-sm font-semibold text-[#3D1A78]">{w.highlight}</p>
      <p className="mt-2 text-xs text-slate-600">{w.tagline}</p>
    </section>
  );
};
