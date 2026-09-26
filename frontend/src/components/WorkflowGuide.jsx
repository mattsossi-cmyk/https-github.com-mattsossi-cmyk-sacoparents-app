import { useState } from "react";
import { ChevronDown, ChevronUp, ListChecks } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ListenButton } from "@/components/ListenButton";

export const GUIDES = {
  judge: { title: "How to use the Judicial Case Review Portal", steps: [
    ["Refer a case", "Use Refer Case: cause number, parties' emails and the professional. Both parents are invited privately; you never see raw parent answers."],
    ["Track status", "The case list shows each parent's assessment status and when the Joint Report and Professional Report are ready. Set a hearing date to get reminders."],
    ["Read the frozen packet", "Every submission is hash-sealed (SHA-256) and versioned. The Court Packet PDF holds the Professional Statement, Joint Report and any explicitly attached reports."],
    ["Read the Professional Report", "Neutral: alignment levels (1–10), individual and joint scale tables, child-focused issues, options and pathways. It contains no custody recommendation, diagnosis or credibility finding."],
    ["Check safety first", "Gold Safety Override cards mean family-violence indicators exist; agreements then follow a Parallel Parenting structure and a one-page order summary is available."],
    ["Message the professional", "Use the case thread for procedural questions; messages are logged to the case record."]] },
  legal_lens: { title: "Before you start the Professional Alignment Report", steps: [
    ["Review the sources", "Read both parents' assessments, both Family Violence screenings and the Joint Report. Raw parent answers stay private — you summarize them neutrally."],
    ["Check safety first", "Record the risk screening and decide whether a joint process is appropriate. Safety findings override ordinary co-parenting recommendations."],
    ["Rate individually, then jointly", "Place Parent A, Parent B and the co-parenting dynamic on the 1–10 scale; note Key Growth Areas for each parent."],
    ["Identify child-focused issues", "Tick the categories that affect the child; write concerns without blame or credibility judgments."],
    ["Choose options & pathways", "Select resources from the directory and the conflict-resolution pathways, with a rationale."],
    ["Write your observation & plan", "Your own professional judgment: 90-day action plan, success indicators, long-term goals, reassessment triggers."],
    ["Court summary, then certify", "Write the concise, neutral court summary. Review the PDF, finalize and certify — only then can it be attached to a court submission."]] },
  professional_statement: { title: "Before you submit to the court", steps: [
    ["Confirm the Joint Report is ready", "Both parents must have completed their assessments; the Joint Report is frozen at submission."],
    ["Write your Professional Statement", "Role, basis for involvement, process summary, observations and next steps — neutral, no custody recommendation."],
    ["Rate the co-parenting dynamic", "The 1–10 score feeds the judge's level history and reassessment comparison."],
    ["Decide what to attach", "The Legal Lens report and a completed Co-Parenting Agreement are attached only if you tick them. Safety Override warnings apply when risk indicators exist."],
    ["Attest and submit", "The packet is hash-sealed (SHA-256) and the court is notified. Re-submitting creates a new version; earlier versions are superseded, never deleted."]] },
  case_create: { title: "Before you open a case", steps: [
    ["Enter the child", "Name or initials only. Court referral details are prefilled when a judge referred the case."],
    ["Invite both parents", "Each parent receives a private invitation; parents never see each other's answers."],
    ["Pick the assessment", "Co-parenting subjects, Safety / Family Violence (professional-mediated), Foundation Statement, or a custom set. Safety subjects never route to joint negotiation."],
    ["Wait for both", "You'll be emailed when both parents finish; the Joint Report is generated automatically for you to review."],
    ["Then report", "Open the Professional Alignment Report from the case to rate, review and certify."]] },
  agreement_create: { title: "Before you start a Co-Parenting Agreement", steps: [
    ["Foundation first", "Ask each parent to write and share their Child-Focused Foundation Statement — strengths, needs, commitments and goals feed the agreement."],
    ["Invite both parents", "Each parent proposes privately across 10 areas; matching answers become specific agreements, differences are listed for discussion."],
    ["Safety check", "If any safety indicator exists the agreement is rendered as a Parallel Parenting structure (written-only communication, neutral exchanges, no direct negotiation)."],
    ["Review the draft", "Open issues are not agreements — they are candidates for discussion, professional consultation or mediation."],
    ["Attach to court (optional)", "A completed agreement can be attached explicitly when you submit the Joint Report to the court."]] },
  foundation: { title: "Before you write your Foundation Statement", steps: [
    ["Answer the three safety questions", "Private to you. If any answer is Yes, your statement stays private and your professional uses the safety pathway."],
    ["Write in your own words", "Ten short sections: shared purpose, vision, priorities, your child's strengths and needs, concerns, commitments, goals, future, your commitment."],
    ["Stay child-focused", "Describe your child and your own commitments — not the other parent. Concerns are stated without blame."],
    ["Save, then share", "Save a draft any time. When complete, share it into your case so the professional and the Co-Parenting Agreement can use it."]] },
};

export function WorkflowGuide({ kind, storageKey, testId }) {
  const g = GUIDES[kind];
  const key = storageKey || `sa-guide-${kind}-collapsed`;
  const [open, setOpen] = useState(() => !localStorage.getItem(key));
  const toggle = () => { const next = !open; setOpen(next); if (next) localStorage.removeItem(key); else localStorage.setItem(key, "1"); };
  if (!g) return null;
  return (
    <section className="rounded-lg border border-brand-purple/30 bg-[#f3edfb] p-4" data-testid={testId || `workflow-guide-${kind}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-sm font-bold text-brand-purple"><ListChecks className="h-4 w-4" /> {g.title}</p>
        <div className="flex items-center gap-1">
          <ListenButton text={`${g.title}. ${g.steps.map(([t, d], i) => `Step ${i + 1}: ${t}. ${d}`).join(" ")}`} variant="ghost" testId={`workflow-guide-${kind}-listen`} />
          <Button variant="ghost" size="sm" onClick={toggle} data-testid={`workflow-guide-${kind}-toggle`}>{open ? <><ChevronUp className="h-4 w-4 mr-1" /> Hide steps</> : <><ChevronDown className="h-4 w-4 mr-1" /> Show steps</>}</Button>
        </div>
      </div>
      {open && (
        <ol className="mt-3 grid gap-2 sm:grid-cols-2" data-testid={`workflow-guide-${kind}-steps`}>
          {g.steps.map(([t, d], i) => (
            <li key={t} className="flex gap-3 rounded-md bg-white/80 p-3 text-sm"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-purple text-xs font-bold text-white">{i + 1}</span><span><strong className="text-[#2f174f]">{t}</strong><span className="block text-xs text-muted-foreground mt-0.5">{d}</span></span></li>
          ))}
        </ol>
      )}
    </section>
  );
}
