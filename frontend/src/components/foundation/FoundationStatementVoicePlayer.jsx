/**
 * FoundationStatementVoicePlayer — "Read to me" for a parent's own
 * Foundation Statement. Streams per-section MP3 audio, plays them
 * sequentially, and emits `onSectionChange(sectionKey|null)` so the
 * parent surface (MyPlan) can highlight the paragraph being spoken.
 *
 * Backed by:
 *   GET /api/mediation/foundation-statement/voice/manifest
 *   GET /api/mediation/foundation-statement/voice/section/{key}
 *
 * Two placement modes:
 *   - variant="inline"   — a pill-shaped button next to Send / Edit
 *   - variant="floating" — a fixed bottom-right FAB (mobile-first)
 * Both share the same underlying player state so tapping the FAB
 * and tapping the inline pill behave identically.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Play, Pause, Square, Volume2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "../../lib/api";
import { logError } from "../../lib/logger";

// Kept in sync with backend `foundation_statement_voice.SUPPORTED_VOICES`.
const VOICE_OPTIONS = [
  { value: "shimmer", label: "Shimmer · warm", hint: "Default" },
  { value: "nova",    label: "Nova · upbeat"   },
  { value: "alloy",   label: "Alloy · neutral" },
  { value: "fable",   label: "Fable · storytelling" },
];

function fetchSectionBlobUrl(audioUrl) {
  // audio_url from the manifest is server-relative ("/api/...") — the
  // shared `api` axios client already prefixes REACT_APP_BACKEND_URL,
  // so we strip the "/api" from the URL here.
  const relative = audioUrl.replace(/^\/api/, "");
  return api
    .get(relative, { responseType: "blob" })
    .then((r) => URL.createObjectURL(new Blob([r.data], { type: "audio/mpeg" })));
}

export default function FoundationStatementVoicePlayer({
  variant = "inline",
  onSectionChange,
  compact = false,
}) {
  const [voice, setVoice] = useState("shimmer");
  const [sections, setSections] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | loading | playing | paused | ended | error
  const [currentIdx, setCurrentIdx] = useState(-1);
  const [errorMsg, setErrorMsg] = useState("");
  const audioRef = useRef(null);
  const blobUrlRef = useRef(null);       // currently-playing blob url
  const preloadedRef = useRef(new Map()); // idx -> blob URL cache (session)
  const cancelledRef = useRef(false);

  // Notify parent whenever the current section changes so MyPlan
  // can highlight it. `null` when nothing is playing.
  useEffect(() => {
    if (!onSectionChange) return;
    if (currentIdx < 0 || currentIdx >= sections.length) {
      onSectionChange(null);
    } else {
      onSectionChange(sections[currentIdx]?.key || null);
    }
  }, [currentIdx, sections, onSectionChange]);

  const releaseBlobs = useCallback(() => {
    preloadedRef.current.forEach((url) => URL.revokeObjectURL(url));
    preloadedRef.current.clear();
    blobUrlRef.current = null;
  }, []);

  // Reset session cache whenever voice changes (voice change ⇒ new
  // audio bytes, old blob URLs would be stale).
  useEffect(() => {
    releaseBlobs();
  }, [voice, releaseBlobs]);

  // Cleanup on unmount.
  useEffect(() => {
    return () => {
      cancelledRef.current = true;
      releaseBlobs();
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
      }
    };
  }, [releaseBlobs]);

  const loadManifest = useCallback(async () => {
    const res = await api.get(
      "/mediation/foundation-statement/voice/manifest",
      { params: { voice } },
    );
    return res.data?.sections || [];
  }, [voice]);

  const getSectionBlobUrl = useCallback(async (section) => {
    const cache = preloadedRef.current;
    if (cache.has(section.index)) return cache.get(section.index);
    const url = await fetchSectionBlobUrl(section.audio_url);
    cache.set(section.index, url);
    return url;
  }, []);

  const playSection = useCallback(async (idx, sectionsList) => {
    if (cancelledRef.current) return;
    if (idx >= sectionsList.length) {
      setStatus("ended");
      setCurrentIdx(-1);
      return;
    }
    const section = sectionsList[idx];
    try {
      const url = await getSectionBlobUrl(section);
      if (cancelledRef.current) return;
      const el = audioRef.current;
      if (!el) return;
      blobUrlRef.current = url;
      el.src = url;
      setCurrentIdx(idx);
      setStatus("playing");
      await el.play();
      // Warm the next section's blob in the background so playback
      // is gapless for the listener.
      const nextSec = sectionsList[idx + 1];
      if (nextSec) {
        getSectionBlobUrl(nextSec).catch(() => { /* soft-fail */ });
      }
    } catch (err) {
      logError("foundation voice play failed", err);
      const detail = err?.response?.data?.detail || "Playback failed.";
      setErrorMsg(String(detail));
      setStatus("error");
      toast.error(String(detail));
    }
  }, [getSectionBlobUrl]);

  const handlePlay = useCallback(async () => {
    if (status === "playing") return;
    // Resume from pause without re-fetching the manifest.
    if (status === "paused" && audioRef.current) {
      try {
        await audioRef.current.play();
        setStatus("playing");
      } catch (err) {
        logError("foundation voice resume failed", err);
      }
      return;
    }
    setStatus("loading");
    setErrorMsg("");
    cancelledRef.current = false;
    try {
      const list = await loadManifest();
      if (list.length === 0) {
        toast.error("Your Foundation Statement is empty.");
        setStatus("idle");
        return;
      }
      setSections(list);
      await playSection(0, list);
    } catch (err) {
      logError("foundation voice manifest failed", err);
      const detail = err?.response?.data?.detail || "Couldn't load your Foundation Statement.";
      setErrorMsg(String(detail));
      setStatus("error");
      toast.error(String(detail));
    }
  }, [status, loadManifest, playSection]);

  const handlePause = useCallback(() => {
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause();
      setStatus("paused");
    }
  }, []);

  const handleStop = useCallback(() => {
    cancelledRef.current = true;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
    }
    setStatus("idle");
    setCurrentIdx(-1);
    // Allow a subsequent play to start fresh.
    setTimeout(() => { cancelledRef.current = false; }, 0);
  }, []);

  const handleEnded = useCallback(() => {
    const nextIdx = currentIdx + 1;
    if (nextIdx < sections.length) {
      playSection(nextIdx, sections);
    } else {
      setStatus("ended");
      setCurrentIdx(-1);
    }
  }, [currentIdx, sections, playSection]);

  const isBusy = status === "loading" || status === "playing";
  const showStop = status === "playing" || status === "paused";

  const buttonBase = variant === "floating"
    ? "rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white shadow-lg h-12 w-12 flex items-center justify-center"
    : compact
      ? "inline-flex items-center gap-1.5 rounded-full bg-[#EFE9F9] hover:bg-[#E5DAF7] text-[#3D1A78] px-3 py-1.5 text-xs font-semibold transition-colors"
      : "inline-flex items-center gap-1.5 rounded-full bg-[#EFE9F9] hover:bg-[#E5DAF7] text-[#3D1A78] px-3 py-1.5 text-xs font-semibold transition-colors";

  const containerClass = variant === "floating"
    ? "fixed bottom-6 right-6 z-40 flex items-center gap-2"
    : "inline-flex items-center gap-2 flex-wrap";

  const label = status === "loading" ? "Loading…"
    : status === "playing" ? "Pause"
    : status === "paused"  ? "Resume"
    : "Read to me";

  const testidPrefix = variant === "floating" ? "voice-fab" : "voice-inline";

  return (
    <div className={containerClass} data-testid={`foundation-${testidPrefix}`}>
      <audio
        ref={audioRef}
        onEnded={handleEnded}
        onError={() => setStatus("error")}
        data-testid="foundation-voice-audio"
      />

      {/* Primary Play / Pause button */}
      <button
        type="button"
        onClick={status === "playing" ? handlePause : handlePlay}
        disabled={status === "loading"}
        className={buttonBase}
        aria-label={label}
        title={label}
        data-testid={`${testidPrefix}-play`}
      >
        {status === "loading" ? (
          <Loader2 size={variant === "floating" ? 20 : 13} className="animate-spin" />
        ) : status === "playing" ? (
          <Pause size={variant === "floating" ? 20 : 13} />
        ) : (
          <Play size={variant === "floating" ? 20 : 13} />
        )}
        {variant !== "floating" && (
          <span>{label}</span>
        )}
      </button>

      {/* Stop button (only when actively playing / paused) */}
      {showStop && (
        <button
          type="button"
          onClick={handleStop}
          className={
            variant === "floating"
              ? "rounded-full bg-white hover:bg-slate-100 text-[#3D1A78] shadow-lg h-10 w-10 flex items-center justify-center border border-[#E5E0EE]"
              : "inline-flex items-center rounded-full bg-white hover:bg-slate-50 text-[#4B4567] border border-[#E5E0EE] w-7 h-7 justify-center"
          }
          aria-label="Stop"
          title="Stop"
          data-testid={`${testidPrefix}-stop`}
        >
          <Square size={variant === "floating" ? 14 : 11} />
        </button>
      )}

      {/* Voice picker — hidden while playing to avoid mid-flight
          changes; the user can Stop → pick → Play again. */}
      {status !== "playing" && status !== "loading" && (
        <label className={
          variant === "floating"
            ? "hidden"
            : "inline-flex items-center gap-1 text-[0.6875rem] text-[#4B4567]"
        }>
          <Volume2 size={11} className="text-[#6E6787]" aria-hidden />
          <select
            value={voice}
            onChange={(e) => setVoice(e.target.value)}
            disabled={isBusy}
            className="bg-transparent border-none text-[0.6875rem] text-[#3D1A78] font-semibold focus:outline-none cursor-pointer"
            aria-label="Voice"
            data-testid={`${testidPrefix}-voice`}
          >
            {VOICE_OPTIONS.map((v) => (
              <option key={v.value} value={v.value}>
                {v.label}{v.hint ? ` (${v.hint})` : ""}
              </option>
            ))}
          </select>
        </label>
      )}

      {status === "error" && errorMsg && variant !== "floating" && (
        <span
          role="alert"
          className="text-[0.6875rem] text-[#C05621]"
          data-testid={`${testidPrefix}-error`}
        >
          {errorMsg}
        </span>
      )}
    </div>
  );
}
