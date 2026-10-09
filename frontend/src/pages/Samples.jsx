/**
 * Samples.jsx — public sample-library page at `/samples`.
 *
 * A single browsable index of every PDF the app can produce. Public
 * (no auth required) so a mediator or attorney evaluating the tool
 * can see the full artefact library without signing up.
 *
 * Files live in `/app/frontend/public/downloads/` and are served
 * directly by the CRA static handler — no backend involvement.
 *
 * Grouped by category so a visitor can find what they need without
 * scrolling a long list.
 */
import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Brain,
  CalendarDays,
  Download,
  ExternalLink,
  FileText,
  GraduationCap,
  Handshake,
  Heart,
  MessageCircle,
  Palette,
  Search,
  ShieldAlert,
  Sparkles,
  Stethoscope,
  Users,
  X,
} from "lucide-react";

const CATEGORIES = [
  {
    id: "joint",
    label: "Co-Parenting Agreements",
    icon: Handshake,
    tone: "purple",
    blurb:
      "Neutral, mediator-ready reports that combine both parents' answers into a single shared view.",
    samples: [
      {
        file: "snc-sample-comparison-report.pdf",
        title: "Complete Co-Parenting Agreement",
        blurb: "Full comparison across all lanes — the flagship joint artefact.",
      },
      {
        file: "sacoparents-coparenting-report.pdf",
        title: "Co-Parenting Alignment Report",
        blurb: "Mediation-ready summary of the two parents' shared and different priorities.",
      },
      {
        file: "sacoparents-sample-coparenting-agreement.pdf",
        title: "Joint Alignment Agreement (Draft)",
        blurb: "Two-parent starter agreement produced from the Compare flow — for mediators to refine.",
      },
      {
        file: "sacoparents-case-status-report-sample.pdf",
        title: "Joint Alignment Case Status Report",
        blurb: "One-page mediator-facing status snapshot with per-parent progress. Downloaded from the /mine console.",
      },
      {
        file: "coparenting_psychological_alignment_framework.pdf",
        title: "Psychological Alignment Framework",
        blurb: "Methodology notes for the psychological deep-dive scoring.",
      },
    ],
  },
  {
    id: "child-needs",
    label: "Child Needs — Deep Dives",
    icon: Sparkles,
    tone: "green",
    blurb:
      "Three parent-facing deep-dive assessments (Educational, Medical, Psychological) with their individual and joint views.",
    samples: [
      {
        file: "snc-sample-educational-deep-dive-assessment.pdf",
        title: "Educational Deep-Dive — Assessment Answers",
        icon: GraduationCap,
      },
      {
        file: "snc-sample-educational-deep-dive.pdf",
        title: "Educational Deep-Dive — Report",
        icon: GraduationCap,
      },
      {
        file: "snc-sample-individual-report-educational.pdf",
        title: "Educational — Individual Report",
        icon: GraduationCap,
      },
      {
        file: "snc-sample-medical-deep-dive-assessment.pdf",
        title: "Medical Deep-Dive — Assessment Answers",
        icon: Stethoscope,
      },
      {
        file: "snc-sample-medical-deep-dive.pdf",
        title: "Medical Deep-Dive — Report",
        icon: Stethoscope,
      },
      {
        file: "snc-sample-individual-report-medical.pdf",
        title: "Medical — Individual Report",
        icon: Stethoscope,
      },
      {
        file: "snc-sample-psychological-deep-dive-assessment.pdf",
        title: "Psychological Deep-Dive — Assessment Answers",
        icon: Brain,
      },
      {
        file: "snc-sample-psychological-deep-dive.pdf",
        title: "Psychological Deep-Dive — Report",
        icon: Brain,
      },
      {
        file: "snc-sample-individual-report-psychological.pdf",
        title: "Psychological — Individual Report",
        icon: Brain,
      },
    ],
  },
  {
    id: "snc",
    label: "Special Needs Concerns (SNC)",
    icon: Heart,
    tone: "purple",
    samples: [
      {
        file: "snc-sample-assessment.pdf",
        title: "SNC — Baseline Assessment Answers",
      },
      {
        file: "snc-sample-assessment-educational.pdf",
        title: "SNC — Educational Assessment Answers",
      },
      {
        file: "snc-sample-assessment-medical.pdf",
        title: "SNC — Medical Assessment Answers",
      },
      {
        file: "snc-sample-assessment-psychological.pdf",
        title: "SNC — Psychological Assessment Answers",
      },
      {
        file: "snc-sample-individual-report.pdf",
        title: "SNC — Individual Report",
      },
    ],
  },
  {
    id: "coparenting",
    label: "Co-Parenting Agreement + Foundation",
    icon: Users,
    tone: "purple",
    samples: [
      {
        file: "coparent-commitment-agreement-fillable.pdf",
        title: "Co-Parent Commitment Agreement (Fillable)",
        blurb: "Blank fillable version parents can complete on paper before generating the joint draft.",
      },
      {
        file: "coparent-commitment-agreement.pdf",
        title: "Co-Parent Commitment Agreement (Sample)",
      },
      {
        file: "sacoparents-foundation-statement-sample.pdf",
        title: "Foundation Statement — Sample (Live-Rendered)",
        blurb: "Fresh sample rendered by the live generator — the exact one-page reflection PDF a parent emails to their mediator before the first session.",
      },
      {
        file: "sacoparents-foundation-statement.pdf",
        title: "Foundation Statement — Legacy Sample",
        blurb: "The four-prompt reflective statement mediators use as the co-parenting north star.",
      },
      {
        file: "sacoparents-coparenting-options.pdf",
        title: "Co-Parenting Options — Overview",
      },
      {
        file: "sacoparents-coparenting-dynamic-sample.pdf",
        title: "Co-Parenting Dynamic Sample",
      },
      {
        file: "coparent-adhd-addendum.pdf",
        title: "Co-Parent ADHD Addendum",
      },
    ],
  },
  {
    id: "cost-splitter",
    label: "Activities Cost Splitter",
    icon: CalendarDays,
    tone: "amber",
    blurb:
      "Neutral cost-share breakdown across activities, education, and medical spend — plus a suggested income-weighted split. Not a court order.",
    samples: [
      {
        file: "sacoparents-cost-splitter-sample.pdf",
        title: "Cost Splitter Ledger + Suggested Split",
        blurb: "Sample income-weighted split (42k / 58k) across sport, music, education and medical categories. Two-parent ledger side-by-side.",
      },
    ],
  },
  {
    id: "safety",
    label: "Family Violence & Safety",
    icon: ShieldAlert,
    tone: "red",
    blurb:
      "Confidential safety-screen output — never shared with the other parent by the app.",
    samples: [
      {
        file: "sacoparents-family-violence-report.pdf",
        title: "Family Violence — Confidential Safety Report",
      },
    ],
  },
  {
    id: "marketing",
    label: "For Professionals",
    icon: FileText,
    tone: "neutral",
    blurb:
      "Handouts and one-pagers for mediators, attorneys, and coordinators.",
    samples: [
      {
        file: "sacoparents-mediator-brochure.pdf",
        title: "Mediator Brochure",
      },
      {
        file: "sacoparents-access-flyer.pdf",
        title: "Practitioner Access Flyer",
      },
    ],
  },
];

