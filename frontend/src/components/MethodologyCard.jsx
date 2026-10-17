import { useState } from "react";
import {
  BookOpenCheck,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Ban,
  Compass,
  Sigma,
  ShieldAlert,
  Clock,
} from "lucide-react";
import { getMethodology } from "../lib/methodology";

/**
 * MethodologyCard — visible-methodology header for every assessment.
 *
 * Per the product feedback: each assessment must up-front declare what it
 * is designed to do, what it cannot determine, how recommendations are
 * selected, whether questions are informed by established models, when
 * professional assistance is appropriate, and how frequently it should
 * be retaken.
 *
 * This card lives at the top of an assessment page. Six sections, each
 * with a matching icon and short body. Everything below "Purpose" is
 * collapsed by default so the top of the assessment stays visually
 * light — parents can expand to read the full methodology when they
 * want the grounding.
 *
 * Props:
 *   id — one of the keys in /app/frontend/src/lib/methodology.js
 *       (e.g. "readiness", "comm_style", "special_needs", "safety")
 */

const CATEGORY_STYLES = {
  assessment: {
    ring: "border-[#C9D9F5]",
    bg: "bg-gradient-to-br from-[#EEF3FE] to-white",
    accent: "text-[#2E4B8A]",
    chip: "bg-[#DDE7F9] text-[#2E4B8A]",
    label: "Assessment",
  },
  safety: {
    ring: "border-[#EED3B5]",
    bg: "bg-gradient-to-br from-[#FEF1EC] to-white",
    accent: "text-[#8C3A1B]",
    chip: "bg-[#F5C9B4] text-[#8C3A1B]",
    label: "Safety Screening",
  },
};

const SECTIONS = [
  { key: "limitations", label: "What it cannot determine", icon: Ban },
  { key: "sources", label: "Sources & established models", icon: BookOpenCheck },
  { key: "logic", label: "How the recommendations are built", icon: Sigma },
  { key: "professionalHelp", label: "When to seek professional help", icon: ShieldAlert },
  { key: "retake", label: "How often to retake", icon: Clock },
];

function SectionBlock({ icon: Icon, label, body }) {
  const isList = Array.isArray(body);
  return (
    <div className="flex items-start gap-3 py-3 border-t border-[#E5E0EE] first:border-0">
      <div className="shrink-0 w-8 h-8 rounded-full bg-white/70 grid place-items-center">
        <Icon size={14} className="text-[#3D1A78]" />
      </div>
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#3D1A78] mb-1">
          {label}
        </div>
        {isList ? (
          <ul className="list-disc pl-5 space-y-1 text-sm text-[#1A1330] leading-relaxed">
            {body.map((item, i) => (
              <li key={`${item.slice(0, 32)}-${i}`}>{item}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-[#1A1330] leading-relaxed">{body}</p>
        )}
      </div>
    </div>
  );
}

export default function MethodologyCard({ id, defaultOpen = false }) {
  const m = getMethodology(id);
  const [open, setOpen] = useState(defaultOpen);
  if (!m) return null;
  const style = CATEGORY_STYLES[m.category] || CATEGORY_STYLES.assessment;
  return (
    <section
      className={`rounded-3xl border ${style.ring} ${style.bg} p-5 sm:p-6 mb-6`}
      data-testid={`methodology-card-${id}`}
      aria-label={`Methodology for ${m.name}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <span
              className={`text-[10px] uppercase tracking-[0.16em] font-bold px-2 py-0.5 rounded-full ${style.chip}`}
              data-testid={`methodology-category-${id}`}
            >
              {style.label}
            </span>
            <span className="text-[10px] uppercase tracking-[0.16em] font-bold text-[#6E6787] flex items-center gap-1">
              <Compass size={11} /> How this assessment works
            </span>
          </div>
          <h2
            className={`font-serif text-xl sm:text-2xl ${style.accent} leading-tight`}
            data-testid={`methodology-name-${id}`}
          >
            {m.name}
          </h2>
          <p
            className="text-sm text-[#1A1330] mt-3 leading-relaxed max-w-3xl"
            data-testid={`methodology-purpose-${id}`}
          >
            <span className="font-bold">Purpose · </span>
            {m.purpose}
          </p>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`mt-4 inline-flex items-center gap-1.5 text-xs font-bold ${style.accent} hover:underline`}
        data-testid={`methodology-toggle-${id}`}
        aria-expanded={open}
      >
        {open ? (
          <>
            Hide the full methodology <ChevronUp size={12} />
          </>
        ) : (
          <>
            Read the full methodology <ChevronDown size={12} />
          </>
        )}
      </button>

      {open && (
        <div
          className="mt-4 rounded-2xl bg-white/70 border border-white p-4"
          data-testid={`methodology-details-${id}`}
        >
          {SECTIONS.map(({ key, label, icon }) => (
            <SectionBlock key={key} icon={icon} label={label} body={m[key]} />
          ))}
        </div>
      )}

      <div
        className="mt-4 flex items-start gap-2 text-[11px] text-[#4B4567] italic"
        data-testid={`methodology-disclaimer-${id}`}
      >
        <AlertTriangle size={12} className="text-[#8C5A2C] mt-0.5 shrink-0" />
        This is a self-reflection tool for mediation preparation — not clinical
        advice, a legal determination, or a substitute for a licensed
        professional&apos;s judgement.
      </div>
    </section>
  );
}
