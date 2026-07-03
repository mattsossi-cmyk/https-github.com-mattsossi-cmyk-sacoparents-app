import React, { useEffect, useRef, useState } from "react";
import { Play, Pause, Volume2, Headphones } from "lucide-react";

/**
 * "Listen First" button — plays a short audio narration before the parent
 * answers the questions on the page. Designed to sit at the top of each
 * guided-journey step.
 *
 * Props:
 *   audioSrc:  string  — public URL of the mp3 (e.g. "/audio/listen-first/step-1-...")
 *   label:     string  — optional pill label, defaults to "Listen First"
 *   subtitle:  string  — optional secondary text
 *   testid:    string  — data-testid prefix (e.g. "step-1-listen")
 */
export default function ListenFirstButton({
  audioSrc,
  label = "Listen First",
  subtitle = "A short guide before you begin",
  testid = "listen-first",
}) {
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    const a = audioRef.current;
    if (!a) return undefined;
    const onTime = () => setProgress(a.currentTime);
    const onLoaded = () => setDuration(a.duration || 0);
    const onEnded = () => {
      setPlaying(false);
      setProgress(0);
    };
    const onErr = () => {
      setError("Couldn’t play the audio. Try refreshing.");
      setPlaying(false);
    };
    a.addEventListener("timeupdate", onTime);
    a.addEventListener("loadedmetadata", onLoaded);
    a.addEventListener("ended", onEnded);
    a.addEventListener("error", onErr);
    return () => {
      a.removeEventListener("timeupdate", onTime);
      a.removeEventListener("loadedmetadata", onLoaded);
      a.removeEventListener("ended", onEnded);
      a.removeEventListener("error", onErr);
    };
  }, [audioSrc]);

  // Pause on unmount so audio doesn't keep playing after navigating away.
  useEffect(() => {
    return () => {
      const a = audioRef.current;
      if (a && !a.paused) {
        try {
          a.pause();
        } catch (_e) {
          /* noop */
        }
      }
    };
  }, []);

  const toggle = async () => {
    const a = audioRef.current;
    if (!a) return;
    setError(null);
    if (playing) {
      a.pause();
      setPlaying(false);
      return;
    }
    try {
      await a.play();
      setPlaying(true);
    } catch (_e) {
      setError("Tap play again if audio didn’t start.");
    }
  };

  const pct = duration > 0 ? Math.min(100, (progress / duration) * 100) : 0;
  const fmt = (s) => {
    if (!Number.isFinite(s) || s <= 0) return "0:00";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div
      className="rounded-2xl bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] text-white p-4 sm:p-5 shadow-md"
      data-testid={`${testid}-panel`}
    >
      <div className="flex items-start gap-3 sm:gap-4">
        <button
          type="button"
          onClick={toggle}
          data-testid={`${testid}-toggle-button`}
          aria-label={playing ? "Pause narration" : "Play narration"}
          className={`shrink-0 w-12 h-12 sm:w-14 sm:h-14 rounded-full grid place-items-center transition-all ${
            playing
              ? "bg-white text-[#3D1A78]"
              : "bg-white text-[#3D1A78] hover:scale-105"
          }`}
        >
          {playing ? <Pause size={22} /> : <Play size={22} className="ml-0.5" />}
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] font-bold opacity-90 mb-1">
            <Headphones size={11} />
            <span>{label}</span>
          </div>
          <div className="font-bold text-base sm:text-lg leading-tight mb-2">
            {subtitle}
          </div>
          <div className="flex items-center gap-3">
            <div className="flex-1 h-1.5 rounded-full bg-white/25 overflow-hidden">
              <div
                className="h-full bg-white transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="text-[11px] tabular-nums opacity-90 shrink-0">
              {fmt(progress)} / {fmt(duration)}
            </div>
            <Volume2 size={14} className="opacity-70 shrink-0" />
          </div>
          {error && (
            <div className="text-[11px] text-white/90 mt-1.5" data-testid={`${testid}-error`}>
              {error}
            </div>
          )}
        </div>
      </div>
      <audio ref={audioRef} src={audioSrc} preload="metadata" data-testid={`${testid}-audio`} />
    </div>
  );
}