const TONE_STYLES = {
  purple: {
    icon: "bg-[#F1EEF7] text-[#3D1A78]",
    ring: "border-[#E5E0EE]",
    eyebrow: "text-[#3D1A78]",
  },
  green: {
    icon: "bg-[#EEF7F1] text-[#1E7A55]",
    ring: "border-[#C7E5D3]",
    eyebrow: "text-[#1E7A55]",
  },
  amber: {
    icon: "bg-[#FFF6EA] text-[#B45F13]",
    ring: "border-[#E6D8C1]",
    eyebrow: "text-[#B45F13]",
  },
  blue: {
    icon: "bg-[#EAF3FA] text-[#1E6FA8]",
    ring: "border-[#B7D9EE]",
    eyebrow: "text-[#1E6FA8]",
  },
  red: {
    icon: "bg-[#FDECEC] text-[#9A3A23]",
    ring: "border-[#F1B7B7]",
    eyebrow: "text-[#9A3A23]",
  },
  neutral: {
    icon: "bg-[#F3F1F8] text-[#4B4567]",
    ring: "border-[#E5E0EE]",
    eyebrow: "text-[#4B4567]",
  },
};

function SampleCard({ sample, tone, DefaultIcon }) {
  const Icon = sample.icon || DefaultIcon;
  const style = TONE_STYLES[tone] || TONE_STYLES.neutral;
  const href = `/downloads/${sample.file}`;
  return (
    <div
      className={`rounded-2xl border ${style.ring} bg-white p-4 flex flex-col gap-3`}
      data-testid={`sample-card-${sample.file}`}
    >
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 rounded-xl grid place-items-center shrink-0 ${style.icon}`}>
          <Icon size={18} strokeWidth={2} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-serif text-base text-[#1A1330] leading-tight">
            {sample.title}
          </div>
          {sample.blurb && (
            <p className="text-[12px] text-[#4B4567] mt-1 leading-snug">
              {sample.blurb}
            </p>
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-2 mt-auto">
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          data-testid={`sample-open-${sample.file}`}
          className="inline-flex items-center gap-1.5 rounded-full border border-[#D6CFE8] text-[#3D1A78] px-3 py-1.5 text-xs font-semibold hover:bg-[#F5F1FB]"
        >
          <ExternalLink size={12} /> Open
        </a>
        <a
          href={href}
          download
          data-testid={`sample-download-${sample.file}`}
          className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] text-white px-3 py-1.5 text-xs font-semibold hover:bg-[#2A0F5F]"
        >
          <Download size={12} /> Download
        </a>
      </div>
    </div>
  );
}

function CategoryBlock({ category }) {
  const Icon = category.icon;
  const style = TONE_STYLES[category.tone] || TONE_STYLES.neutral;
  return (
    <section className="mb-10" data-testid={`sample-category-${category.id}`}>
      <div className="flex items-start gap-3 mb-4">
        <div className={`w-11 h-11 rounded-2xl grid place-items-center shrink-0 ${style.icon}`}>
          <Icon size={20} strokeWidth={2.2} />
        </div>
        <div>
          <div className={`text-[10px] uppercase tracking-[0.22em] font-bold mb-1 ${style.eyebrow}`}>
            {category.samples.length} sample{category.samples.length === 1 ? "" : "s"}
          </div>
          <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-tight">
            {category.label}
          </h2>
          {category.blurb && (
            <p className="text-sm text-[#4B4567] mt-1 leading-relaxed max-w-2xl">
              {category.blurb}
            </p>
          )}
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {category.samples.map((s) => (
          <SampleCard
            key={s.file}
            sample={s}
            tone={category.tone}
            DefaultIcon={category.icon}
          />
        ))}
      </div>
    </section>
  );
}

export default function Samples() {
  const totalCount = CATEGORIES.reduce((acc, c) => acc + c.samples.length, 0);
  const [query, setQuery] = useState("");

  // Filter categories to only those with matching cards. A match is
  // case-insensitive substring match against sample title, blurb, or
  // parent category label. Empty query → show everything.
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return CATEGORIES;
    return CATEGORIES.map((cat) => {
      const catHit = cat.label.toLowerCase().includes(q);
      const samples = cat.samples.filter((s) => {
        if (catHit) return true;
        const hay = `${s.title || ""} ${s.blurb || ""} ${s.file || ""}`.toLowerCase();
        return hay.includes(q);
      });
      return { ...cat, samples };
    }).filter((cat) => cat.samples.length > 0);
  }, [query]);

  const filteredCount = filtered.reduce((acc, c) => acc + c.samples.length, 0);
  const isFiltered = query.trim().length > 0;

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#FAFAFC] to-white">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-[#3D1A78] hover:text-[#2A0F5F] mb-6"
          data-testid="samples-back"
        >
          <ArrowLeft size={14} /> Back to home
        </Link>

        <header className="mb-6" data-testid="samples-header">
          <div className="eyebrow text-[#3D1A78] mb-2">Sample library</div>
          <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl text-[#1A1330] leading-tight">
            Every artefact this app can produce
          </h1>
          <p className="text-[#4B4567] mt-3 max-w-2xl leading-relaxed">
            {totalCount} sample PDFs — the same layouts a signed-in parent
            and their mediator or attorney will see with real data. Open
            each in your browser or download to share with your team.
            Nothing here contains real client data — every field is
            fictional composite content watermarked{" "}
            <em className="font-medium">EXAMPLE</em>.
          </p>
        </header>

        {/* Search + jumplink strip */}
        <div className="mb-10 space-y-4" data-testid="samples-search-strip">
          <div className="relative max-w-xl">
            <Search
              size={16}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-[#857E9C]"
              aria-hidden
            />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search samples — try 'medical', 'agreement', 'foundation'…"
              aria-label="Search samples"
              data-testid="samples-search-input"
              className="w-full pl-11 pr-11 py-3 rounded-full border border-[#D6CFE8] bg-white text-sm text-[#1A1330] placeholder-[#857E9C] focus:outline-none focus:border-[#3D1A78] focus:ring-2 focus:ring-[#3D1A78]/20"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Clear search"
                data-testid="samples-search-clear"
                className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-[#857E9C] hover:bg-[#F5F1FB] hover:text-[#3D1A78]"
              >
                <X size={14} />
              </button>
            )}
          </div>
          {isFiltered ? (
            <div
              className="text-xs text-[#4B4567]"
              data-testid="samples-search-results-count"
            >
              {filteredCount === 0
                ? "No samples match your search."
                : `Showing ${filteredCount} of ${totalCount} samples matching "${query.trim()}".`}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((c) => (
                <a
                  key={c.id}
                  href={`#category-${c.id}`}
                  className="text-xs rounded-full border border-[#D6CFE8] bg-white text-[#3D1A78] px-3 py-1.5 hover:bg-[#F5F1FB] font-medium"
                  data-testid={`samples-jumplink-${c.id}`}
                >
                  {c.label} · {c.samples.length}
                </a>
              ))}
            </div>
          )}
        </div>

        {filtered.length === 0 && isFiltered && (
          <div
            className="rounded-3xl border border-dashed border-[#D6CFE8] bg-white p-8 text-center"
            data-testid="samples-empty-state"
          >
            <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-[#F5F1FB] text-[#3D1A78] grid place-items-center">
              <Search size={22} strokeWidth={2.2} />
            </div>
            <h2 className="font-serif text-xl text-[#1A1330]">
              No sample matches &ldquo;{query.trim()}&rdquo;
            </h2>
            <p className="text-sm text-[#4B4567] mt-2 max-w-md mx-auto leading-relaxed">
              Try broader terms like <em>medical</em>, <em>agreement</em>,{" "}
              <em>foundation</em>, or <em>psychological</em> — or clear
              the search to browse all {totalCount} samples.
            </p>
            <button
              type="button"
              onClick={() => setQuery("")}
              className="mt-4 inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-4 py-2 text-sm font-semibold hover:bg-[#2A0F5F]"
              data-testid="samples-empty-clear"
            >
              Clear search
            </button>
          </div>
        )}

        {filtered.map((category) => (
          <div id={`category-${category.id}`} key={category.id}>
            <CategoryBlock category={category} />
          </div>
        ))}

        <div className="mt-12 rounded-3xl border border-[#E5E0EE] bg-white p-6 sm:p-8 shadow-sm">
          <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-tight">
            Ready to see it with real data?
          </h2>
          <p className="text-sm text-[#4B4567] mt-2 leading-relaxed max-w-2xl">
            Every sample above is generated from a real parent&rsquo;s
            reflective answers — with none of the co-parent&rsquo;s
            private notes visible. Sign in as a parent to start your own,
            or explore the demo mode.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              to="/register"
              className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#2A0F5F]"
              data-testid="samples-cta-register"
            >
              Create an account
            </Link>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 rounded-full border border-[#D6CFE8] text-[#3D1A78] px-5 py-2.5 text-sm font-semibold hover:bg-[#F5F1FB]"
              data-testid="samples-cta-demo"
            >
              Try demo mode
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
