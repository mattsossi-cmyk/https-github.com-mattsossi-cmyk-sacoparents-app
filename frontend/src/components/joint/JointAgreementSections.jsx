/**
 * JointAgreementSections — reusable render pieces for the Joint
 * Co-Parenting Agreement Draft.
 *
 * Extracted from `pages/JointAgreement.jsx` so the authenticated view
 * and the public shared-link view can render the same buckets/sections
 * without duplicating markup. Both files import from here.
 */
import React from "react";

export function Bucket({ label, colour, items, mode, parentAName, parentBName }) {
  return (
    <div
      className="rounded-2xl border p-4 sm:p-5"
      style={{ backgroundColor: `${colour}0F`, borderColor: `${colour}55` }}
      data-testid={`joint-agreement-bucket-${mode}`}
    >
      <div
        className="text-[0.6875rem] uppercase tracking-[0.22em] font-bold mb-3"
        style={{ color: colour }}
      >
        {label}{" "}
        <span className="text-[#6E6787] font-semibold">· {items.length}</span>
      </div>
      {items.length === 0 ? (
        <div className="text-sm text-[#6E6787] italic">(none)</div>
      ) : (
        <ul className="space-y-3">
          {items.map((it, i) => {
            if (mode === "both") {
              const rowKey = `${it.area || ""}::${it.parent_a_text || ""}::${it.parent_b_text || ""}::${i}`;
              return (
                <li key={rowKey} className="rounded-xl bg-white p-3 border border-white/60">
                  {it.area && (
                    <div className="text-[0.625rem] uppercase tracking-wider text-[#6E6787] font-semibold mb-1">
                      {it.area}
                    </div>
                  )}
                  <div className="grid sm:grid-cols-2 gap-3">
                    <div className="rounded-lg bg-[#F7F4FC] p-2.5">
                      <div className="text-[0.625rem] uppercase tracking-wider text-[#3D1A78] font-semibold mb-1">
                        {parentAName}
                      </div>
                      <div className="text-sm text-[#1A1330]">{it.parent_a_text}</div>
                    </div>
                    <div className="rounded-lg bg-[#EAF7F7] p-2.5">
                      <div className="text-[0.625rem] uppercase tracking-wider text-[#0F6F6F] font-semibold mb-1">
                        {parentBName}
                      </div>
                      <div className="text-sm text-[#1A1330]">{it.parent_b_text}</div>
                    </div>
                  </div>
                </li>
              );
            }
            const rowKey = `${it.area || ""}::${it.text || ""}::${i}`;
            return (
              <li
                key={rowKey}
                className="rounded-xl bg-white p-3 border border-white/60"
              >
                {it.area && (
                  <div className="text-[0.625rem] uppercase tracking-wider text-[#6E6787] font-semibold mb-1">
                    {it.area}
                  </div>
                )}
                <div className="text-sm text-[#1A1330]">{it.text}</div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function Section({ section, parentAName, parentBName }) {
  return (
    <section
      className="mt-8"
      data-testid={`joint-agreement-section-${section.key}`}
    >
      <div className="flex items-center gap-2 mb-2">
        <h2 className="font-serif text-2xl text-[#1A1330]">{section.title}</h2>
        <span className="text-xs text-[#6E6787]">
          {section.counts.both_proposed} both ·{" "}
          {section.counts.parent_a_only} {parentAName} ·{" "}
          {section.counts.parent_b_only} {parentBName}
        </span>
      </div>
      {section.description && (
        <p className="text-sm text-[#4B4567] mb-4 leading-relaxed max-w-3xl">
          {section.description}
        </p>
      )}
      <div className="grid gap-3">
        <Bucket
          label="Both proposed"
          colour="#1F5C3B"
          items={section.both_proposed || []}
          mode="both"
          parentAName={parentAName}
          parentBName={parentBName}
        />
        <Bucket
          label={`${parentAName} only`}
          colour="#3D1A78"
          items={section.parent_a_only || []}
          mode="a"
          parentAName={parentAName}
          parentBName={parentBName}
        />
        <Bucket
          label={`${parentBName} only`}
          colour="#8A6B12"
          items={section.parent_b_only || []}
          mode="b"
          parentAName={parentAName}
          parentBName={parentBName}
        />
      </div>
    </section>
  );
}
