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

export const PRO_TOUR = [
  { id: "primary-cta-bar", title: "Five steps, in order", tip: "Invite Parents sends each parent a private assessment link. Review Assessments shows who has completed and the private safety-screening status. Joint Report opens the system-generated comparison once both finish. Legal Lens Review is where you label sources and add your professional statement. Court Report freezes and submits the packet to the referring judge. Court-ordered matters arrive via the Judge Portal card below." },
  { id: "pipeline-stepper", title: "Workflow pipeline", tip: "Pick a case and watch it move: Individual Assessments → Joint → Options & Resources → Pathway → Professional Report. Click any step to jump straight into that part of the case." },
  { id: "pro-contact-card", title: "Report cover contact", tip: "Add your phone, office address, headshot, firm logo and signature once — they print on the Professional Report cover and the court-packet cover letter automatically." },
  { id: "assistant-open-btn", title: "Align Assistant", tip: "An advisory helper that explains where the parents agree, where gaps are minor or high, and which pathways from the library fit. It drafts for your review; it never files or decides anything." },
  { id: "joint-reports-section", title: "Your cases", tip: "Every case you created or received by court referral lists here with parent status and one-click access to the Joint Report and Professional Report." },
];

export const JUDGE_TOUR = [
  { id: "judge-workflow-guide", title: "How the Judicial Portal works", tip: "Refer a case → the professional invites both parents → parents complete private assessments → the professional reviews the Joint Report and files a neutral Professional Report. You never see raw parent answers." },
  { id: "refer-case-toggle-btn", title: "Refer a case", tip: "Enter the parties, cause number, hearing date and the parties' ZIP, then pick a nearby verified professional. The professional receives the referral by email and confirms acceptance." },
  { id: "court-case-search", title: "Your referred cases", tip: "Every case you referred lists here with its stage: invited, assessments in progress, Joint Report ready, Professional Report filed. Select one to see parent status, hearing date and available reports." },
  { id: "court-packets-heading", title: "Court Packets addressed to you", tip: "Professionals submit court packets here: a signed cover letter plus the reports they chose to file. Opening a packet is logged for the sending professional; a Reader Guide sits beside each Professional Report." },
  { id: "court-directory", title: "Court directory & urgent alerts", tip: "Find verified professionals by area, and receive an urgent-safety email alert if a professional flags a safety concern on one of your cases." },
];

export const FOUNDATION_TOUR = [
  { id: "foundation-section-1", title: "1. Shared Purpose", tip: "The parent's own words on what their child deserves from both parents, regardless of what brought the family here. Written in the parent's voice — never edited by SA CoParents." },
  { id: "foundation-section-2", title: "2. My Vision for My Child", tip: "A child-at-the-center statement of the future the parent wants — how the child should feel and grow. Professionals read this as the parent's stated intent." },
  { id: "foundation-section-3", title: "3–4. Priorities & Understanding My Child", tip: "Priorities are one line each; strengths and current needs describe the child, not the other parent. When both parents share statements, matching priorities become alignment in the Joint Agreement." },
  { id: "foundation-section-5", title: "5–7. Concerns, Wellness & Technology, What My Child May Need", tip: "Concerns — including sleep, wellness, smartphones, social media and screens — are stated without blame and paired with what the child needs. This keeps the statement usable in mediation and in front of a professional." },
  { id: "foundation-section-8", title: "8–9. Commitments & 12-Month Goals", tip: "Concrete personal commitments and goals the parent is making. The professional can later check these against Key Growth Areas at reassessment." },
  { id: "foundation-section-11", title: "10–11. Future & Parent Commitment", tip: "Closing reflection and a one-paragraph Foundation Statement, signed by the parent. It is not a legal agreement and does not replace legal advice or a court order." },
];

export const AGREEMENT_TOUR = [
  { id: "agreement-summary", title: "At a Glance", tip: "Three tallies generated from both parents' private proposals: Areas of Alignment, Specific Agreements (matching follow-up answers), and Issues Still Requiring Resolution (answers that differ)." },
  { id: "agreement-section-foundation", title: "1. Our Child-Focused Foundation", tip: "Each of the 11 sections starts with a Shared Goal, then Current Alignment, Specific Agreements, and open issues. A status badge (Agreed / Partly agreed / Requires resolution) is computed, not chosen." },
  { id: "agreement-section-transitions", title: "2. Parenting-Time Transitions", tip: "Follow-up questions (where, lateness, changes, belongings, contact) become clauses when both parents answered the same way; differing answers are listed for discussion — never decided for them." },
  { id: "agreement-section-communication", title: "3. Communication", tip: "Method, response times, emergencies, tone and boundaries. Matching answers also fill the Communication Method and Decision Process rows used by professionals." },
  { id: "agreement-section-wellness_tech", title: "8. Wellness, Phones & Social Media", tip: "Sleep, meals and activity anchors, the age for a smartphone, acceptable apps and social media, screen limits, and how an online-safety concern is shared between homes." },
  { id: "agreement-section-differences", title: "10. Managing Differences", tip: "How the parents agreed to handle future disagreements: written proposal first, SA CoParents tools, a professional, then mediation before court." },
  { id: "agreement-signatures", title: "Legal Notice, Acknowledgment & Signatures", tip: "The agreement closes with the Important Legal Notice and Disclaimer, then an Acknowledgment both parents sign. Open issues are not agreements — they are candidates for conversation, professional consultation or mediation before signing." },
];
