/**
 * ProfessionalsIntroAudio — shimmer-voiced audio explainer for the
 * /for-professionals page. Public asset (no auth required).
 *
 * UX:
 *  * Lazy: does NOT hit the audio endpoint on mount (that would fire
 *    the TTS call for every page-view even from bots). Only calls
 *    `/manifest` on mount to render the transcript. The audio URL is
 *    handed to a native <audio> element that only fetches on Play.
 *  * Transcript is always visible so a professional skimming the page
 *    can decide whether to listen without hitting Play.
 *  * "Shimmer voice" chip near the player so mediators know it's
 *    intentionally warm/female — no surprise on Play.
 */
import React, { useEffect, useRef, useState } from "react";
import { Play, Pause, Volume2, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

export default function ProfessionalsIntroAudio() {
  const [manifest, setManifest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [manifestError, setManifestError] = useState(null);
  const [playing, setPlaying] = useState(false);
  const [audioLoading, setAudioLoading] = useState(false);
  const [audioError, setAudioError] = useState(null);
  const audioRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .get("/for-professionals/intro-audio/manifest")
      .then((r) => {
        if (cancelled) return;
        setManifest(r.data || null);
      })
      .catch((err) => {
        if (cancelled) return;
        logError("intro audio manifest failed", err);
        setManifestError("Audio intro is temporarily unavailable.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const togglePlay = async () => {
    const el = audioRef.current;
    if (!el) return;
    setAudioError(null);
    if (playing) {
      el.pause();
      return;
    }
    try {
      setAudioLoading(true);
      await el.play();
    } catch (err) {
      logError("intro audio play failed", err);
      setAudioError("Couldn't play the intro. Please try again.");
    } finally {
      setAudioLoading(false);
    }
  };

  if (loading) {
    return (
      <div
        className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 flex items-center gap-3"
        data-testid="for-pros-intro-audio-loading"
      >
        <Loader2 size={16} className="animate-spin text-[#3D1A78]" />
        <span className="text-sm text-[#4B4567]">Loading audio intro…</span>
      </div>
    );
  }

  if (manifestError || !manifest) {
    return (
      <div
        className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6"
        data-testid="for-pros-intro-audio-unavailable"
      >
        <div className="text-sm text-[#4B4567]">{manifestError || "Audio intro is unavailable right now."}</div>
      </div>
    );
  }

  const absoluteAudioUrl = manifest.audio_url?.startsWith("http")
    ? manifest.audio_url
    : `${BACKEND}${manifest.audio_url}`;

  return (
    <div
      className="rounded-3xl border border-[#E5E0EE] bg-gradient-to-br from-white to-[#FAF8FD] p-5 sm:p-6"
      data-testid="for-pros-intro-audio"
    >
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <div className="shrink-0 w-11 h-11 rounded-2xl bg-[#EFE9F9] text-[#3D1A78] flex items-center justify-center">
          <Volume2 size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            60-second audio intro
          </div>
          <div className="font-serif text-lg text-[#1A1330] mt-0.5 leading-snug">
            A brief walkthrough for busy professionals
          </div>
        </div>
        <span
          className="inline-flex items-center gap-1 rounded-full bg-[#F5F1FB] text-[#3D1A78] text-[10px] uppercase tracking-[0.18em] font-bold px-2.5 py-1"
          data-testid="for-pros-intro-audio-voice-chip"
        >
          Shimmer voice
        </span>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <button
          type="button"
          onClick={togglePlay}
          disabled={audioLoading}
          className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] hover:bg-[#2A0F5F] text-white px-5 py-2.5 text-sm font-semibold shadow-sm transition-colors disabled:opacity-60"
          data-testid="for-pros-intro-audio-play"
          aria-label={playing ? "Pause audio intro" : "Play audio intro"}
        >
          {audioLoading ? (
            <Loader2 size={14} className="animate-spin" />
          ) : playing ? (
            <Pause size={14} />
          ) : (
            <Play size={14} />
          )}
          {playing ? "Pause" : "Play intro"}
        </button>
        <span
          className="text-xs text-[#857E9C]"
          data-testid="for-pros-intro-audio-runtime"
        >
          ~60 seconds · OpenAI TTS
        </span>
      </div>

      {audioError && (
        <div
          className="mt-3 text-xs text-[#8A5B00] bg-[#FFF6E5] border border-[#F0D9A1] rounded-lg px-3 py-1.5"
          data-testid="for-pros-intro-audio-error"
        >
          {audioError}
        </div>
      )}

      {/* Hidden native audio element — the button above is the visible
          control so we can style consistently across browsers. */}
      <audio
        ref={audioRef}
        src={absoluteAudioUrl}
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onError={() => {
          setPlaying(false);
          setAudioError("Couldn't load the intro audio.");
        }}
        data-testid="for-pros-intro-audio-element"
      />

      <details
        className="mt-4 group"
        data-testid="for-pros-intro-audio-transcript"
      >
        <summary
          className="cursor-pointer list-none text-xs font-semibold text-[#3D1A78] hover:underline inline-flex items-center gap-1"
          data-testid="for-pros-intro-audio-transcript-summary"
        >
          <span className="group-open:hidden">Read transcript →</span>
          <span className="hidden group-open:inline">Hide transcript ↑</span>
        </summary>
        <p
          className="mt-3 text-sm text-[#4B4567] leading-relaxed"
          data-testid="for-pros-intro-audio-transcript-body"
        >
          {manifest.transcript}
        </p>
      </details>
    </div>
  );
}
