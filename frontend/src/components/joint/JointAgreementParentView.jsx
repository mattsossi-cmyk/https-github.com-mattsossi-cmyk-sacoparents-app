/**
 * JointAgreementParentView — parent-friendly 5-bucket view of the
 * Joint Co-Parenting Agreement Draft. Mirrors the Joint Report parent
 * view but mapped to the agreement domain (proposed clauses instead
 * of assessment perceptions).
 *
 * Buckets:
 *   1. What You've Both Proposed
 *   2. Where Each of You Has Different Ideas
 *   3. Clauses That May Need Refinement
 *   4. Options for Blending Your Ideas
 *   5. Questions for Your Next Conversation
 *
 * The row-strip layout in `payload.sections` stays available for the
 * "Detailed Comparison" appendix rendered by the parent page.
 */
import React from "react";
import {
  CheckCircle2, GitCompare, AlertCircle, Lightbulb, MessageCircleQuestion,
} from "lucide-react";

const BUCKETS = [
  {
    key: "what_you_both_proposed",
    icon: CheckCircle2,
    accent: "#1F5C3B",
    accentBorder: "#B5DFC5",
  },
  {
    key: "where_you_have_different_ideas",
    icon: GitCompare,
    accent: "#8A5B00",
    accentBorder: "#F0D9A8",
  },
  {
    key: "may_need_refinement",
    icon: AlertCircle,
    accent: "#B02A2A",
    accentBorder: "#EFB4B4",
  },
  {
    key: "options_to_consider",
    icon: Lightbulb,
    accent: "#3D1A78",
    accentBorder: "#D6CFE8",
  },
  {
    key: "questions_for_next_conversation",
    icon: MessageCircleQuestion,
    accent: "#0F6F6F",
    accentBorder: "#B5DFC5",
  },
];


function BucketBothProposed({ data }) {
  if (!data.count) {
    return (
      <p className="text-sm text-[#4B4567] italic">
        No overlapping clauses yet — as each parent finalises their
        draft, the shared clauses will surface here first.
      </p>
    );
  }
  return (
    <ul className="space-y-2.5">
      {data.items.map((it, i) => (
        <li
          key={`${it.text}-${i}`}
          className="rounded-xl bg-white/70 border border-white p-3"
        >
          {(it.area || it.section_title) && (
            <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#1F5C3B] mb-1">
              {it.area || it.section_title}
            </div>
          )}
          <div className="text-sm text-[#1A1330] leading-relaxed">{it.text}</div>
        </li>
      ))}
    </ul>
  );
}


