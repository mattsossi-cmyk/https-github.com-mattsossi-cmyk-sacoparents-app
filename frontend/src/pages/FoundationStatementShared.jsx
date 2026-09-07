/**
 * FoundationStatementShared — public preview page for a shared
 * Foundation Statement. Opens from the email pill button
 * ("Open the statement online") without any login. Two features
 * on top of the raw prose:
 *   1. Read-to-me voice player (Shimmer / Nova / Alloy / Fable),
 *      section-by-section, with per-section highlighting.
 *   2. Download PDF fallback — the recipient can still grab the
 *      artefact if they want to forward or file it.
 *
 * Public, unauthenticated route: /foundation/shared/:token
 *
 * Backed by:
 *   GET /api/mediation/foundation-statement/shared/{token}
 *   GET /api/mediation/foundation-statement/shared/{token}/voice/manifest
 *   GET /api/mediation/foundation-statement/shared/{token}/voice/section/{key}
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import {
  ArrowLeft,
  Heart,
  Loader2,
  Pause,
  Play,
  ShieldCheck,
  Square,
  Volume2,
} from "lucide-react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const VOICE_OPTIONS = [
  { value: "shimmer", label: "Shimmer · warm" },
  { value: "nova",    label: "Nova · upbeat" },
  { value: "alloy",   label: "Alloy · neutral" },
  { value: "fable",   label: "Fable · storytelling" },
];

function useSharedFoundation(token) {
  const [state, setState] = useState({ loading: true, data: null, error: null });
  useEffect(() => {
    let cancelled = false;
    axios
      .get(`${API}/mediation/foundation-statement/shared/${encodeURIComponent(token)}`)
      .then((r) => {
        if (!cancelled) setState({ loading: false, data: r.data, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        const detail =
          err?.response?.data?.detail || "This link has expired or is invalid.";
        setState({ loading: false, data: null, error: detail });
      });
    return () => { cancelled = true; };
  }, [token]);
  return state;
}

function usePublicVoicePlayer(token, activeSetter) {
  const [voice, setVoice] = useState("shimmer");
  const [sections, setSections] = useState([]);
  const [status, setStatus] = useState("idle");
  const [currentIdx, setCurrentIdx] = useState(-1);
  const audioRef = useRef(null);
  const blobCache = useRef(new Map());
  const cancelledRef = useRef(false);

  useEffect(() => {
    activeSetter?.(
      currentIdx >= 0 && currentIdx < sections.length
        ? sections[currentIdx].key
        : null,
    );
  }, [currentIdx, sections, activeSetter]);

  const releaseBlobs = useCallback(() => {
    blobCache.current.forEach((u) => URL.revokeObjectURL(u));
    blobCache.current.clear();
  }, []);

  useEffect(() => releaseBlobs, [voice, releaseBlobs]);
  useEffect(() => () => {
    cancelledRef.current = true;
    releaseBlobs();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
    }
  }, [releaseBlobs]);

  const fetchBlobUrl = useCallback(async (audioUrl) => {
    const res = await axios.get(`${process.env.REACT_APP_BACKEND_URL}${audioUrl}`, {
      responseType: "blob",
    });
    return URL.createObjectURL(new Blob([res.data], { type: "audio/mpeg" }));
  }, []);

  const getSectionBlob = useCallback(async (section) => {
    if (blobCache.current.has(section.index)) return blobCache.current.get(section.index);
    const url = await fetchBlobUrl(section.audio_url);
    blobCache.current.set(section.index, url);
    return url;
  }, [fetchBlobUrl]);

  const playSection = useCallback(async (idx, list) => {
    if (cancelledRef.current) return;
    if (idx >= list.length) {
      setStatus("ended");
      setCurrentIdx(-1);
      return;
    }
    const sec = list[idx];
    try {
      const url = await getSectionBlob(sec);
      if (cancelledRef.current) return;
      const el = audioRef.current;
      if (!el) return;
      el.src = url;
      setCurrentIdx(idx);
      setStatus("playing");
      await el.play();
      const next = list[idx + 1];
      if (next) getSectionBlob(next).catch(() => {});
    } catch (err) {
      const msg = err?.response?.data?.detail || "Playback failed.";
      toast.error(String(msg));
      setStatus("error");
    }
  }, [getSectionBlob]);

  const handlePlay = useCallback(async () => {
    if (status === "playing") return;
    if (status === "paused" && audioRef.current) {
      try { await audioRef.current.play(); setStatus("playing"); }
      catch { /* soft-fail */ }
      return;
    }
    setStatus("loading");
    cancelledRef.current = false;
    try {
      const r = await axios.get(
        `${API}/mediation/foundation-statement/shared/${encodeURIComponent(token)}/voice/manifest`,
        { params: { voice } },
      );
      const list = r.data?.sections || [];
      if (list.length === 0) {
        toast.error("This statement has no content to read.");
        setStatus("idle");
        return;
      }
      setSections(list);
      await playSection(0, list);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Couldn't load the statement.";
      toast.error(String(msg));
      setStatus("error");
    }
  }, [status, voice, token, playSection]);

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
    setTimeout(() => { cancelledRef.current = false; }, 0);
  }, []);

  const handleEnded = useCallback(() => {
    playSection(currentIdx + 1, sections);
  }, [currentIdx, sections, playSection]);

  return {
    voice, setVoice, status, currentIdx,
    audioRef, handlePlay, handlePause, handleStop, handleEnded,
  };
}

