/**
 * JointAlignmentSamplePreview — a PUBLIC sample of what the private
 * Joint Alignment Preview looks like AFTER both parents have finished
 * their independent reflections.
 *
 * Rationale: parents asked "what does the joint version look like
 * before I invite my co-parent?" This page shows a realistic, fully
 * fictional preview with all the same UI as the real
 * `JointAlignmentPreview` — same counts pills, same agree / differ /
 * incomplete topic table — so a hesitant parent can peek without
 * signing up.
 *
 * No live API calls, no auth. The sample data is deliberately
 * NEUTRAL: mix of agreements and differences, no adversarial or
 * loaded topics, no violence markers. `SAMPLE_CASE_META` explicitly
 * flags the data as fictional in every prominent surface.
 */
import React from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  MinusCircle,
  Circle,
  Sparkles,
  Users,
  FileText,
  Download,
  Mail,
} from "lucide-react";

const BACKEND = process.env.REACT_APP_BACKEND_URL;
const SAMPLE_PDF_PATH = "/api/insights/samples/joint-alignment-preview.pdf";
const SAMPLE_PDF_URL = `${BACKEND}${SAMPLE_PDF_PATH}`;
const SAMPLE_PAGE_URL = `${BACKEND}/samples/joint-alignment-preview`;

// Pre-composed message a parent uses to email the sample to their
// co-parent BEFORE either of them signs up. Keep the tone neutral,
// personal, non-adjudicative — matches the platform guardrail.
const COPARENT_EMAIL_SUBJECT = "Something I want to try before we sit down with a professional";
const COPARENT_EMAIL_BODY = [
  "Hi,",
  "",
  "I found a small tool that helps two co-parents each answer the same reflection questions independently — then shows a side-by-side of where we agree, where we differ, and where one of us hasn't finished yet. Nothing gets shared until we both say so.",
  "",
  "Here's what the joint preview would look like (this is a sample with fictional parents):",
  `  Web: ${SAMPLE_PAGE_URL}`,
  `  PDF: ${SAMPLE_PDF_URL}`,
  "",
  "If you want to try it, we'd each sign up separately at https://sacoparentsapp.online and one of us would invite the other.",
  "",
  "Thanks for considering,",
].join("\n");

// ---- Sample data (fictional, neutral). Never change the shape of
// this without also updating the real /joint-alignment/{id}/preview
// endpoint's response contract, so the two pages stay in lockstep.
const SAMPLE_CASE_META = {
  parents: ["Alex", "Sam"],
  child: { name: "Rian", age: 8 },
};

const SAMPLE_TOPICS = [
  {
    key: "school-routines",
    title: "School morning routines",
    section: "Weekday transitions",
    status: "agree",
    note: "Both parents landed on the same wake / drop-off pattern.",
  },
  {
    key: "screen-time",
    title: "Screen time on weeknights",
    section: "Daily rhythms",
    status: "agree",
    note: "Same limit, same house rule.",
  },
  {
    key: "extracurriculars",
    title: "Extracurricular activities",
    section: "Weekly commitments",
    status: "differ",
    note: "One parent wants a lighter schedule; worth talking about.",
  },
  {
    key: "handovers",
    title: "Handover timing on Fridays",
    section: "Transitions",
    status: "differ",
    note: "Different preferred times - a small change to your plan may resolve this.",
  },
  {
    key: "holidays",
    title: "Winter holidays",
    section: "Special occasions",
    status: "agree",
    note: "Same view on how to split the school break.",
  },
  {
    key: "healthcare",
    title: "Healthcare decisions",
    section: "Big-picture parenting",
    status: "incomplete",
    note: "One of you didn't finish this section yet - mark it not done.",
  },
];

const SAMPLE_SUMMARY = {
  agreed: SAMPLE_TOPICS.filter((t) => t.status === "agree").length,
  differed: SAMPLE_TOPICS.filter((t) => t.status === "differ").length,
  incomplete: SAMPLE_TOPICS.filter((t) => t.status === "incomplete").length,
};