function BucketDifferentIdeas({ data, parentAName, parentBName }) {
  if (!data.count) {
    return (
      <p className="text-sm text-[#4B4567] italic">
        No divergent clauses — you&rsquo;ve both proposed the same
        things across every section.
      </p>
    );
  }
  return (
    <ul className="space-y-3">
      {data.items.map((it, i) => (
        <li
          key={`${it.topic}-${i}`}
          className="rounded-xl bg-white/70 border border-white p-3"
        >
          <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#8A5B00] mb-1.5">
            {it.topic}
          </div>
          <div className="grid sm:grid-cols-2 gap-2">
            <div className={`rounded-lg p-2 text-sm text-[#1A1330] ${it.parent_a ? "bg-[#F7F4FC]" : "bg-white/50"}`}>
              <div className="text-[0.625rem] uppercase tracking-wider text-[#3D1A78] font-semibold mb-0.5">
                {parentAName}
              </div>
              {it.parent_a || <em className="text-[#6E6787]">no clause proposed</em>}
            </div>
            <div className={`rounded-lg p-2 text-sm text-[#1A1330] ${it.parent_b ? "bg-[#EAF7F7]" : "bg-white/50"}`}>
              <div className="text-[0.625rem] uppercase tracking-wider text-[#0F6F6F] font-semibold mb-0.5">
                {parentBName}
              </div>
              {it.parent_b || <em className="text-[#6E6787]">no clause proposed</em>}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}


function BucketRefinement({ data }) {
  if (!data.count) {
    return (
      <p className="text-sm text-[#4B4567] italic">
        Nothing is currently flagged as unresolved. If a topic feels
        unsettled, add it to your Foundation Statement so it surfaces here.
      </p>
    );
  }
  return (
    <ul className="space-y-2.5">
      {data.items.map((it, i) => (
        <li
          key={`${it.topic}-${i}`}
          className="rounded-xl bg-white/70 border border-white p-3"
        >
          <div className="flex items-baseline gap-2 mb-0.5">
            <div className="text-sm font-semibold text-[#1A1330]">
              {it.topic || "Open item"}
            </div>
            {it.both_flagged && (
              <span className="text-[0.625rem] uppercase tracking-wider text-[#B02A2A] font-bold">
                Both flagged
              </span>
            )}
          </div>
          {it.detail && (
            <div className="text-sm text-[#4B4567] leading-relaxed">
              {it.detail}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}


function BucketOptions({ data }) {
  return (
    <ul className="space-y-2.5">
      {data.items.map((it, i) => (
        <li
          key={`${it.title}-${i}`}
          className="rounded-xl bg-white/70 border border-white p-3"
        >
          <div className="text-sm font-semibold text-[#3D1A78] mb-1">
            {it.title}
          </div>
          <div className="text-sm text-[#1A1330] leading-relaxed">
            {it.detail}
          </div>
        </li>
      ))}
    </ul>
  );
}


function BucketQuestions({ data }) {
  return (
    <ol className="space-y-2.5">
      {data.items.map((it, i) => (
        <li
          key={`${it.topic}-${i}`}
          className="rounded-xl bg-white/70 border border-white p-3"
        >
          <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#0F6F6F] mb-1">
            {it.topic}
          </div>
          <div className="text-sm text-[#1A1330] leading-relaxed italic">
            &ldquo;{it.question}&rdquo;
          </div>
        </li>
      ))}
    </ol>
  );
}


function BucketBody({ bucketKey, data, parentAName, parentBName }) {
  if (!data) return null;
  switch (bucketKey) {
    case "what_you_both_proposed": return <BucketBothProposed data={data} />;
    case "where_you_have_different_ideas":
      return <BucketDifferentIdeas data={data} parentAName={parentAName} parentBName={parentBName} />;
    case "may_need_refinement": return <BucketRefinement data={data} />;
    case "options_to_consider": return <BucketOptions data={data} />;
    case "questions_for_next_conversation": return <BucketQuestions data={data} />;
    default: return null;
  }
}


export default function JointAgreementParentView({ parentView, parentAName, parentBName }) {
  if (!parentView) return null;
  return (
    <div
      className="space-y-4 sm:space-y-5"
      data-testid="joint-agreement-parent-view"
    >
      {BUCKETS.map((b) => {
        const data = parentView[b.key];
        if (!data) return null;
        return (
          <section
            key={b.key}
            className="rounded-3xl border p-5 sm:p-6"
            style={{
              backgroundColor: `${b.accent}0A`,
              borderColor: b.accentBorder,
            }}
            data-testid={`joint-agreement-bucket-${b.key}`}
          >
            <div className="flex items-start gap-3 mb-4">
              <div
                className="shrink-0 h-10 w-10 rounded-full grid place-items-center text-white shadow-sm"
                style={{ backgroundColor: b.accent }}
              >
                <b.icon size={16} />
              </div>
              <div className="min-w-0">
                <h2 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-tight">
                  {data.title}
                </h2>
                <p className="text-xs sm:text-sm text-[#4B4567] mt-1 leading-relaxed">
                  {data.description}
                </p>
              </div>
              {typeof data.count === "number" && data.count > 0 && (
                <span
                  className="ml-auto shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold"
                  style={{
                    backgroundColor: `${b.accent}18`,
                    color: b.accent,
                  }}
                >
                  {data.count}
                </span>
              )}
            </div>
            <BucketBody
              bucketKey={b.key}
              data={data}
              parentAName={parentAName}
              parentBName={parentBName}
            />
          </section>
        );
      })}
    </div>
  );
}
