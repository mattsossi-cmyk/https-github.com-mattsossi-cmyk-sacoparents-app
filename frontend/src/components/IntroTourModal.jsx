import React, { useEffect, useRef, useState } from "react";
import { X, Volume2, VolumeX } from "lucide-react";

const STORAGE_KEY = "sac_intro_tour_seen_v3_branded";
const SKIP_AFTER_MS = 3000;
// Hard cap: if the video errors or never reports playback progress within
// this window, we auto-proceed so the parent flow (guest login + navigate to
// dashboard) is never stuck behind an un-playable video. Chosen to be longer
// than the ~55 s intro so a normally-playing video always ends first.
const MAX_STALL_MS = 15000;

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
  const [videoFailed, setVideoFailed] = useState(false);

  useEffect(() => {
    if (!open) return;
    setCanSkip(false);
    setMuted(false);
    setNeedsUnmutedTap(false);
    setVideoFailed(false);
    const skipTimer = setTimeout(() => setCanSkip(true), SKIP_AFTER_MS);

    // Failsafe watchdog: if the video hasn't reported any playback progress
    // within MAX_STALL_MS, treat it as failed and let the user through so
    // they aren't stuck watching a black screen.
    let stallTimer = setTimeout(() => {
      const v = videoRef.current;
      const progressed = v && Number.isFinite(v.currentTime) && v.currentTime > 0.1;
      if (!progressed) setVideoFailed(true);
    }, MAX_STALL_MS);

    // Reset the stall timer every time the video actually reports progress.
    const v = videoRef.current;
    const onTime = () => {
      if (v && v.currentTime > 0.1) {
        clearTimeout(stallTimer);
      }
    };
    v?.addEventListener("timeupdate", onTime);

    return () => {
      clearTimeout(skipTimer);
      clearTimeout(stallTimer);
      v?.removeEventListener("timeupdate", onTime);
    };
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
        src="/intro-tour.mp4?v=slideshow-2026-07-07h"
        autoPlay
        playsInline
        onEnded={close}
        onError={() => setVideoFailed(true)}
        className="max-w-full max-h-full"
        data-testid="intro-tour-video"
      />

      {/* Video-failed fallback — if the intro can't play, don't strand the
          user. Offer a clear "Enter" action that fires the same close/proceed
          handler the video's onEnded would have. */}
      {videoFailed && (
        <div
          className="absolute inset-0 flex flex-col items-center justify-center text-center px-6 gap-5 bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] text-white"
          data-testid="intro-tour-fallback"
        >
          <div className="font-serif text-2xl sm:text-3xl leading-snug max-w-md">
            The intro video couldn&apos;t load, but your assessment is ready.
          </div>
          <button
            onClick={close}
            className="px-6 py-3 rounded-full bg-white text-[#3D1A78] font-semibold text-sm shadow-xl hover:scale-[1.02] transition-transform"
            data-testid="intro-tour-enter-now-button"
          >
            Enter the assessment
          </button>
        </div>
      )}

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