const ALIGNMENT_META = {
  agree: {
    label: "You agree",
    icon: CheckCircle2,
    cls: "text-[#186142] bg-[#E1F3E8] border-[#B7DEC6]",
  },
  differ: {
    label: "You differ",
    icon: MinusCircle,
    cls: "text-[#8A5B00] bg-[#FFF6E5] border-[#F0D9A1]",
  },
  incomplete: {
    label: "Not both completed",
    icon: Circle,
    cls: "text-[#5C5471] bg-[#F1EEF4] border-[#DED8E5]",
  },
};

function CountPill({ count, label, tone }) {
  return (
    <div
      className={`rounded-2xl border px-4 py-3 flex-1 min-w-[110px] ${tone}`}
      data-testid={`sample-preview-count-${label.toLowerCase()}`}
    >
      <div className="text-2xl font-serif leading-none">{count}</div>
      <div className="text-[11px] uppercase tracking-[0.14em] font-semibold mt-1">
        {label}
      </div>
    </div>
  );
}

function TopicRow({ topic }) {
  const meta = ALIGNMENT_META[topic.status];
  const Icon = meta.icon;
  return (
    <li
      className="flex items-start gap-3 px-5 py-4 border-b last:border-b-0 border-[#EEE8F7]"
      data-testid={`sample-preview-topic-${topic.key}`}
    >
      <div className={`shrink-0 rounded-xl border px-2.5 py-1 flex items-center gap-1.5 ${meta.cls}`}>
        <Icon size={13} strokeWidth={2.2} />
        <span className="text-[11px] uppercase tracking-[0.14em] font-semibold">
          {meta.label}
        </span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="font-serif text-[15px] text-[#1A1330] leading-snug">
          {topic.title}
        </div>
        <div className="text-[11px] uppercase tracking-[0.16em] font-semibold text-[#857E9C] mt-0.5">
          {topic.section}
        </div>
        <p className="text-[13px] text-[#4B4567] mt-1.5 leading-relaxed">
          {topic.note}
        </p>
      </div>
    </li>
  );
}

