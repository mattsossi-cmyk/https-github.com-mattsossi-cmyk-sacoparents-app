/**
 * DeepDivePartsNarrative — renders the rich per-part storytelling block
 * shared by the Educational and Psychological Deep Dive v2 report pages.
 *
 * Consumes the `parts_narrative`, `opening_story`, and `closing_story`
 * fields from the report payload. Safe to render even when the fields
 * are missing (older cached reports).
 */
import React from "react";
import { Sparkles, TrendingUp, AlertCircle } from "lucide-react";

const BAND_STYLES = {
  high:     "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]",
  moderate: "bg-[#FFF6E5] text-[#8A5B00] border-[#F0D9A8]",
  low:      "bg-[#F8D7D7] text-[#B02A2A] border-[#EFB4B4]",
  unrated:  "bg-[#F1EEF7] text-[#4B4567] border-[#E5E0EE]",
};

function BandPill({ band, headline, percent, answered }) {
  const cls = BAND_STYLES[band] || BAND_STYLES.unrated;
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[0.625rem] font-bold border ${cls}`}>
      {headline || band}
      {answered ? <span className="ml-1.5 tabular-nums">· {percent}%</span> : null}
    </span>
  );
}

export default function DeepDivePartsNarrative({
  parts,
  opening,
  closing,
  testidPrefix,
}) {
  if (!parts?.length && !opening && !closing) return null;

  return (
    <section
      className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm"
      data-testid={`${testidPrefix}-parts-narrative`}
    >
      <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
        Your story, part by part
      </div>
      <h2 className="font-serif text-xl text-[#1A1330]">
        The five parts, told back to you
      </h2>

      {opening && (
        <p
          className="mt-3 text-sm text-[#1A1330] leading-relaxed"
          data-testid={`${testidPrefix}-parts-opening`}
        >
          {opening}
        </p>
      )}

      <div className="mt-5 space-y-4">
        {(parts || []).map((part) => (
          <article
            key={part.id}
            className="rounded-2xl border border-[#EEE9F7] bg-[#FCFBFE] p-4 sm:p-5"
            data-testid={`${testidPrefix}-part-${part.id}`}
          >
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div className="min-w-0">
                <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
                  Part {part.number}
                </div>
                <div className="font-serif text-lg text-[#1A1330] mt-0.5">
                  {part.name}
                </div>
              </div>
              <BandPill
                band={part.band}
                headline={part.band_headline}
                percent={part.percent}
                answered={part.answered}
              />
            </div>
            {part.purpose && (
              <p className="mt-2 text-xs text-[#6A5799] italic">
                {part.purpose}
              </p>
            )}
            {part.narrative && (
              <p className="mt-2 text-sm text-[#1A1330] leading-relaxed">
                {part.narrative}
              </p>
            )}

            {(part.strengths || []).length > 0 && (
              <div className="mt-3" data-testid={`${testidPrefix}-part-${part.id}-strengths`}>
                <div className="flex items-center gap-1.5 text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#1F5C3B]">
                  <Sparkles size={12} /> Strengths in this part
                </div>
                <ul className="mt-1 list-disc pl-5 text-xs text-[#1A1330] space-y-1">
                  {part.strengths.map((s) => (
                    <li key={s.id}>
                      {s.prompt}
                      <span className="ml-1 text-[#1F5C3B] font-semibold">
                        (you scored {s.value}/4)
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {(part.growth || []).length > 0 && (
              <div className="mt-3" data-testid={`${testidPrefix}-part-${part.id}-growth`}>
                <div className="flex items-center gap-1.5 text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#B02A2A]">
                  <TrendingUp size={12} /> Where to grow
                </div>
                <ul className="mt-1 list-disc pl-5 text-xs text-[#1A1330] space-y-1">
                  {part.growth.map((g) => (
                    <li key={g.id}>
                      {g.prompt}
                      <span className="ml-1 text-[#B02A2A] font-semibold">
                        (you scored {g.value}/4)
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {part.child_reflection && (
              <div
                className="mt-3 flex items-start gap-2 rounded-xl border border-[#D6CFE8] bg-[#F5F1FB] px-3 py-2"
                data-testid={`${testidPrefix}-part-${part.id}-child-reflection`}
              >
                <AlertCircle size={13} className="shrink-0 mt-0.5 text-[#3D1A78]" />
                <p className="text-xs text-[#3D1A78] italic">
                  {part.child_reflection}
                </p>
              </div>
            )}
          </article>
        ))}
      </div>

      {closing && (
        <div
          className="mt-5 rounded-2xl border border-[#D6CFE8] bg-[#F5F1FB] p-4"
          data-testid={`${testidPrefix}-parts-closing`}
        >
          <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-1">
            A note to close
          </div>
          <p className="text-sm text-[#1A1330] leading-relaxed">{closing}</p>
        </div>
      )}
    </section>
  );
}
