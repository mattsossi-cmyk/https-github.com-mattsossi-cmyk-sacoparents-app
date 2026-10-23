/**
 * Self Journey awards: one pop-up per big milestone, with the SA CoParents logo (purple / dark blue / white).
 * Milestones: Self-Assessment done, Co-Parenting Assessment done, Foundation Statement approved, whole journey.
 * Each is granted once (dated in progress.awards). The last one unlocks the printable certificate.
 */
import React, { useEffect, useRef, useState } from "react";
import confetti from "canvas-confetti";

export const MILESTONES = ["selfAssessment", "coparenting", "foundation"];

export const AWARDS = {
  selfAssessment: {
    title: "Self-Reflection Award",
    text: "You completed your Self-Assessment. Taking an honest look at yourself is a gift to your child.",
  },
  coparenting: {
    title: "Co-Parenting Insight Award",
    text: "You completed your Co-Parenting Assessment. Understanding how things work today helps you plan what comes next.",
  },
  foundation: {
    title: "Foundation Award",
    text: "You approved your Foundation Statement, the principles that will guide your decisions for your child.",
  },
  journey: {
    title: "Self Journey Award",
    text: "You completed your SA CoParents Self Journey. Your certificate is ready to download and print.",
  },
};

// Grants the next earned milestone once and shows its pop-up; waits while `paused` (an assessment or sheet is open).
export function useMilestoneAwards({ progress, setProgress, saveRef, earned, paused }) {
  const [award, setAward] = useState(null);
  const key = MILESTONES.find((k) => earned[k] && !progress.awards?.[k]);
  useEffect(() => {
    if (paused || award || !key) return;
    const next = { ...progress, awards: { ...progress.awards, [key]: new Date().toISOString() } };
    setProgress(next);
    Promise.resolve(saveRef.current?.(next)).catch(() => {});
    setAward(key);
  }, [paused, award, key]); // eslint-disable-line react-hooks/exhaustive-deps
  return [award, setAward];
}

const still = (calm) => calm || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export function AwardModal({ award, logoSrc, calm, onClose, onCertificate }) {
  const closeRef = useRef(null);
  const a = AWARDS[award];

  useEffect(() => {
    closeRef.current?.focus();
    if (!still(calm)) {
      confetti({ particleCount: 90, spread: 70, origin: { y: 0.3 }, zIndex: 60, disableForReducedMotion: true,
        colors: ["#5b3fa0", "#1b2a6b", "#c9b8f0", "#ffffff"] });
    }
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [award]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="sj-award-scrim" data-testid="sj-award-overlay">
      <div className="sj-award" role="dialog" aria-modal="true" aria-labelledby="sj-award-title" data-testid="sj-award" data-award={award}>
        <p className="sj-award-kicker">Award earned</p>
        <div className="sj-award-medal">
          <img src={logoSrc} alt="SA CoParents" data-testid="sj-award-logo" />
        </div>
        <h2 id="sj-award-title" data-testid="sj-award-title">{a.title}</h2>
        <p className="sj-award-text">{a.text}</p>
        {award === "journey" && (
          <button type="button" className="sj-next sj-award-btn" onClick={onCertificate} data-testid="sj-award-certificate">
            Download my certificate
          </button>
        )}
        <button type="button" ref={closeRef} className="sj-outline-btn sj-award-btn" onClick={onClose} data-testid="sj-award-close">
          {award === "journey" ? "Close" : "Keep going"}
        </button>
      </div>
    </div>
  );
}
