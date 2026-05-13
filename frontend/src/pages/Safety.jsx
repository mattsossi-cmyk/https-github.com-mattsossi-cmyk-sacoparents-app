import React, { useCallback, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Phone,
  MessageSquare,
  Globe,
  ShieldAlert,
  ArrowLeft,
  ExternalLink,
  Home,
  Shield,
} from "lucide-react";

const NATIONAL_RESOURCES = [
  {
    id: "ndvh",
    name: "National Domestic Violence Hotline",
    phone: "1-800-799-7233",
    phoneHref: "tel:18007997233",
    text: 'Text "START" to 88788',
    textHref: "sms:88788?&body=START",
    web: "https://www.thehotline.org",
    description:
      "24/7 confidential support for anyone experiencing or affected by domestic violence. Free, available in 200+ languages.",
  },
  {
    id: "988",
    name: "988 Suicide & Crisis Lifeline",
    phone: "988",
    phoneHref: "tel:988",
    text: 'Text "988" to 988',
    textHref: "sms:988?&body=988",
    web: "https://988lifeline.org",
    description:
      "24/7 free and confidential support for anyone in suicidal crisis or emotional distress. Call or text 988 anytime, from anywhere in the U.S.",
  },
  {
    id: "stronghearts",
    name: "StrongHearts Native Helpline",
    phone: "1-844-762-8483",
    phoneHref: "tel:18447628483",
    web: "https://strongheartshelpline.org",
    description:
      "Culturally-appropriate, anonymous, and confidential support for Native Americans and Alaska Natives affected by domestic, dating, and sexual violence.",
  },
  {
    id: "loveisrespect",
    name: "love is respect (for teens & young adults)",
    phone: "1-866-331-9474",
    phoneHref: "tel:18663319474",
    text: 'Text "LOVEIS" to 22522',
    textHref: "sms:22522?&body=LOVEIS",
    web: "https://www.loveisrespect.org",
    description:
      "Support, info, and advocacy for young people in dating relationships, including digital abuse.",
  },
  {
    id: "rainn",
    name: "RAINN — Sexual Assault Hotline",
    phone: "1-800-656-4673",
    phoneHref: "tel:18006564673",
    web: "https://www.rainn.org",
    description:
      "24/7 sexual assault hotline run by the Rape, Abuse & Incest National Network. Free and confidential.",
  },
];

const SAN_ANTONIO_RESOURCES = [
  {
    id: "fvps",
    name: "Family Violence Prevention Services / Battered Women & Children's Shelter",
    phone: "210-733-8810",
    phoneHref: "tel:2107338810",
    web: "https://fvps.org",
    description:
      "San Antonio's primary domestic violence shelter and crisis hotline. 24/7 emergency shelter, counseling, and legal advocacy.",
  },
  {
    id: "bcfjc",
    name: "Bexar County Family Justice Center",
    phone: "210-631-0100",
    phoneHref: "tel:2106310100",
    web: "https://www.bexar.org/3206/Family-Justice-Center",
    description:
      "One-stop center co-locating advocates, law enforcement, prosecutors, and civil legal services for survivors in Bexar County.",
  },
  {
    id: "peace",
    name: "PEACE Initiative",
    phone: "210-533-2729",
    phoneHref: "tel:2105332729",
    web: "https://peaceinitiative.net",
    description:
      "Education, advocacy, and survivor-led support groups for women and children affected by domestic violence in San Antonio.",
  },
  {
    id: "saps_safe",
    name: "City of San Antonio — Stand Up SA / Collaborative Commission",
    web: "https://www.sa.gov/Directory/Departments/Metro-Health/Services/Violence-Prevention",
    description:
      "City-wide violence prevention resources, including safety planning and connections to advocates.",
  },
];

const EMERGENCY = {
  name: "Emergency — call 911",
  phone: "911",
  phoneHref: "tel:911",
};

function quickExit() {
  try {
    // Best-effort: scrub the current entry and replace the tab with a neutral site.
    // history.back() after replace ensures the back button doesn't return here.
    window.history.replaceState(null, "", "/");
    window.location.replace("https://www.google.com/search?q=weather");
  } catch {
    window.location.href = "https://www.google.com";
  }
}

