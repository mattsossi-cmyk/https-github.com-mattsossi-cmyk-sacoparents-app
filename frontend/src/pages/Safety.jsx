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
