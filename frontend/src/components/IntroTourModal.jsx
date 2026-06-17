import React, { useEffect, useRef, useState } from "react";
import { X, Volume2, VolumeX } from "lucide-react";

const STORAGE_KEY = "sac_intro_tour_seen_v3_branded";
const SKIP_AFTER_MS = 3000;

/**
 * Full-screen video overlay that plays once per device after the user clicks
 * "Enter the App". Skippable after 3 seconds. Persists a flag in localStorage
 * so returning visitors don't see it again.
 *
 * Usage:
 *   <IntroTourModal open={showIntro} onClose={() => setShowIntro(false)} />
 *
 * To trigger:
 *   if (!IntroTourModal.hasBeenSeen()) setShowIntro(true);
 *
 * Call `IntroTourModal.markSeen()` after closing to remember it.
 */
export default function IntroTourModal({ open, onClose }) {
  const videoRef = useRef(null);
  const [canSkip, setCanSkip] = useState(false);
  const [muted, setMuted] = useState(false);
  const [needsUnmutedTap, setNeedsUnmutedTap] = useState(false);

  useEffect(() => {
    if (!open) return;
    setCanSkip(false);
    setMuted(false);
    setNeedsUnmutedTap(false);
    const timer = setTimeout(() => setCanSkip(true), SKIP_AFTER_MS);
    return () => clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!open || !videoRef.current) return;
    const v = videoRef.current;
    v.muted = false;
    // Try to autoplay with sound. If the browser blocks it (mobile Safari, etc.),
    // fall back to muted autoplay + show a "tap to unmute" hint.
    const playPromise = v.play();
    if (playPromise && typeof playPromise.catch === "function") {
      playPromise.catch(() => {
        v.muted = true;
        setMuted(true);
        setNeedsUnmutedTap(true);
        v.play().catch(() => {
          /* if even muted autoplay fails, user can press play manually */
        });
      });
    }
  }, [open]);

  if (!open) return null;

  const close = () => {
    try {
      window.localStorage.setItem(STORAGE_KEY, "1");
    } catch (_e) {
      /* private mode */
    }
    onClose?.();
  };

  const toggleMute = () => {
    const v = videoRef.current;
    if (!v) return;
    v.muted = !v.muted;
    setMuted(v.muted);
    if (!v.muted) setNeedsUnmutedTap(false);
  };

  return (
    <div
      className="fixed inset-0 z-[100] bg-black flex items-center justify-center"
      data-testid="intro-tour-modal"
    >
      <video
        ref={videoRef}
        src="/intro-tour.mp4?v=branded-2026-06-17"
        autoPlay
        playsInline
        onEnded={close}
        className="max-w-full max-h-full"
        data-testid="intro-tour-video"
      />

      {/* Tap-to-unmute hint (only when autoplay-with-sound was blocked) */}
      {needsUnmutedTap && (
        <button
          onClick={toggleMute}
          className="absolute bottom-24 left-1/2 -translate-x-1/2 bg-white/95 text-[#3D1A78] px-5 py-3 rounded-full text-sm font-semibold shadow-2xl backdrop-blur-sm flex items-center gap-2 hover:bg-white"
          data-testid="intro-tour-unmute-button"
        >
          <Volume2 size={16} />
          Tap for sound
        </button>
      )}

      {/* Mute toggle */}
      <button
        onClick={toggleMute}
        className="absolute top-6 left-6 w-11 h-11 grid place-items-center rounded-full bg-black/50 text-white hover:bg-black/70 backdrop-blur-sm"
        aria-label={muted ? "Unmute" : "Mute"}
        data-testid="intro-tour-mute-button"
      >
        {muted ? <VolumeX size={18} /> : <Volume2 size={18} />}
      </button>

      {/* Skip button — disabled for first 3s */}
      <button
        onClick={close}
        disabled={!canSkip}
        className={`absolute top-6 right-6 px-4 py-2 rounded-full text-sm font-semibold backdrop-blur-sm transition-opacity ${
          canSkip
            ? "bg-white/95 text-[#3D1A78] hover:bg-white"
            : "bg-white/30 text-white cursor-not-allowed"
        }`}
        data-testid="intro-tour-skip-button"
      >
        {canSkip ? "Skip intro" : "Skip in a moment…"}
      </button>

      {/* X dismiss (always available) */}
      <button
        onClick={close}
        className="absolute bottom-6 right-6 w-11 h-11 grid place-items-center rounded-full bg-black/50 text-white hover:bg-black/70 backdrop-blur-sm"
        aria-label="Close intro"
        data-testid="intro-tour-close-button"
      >
        <X size={18} />
      </button>
    </div>
  );
}

IntroTourModal.hasBeenSeen = () => {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "1";
  } catch (_e) {
    return false;
  }
};

IntroTourModal.markSeen = () => {
  try {
    window.localStorage.setItem(STORAGE_KEY, "1");
  } catch (_e) {
    /* private mode */
  }
};
