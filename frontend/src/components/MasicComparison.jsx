/**
 * MasicComparison — Honest, transparent side-by-side of the safety-screen
 * domains covered by SA CoParents vs. the MASIC-S (Mediator's Assessment
 * of Safety Issues and Concerns — Short form; Holtzworth-Munroe, Beck &
 * Applegate). Shown on the Methodology page as a survivor / reviewer
 * transparency artefact — NOT a claim of equivalence.
 *
 * The `state` on each row is one of:
 *   "covered"      — the domain is asked in the current live screen
 *   "partial"      — asked, but not with the specificity or wording MASIC-S
 *                    uses (e.g., generic "threats" instead of homicide/suicide)
 *   "gap"          — the current live screen does NOT ask about this domain
 *   "pending"      — flagged for the reviewer panel to draft wording for
 *
 * Rows must be maintained by hand as questions are added or reworded.
 */
import { Check, Minus, X, HelpCircle } from "lucide-react";

const STATE_META = {
  covered: {
    label:   "Covered",
    color:   "text-[#1F5C3B]",
    bg:      "bg-[#E6F4EC]",
    ring:    "ring-[#1F5C3B]/30",
    Icon:    Check,
  },
  partial: {
    label:   "Partial",
    color:   "text-[#8A5B00]",
    bg:      "bg-[#FFF6E5]",
    ring:    "ring-[#AA7428]/30",
    Icon:    Minus,
  },
  gap: {
    label:   "Gap",
    color:   "text-[#B02A2A]",
    bg:      "bg-[#FCE3DC]",
    ring:    "ring-[#9A3A23]/30",
    Icon:    X,
  },
  pending: {
    label:   "Reviewer pending",
    color:   "text-[#3D1A78]",
    bg:      "bg-[#F0EAFB]",
    ring:    "ring-[#3D1A78]/30",
    Icon:    HelpCircle,
  },
};

// Ordered from most safety-critical to contextual.
const ROWS = [
  { domain: "Physical violence (recent + historical)",       state: "covered", note: "Section 1 items on physical harm and injuries." },
  { domain: "Threats of physical harm",                       state: "covered", note: "Direct-threat items in Section 1." },
  { domain: "Homicide / suicide threats",                     state: "partial", note: "Not called out as a distinct item; captured only if the parent volunteers it." },
  { domain: "Strangulation / choking",                        state: "gap",     note: "Not currently asked. Strangulation is a top predictor of lethal-risk escalation." },
  { domain: "Weapons in the home / access to firearms",       state: "gap",     note: "Not currently asked. High-priority reviewer domain." },
  { domain: "Sexual coercion / non-consensual sexual acts",   state: "gap",     note: "Not currently asked. Reviewer-drafted wording pending." },
  { domain: "Coercive control (patterns, not incidents)",     state: "partial", note: "Some items address control; MASIC-S goes deeper into patterns." },
  { domain: "Stalking (in-person + digital)",                 state: "partial", note: "In-person following is asked; digital / online tracking is not distinct." },
  { domain: "Digital surveillance / device monitoring",       state: "gap",     note: "Not currently asked. Growing area of post-separation abuse." },
  { domain: "Financial control / economic abuse",             state: "gap",     note: "Not currently asked." },
  { domain: "Threats involving the children",                 state: "partial", note: "Child-related risk is asked broadly; specific threats-to-take-the-child are not." },
  { domain: "Post-separation escalation",                     state: "partial", note: "Timing of behaviour is not currently distinguished." },
  { domain: "Fear of the other parent",                       state: "covered", note: "Directly asked in Section 2." },
  { domain: "Fear of consequences for disagreeing",           state: "pending", note: "Wording being drafted with the reviewer panel." },
  { domain: "Substance abuse / intoxication during incidents", state: "gap",    note: "Not currently asked." },
  { domain: "Child abuse (direct)",                           state: "partial", note: "Child safety is prompted at intake; specific abuse types are not itemised." },
  { domain: "Mental-health concerns affecting safety",        state: "gap",     note: "Not asked — belongs in a specialist evaluation." },
  { domain: "Prior court involvement / protective orders",    state: "partial", note: "The parent can mention it in free-text; not a structured field." },
];

