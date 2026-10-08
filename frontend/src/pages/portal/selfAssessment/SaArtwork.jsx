import React from "react";

const SA_ALT =
  "Self Assessment: reflect on your strengths, identify growth areas, set personal goals and track your progress. Your journey. Your growth. A brighter future for your child.";

// Page artwork (top on phones, right column on desktop). `name` maps to /images/{name}.webp + -640.webp.
export function SaArtwork({ testid, className = "", name = "sa-self-assessment", alt = SA_ALT }) {
  return (
    <img
      data-testid={testid}
      src={`/images/${name}-640.webp`}
      srcSet={`/images/${name}-640.webp 640w, /images/${name}.webp 1024w`}
      sizes="(min-width: 1024px) 440px, 100vw"
      alt={alt}
      width={1024}
      height={1536}
      className={`w-full h-auto rounded-3xl shadow-lg border border-purple-100 ${className}`}
    />
  );
}