export default function Safety() {
  // Press ESC to quick-exit (common safety convention)
  const onKey = useCallback((e) => {
    if (e.key === "Escape") {
      e.preventDefault();
      quickExit();
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onKey]);

  return (
    <div className="min-h-screen gentle-bg">
      {/* Top safety bar with Quick Exit */}
      <div
        className="sticky top-0 z-40 backdrop-blur-md bg-[#C28771]/10 border-b border-[#C28771]/25"
        data-testid="safety-top-bar"
      >
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between gap-3">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-[#5C6B64] hover:text-[#2A3631]"
            data-testid="safety-back-home"
          >
            <ArrowLeft size={14} />
            Back to SA Coparents
          </Link>
          <button
            type="button"
            onClick={quickExit}
            className="inline-flex items-center gap-2 rounded-full bg-[#C28771] hover:bg-[#a87560] text-white px-5 py-2.5 text-sm font-medium shadow-sm transition-colors"
            data-testid="safety-quick-exit-button"
            aria-label="Quick exit — leave this page immediately"
            title="Press the ESC key any time to leave this page"
          >
            <Home size={14} />
            Quick exit
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-12 fade-up">
        {/* Hero */}
        <div className="card-soft p-8 sm:p-10 mb-8 relative overflow-hidden">
          <div className="absolute -top-12 -right-12 w-48 h-48 rounded-full bg-[#C28771]/10" />
          <div className="relative">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-[#C28771]/15 text-[#C28771] grid place-items-center">
                <ShieldAlert size={18} />
              </div>
              <div className="eyebrow">Safety resources</div>
            </div>
            <h1 className="font-serif text-4xl sm:text-5xl text-[#2A3631] leading-tight mb-4">
              You are not alone. Help is available.
            </h1>
            <p className="text-[#5C6B64] leading-relaxed max-w-2xl">
              If you, your child, or someone you love is experiencing domestic
              violence, intimate partner violence, or feels unsafe — please reach out.
              The contacts below are confidential, free, and staffed by trained
              advocates. SA Coparents is a preparation tool — it is not a substitute
              for professional safety planning.
            </p>

            <div
              className="mt-6 rounded-2xl bg-[#C28771] text-white p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
              data-testid="safety-emergency-banner"
            >
              <div>
                <div className="text-xs uppercase tracking-[0.2em] opacity-90">
                  In immediate danger
                </div>
                <div className="font-serif text-2xl">{EMERGENCY.name}</div>
              </div>
              <a
                href={EMERGENCY.phoneHref}
                className="inline-flex items-center gap-2 rounded-full bg-white text-[#C28771] px-5 py-2.5 font-medium hover:bg-[#FDFAF3] transition-colors"
                data-testid="safety-call-911"
              >
                <Phone size={16} /> Call 911
              </a>
            </div>
          </div>
        </div>

        {/* National */}
        <SectionHeading
          eyebrow="National (United States)"
          title="24/7 confidential hotlines"
        />
        <div className="grid sm:grid-cols-2 gap-5 mb-12">
          {NATIONAL_RESOURCES.map((r) => (
            <ResourceCard key={r.id} r={r} />
          ))}
        </div>

        {/* San Antonio */}
        <SectionHeading
          eyebrow="San Antonio & Bexar County"
          title="Local support, shelters & advocacy"
        />
        <div className="grid sm:grid-cols-2 gap-5 mb-12">
          {SAN_ANTONIO_RESOURCES.map((r) => (
            <ResourceCard key={r.id} r={r} />
          ))}
        </div>

        {/* Parallel Parenting provision */}
        <ParallelParentingSection />

        {/* Safety planning tips */}
        <SectionHeading eyebrow="A gentle reminder" title="Privacy on this device" />
        <div className="card-soft p-7 mb-12">
          <ul className="space-y-3 text-[#2A3631]">
            <li className="flex gap-3">
              <span className="w-1.5 h-1.5 rounded-full bg-[#849D8E] mt-2.5 shrink-0" />
              <span>
                Use the <strong>Quick exit</strong> button at the top, or press the{" "}
                <kbd className="px-1.5 py-0.5 rounded bg-[#F5F3E9] text-xs">ESC</kbd>{" "}
                key, to leave this page instantly.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="w-1.5 h-1.5 rounded-full bg-[#849D8E] mt-2.5 shrink-0" />
              <span>
                Consider browsing in <strong>private / incognito mode</strong>, or
                clearing your browser history after visiting safety resources.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="w-1.5 h-1.5 rounded-full bg-[#849D8E] mt-2.5 shrink-0" />
              <span>
                If you suspect your phone or computer is being monitored, please call
                a hotline from a different device — a friend's phone, a public library,
                or a workplace computer.
              </span>
            </li>
            <li className="flex gap-3">
              <span className="w-1.5 h-1.5 rounded-full bg-[#849D8E] mt-2.5 shrink-0" />
              <span>
                The National DV Hotline can help you build a personalized safety plan,
                even before you decide on next steps.
              </span>
            </li>
          </ul>
        </div>

        <div className="text-center text-xs text-[#8A9A92] italic">
          Information current as of 2026. If a number has changed, please visit the
          linked website or call 211 for local resource referrals.
        </div>
      </div>
    </div>
  );
}

function SectionHeading({ eyebrow, title }) {
  return (
    <div className="mb-5">
      <div className="eyebrow mb-2">{eyebrow}</div>
      <h2 className="font-serif text-2xl sm:text-3xl text-[#2A3631]">{title}</h2>
    </div>
  );
}

function ResourceCard({ r }) {
  return (
    <div className="card-soft p-6" data-testid={`safety-resource-${r.id}`}>
      <div className="font-serif text-xl text-[#2A3631] mb-2">{r.name}</div>
      <p className="text-sm text-[#5C6B64] mb-4 leading-relaxed">{r.description}</p>
      <div className="flex flex-wrap gap-2">
        {r.phone && (
          <a
            href={r.phoneHref}
            className="inline-flex items-center gap-2 rounded-full bg-[#849D8E] hover:bg-[#6C8576] text-white px-4 py-2 text-sm transition-colors"
            data-testid={`safety-call-${r.id}`}
          >
            <Phone size={14} /> {r.phone}
          </a>
        )}
        {r.text && (
          <a
            href={r.textHref}
            className="inline-flex items-center gap-2 rounded-full bg-[#F5F3E9] hover:bg-[#E8ECE9] text-[#2A3631] px-4 py-2 text-sm transition-colors"
            data-testid={`safety-text-${r.id}`}
          >
            <MessageSquare size={14} /> {r.text}
          </a>
        )}
        {r.web && (
          <a
            href={r.web}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-full bg-[#F5F3E9] hover:bg-[#E8ECE9] text-[#2A3631] px-4 py-2 text-sm transition-colors"
            data-testid={`safety-web-${r.id}`}
          >
            <Globe size={14} /> Website <ExternalLink size={12} />
          </a>
        )}
      </div>
    </div>
  );
}

function ParallelParentingSection() {
  return (
    <section className="mb-12" data-testid="safety-parallel-parenting-section">
      <SectionHeading
        eyebrow="When co-parenting isn't safe"
        title="Parallel parenting: a safer framework"
      />

      {/* Lead card */}
      <div className="card-soft p-7 sm:p-8 mb-5 relative overflow-hidden">
        <div className="absolute -top-10 -left-10 w-40 h-40 rounded-full bg-[#849D8E]/10" />
        <div className="relative">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-[#849D8E]/15 text-[#5C7A6A] grid place-items-center">
              <Shield size={18} />
            </div>
            <div className="eyebrow">A different framework</div>
          </div>
          <p className="text-[#2A3631] leading-relaxed mb-4">
            When there has been domestic violence, parenting arrangements require a
            very different framework than traditional co-parenting models. In these
            situations, the priority is not improving the parental relationship —
            it is protecting the physical and psychological safety of the child and
            the survivor parent.
          </p>
          <p className="text-[#5C6B64] leading-relaxed">
            <strong className="text-[#2A3631]">Parallel parenting</strong> is often
            considered the safer alternative because it minimizes direct interaction
            between parents while still allowing the child to maintain structured
            contact with both parents when appropriate.
          </p>
        </div>
      </div>

      {/* Why traditional co-parenting fails */}
      <PPCard title="Why traditional co-parenting often fails in domestic violence cases">
        <p className="text-[#5C6B64] mb-3">Traditional co-parenting assumes:</p>
        <PPList items={[
          "Mutual respect",
          "Ability to communicate safely",
          "Shared decision-making",
          "Emotional regulation",
          "Basic trust",
        ]} />
        <p className="text-[#5C6B64] mt-5 mb-3">
          Domestic violence undermines all of these assumptions. Abuse dynamics often
          continue after separation through:
        </p>
        <PPList items={[
          "Harassing texts or calls",
          "Manipulation through the children",
          "Financial control",
          "False allegations",
          "Intimidation during exchanges",
          "Monitoring the survivor parent's activities",
          "Undermining parenting authority",
        ]} />
        <p className="text-[#5C6B64] mt-5 italic">
          In these cases, requiring frequent communication can unintentionally
          create continued access for coercive control.
        </p>
      </PPCard>

      {/* What parallel parenting means */}
      <PPCard title="What parallel parenting means">
        <p className="text-[#5C6B64] mb-4">
          Parallel parenting is a high-boundary parenting model designed to reduce
          conflict and limit opportunities for abuse. The parents disengage from each
          other as much as possible while maintaining clear parenting structures.
        </p>
        <div className="rounded-2xl bg-[#F5F3E9] p-5 mb-5">
          <div className="text-xs uppercase tracking-[0.2em] text-[#8A9A92] mb-2">
            The focus shifts from
          </div>
          <div className="font-serif text-lg text-[#2A3631] italic mb-3">
            "How can parents work together?"
          </div>
          <div className="text-xs uppercase tracking-[0.2em] text-[#8A9A92] mb-2">to</div>
          <div className="font-serif text-lg text-[#5C7A6A] italic">
            "How can the child remain safe and stable with minimal parental interaction?"
          </div>
        </div>
        <p className="text-[#5C6B64] mb-3 font-medium text-[#2A3631]">
          Core features of parallel parenting
        </p>
        <PPList items={[
          "Limited direct communication",
          "Structured schedules",
          "Written-only communication when possible",
          "Clear boundaries",
          "Independent decision-making in each household",
          "Detailed court orders or parenting plans",
          "Neutral exchange locations",
          "Third-party communication platforms (e.g., OurFamilyWizard)",
        ]} />
      </PPCard>

      {/* Concerns */}
      <PPCard title="Parenting concerns in domestic violence cases">
        <PPSubsection
          number="1"
          title="Ongoing coercive control"
          lead="Even after separation, abuse may continue through parenting interactions."
        >
          <p className="text-[#5C6B64] mb-2 text-sm">Examples:</p>
          <PPList items={[
            "Excessive messaging",
            "Threats disguised as parenting concerns",
            "Last-minute schedule changes",
            "Using children to gather information",
            "Refusing to return children on time",
            "Creating crises to maintain control",
          ]} />
          <p className="text-[#5C6B64] mt-4 italic text-sm">
            Parallel parenting helps reduce these opportunities by limiting
            discretionary contact.
          </p>
        </PPSubsection>

        <PPSubsection
          number="2"
          title="Child emotional safety"
          lead="Children exposed to domestic violence may experience:"
        >
          <PPList items={[
            "Anxiety",
            "Hypervigilance",
            "Loyalty conflicts",
            "Trauma symptoms",
            "Parentification",
            "Fear during exchanges",
          ]} />
          <p className="text-[#5C6B64] mt-4 mb-2 text-sm">
            Children often benefit from predictable routines and reduced parental
            conflict exposure. A parenting plan should address:
          </p>
          <PPList items={[
            "Consistent routines",
            "Transition supports",
            "Emotional regulation strategies",
            "Therapy access if needed",
            "Safe exchange procedures",
          ]} />
        </PPSubsection>

        <PPSubsection
          number="3"
          title="Communication challenges"
          lead="Direct communication may retraumatize the survivor parent or escalate conflict."
        >
          <p className="text-[#5C6B64] mb-2 text-sm">Helpful strategies include:</p>
          <PPList items={[
            "Written-only communication",
            "BIFF responses (Brief, Informative, Friendly, Firm)",
            "Communication restricted to child-related topics",
            "Scheduled communication windows",
            "Use of monitored parenting apps",
          ]} />
          <p className="text-[#5C6B64] mt-4 mb-2 text-sm">Some cases require:</p>
          <PPList items={[
            "Third-party intermediaries",
            "Parenting coordinators",
            "Attorneys handling communication",
          ]} />
        </PPSubsection>

        <PPSubsection
          number="4"
          title="Decision-making authority"
          lead="Joint decision-making can become another arena for power struggles."
        >
          <p className="text-[#5C6B64] mb-2 text-sm">
            In high-conflict or abusive dynamics, courts sometimes allocate:
          </p>
          <PPList items={[
            "Sole decision-making authority in certain areas",
            "Tie-breaking authority",
            "Separate spheres of responsibility",
          ]} />
          <p className="text-[#5C6B64] mt-4 mb-2 text-sm">For example:</p>
          <PPList items={[
            "One parent handles medical decisions",
            "One parent handles educational decisions",
          ]} />
          <p className="text-[#5C6B64] mt-4 italic text-sm">
            This reduces repeated conflict and manipulation.
          </p>
        </PPSubsection>

        <PPSubsection
          number="5"
          title="Exchanges and safety planning"
          lead="Exchanges are often high-risk moments."
        >
          <p className="text-[#5C6B64] mb-2 text-sm">Safety-focused considerations:</p>
          <PPList items={[
            "Neutral public locations",
            "School-based exchanges",
            "Third-party transport",
            "Staggered arrival/departure times",
            "No-contact exchange protocols",
          ]} />
          <p className="text-[#5C6B64] mt-4 mb-2 text-sm">In severe cases:</p>
          <PPList items={[
            "Supervised visitation may be necessary",
            "Protective orders may affect parenting arrangements",
          ]} />
        </PPSubsection>

        <PPSubsection
          number="6"
          title="Children as messengers"
          lead="One major concern is children being drawn into adult conflict."
          last
        >
          <p className="text-[#5C6B64] mb-2 text-sm">Children should never:</p>
          <PPList items={[
            "Carry messages",
            "Report on the other parent",
            "Relay financial information",
            "Be pressured to \u201Cchoose sides\u201D",
          ]} />
          <p className="text-[#5C6B64] mt-4 italic text-sm">
            Parallel parenting aims to create emotional separation between the
            parental conflict and the child's experience.
          </p>
        </PPSubsection>
      </PPCard>

      {/* Clinical / Legal */}
      <PPCard title="Important clinical and legal considerations">
        <div className="mb-5">
          <div className="font-serif text-lg text-[#2A3631] mb-2">
            Domestic violence is not always "mutual conflict"
          </div>
          <p className="text-[#5C6B64] text-sm mb-2">Professionals must distinguish:</p>
          <div className="flex flex-col sm:flex-row items-stretch gap-3">
            <div className="flex-1 rounded-xl bg-[#F5F3E9] p-4 text-center">
              <div className="text-xs uppercase tracking-[0.2em] text-[#8A9A92] mb-1">From</div>
              <div className="text-[#2A3631]">High-conflict relationships</div>
            </div>
            <div className="self-center text-[#8A9A92] text-sm">vs.</div>
            <div className="flex-1 rounded-xl bg-[#C28771]/10 p-4 text-center">
              <div className="text-xs uppercase tracking-[0.2em] text-[#A26852] mb-1">To</div>
              <div className="text-[#2A3631]">Coercive controlling violence</div>
            </div>
          </div>
          <p className="text-[#5C6B64] text-sm mt-3 italic">
            Treating abuse as simply "poor communication" can endanger survivors
            and children.
          </p>
        </div>

        <div className="mb-5">
          <div className="font-serif text-lg text-[#2A3631] mb-2">
            Reunification and family therapy require caution
          </div>
          <p className="text-[#5C6B64] text-sm mb-2">
            Family therapy or co-parenting counseling may be inappropriate when:
          </p>
          <PPList items={[
            "There is fear or intimidation",
            "One parent controls the other",
            "Abuse is ongoing",
            "Accountability is absent",
          ]} />
          <p className="text-[#5C6B64] text-sm mt-3 italic">
            In some cases, conjoint therapy can increase risk.
          </p>
        </div>

        <div>
          <div className="font-serif text-lg text-[#2A3631] mb-2">
            Children may need individual support
          </div>
          <p className="text-[#5C6B64] text-sm mb-2">
            Children exposed to domestic violence may benefit from:
          </p>
          <PPList items={[
            "Trauma-informed therapy",
            "Play therapy",
            "Emotional regulation work",
            "Psychoeducation about conflict and safety",
          ]} />
          <p className="text-[#5C6B64] text-sm mt-3 italic">
            The therapeutic goal is often stabilization and safety — not forcing
            reconciliation between parents.
          </p>
        </div>
      </PPCard>

      {/* Effective plans */}
      <PPCard title="What effective parallel parenting plans usually include">
        <p className="text-[#5C6B64] mb-3">A strong plan often specifies:</p>
        <div className="grid sm:grid-cols-2 gap-x-6 gap-y-1">
          <PPList items={[
            "Exact exchange times and locations",
            "Communication methods",
            "Response time expectations",
            "Holiday schedules",
            "Medical and school procedures",
          ]} />
          <PPList items={[
            "Emergency protocols",
            "Rules regarding new partners",
            "Travel restrictions",
            "Dispute resolution procedures",
          ]} />
        </div>
        <p className="text-[#5C6B64] mt-5 italic">
          The more detailed the plan, the fewer opportunities exist for conflict
          escalation.
        </p>
      </PPCard>

      {/* Goal */}
      <div
        className="card-soft p-7 sm:p-8 relative overflow-hidden"
        data-testid="safety-pp-goal"
      >
        <div className="absolute -bottom-12 -right-12 w-48 h-48 rounded-full bg-[#849D8E]/10" />
        <div className="relative">
          <div className="eyebrow mb-3">The goal of parallel parenting</div>
          <h3 className="font-serif text-2xl sm:text-3xl text-[#2A3631] mb-4 leading-tight">
            Not closeness between parents — safety, stability, and predictability
            for the child.
          </h3>
          <p className="text-[#5C6B64] mb-4">Parallel parenting is about:</p>
          <PPList items={[
            "Reducing exposure to conflict",
            "Creating predictability",
            "Supporting child stability",
            "Protecting safety",
            "Allowing children to maintain relationships when appropriate",
          ]} />
          <p className="text-[#5C6B64] mt-5 text-sm">
            In some families, parallel parenting eventually evolves into healthier
            co-parenting. In others, long-term structured separation remains the
            safest and healthiest arrangement.
          </p>
        </div>
      </div>
    </section>
  );
}

function PPCard({ title, children }) {
  return (
    <details
      className="card-soft p-0 mb-5 group overflow-hidden"
      data-testid={`safety-pp-card-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40)}`}
    >
      <summary className="cursor-pointer list-none p-6 sm:p-7 flex items-start justify-between gap-4 hover:bg-[#F5F3E9]/40 transition-colors">
        <h3 className="font-serif text-xl sm:text-2xl text-[#2A3631] leading-snug">
          {title}
        </h3>
        <span className="shrink-0 mt-1 w-7 h-7 rounded-full bg-[#849D8E]/15 text-[#5C7A6A] grid place-items-center text-lg leading-none group-open:rotate-45 transition-transform">
          +
        </span>
      </summary>
      <div className="px-6 sm:px-7 pb-7 -mt-2">{children}</div>
    </details>
  );
}

function PPSubsection({ number, title, lead, children, last }) {
  return (
    <div className={last ? "" : "mb-6 pb-6 border-b border-[#E8ECE9]"}>
      <div className="flex items-baseline gap-3 mb-2">
        <span className="font-serif text-lg text-[#5C7A6A]">{number}.</span>
        <h4 className="font-serif text-lg text-[#2A3631]">{title}</h4>
      </div>
      {lead && <p className="text-[#5C6B64] text-sm mb-3">{lead}</p>}
      {children}
    </div>
  );
}

function PPList({ items }) {
  return (
    <ul className="space-y-2">
      {items.map((it) => (
        <li key={it} className="flex gap-3 text-[#2A3631] text-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-[#849D8E] mt-2 shrink-0" />
          <span>{it}</span>
        </li>
      ))}
    </ul>
  );
}