function StatePill({ state }) {
  const meta = STATE_META[state] || STATE_META.gap;
  const { Icon } = meta;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.625rem] font-bold ${meta.bg} ${meta.color} ring-1 ${meta.ring}`}
      data-testid={`masic-state-${state}`}
    >
      <Icon size={10} /> {meta.label}
    </span>
  );
}

export default function MasicComparison() {
  const counts = ROWS.reduce((acc, r) => {
    acc[r.state] = (acc[r.state] || 0) + 1;
    return acc;
  }, {});
  return (
    <aside
      className="not-prose rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 my-6"
      data-testid="masic-comparison"
      aria-labelledby="masic-comparison-title"
    >
      <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
        Transparency sidebar
      </div>
      <h3
        id="masic-comparison-title"
        className="font-serif text-xl text-[#1A1330] mb-1"
      >
        How this screen compares to MASIC-S
      </h3>
      <p className="text-sm text-[#4B4567] leading-relaxed mb-3">
        The <a
          href="https://law.indiana.edu/faculty/profiles/documents/holtzworth-munroe-a-masic-s-info.pdf"
          target="_blank"
          rel="noopener noreferrer"
          className="underline text-[#3D1A78]"
        >MASIC-S</a> (Mediator&rsquo;s Assessment of Safety Issues and
        Concerns — Short) was designed specifically to screen separating
        parents for intimate-partner violence and mediation-safety
        concerns. It is the most directly relevant comparator for a tool
        like this one. The table below is an honest, public map of which
        MASIC-S domains our current live screen covers, partially covers,
        or does not yet cover.
      </p>
      <p className="text-xs text-[#4B4567] italic leading-relaxed mb-4">
        This does <strong>not</strong> claim equivalence to MASIC-S. Filling
        the gaps requires reviewer input from a DV advocate, forensic
        psychologist, and Texas family-law attorney; wording will be added
        only after that review.
      </p>

      <div className="flex flex-wrap gap-2 mb-4">
        {["covered", "partial", "gap", "pending"].map((s) => (
          <span
            key={s}
            className="inline-flex items-center gap-1.5 text-[0.6875rem] text-[#4B4567]"
          >
            <StatePill state={s} />
            <span>{counts[s] || 0}</span>
          </span>
        ))}
      </div>

      <div className="overflow-hidden rounded-2xl border border-[#E5E0EE]">
        <table className="w-full text-sm" data-testid="masic-comparison-table">
          <thead className="bg-[#F8F5FF] text-[#3D1A78]">
            <tr className="text-left">
              <th className="px-3 py-2 text-[0.625rem] uppercase tracking-[0.15em] font-bold">MASIC-S domain</th>
              <th className="px-3 py-2 text-[0.625rem] uppercase tracking-[0.15em] font-bold">Our coverage</th>
              <th className="px-3 py-2 text-[0.625rem] uppercase tracking-[0.15em] font-bold hidden sm:table-cell">Notes</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row, idx) => (
              <tr
                key={row.domain}
                className={idx % 2 === 0 ? "bg-white" : "bg-[#FAF8FE]"}
              >
                <td className="px-3 py-2.5 align-top text-[#1A1330] font-semibold w-1/3">
                  {row.domain}
                </td>
                <td className="px-3 py-2.5 align-top">
                  <StatePill state={row.state} />
                </td>
                <td className="px-3 py-2.5 align-top text-[0.75rem] text-[#4B4567] hidden sm:table-cell">
                  {row.note}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-[0.6875rem] text-[#6A5799] italic mt-3">
        Last coverage audit: February 26, 2026. This table will move rows
        from <em>Gap</em> / <em>Reviewer pending</em> to <em>Covered</em>{" "}
        only after items are approved by the reviewer panel and printed
        with their names + review date.
      </p>
    </aside>
  );
}
