import React from "react";

const ALT =
  "Self Assessment: reflect on your strengths, identify growth areas, set personal goals and track your progress. Your journey. Your growth. A brighter future for your child.";

// Self Assessment artwork (top on phones, right column on desktop).
export function SaArtwork({ testid, className = "" }) {
  return (
    <img
      data-testid={testid}
      src="/images/sa-self-assessment-640.webp"
      srcSet="/images/sa-self-assessment-640.webp 640w, /images/sa-self-assessment.webp 1024w"
      sizes="(min-width: 1024px) 440px, 100vw"
      alt={ALT}
      width={1024}
      height={1536}
      className={`w-full h-auto rounded-3xl shadow-lg border border-purple-100 ${className}`}
    />
  );
}