function VoicePlayerBar({ token, onSection }) {
  const {
    voice, setVoice, status,
    audioRef, handlePlay, handlePause, handleStop, handleEnded,
  } = usePublicVoicePlayer(token, onSection);
  const isPlaying = status === "playing";
  const showStop = status === "playing" || status === "paused";
  return (
    <div className="inline-flex items-center gap-2 flex-wrap" data-testid="shared-voice-player">
      <audio ref={audioRef} onEnded={handleEnded} data-testid="shared-voice-audio" />
      <button
        type="button"
        onClick={isPlaying ? handlePause : handlePlay}
        disabled={status === "loading"}
        className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold disabled:opacity-60"
        data-testid="shared-voice-play"
      >
        {status === "loading" ? (
          <><Loader2 size={14} className="animate-spin" /> Loading…</>
        ) : isPlaying ? (
          <><Pause size={14} /> Pause</>
        ) : status === "paused" ? (
          <><Play size={14} /> Resume</>
        ) : (
          <><Play size={14} /> Read to me</>
        )}
      </button>
      {showStop && (
        <button
          type="button"
          onClick={handleStop}
          className="inline-flex items-center rounded-full bg-white hover:bg-slate-50 text-[#4B4567] border border-[#E5E0EE] w-9 h-9 justify-center"
          aria-label="Stop"
          data-testid="shared-voice-stop"
        >
          <Square size={12} />
        </button>
      )}
      {!isPlaying && status !== "loading" && (
        <label className="inline-flex items-center gap-1 text-xs text-[#4B4567]">
          <Volume2 size={12} className="text-[#857E9C]" />
          <select
            value={voice}
            onChange={(e) => setVoice(e.target.value)}
            className="bg-transparent border-none text-[12px] text-[#3D1A78] font-semibold focus:outline-none cursor-pointer"
            data-testid="shared-voice-select"
          >
            {VOICE_OPTIONS.map((v) => (
              <option key={v.value} value={v.value}>{v.label}</option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}

export default function FoundationStatementShared() {
  const { token } = useParams();
  const { loading, data, error } = useSharedFoundation(token);
  const [activeSection, setActiveSection] = useState(null);

  const expiresLine = useMemo(() => {
    if (!data?.expires_at) return null;
    try {
      return `Link expires ${new Date(data.expires_at).toLocaleDateString([], {
        month: "long", day: "numeric", year: "numeric",
      })}`;
    } catch { return null; }
  }, [data]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#F5F1FB] via-[#FBF9FE] to-white">
      <header className="max-w-3xl mx-auto px-4 sm:px-6 pt-8 pb-4">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline"
          data-testid="shared-back-home"
        >
          <ArrowLeft size={14} /> SA CoParents
        </Link>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 pb-16" data-testid="shared-foundation-main">
        {loading && (
          <div
            className="flex items-center gap-2 text-[#4B4567] py-16 justify-center"
            data-testid="shared-loading"
          >
            <Loader2 size={16} className="animate-spin" /> Loading this Foundation Statement…
          </div>
        )}
        {error && (
          <div
            className="rounded-3xl border border-[#E5E0EE] bg-white px-6 py-12 text-center"
            data-testid="shared-error"
          >
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#C05621] mb-2">
              Link unavailable
            </div>
            <h1 className="font-serif text-3xl text-[#1A1330] leading-tight">
              This link isn&apos;t available
            </h1>
            <p className="text-[#4B4567] mt-3 text-sm">{error}</p>
            <p className="text-[#857E9C] mt-2 text-xs">
              If you were expecting to view a Foundation Statement, ask the sender to send you a fresh link.
            </p>
          </div>
        )}
        {data && (
          <>
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
              <Heart size={12} /> Foundation Statement
            </div>
            <h1
              className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight mt-2"
              data-testid="shared-foundation-title"
            >
              {data.sender_name}&apos;s reflection
            </h1>
            <p className="text-[#4B4567] mt-3 leading-relaxed max-w-2xl">
              A short reflection <strong>{data.sender_name}</strong> wrote to
              prepare for a conversation about their co-parenting — from
              their child&apos;s perspective, from yours, and from their own.
              It is <em>not</em> a set of demands, and it is <em>not</em>{" "}
              a court filing.
            </p>

            {data.sender_note && (
              <div
                className="mt-6 rounded-2xl bg-[#F5F1FB] border-l-4 border-[#3D1A78] px-4 py-3"
                data-testid="shared-sender-note"
              >
                <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
                  A note from {data.sender_name}
                </div>
                <p className="text-sm text-[#1A1330] leading-relaxed whitespace-pre-wrap">
                  {data.sender_note}
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <VoicePlayerBar token={token} onSection={setActiveSection} />
              <a
                href={`${API}/mediation/foundation-statement/shared/${encodeURIComponent(token)}/pdf`}
                className="text-xs font-semibold text-[#3D1A78] hover:underline hidden"
                data-testid="shared-download-pdf-placeholder"
              >
                Download PDF
              </a>
            </div>

            {/* Sections */}
            <div className="mt-8 space-y-5" data-testid="shared-sections">
              {data.sections.map((s) => {
                const active = s.key === activeSection;
                return (
                  <section
                    key={s.key}
                    data-testid={`shared-section-${s.key}`}
                    data-voice-active={active ? "true" : undefined}
                    className={
                      "rounded-2xl border px-5 py-4 transition-colors " +
                      (active
                        ? "border-[#3D1A78] bg-[#EFE9F9]"
                        : "border-[#E5E0EE] bg-white")
                    }
                  >
                    <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
                      {s.label}
                    </div>
                    <p className="text-[#1A1330] leading-relaxed whitespace-pre-wrap">
                      {s.text}
                    </p>
                  </section>
                );
              })}
            </div>

            {/* Guardrail strip */}
            <div
              className="mt-8 flex items-start gap-2 rounded-2xl bg-white border border-[#E5E0EE] px-4 py-3 text-[12px] text-[#4B4567]"
              data-testid="shared-court-disclaimer"
            >
              <ShieldCheck size={14} className="flex-shrink-0 mt-0.5 text-[#3D1A78]" />
              <p className="!m-0 leading-relaxed">
                This is a parent-authored reflection, not a clinical
                evaluation or court filing. Reading it before a mediation
                or first co-parenting conversation makes the discussion
                calmer and more focused.
                {expiresLine && (
                  <span className="block text-[#857E9C] mt-1 text-[11px]">
                    {expiresLine}
                  </span>
                )}
              </p>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
