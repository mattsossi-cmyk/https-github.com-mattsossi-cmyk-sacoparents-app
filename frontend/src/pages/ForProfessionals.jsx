/**
 * ForProfessionals.jsx — public marketing page at `/for-professionals`
 * that positions SA CoParents to mediators, family attorneys, and DV
 * practitioners. Answers the 7 FAQ items that professionals ask before
 * accepting a parent-generated report.
 *
 * No auth required. Deep links to the Sample Library and the
 * Professionals directory so a visitor can evaluate concrete
 * artefacts before signing up.
 */
import React from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Award,
  FileText,
  ShieldCheck,
  Users,
  Scale,
  Sparkles,
  Lock,
  Mail,
  ExternalLink,
  MessageSquare,
  BookOpen,
  Heart,
  Send,
  GitCompare,
  Target,
  MessageCircle,
} from "lucide-react";
import ProfessionalsIntroAudio from "../components/ProfessionalsIntroAudio";
import PreferredProfessionalsStrip from "../components/PreferredProfessionalsStrip";

// The four-step Align workflow — mirrors the same 4-step framing used
// on the Landing ecosystem strip so parents and professionals see the
// exact same vocabulary across both sites. Clinical-neutral by design:
// verbs describe what the PROFESSIONAL does, no marketing fluff.
const ALIGN_WORKFLOW = [
  {
    key: "invite",
    label: "Invite",
    icon: Send,
    body: "Send both parents a secure invitation link. Each parent gets their own private space to reflect.",
  },
  {
    key: "compare",
    label: "Compare",
    icon: GitCompare,
    body: "Each parent completes their reflection independently, in their own time. No shared answers, no adversarial framing.",
  },
  {
    key: "identify-alignment",
    label: "Identify Alignment",
    icon: Target,
    body: "Align generates a side-by-side view of shared understanding and differences worth discussing — nothing adjudicative.",
  },
  {
    key: "guide-conversation",
    label: "Guide Conversation",
    icon: MessageCircle,
    body: "Bring the Co-Parenting Agreement into your session and use it to focus the conversation on the child.",
  },
];

const FAQS = [
  {
    q: "Are the reports admissible or advisory?",
    icon: Scale,
    a: "The reports are advisory — mediator-facing prep artefacts, not adjudicative findings. Each PDF carries a plain-language disclaimer at the top and footer stating that it is neutral, non-diagnostic, and prepared for professional reference only. Nothing produced by the app is intended for court submission without your professional review and reframing.",
  },
  {
    q: "How is neutrality enforced?",
    icon: Sparkles,
    a: "Every parent-facing question uses first-person, parent-attributed language (\"I feel…\", \"We would like…\") — never accusatory framing. LLM summaries are constrained by a guardrail prompt that blocks adjudicative or diagnostic language, and the summary hard short-circuits to a safety sentence when either parent reports family violence. A visible \"AI-drafted\" pill sits next to every model-generated block so you always know what came from the parents' verbatim answers versus what the model composed.",
  },
  {
    q: "What about family-violence safety?",
    icon: ShieldCheck,
    a: "Parents complete a private safety screen before any co-parent invitation can be sent. Parents scoring at high concern or coercive control levels see a red \"direct outreach isn't recommended right now\" panel with a DV hotline and advocate resources — the invite flow is blocked. Professional-directed sends (that you initiate) are deliberately not gated: you are not the safety risk.",
  },
  {
    q: "How do you protect the co-parent's private answers?",
    icon: Lock,
    a: "Each parent completes their reflection independently. On the Compare view, only aggregated dimension scores and the neutral LLM summary are shared between parents — free-text notes and raw answers never leave the parent who wrote them. All shareable links are consent-gated at mint, JWT-signed, revocable at any time, and every read is logged as a PHI access event.",
  },
  {
    q: "What data do you collect on my clients?",
    icon: Users,
    a: "The bare minimum: name, email, and the answers the parent chooses to record. We do not train models on any customer data. Everything is encrypted in transit and at rest. Parents can delete their account and every associated record instantly from their Account page. Full breakdown is on our public /privacy and /legal/hipaa pages.",
  },
  {
    q: "How does this fit into my existing mediation workflow?",
    icon: FileText,
    a: "Two ways. (1) Parent-initiated: parents complete the reflection and email you the mediator-ready PDF using the built-in \"Email to professional\" button — you receive a signed link that expires in 7–30 days. (2) Professional-initiated: from sacoparentsalign.com you create a Joint Alignment Case, both parents get secure invitation tokens, and the 10-page joint report is generated on your side after both complete. No shared database, no shared credentials — data-minimised handoff only.",
  },
  {
    q: "Can I see sample reports before recommending this to a client?",
    icon: BookOpen,
    a: "Yes — the /samples library is public. Every downloadable PDF the app produces is browsable there, organised into six categories (Joint Alignment, Child Needs Deep-Dives, Special Needs, Co-Parenting Foundation, Family Violence, and For Professionals). No signup required.",
  },
];

