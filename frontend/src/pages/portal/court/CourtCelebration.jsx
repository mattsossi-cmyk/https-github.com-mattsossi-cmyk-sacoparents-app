import React, { useEffect } from "react";
import confetti from "canvas-confetti";

import { CourtDialog } from "./CourtDialog";

const COLORS = ["#3b1566", "#7b2cbf", "#2fa144", "#f1d9a0", "#3a86ff"];

// Shown once to each parent when every differing area is marked agreed.
export function CourtCelebration({ open, notice, onClose, onPdf }) {
  useEffect(() => {
    if (!open) return;
    const fire = (x) => confetti({ particleCount: 70, spread: 70, startVelocity: 32, origin: { x, y: 0.6 }, colors: COLORS, zIndex: 70, disableForReducedMotion: true });
    fire(0.3);
    const t = setTimeout(() => fire(0.7), 250);
    return () => clearTimeout(t);
  }, [open]);

  return (
    <CourtDialog open={open} onClose={onClose} testid="court-celebration" title="You did this together" desc="Every area where your answers differed is now marked agreed. That takes patience, and it puts your child first.">
      <div className="text-center -mt-1 mb-4">
        <span className="inline-flex w-16 h-16 rounded-full bg-emerald-50 text-[#2fa144] items-center justify-center text-3xl">
          <i className="fa-solid fa-handshake"></i>
        </span>
      </div>
      <p data-testid="court-celebration-notice" className="text-[0.6875rem] leading-snug text-[#5c2c8e] bg-[#f2ebfc] rounded-lg px-3 py-2 mb-5">{notice}</p>
      <div className="flex flex-col sm:flex-row gap-2.5">
        <button type="button" data-testid="court-celebration-pdf" onClick={onPdf} className="flex-1 bg-[#2fa144] hover:bg-[#268537] text-white font-bold py-3 px-5 rounded-lg transition-colors">
          <i className="fa-solid fa-file-pdf mr-2"></i>Download Comparison PDF
        </button>
        <button type="button" data-testid="court-celebration-done" onClick={onClose} className="flex-1 bg-[#f2ebfc] hover:bg-[#e7dbf8] text-[#3b1566] font-bold py-3 px-5 rounded-lg transition-colors">
          Close
        </button>
      </div>
    </CourtDialog>
  );
}