export default function JointAlignmentSamplePreview() {
  return (
    <div
      className="min-h-screen bg-[#FAF8FD]"
      data-testid="joint-alignment-sample-preview-page"
    >
      {/* Sample banner — always visible so a parent skimming the
          page never mistakes this for their own case. */}
      <div
        className="bg-[#3D1A78] text-white text-center px-4 py-2 text-[12px] tracking-[0.12em] uppercase font-semibold"
        data-testid="sample-preview-sample-banner"
      >
        Sample · Not your data · {SAMPLE_CASE_META.parents.join(" & ")} with
        child {SAMPLE_CASE_META.child.name} (fictional)
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="sample-preview-back-link"
        >
          <ArrowLeft size={14} /> Back to home
        </Link>

        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
          <ShieldCheck size={12} /> What you and your co-parent would see
        </div>
        <h1
          className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight mt-1"
          data-testid="sample-preview-title"
        >
          A quick look at where two co-parents land
        </h1>
        <p className="text-[#4B4567] mt-3 leading-relaxed max-w-2xl">
          This is a fictional example of the private preview both
          parents see after independently completing their
          reflections. You only see whether each topic reads as an{" "}
          <strong>agree</strong>, a <strong>differ</strong>, or a
          section one of you didn&rsquo;t finish. Neither parent&rsquo;s
          actual answers are visible on this page.
        </p>

        <div
          className="mt-6 rounded-2xl border border-[#D6CFE8] bg-[#F5F1FB] p-4 text-[13px] text-[#3D1A78]"
          data-testid="sample-preview-privacy-banner"
        >
          <div className="font-semibold flex items-center gap-1.5 mb-1">
            <ShieldCheck size={14} /> Your real preview is never shared publicly
          </div>
          In the live product, this exact layout is generated only for
          the two parents on a case. Releasing the full Joint Alignment
          Report to a named professional is a <em>separate</em> action
          that requires both of you to record release consent.
        </div>

        {/* Summary counts */}
        <div className="mt-6 flex flex-wrap gap-3" data-testid="sample-preview-summary">
          <CountPill
            count={SAMPLE_SUMMARY.agreed}
            label="Agreed"
            tone="text-[#186142] bg-[#E1F3E8] border-[#B7DEC6]"
          />
          <CountPill
            count={SAMPLE_SUMMARY.differed}
            label="Differed"
            tone="text-[#8A5B00] bg-[#FFF6E5] border-[#F0D9A1]"
          />
          <CountPill
            count={SAMPLE_SUMMARY.incomplete}
            label="Incomplete"
            tone="text-[#5C5471] bg-[#F1EEF4] border-[#DED8E5]"
          />
        </div>

        {/* Topic-by-topic */}
        <div className="mt-6 rounded-2xl border border-[#E5E0EE] bg-white overflow-hidden">
          <div className="px-5 py-3 border-b border-[#EEE8F7] bg-[#FAF8FD]">
            <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
              Topic-by-topic
            </div>
          </div>
          <ul data-testid="sample-preview-topics">
            {SAMPLE_TOPICS.map((topic) => (
              <TopicRow key={topic.key} topic={topic} />
            ))}
          </ul>
        </div>

        {/* CTAs — dual-track landing framing */}
        <div
          className="mt-10 rounded-3xl border-2 border-[#3D1A78]/20 bg-white p-6 sm:p-8"
          data-testid="sample-preview-ctas"
        >
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
            <Sparkles size={12} /> Ready to build yours?
          </div>
          <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-snug mt-1">
            Every parent starts with their own reflection.
          </h2>
          <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
            Once your co-parent completes theirs, you both see a
            preview exactly like this one — private, agreement-flag-only.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              to="/register"
              className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] hover:bg-[#2A0F5F] text-white px-6 py-3 text-sm font-semibold shadow-sm transition-colors"
              data-testid="sample-preview-cta-start"
            >
              <Users size={14} /> Start on my own <ArrowRight size={14} />
            </Link>
            <Link
              to="/join"
              className="inline-flex items-center gap-2 rounded-full bg-white border-2 border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-6 py-3 text-sm font-semibold transition-colors"
              data-testid="sample-preview-cta-invited"
            >
              I have an invitation
            </Link>
            <Link
              to="/samples"
              className="inline-flex items-center gap-2 rounded-full text-[#3D1A78] hover:underline px-4 py-3 text-sm font-semibold"
              data-testid="sample-preview-cta-more-samples"
            >
              <FileText size={14} /> See other sample reports
            </Link>
          </div>

          {/* Share-this-sample strip — download PDF + email co-parent.
              Sits inside the CTA card because the whole point is to
              hand this to someone who hasn't signed up yet. */}
          <div
            className="mt-6 pt-6 border-t border-[#EEE8F7]"
            data-testid="sample-preview-share-strip"
          >
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
              Share this sample with your co-parent
            </div>
            <p className="text-[13px] text-[#4B4567] leading-relaxed mb-3">
              Some parents like to send this concept to their co-parent
              first — before either of you signs up.
            </p>
            <div className="flex flex-wrap gap-3">
              <a
                href={SAMPLE_PDF_PATH}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-full bg-white border-2 border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-5 py-2.5 text-sm font-semibold transition-colors"
                data-testid="sample-preview-download-pdf"
              >
                <Download size={14} /> Download sample PDF
              </a>
              <a
                href={`mailto:?subject=${encodeURIComponent(COPARENT_EMAIL_SUBJECT)}&body=${encodeURIComponent(COPARENT_EMAIL_BODY)}`}
                className="inline-flex items-center gap-2 rounded-full bg-[#0E7A7A] hover:bg-[#0A5E5E] text-white px-5 py-2.5 text-sm font-semibold transition-colors"
                data-testid="sample-preview-email-coparent"
              >
                <Mail size={14} /> Email to my co-parent
              </a>
            </div>
          </div>
        </div>

        {/* Small fine-print / attribution row */}
        <p
          className="mt-6 text-[11px] text-[#857E9C] leading-relaxed"
          data-testid="sample-preview-fineprint"
        >
          The people, child, and topics on this page are fictional.
          The real preview is generated from each parent&rsquo;s own
          reflection and is never published outside the case.
        </p>
      </div>
    </div>
  );
}
