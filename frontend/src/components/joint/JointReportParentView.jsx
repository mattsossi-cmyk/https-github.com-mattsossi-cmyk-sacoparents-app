/**
 * JointReportParentView — parent-friendly 5-bucket view of the Joint
 * Report, replacing the row-strip layout as the primary presentation.
 *
 * Buckets (mirrors backend `parent_view`):
 *   1. What You Both Care About
 *   2. Where You See Things Differently
 *   3. What May Need Attention
 *   4. Options to Consider
 *   5. Questions for Your Next Conversation
 *
 * The old row-strip sections still ship in `payload.sections` — this
 * component leaves rendering of the "Detailed Comparison" appendix to
 * its caller (they can show/hide it or drop it in a <details> block).
 */
import React from "react";
import {
  Heart, Split, AlertCircle, Lightbulb, MessageCircleQuestion,
} from "lucide-react";

const BUCKETS = [
  {
    key: "what_you_both_care_about",
    icon: Heart,
    accent: "#1F5C3B",
    accentBg: "#E6F4EC",
    accentBorder: "#B5DFC5",
  },
  {
    key: "where_you_see_things_differently",
    icon: Split,
    accent: "#8A5B00",
    accentBg: "#FFF6E5",
    accentBorder: "#F0D9A8",
  },
  {
    key: "what_may_need_attention",
    icon: AlertCircle,
    accent: "#B02A2A",
    accentBg: "#FCEDEB",
    accentBorder: "#EFB4B4",
  },
  {
    key: "options_to_consider",
    icon: Lightbulb,
    accent: "#3D1A78",
    accentBg: "#F5F1FB",
    accentBorder: "#D6CFE8",
  },
  {
    key: "questions_for_next_conversation",
    icon: MessageCircleQuestion,
    accent: "#0F6F6F",
    accentBg: "#EAF7F7",
    accentBorder: "#B5DFC5",
  },
];


function BucketCareAbout({ data }) {
  if (!data.count && !(data.shared_pathways || []).length) {
    return (
      <p className="text-sm text-[#4B4567] italic">
        No shared priorities have been captured yet — as both of you
        answer more of the assessments, this section will populate.
      </p>
    );
  }
  return (
    <ul className="space-y-2.5">
      {(data.items || []).map((it, i) => (
        <li
          key={`${it.text}-${i}`}
          className="rounded-xl bg-white/70 border border-white p-3 text-sm text-[#1A1330] leading-relaxed"
        >
          {it.text}
        </li>
      ))}
      {(data.shared_pathways || []).length > 0 && (
        <li className="rounded-xl bg-white/70 border border-white p-3">
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#1F5C3B] mb-1">
            Pathways both of you named
          </div>
          <div className="flex flex-wrap gap-1.5">
            {data.shared_pathways.map((p) => (
              <span
                key={p}
                className="text-xs bg-[#1F5C3B]/10 text-[#1F5C3B] rounded-full px-2 py-0.5 font-semibold capitalize"
              >
                {p}
              </span>
            ))}
          </div>
        </li>
      )}
    </ul>
  );
}


function BucketDifferences({ data }) {
  if (!data.count) {
    return (
      <p className="text-sm text-[#4B4567] italic">
        No perception differences have been surfaced — either both of
        your responses align, or the underlying assessments aren&rsquo;t
        yet complete for both parents.
      </p>
    );
  }
  return (
    <ul className="space-y-3">
      {(data.items || []).map((it, i) => (
        <li
          key={`${it.topic}-${i}`}
          className="rounded-xl bg-white/70 border border-white p-3"
        >
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#8A5B00] mb-1.5">
            {it.topic}
          </div>
          <div className="grid sm:grid-cols-2 gap-2">
            <div className="rounded-lg bg-[#F7F4FC] p-2 text-sm text-[#1A1330]">
              <div className="text-[10px] uppercase tracking-wider text-[#3D1A78] font-semibold mb-0.5">Parent A</div>
              {it.parent_a || <em className="text-[#6E6787]">no response</em>}
            </div>
            <div className="rounded-lg bg-[#EAF7F7] p-2 text-sm text-[#1A1330]">
              <div className="text-[10px] uppercase tracking-wider text-[#0F6F6F] font-semibold mb-0.5">Parent B</div>
              {it.parent_b || <em className="text-[#6E6787]">no response</em>}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}


function BucketNeedsAttention({ data }) {
  if (!data.count) {
    return (
      <p className="text-sm text-[#4B4567] italic">
        Nothing is currently flagged as needing focused attention — a
        good sign, though this section will update as more topics come up.
      </p>
    );
  }
  return (
    <ul className="space-y-2.5">
      {(data.items || []).map((it, i) => (
        <li
          key={`${it.topic}-${i}`}
          className="rounded-xl bg-white/70 border border-white p-3"
        >
          <div className="text-sm font-semibold text-[#1A1330] mb-0.5">
            {it.topic}
          </div>
          {it.reason && (
            <div className="text-sm text-[#4B4567] leading-relaxed">
              {it.reason}
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
      {(data.items || []).map((it, i) => (
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
      {(data.items || []).map((it, i) => (
        <li
          key={`${it.topic}-${i}`}
          className="rounded-xl bg-white/70 border border-white p-3"
        >
          <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-[#0F6F6F] mb-1">
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


function BucketBody({ bucketKey, data }) {
  if (!data) return null;
  switch (bucketKey) {
    case "what_you_both_care_about": return <BucketCareAbout data={data} />;
    case "where_you_see_things_differently": return <BucketDifferences data={data} />;
    case "what_may_need_attention": return <BucketNeedsAttention data={data} />;
    case "options_to_consider": return <BucketOptions data={data} />;
    case "questions_for_next_conversation": return <BucketQuestions data={data} />;
    default: return null;
  }
}


export default function JointReportParentView({ parentView }) {
  if (!parentView) return null;
  return (
    <div
      className="space-y-4 sm:space-y-5"
      data-testid="joint-report-parent-view"
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
            data-testid={`joint-report-bucket-${b.key}`}
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
            <BucketBody bucketKey={b.key} data={data} />
          </section>
        );
      })}
    </div>
  );
}
