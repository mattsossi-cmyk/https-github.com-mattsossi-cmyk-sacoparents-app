import React, { useEffect, useRef, useState } from "react";
import { Play, Pause, Volume2, VolumeX, Maximize2, Film } from "lucide-react";

/**
 * WatchFirstVideo — an inline video player designed to introduce a step in the
 * guided parent journey. Same visual language as ListenFirstButton but plays a
 * short reflection video (branded background + narration + on-screen title).
 *
 * Props:
 *   videoSrc:   string  — public URL of the mp4
 *   posterSrc:  string  — optional poster image
 *   label:      string  — pill label (e.g. "Watch First")
 *   subtitle:   string  — the "what this video is" line
 *   testid:     string  — data-testid prefix
 */
export default function WatchFirstVideo({
  videoSrc,
  posterSrc,
  label = "Watch First",
  subtitle = "A short reflection before you begin",
  testid = "watch-first",
}) {
  const videoRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return undefined;
    const onTime = () => setProgress(v.currentTime);
    const onLoaded = () => setDuration(v.duration || 0);
    const onEnded = () => {
      setPlaying(false);
      setProgress(0);
    };
    const onErr = () => {
      setError("Couldn’t play the video. Try refreshing.");
      setPlaying(false);
    };
    v.addEventListener("timeupdate", onTime);
    v.addEventListener("loadedmetadata", onLoaded);
    v.addEventListener("ended", onEnded);
    v.addEventListener("error", onErr);
    return () => {
      v.removeEventListener("timeupdate", onTime);
      v.removeEventListener("loadedmetadata", onLoaded);
      v.removeEventListener("ended", onEnded);
      v.removeEventListener("error", onErr);
    };
  }, [videoSrc]);

  // Pause on unmount so the video doesn't keep playing after route change.
  useEffect(() => {
    return () => {
      const v = videoRef.current;
      if (v && !v.paused) {
        try {
          v.pause();
        } catch (_e) {
          /* noop */
        }
      }
    };
  }, []);

  const toggle = async () => {
    const v = videoRef.current;
    if (!v) return;
    setError(null);
    if (playing) {
      v.pause();
      setPlaying(false);
      return;
    }
    try {
      await v.play();
      setPlaying(true);
    } catch (_e) {
      setError("Tap play again if the video didn’t start.");
    }
  };

  const toggleMute = () => {
    const v = videoRef.current;
    if (!v) return;
    const next = !muted;
    v.muted = next;
    setMuted(next);
  };

  const goFullscreen = async () => {
    const v = videoRef.current;
    if (!v) return;
    try {
      if (v.requestFullscreen) await v.requestFullscreen();
      else if (v.webkitEnterFullscreen) v.webkitEnterFullscreen();
    } catch (_e) {
      /* silently fail — some browsers block */
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
      className="rounded-2xl overflow-hidden bg-[#1A1330] shadow-md border border-[#E5E0EE]"
      data-testid={`${testid}-panel`}
    >
      {/* Video surface */}
      <div className="relative aspect-[4/5] sm:aspect-[16/9] bg-black">
        <video
          ref={videoRef}
          src={videoSrc}
          poster={posterSrc}
          preload="metadata"
          playsInline
          className="absolute inset-0 w-full h-full object-cover"
          onClick={toggle}
          data-testid={`${testid}-video`}
        />
        {/* Center play overlay when paused */}
        {!playing && (
          <button
            type="button"
            onClick={toggle}
            aria-label="Play video"
            data-testid={`${testid}-center-play`}
            className="absolute inset-0 flex items-center justify-center bg-black/25 hover:bg-black/15 transition-colors"
          >
            <span className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-white text-[#3D1A78] grid place-items-center shadow-2xl">
              <Play size={28} className="ml-1" />
            </span>
          </button>
        )}
        {/* Top label */}
        <div className="absolute top-0 left-0 right-0 p-3 sm:p-4 flex items-center justify-between text-white text-[10px] uppercase tracking-[0.22em] font-bold pointer-events-none">
          <span className="inline-flex items-center gap-1.5 bg-black/40 rounded-full px-2.5 py-1 backdrop-blur-sm">
            <Film size={11} />
            {label}
          </span>
        </div>
      </div>

      {/* Controls strip */}
      <div className="bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-4 py-3 sm:px-5 sm:py-3.5">
        <div className="flex items-center gap-3 sm:gap-4">
          <button
            type="button"
            onClick={toggle}
            data-testid={`${testid}-toggle-button`}
            aria-label={playing ? "Pause" : "Play"}
            className="shrink-0 w-10 h-10 rounded-full bg-white text-[#3D1A78] grid place-items-center hover:scale-105 transition-transform"
          >
            {playing ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
          </button>
          <div className="flex-1 min-w-0">
            <div className="text-sm sm:text-base font-bold leading-tight truncate">
              {subtitle}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <div className="flex-1 h-1.5 rounded-full bg-white/25 overflow-hidden">
                <div
                  className="h-full bg-white transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-[11px] tabular-nums opacity-90 shrink-0">
                {fmt(progress)} / {fmt(duration)}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={toggleMute}
            data-testid={`${testid}-mute-button`}
            aria-label={muted ? "Unmute" : "Mute"}
            className="shrink-0 w-9 h-9 rounded-full bg-white/15 hover:bg-white/25 grid place-items-center"
          >
            {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
          </button>
          <button
            type="button"
            onClick={goFullscreen}
            data-testid={`${testid}-fullscreen-button`}
            aria-label="Fullscreen"
            className="shrink-0 w-9 h-9 rounded-full bg-white/15 hover:bg-white/25 grid place-items-center"
          >
            <Maximize2 size={14} />
          </button>
        </div>
        {error && (
          <div className="text-[11px] text-white/90 mt-1.5" data-testid={`${testid}-error`}>
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
