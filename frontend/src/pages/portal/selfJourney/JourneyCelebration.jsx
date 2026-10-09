import React, { useEffect } from "react";
import confetti from "canvas-confetti";

import { CourtDialog } from "../court/CourtDialog";

const COLORS = ["#3b1566", "#6b2fb3", "#2f9e44", "#1a73d9", "#f1d9a0"];

// Shown once per parent, the first time all five Self Journey assessments are done.
export function JourneyCelebration({ open, onClose, onPdf, downloading }) {
  useEffect(() => {
    if (!open) return undefined;
    const fire = (x) => confetti({ particleCount: 60, spread: 70, startVelocity: 28, origin: { x, y: 0.6 }, colors: COLORS, zIndex: 70, disableForReducedMotion: true });
    fire(0.3);
    const t = setTimeout(() => fire(0.7), 250);
    return () => clearTimeout(t);
  }, [open]);

  return (
    <CourtDialog
      open={open}
      onClose={onClose}
      testid="journey-celebration"
      title="You did this for your child"
      desc="All five assessments are complete. Taking the time to understand yourself, your co-parenting, and your child's needs is a real gift to them."
    >
      <div className="text-center -mt-1 mb-5">
        <span className="inline-flex w-16 h-16 rounded-full bg-purple-50 text-[#6b2fb3] items-center justify-center text-3xl">
          <i className="fa-solid fa-heart"></i>
        </span>
      </div>
      <div className="flex flex-col sm:flex-row gap-2.5">
        <button
          type="button"
          data-testid="journey-celebration-pdf"
          onClick={onPdf}
          disabled={downloading}
          className="flex-1 bg-[#2f9e44] hover:bg-[#268539] disabled:opacity-60 text-white font-bold py-3 px-5 rounded-lg transition-colors"
        >
          <i className="fa-solid fa-file-pdf mr-2"></i>Download Journey Summary
        </button>
        <button
          type="button"
          data-testid="journey-celebration-done"
          onClick={onClose}
          className="flex-1 bg-[#f2ebfc] hover:bg-[#e7dbf8] text-[#3b1566] font-bold py-3 px-5 rounded-lg transition-colors"
        >
          Close
        </button>
      </div>
    </CourtDialog>
  );
}
