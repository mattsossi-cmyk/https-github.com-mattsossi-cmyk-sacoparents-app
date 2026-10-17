import React, { useEffect, useRef, useState } from "react";
import { Wind, Pause, Play, X } from "lucide-react";

/**
 * 4-7-8 breathing exercise — proven to engage the parasympathetic nervous
 * system and reduce stress within 60–90 seconds. Used inside the Reflection
 * page before journaling, and any time a user feels overwhelmed.
 *
 * Cycle: Inhale 4s → Hold 7s → Exhale 8s. Default: 4 cycles (~76 seconds).
 */
const PHASES = [
  { key: "inhale", label: "Breathe in",  cue: "through your nose",      seconds: 4 },
  { key: "hold",   label: "Hold gently", cue: "with soft shoulders",    seconds: 7 },
  { key: "exhale", label: "Breathe out", cue: "slowly through your mouth", seconds: 8 },
];

export default function BreathingExercise({ cycles = 4, onComplete, embedded = false }) {
  const [running, setRunning] = useState(false);
  const [phaseIdx, setPhaseIdx] = useState(0);
  const [cycleNum, setCycleNum] = useState(1);
  const [tick, setTick] = useState(0);
  const tickRef = useRef(null);

  // Tick every 100ms for smooth animation
  useEffect(() => {
    if (!running) {
      if (tickRef.current) clearInterval(tickRef.current);
      tickRef.current = null;
      return undefined;
    }
    tickRef.current = setInterval(() => setTick((t) => t + 1), 100);
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, [running]);

  // Advance phases / cycles based on tick
  useEffect(() => {
    if (!running) return;
    const phase = PHASES[phaseIdx];
    const seconds = tick / 10;
    if (seconds >= phase.seconds) {
      if (phaseIdx === PHASES.length - 1) {
        // End of cycle
        if (cycleNum >= cycles) {
          setRunning(false);
          setCycleNum(1);
          setPhaseIdx(0);
          setTick(0);
          onComplete?.();
          return;
        }
        setCycleNum((n) => n + 1);
        setPhaseIdx(0);
      } else {
        setPhaseIdx((i) => i + 1);
      }
      setTick(0);
    }
  }, [tick, running, phaseIdx, cycleNum, cycles, onComplete]);

  const phase = PHASES[phaseIdx];
  const secondsLeft = Math.max(0, Math.ceil(phase.seconds - tick / 10));
  // Circle scale animation: grows on inhale, holds on hold, shrinks on exhale
  let scale = 1;
  if (running) {
    const progress = Math.min(1, tick / 10 / phase.seconds);
    if (phase.key === "inhale") scale = 0.55 + progress * 0.45;
    else if (phase.key === "hold") scale = 1;
    else if (phase.key === "exhale") scale = 1 - progress * 0.45;
  } else {
    scale = 0.55;
  }

  const start = () => {
    setPhaseIdx(0);
    setCycleNum(1);
    setTick(0);
    setRunning(true);
  };
  const stop = () => {
    setRunning(false);
    setPhaseIdx(0);
    setCycleNum(1);
    setTick(0);
  };

  return (
    <div
      className={`relative ${embedded ? "" : "card-soft p-6 sm:p-8"} text-center`}
      data-testid="breathing-exercise"
    >
      {!embedded && (
        <>
          <div className="eyebrow mb-2">Take a moment</div>
          <div className="font-serif text-2xl sm:text-3xl text-[#1A1330] mb-1">
            A breath before you begin.
          </div>
          <p className="text-[14px] text-[#4B4567] mb-6 max-w-md mx-auto">
            Four cycles of 4-7-8 breathing. About one minute. Lowers the noise so what
            you write here can come from your wiser self, not your reactive one.
          </p>
        </>
      )}

      {/* Animated breath circle */}
      <div className="relative h-72 sm:h-80 flex items-center justify-center mb-6">
        <div
          className="absolute rounded-full bg-[#3D1A78]/15 transition-transform duration-1000 ease-in-out"
          style={{
            width: 240,
            height: 240,
            transform: `scale(${scale * 1.25})`,
          }}
        />
        <div
          className="absolute rounded-full bg-[#3D1A78]/25 transition-transform duration-1000 ease-in-out"
          style={{
            width: 200,
            height: 200,
            transform: `scale(${scale * 1.1})`,
          }}
        />
        <div
          className="absolute rounded-full bg-[#3D1A78]/40 transition-transform duration-1000 ease-in-out flex items-center justify-center"
          style={{
            width: 160,
            height: 160,
            transform: `scale(${scale})`,
          }}
        >
          <div className="text-center">
            <div className="text-white font-serif text-2xl mb-0.5" data-testid="breathing-phase-label">
              {running ? phase.label : "Ready?"}
            </div>
            {running && (
              <div className="text-white/85 text-xs">{phase.cue}</div>
            )}
          </div>
        </div>
      </div>

      {/* Status row */}
      <div className="flex items-center justify-center gap-6 mb-6 text-[13px] text-[#4B4567]">
        <div>
          <div className="uppercase tracking-wider text-[10px] text-[#6E6787]">Cycle</div>
          <div className="font-serif text-lg text-[#1A1330]" data-testid="breathing-cycle">
            {cycleNum} / {cycles}
          </div>
        </div>
        <div className="w-px h-8 bg-[#E5E0EE]" />
        <div>
          <div className="uppercase tracking-wider text-[10px] text-[#6E6787]">Time</div>
          <div className="font-serif text-lg text-[#1A1330]" data-testid="breathing-countdown">
            {secondsLeft}s
          </div>
        </div>
      </div>

      <div className="flex items-center justify-center gap-3">
        {!running ? (
          <button
            onClick={start}
            className="btn-sage inline-flex items-center gap-2"
            data-testid="breathing-start-button"
          >
            <Play size={16} />
            {cycleNum > 1 ? "Resume" : "Begin"}
          </button>
        ) : (
          <button
            onClick={stop}
            className="btn-soft inline-flex items-center gap-2"
            data-testid="breathing-stop-button"
          >
            <Pause size={16} /> Stop
          </button>
        )}
      </div>
    </div>
  );
}

/** Compact modal version usable from anywhere in the app */
export function BreathingModal({ open, onClose }) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 bg-[#1A1330]/70 backdrop-blur-sm flex items-center justify-center p-4"
      data-testid="breathing-modal"
    >
      <div className="bg-white rounded-3xl max-w-md w-full p-6 sm:p-8 relative shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-[#4B4567] hover:text-[#1A1330]"
          aria-label="Close"
          data-testid="breathing-modal-close"
        >
          <X size={18} />
        </button>
        <div className="flex items-center gap-2 mb-1">
          <Wind size={16} className="text-[#3D1A78]" />
          <div className="eyebrow">Breathing exercise</div>
        </div>
        <BreathingExercise embedded onComplete={onClose} />
      </div>
    </div>
  );
}