const HIGHLIGHTS = [
  {
    icon: Sparkles,
    label: "Neutral by design",
    body: "First-person, parent-attributed language across every reflection. No accusatory phrasing.",
  },
  {
    icon: ShieldCheck,
    label: "Safety-gated",
    body: "Family-violence safety screen precedes any co-parent invite. High-concern flows are re-routed.",
  },
  {
    icon: Lock,
    label: "HIPAA + HB 300 aware",
    body: "PHI access logs, consent-gated shares, revocable links, and Virtru-encrypted email option.",
  },
  {
    icon: FileText,
    label: "Court-facing disclaimers",
    body: "Every PDF explicitly states it is advisory prep material — not a court finding.",
  },
];

export default function ForProfessionals() {
  return (
    <div className="min-h-screen bg-white" data-testid="for-professionals-page">
      {/* Top nav strip */}
      <header className="px-5 sm:px-8 py-5 border-b border-[#E5E0EE] bg-white/80 backdrop-blur-sm sticky top-0 z-30">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-[#4B4567] hover:text-[#1A1330]"
            data-testid="for-pros-back-home"
          >
            <ArrowLeft size={14} /> SA CoParents home
          </Link>
          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              to="/samples"
              className="text-xs sm:text-sm font-semibold text-[#3D1A78] hover:underline inline-flex items-center gap-1"
              data-testid="for-pros-samples-link"
            >
              <BookOpen size={12} /> Sample library
            </Link>
            <Link
              to="/register"
              className="text-xs sm:text-sm font-semibold text-white bg-[#3D1A78] hover:bg-[#2a0f5f] px-3 py-1.5 rounded-full transition-colors inline-flex items-center gap-1"
              data-testid="for-pros-signup"
            >
              Create account <ArrowRight size={12} />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main id="main-content">
      <section className="px-5 sm:px-8 py-12 sm:py-16 bg-white border-b border-[#E5E0EE]">
        <div className="max-w-6xl mx-auto">
          <div className="inline-flex items-center gap-2 rounded-full bg-white border border-[#D6CFE8] px-3 py-1 mb-6" data-testid="for-pros-eyebrow">
            <Award size={12} className="text-[#3D1A78]" />
            <span className="text-[0.6875rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              For mediators &amp; family attorneys
            </span>
          </div>
          <h1
            className="font-serif text-4xl sm:text-5xl lg:text-6xl text-[#1A1330] leading-[1.05] tracking-tight max-w-4xl"
            data-testid="for-pros-headline"
          >
            SA CoParents for mediation practices.
          </h1>
          <p
            className="mt-6 text-base sm:text-lg text-[#4B4567] leading-relaxed max-w-3xl"
            data-testid="for-pros-supporting-copy"
          >
            SA CoParents produces neutral, mediator-facing preparation
            artefacts from structured parent reflections — Foundation
            Statement, Communication Reflection, Activities Cost Split,
            and the six-topic Joint Alignment compare. Every artefact
            is non-diagnostic, non-adjudicative, and disclaimed on the
            first page.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to="/professional/joint-alignment/new"
              className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-5 py-2.5 text-sm font-semibold transition-colors"
              data-testid="for-pros-create-case-cta"
            >
              <Sparkles size={14} /> Create a Joint Alignment case
            </Link>
            <Link
              to="/professional/joint-alignment/mine"
              className="inline-flex items-center gap-2 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-5 py-2.5 text-sm font-semibold transition-colors"
              data-testid="for-pros-manage-cases-cta"
            >
              Manage my cases
            </Link>
            <Link
              to="/samples"
              className="inline-flex items-center gap-2 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-5 py-2.5 text-sm font-semibold transition-colors"
              data-testid="for-pros-primary-cta"
            >
              Browse sample reports <ArrowRight size={14} />
            </Link>
            <a
              href="mailto:mattsossi@bsossi.com?subject=SA%20CoParents%20-%20Professional%20enquiry"
              className="inline-flex items-center gap-2 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-5 py-2.5 text-sm font-semibold transition-colors"
              data-testid="for-pros-contact-cta"
            >
              <Mail size={14} /> Contact us
            </a>
          </div>

          {/* 60-second ElevenLabs-voiced audio explainer. Lazy — never
              fires the TTS endpoint until a visitor clicks Play. */}
          <div className="mt-8 max-w-2xl">
            <ProfessionalsIntroAudio />
          </div>
        </div>
      </section>

      {/* Preferred professionals — small directory strip so a
          visitor sees at a glance that real practitioners already
          use the tool. Hidden if the endpoint returns zero rows. */}
      <PreferredProfessionalsStrip />

      {/* Four-step Align workflow — mirrors the exact language on
          the Landing ecosystem strip so both sites use the same
          vocabulary. Sits directly under the hero so a professional
          scanning the page sees WHAT their workflow looks like before
          the FAQ dives into policy detail. */}
      <section
        className="px-5 sm:px-8 py-14 sm:py-20 bg-white border-b border-[#E5E0EE]"
        data-testid="for-pros-align-workflow"
      >        <div className="max-w-6xl mx-auto">
          <div className="max-w-2xl">
            <div className="eyebrow mb-2">Your workflow on SA CoParents Align</div>
            <h2 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
              Invite. Compare. Identify Alignment. Guide Conversation.
            </h2>
            <p className="mt-4 text-sm sm:text-base text-[#4B4567] leading-relaxed">
              Four discrete steps. Same clinical-neutral language on
              both sites — so parents and professionals see the same
              framing whether they arrive from sacoparentsapp.online
              or sacoparentsalign.com.
            </p>
          </div>

          <ol
            className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
            data-testid="for-pros-align-workflow-steps"
          >
            {ALIGN_WORKFLOW.map((step, i) => {
              const Icon = step.icon;
              return (
                <li
                  key={step.key}
                  className="relative rounded-2xl border-2 border-[#E5E0EE] hover:border-[#3D1A78] bg-white p-5 transition-colors flex flex-col"
                  data-testid={`for-pros-align-step-${step.key}`}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <div className="shrink-0 w-10 h-10 rounded-2xl bg-[#3D1A78] text-white flex items-center justify-center">
                      <Icon size={18} strokeWidth={2.2} />
                    </div>
                    <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
                      Step {i + 1}
                    </div>
                  </div>
                  <div className="font-serif text-lg text-[#1A1330] leading-tight">
                    {step.label}
                  </div>
                  <p className="mt-2 text-[0.8125rem] text-[#4B4567] leading-relaxed">
                    {step.body}
                  </p>
                </li>
              );
            })}
          </ol>
        </div>
      </section>

      {/* Four-highlight strip */}
      <section className="px-5 sm:px-8 py-10 border-y border-[#E5E0EE] bg-[#FAF8FD]">
        <div className="max-w-6xl mx-auto grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {HIGHLIGHTS.map((h) => {
            const Icon = h.icon;
            return (
              <div
                key={h.label}
                className="flex items-start gap-3"
                data-testid={`for-pros-highlight-${h.label.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <div className="shrink-0 w-10 h-10 rounded-2xl bg-[#EFE9F9] text-[#3D1A78] flex items-center justify-center">
                  <Icon size={18} />
                </div>
                <div className="min-w-0">
                  <div className="text-[0.8125rem] font-semibold text-[#1A1330]">
                    {h.label}
                  </div>
                  <div className="text-xs text-[#4B4567] mt-0.5 leading-relaxed">
                    {h.body}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* FAQ block — 7 items */}
      <section className="px-5 sm:px-8 py-14 sm:py-20">
        <div className="max-w-4xl mx-auto">
          <div className="eyebrow mb-2">Questions we hear often</div>
          <h2 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mb-3">
            Straight answers, before you recommend us.
          </h2>
          <p className="text-sm sm:text-base text-[#4B4567] max-w-2xl leading-relaxed">
            We built this app assuming professionals would scrutinise every
            claim. Here's what a mediator or attorney typically asks before
            accepting a parent-generated report.
          </p>

          <div className="mt-10 space-y-4" data-testid="for-pros-faqs">
            {FAQS.map((f, i) => {
              const Icon = f.icon;
              return (
                <details
                  key={f.q}
                  className="group rounded-2xl border border-[#E5E0EE] bg-white hover:border-[#3D1A78] transition-colors"
                  data-testid={`for-pros-faq-${i}`}
                >
                  <summary
                    className="cursor-pointer list-none px-5 py-4 flex items-start gap-4"
                    data-testid={`for-pros-faq-${i}-summary`}
                  >
                    <div className="shrink-0 w-10 h-10 rounded-2xl bg-[#EFE9F9] text-[#3D1A78] flex items-center justify-center">
                      <Icon size={18} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[15px] sm:text-base font-semibold text-[#1A1330] leading-snug">
                        {f.q}
                      </div>
                    </div>
                    <span className="shrink-0 text-[#3D1A78] text-lg group-open:hidden">
                      +
                    </span>
                    <span className="shrink-0 text-[#3D1A78] text-lg hidden group-open:inline">
                      −
                    </span>
                  </summary>
                  <div
                    className="px-5 pb-5 pl-[76px] text-sm text-[#4B4567] leading-relaxed"
                    data-testid={`for-pros-faq-${i}-body`}
                  >
                    {f.a}
                  </div>
                </details>
              );
            })}
          </div>
        </div>
      </section>

      {/* Closing CTA */}
      <section className="px-5 sm:px-8 py-14 sm:py-20 bg-[#1A1330] text-white">
        <div className="max-w-4xl mx-auto text-center">
          <Heart size={28} className="mx-auto text-[#CFC1EA] mb-4" />
          <h2 className="font-serif text-3xl sm:text-4xl leading-tight">
            Review a sample before you refer.
          </h2>
          <p className="mt-4 text-[#CFC1EA] max-w-2xl mx-auto text-sm sm:text-base leading-relaxed">
            The full sample library is public — no signup required.
            Reach out via email when you&rsquo;d like to discuss
            introducing SA CoParents to a specific case or practice.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              to="/samples"
              className="inline-flex items-center gap-2 rounded-full bg-white text-[#3D1A78] hover:bg-[#F5F1FB] px-5 py-2.5 text-sm font-semibold transition-colors"
              data-testid="for-pros-closing-samples"
            >
              <BookOpen size={14} /> Open sample library
            </Link>
            <a
              href="mailto:mattsossi@bsossi.com?subject=SA%20CoParents%20-%20Professional%20enquiry"
              className="inline-flex items-center gap-2 rounded-full border border-white/40 text-white hover:bg-white/10 px-5 py-2.5 text-sm font-semibold transition-colors"
              data-testid="for-pros-closing-contact"
            >
              <MessageSquare size={14} /> Contact us
            </a>
          </div>

          <div className="mt-10 text-[0.6875rem] uppercase tracking-[0.22em] text-[#CFC1EA]">
            SA CoParents · San Antonio, Texas
          </div>
        </div>
      </section>
      </main>

      {/* Footer legal strip */}
      <footer className="px-5 sm:px-8 py-6 border-t border-[#E5E0EE] bg-[#FAF8FD]">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs text-[#4B4567]">
          <div>Advisory prep tools — not legal advice, therapy, or diagnosis.</div>
          <div className="flex items-center gap-4">
            <Link to="/privacy-notice" className="hover:underline" data-testid="for-pros-footer-privacy">Privacy Notice</Link>
            <Link to="/legal/hipaa" className="hover:underline" data-testid="for-pros-footer-hipaa">HIPAA</Link>
            <Link to="/terms" className="hover:underline" data-testid="for-pros-footer-terms">Terms</Link>
            <Link to="/samples" className="hover:underline inline-flex items-center gap-1" data-testid="for-pros-footer-samples">
              Samples <ExternalLink size={10} />
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
