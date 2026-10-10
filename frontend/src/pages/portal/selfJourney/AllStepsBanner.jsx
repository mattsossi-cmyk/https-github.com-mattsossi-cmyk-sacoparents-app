import React, { useEffect } from "react";
import confetti from "canvas-confetti";

import { CertificateButton } from "./CertificateButton";

const PURPLES = ["#4a1d7a", "#6b2fb3", "#9b6ad6", "#c9a8f0", "#ffffff"];

// "6 of 6 finished" banner; `sparkle` plays a short purple star burst once. Holds the certificate download.
export function AllStepsBanner({ sparkle, defaultName }) {
  useEffect(() => {
    if (!sparkle) return undefined;
    const fire = (x) => confetti({ particleCount: 70, spread: 80, startVelocity: 26, scalar: 1.1, shapes: ["star"], origin: { x, y: 0.3 }, colors: PURPLES, zIndex: 70, disableForReducedMotion: true });
    fire(0.35);
    const t = setTimeout(() => fire(0.65), 220);
    return () => clearTimeout(t);
  }, [sparkle]);

  return (
    <div data-testid="door-self-all-steps-banner" role="status" className="relative overflow-hidden rounded-2xl bg-[#4a1d7a] text-white px-5 py-4 flex flex-wrap items-center gap-4 shadow-[0_12px_30px_-12px_rgba(74,29,122,0.7)]">
      <i aria-hidden="true" className="fa-solid fa-star absolute right-4 top-2 text-[10px] text-purple-300/70"></i>
      <i aria-hidden="true" className="fa-solid fa-star absolute right-10 bottom-3 text-[7px] text-purple-200/60"></i>
      <span className="shrink-0 w-12 h-12 rounded-full bg-white text-[#4a1d7a] flex items-center justify-center text-xl shadow-md">
        <i className="fa-solid fa-check"></i>
      </span>
      <div className="min-w-0 flex-1 basis-48">
        <p data-testid="door-self-all-steps-title" className="text-base font-extrabold leading-tight">6 of 6 finished</p>
        <p className="text-[12px] text-purple-100 leading-snug mt-0.5">
          Every step of your Individual Journey is done. That's a real gift to your child.
        </p>
      </div>
      <CertificateButton defaultName={defaultName} />
    </div>
  );
}
