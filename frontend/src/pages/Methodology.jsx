import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, FlaskConical, TriangleAlert, Info } from "lucide-react";
import MasicComparison from "../components/MasicComparison";
import ReviewerPanelCard from "../components/ReviewerPanelCard";

const LAST_UPDATED = "February 26, 2026";

/**
 * Methodology & Assessment Validation
 *
 * Publishes the sourcing, scoring logic, and known limitations of every
 * scored assessment inside SA CoParents. Explicitly clarifies that these
 * are educational readiness snapshots — not clinical instruments.
 */
export default function Methodology() {
  return (
    <div className="min-h-screen gentle-bg" data-testid="methodology-page">
      <div className="max-w-3xl mx-auto px-5 sm:px-6 py-10 sm:py-14">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-[#2A0F5F] hover:text-[#3D1A78] mb-6"
          data-testid="methodology-back-link"
        >
          <ArrowLeft size={14} /> Back to SA CoParents
        </Link>

        <div className="eyebrow mb-3">Methodology & Validation</div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] mb-2 leading-tight">
          How we score you — and what it means.
        </h1>
        <p className="text-sm text-[#857E9C] mb-8">Last updated: {LAST_UPDATED}</p>

        <div
          className="rounded-2xl border border-[#F5C147]/40 bg-[#FFF8E6] p-4 flex gap-3 items-start not-prose mb-8"
          role="note"
          data-testid="methodology-disclaimer"
        >
          <TriangleAlert size={18} className="text-[#B27700] mt-0.5 shrink-0" />
          <p className="text-sm text-[#5C4200] leading-relaxed">
            <strong>These are readiness snapshots, not clinical diagnoses.</strong>{" "}
            No score on this app substitutes for evaluation by a licensed
            mediator, family lawyer, therapist, or physician. Every scored
            output ends with "consider talking to a qualified professional."
          </p>
        </div>

        <Prose>
          <p>
            SA CoParents is an educational and preparation tool. Whenever we
            show you a score, this page tells you exactly where that number
            came from, what it measures, and where it stops.
          </p>

          <H2>1. Mediation Readiness (0–100)</H2>
          <p><strong>What it measures.</strong> Your preparation across four dimensions:</p>
          <ul>
            <li><strong>Child-focused focus</strong> — the specificity + child-directed framing of the goals you named.</li>
            <li><strong>Priorities clarity</strong> — whether you've ranked and rationalised your top mediation topics.</li>
            <li><strong>Communication readiness</strong> — your self-assessed patterns around requests, listening, and de-escalation.</li>
            <li><strong>Emotional regulation</strong> — the presence of concrete plans for reacting to triggers.</li>
          </ul>
          <p>
            <strong>How it's calculated.</strong> Deterministic rule-based scoring
            of the fields you fill in: word-count thresholds, presence of
            required components, penalty for one-word answers. The exact rules
            live in <code>backend/summary_scoring.py</code>. There is no ML
            model in this score.
          </p>
          <p>
            <strong>What it does NOT measure.</strong> The score cannot see
            emotional labor, real-world power dynamics, or coercion. A high
            score means you've written a lot of child-focused content — it
            does not mean mediation will be safe or successful for your
            specific family.
          </p>

          <H2>2. Family Violence and Communication Safety Screen</H2>
          <p>
            <strong>Source instruments.</strong> The Section-1 immediate-safety
            screen is adapted from the widely-used <em>Danger Assessment</em>{" "}
            (Campbell, 1986) and the <em>HITS</em> screening tool (Sherin
            et&nbsp;al., 1998), with wording tailored for co-parenting contexts.
            Section 2 (communication readiness) is original but reviewed
            against the WEB Scale and the ODARA framework.
          </p>
          <p>
            <strong>Output.</strong> A four-level communication pathway —
            <em> No-direct contact · Structured written · Assisted · Cooperative</em>{" "}
            — with an explanation of why. Any single "yes" in the Section-1
            immediate-safety questions triggers the No-direct-contact pathway.
          </p>
          <p>
            <strong>Important limits.</strong> This is a{" "}
            <strong>screening tool, not a validated clinical assessment</strong>.
            It is <strong>not</strong> the Danger Assessment, MASIC-S, or
            HITS. The Danger Assessment estimates lethal / near-lethal
            risk in abusive intimate relationships and its scoring is tied
            to specialized training; HITS was validated in family-practice
            settings, not in divorce, custody, or mediation populations.
            This screen has <strong>not been independently validated</strong>{" "}
            in custody or mediation populations, and its scoring is
            heuristic. It should not be used in court proceedings without
            accompanying professional evaluation. Texas crisis hotlines are
            surfaced in every result regardless of level, and the "pathway"
            and "Texas resources" sections of the PDF cannot be hidden by
            the user when sharing.
          </p>
          <p>
            <strong>What this screen decides — and what it does not.</strong>{" "}
            The screen recommends a <em>communication structure</em> for the
            parent to consider. It does <strong>not</strong> decide
            mediation suitability, visitation, custody, protective orders,
            or any other legal or clinical outcome. Decisions of that
            weight require a qualified human assessment (family-law
            attorney, licensed clinician or forensic evaluator, DV
            advocate). For Level 1 &amp; 2 results the app suppresses AI
            communication coaching, because coaching a survivor to
            communicate "better" with a coercive co-parent shifts
            responsibility onto the person experiencing harm.
          </p>

          <MasicComparison />

          <ReviewerPanelCard />

          <H2>3. AI Coach responses</H2>
          <p>
            The interactive coach uses Anthropic Claude 4.5 via the Emergent
            LLM key. Prompts are constrained by a system instruction that
            forbids diagnosis, dosage advice, legal advice, or crisis triage.
            When triggered by risk keywords, the coach immediately surfaces
            local hotlines and offers to switch to the Safety Screen.
            AI responses are <strong>not stored on Anthropic's servers</strong>{" "}
            for training. See our <Link to="/privacy" className="text-[#2A0F5F] underline">Privacy Policy</Link> for details.
          </p>

          <H2>5. "Your next three steps" recommendation engine</H2>
          <p>
            Deterministic, not AI. Given your latest scores across all
            assessments, a fixed decision table picks up to three
            highest-leverage next actions. Rule source:{" "}
            <code>backend/next_steps_routes.py</code>. This means the same
            inputs always produce the same recommendations — an important
            transparency guarantee.
          </p>

          <H2>Where we lack empirical validation</H2>
          <p>
            SA CoParents is a new tool. The Mediation Readiness, Special
            Needs 7-domain, and Communication Readiness scores are{" "}
            <strong>not yet externally validated</strong> by a peer-reviewed
            study. We are actively collecting anonymized outcome signals
            (with opt-in consent) to publish reliability + concurrent-validity
            work in future.
          </p>
          <p>
            In the meantime, use every score as a <strong>conversation
            starter</strong> with your mediator or therapist — not as the
            last word.
          </p>

          <H2>Change log &amp; scoring history</H2>
          <p>
            Every meaningful change to a scoring rule is recorded in the
            public repository at{" "}
            <a href="https://github.com/mattsossi-cmyk/sacoparents-app" target="_blank" rel="noopener noreferrer" className="text-[#2A0F5F] underline">github.com/mattsossi-cmyk/sacoparents-app</a>.
            If a rule change would materially shift your historical scores,
            we recompute in a way that keeps your longitudinal chart honest:
            we snapshot the version tag alongside each stored score, and only
            recompute forward.
          </p>

          <H2>Questions or peer review requests</H2>
          <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4 not-prose flex gap-3 items-start">
            <FlaskConical size={18} className="text-[#3D1A78] mt-0.5 shrink-0" />
            <div className="text-sm text-[#4B4567] leading-relaxed">
              We welcome academic collaboration. If you're a researcher or
              clinician who'd like to review our rules, please email{" "}
              <a href="mailto:mattsossi@bsossi.com" className="text-[#2A0F5F] underline">mattsossi@bsossi.com</a>{" "}
              and we'll set up a call within 5 business days.
            </div>
          </div>

          <p className="text-xs text-[#857E9C] italic mt-8">
            SA CoParents · 16607 Blanco #703, San Antonio, Texas 78232
          </p>
        </Prose>
      </div>
    </div>
  );
}

function H2({ children }) {
  return <h2 className="font-serif text-2xl text-[#1A1330] mt-10 mb-3">{children}</h2>;
}

function Prose({ children }) {
  return (
    <div className="prose-soft space-y-3 text-[#1A1330] leading-relaxed [&_p]:text-[#4B4567] [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1.5 [&_li]:text-[#4B4567] [&_strong]:text-[#1A1330] [&_em]:text-[#3D1A78] [&_code]:bg-[#EFE9F9] [&_code]:text-[#3D1A78] [&_code]:rounded [&_code]:px-1 [&_code]:text-[13px] text-[15px]">
      {children}
    </div>
  );
}
