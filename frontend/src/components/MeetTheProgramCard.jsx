import React, { useRef, useState } from "react";
import { Play, X, Download, Share2, Film, SkipForward } from "lucide-react";
import { toast } from "sonner";

/**
 * Trailer catalog — makes the card reusable so future videos slot in with one
 * new entry. The Dashboard renders each trailer via <MeetTheProgramCard> passing
 * a `trailer` prop; the legacy default export keeps the original 21s trailer.
 */
export const TRAILERS = {
  "meet-the-program": {
    id: "meet-the-program",
    eyebrow: "21-second trailer",
    title: "Meet the SA Coparents program",
    blurb: "A quick walk through the seven steps — perfect to share on Facebook or Instagram.",
    videoSrc: "/videos/meet-the-program.mp4",
    posterSrc: "/images/steps/step-safety-assessment.png",
    downloadName: "sa-coparents-meet-the-program.mp4",
    shareText:
      "Preparing for mediation shouldn't feel like a fight — take a look at how SA Coparents guides you through it.",
  },
  "three-reports": {
    id: "three-reports",
    eyebrow: "45-second trailer",
    title: "Three reports. One goal.",
    blurb:
      "Meet the Conflict Assessment, Foundation Statement, and Mediation Declaration — built to walk into mediation with clarity.",
    videoSrc: "/videos/three-reports.mp4",
    posterSrc: "/images/three-reports-poster.png",
    downloadName: "sa-coparents-three-reports.mp4",
    shareText:
      "Three private reports that help you walk into mediation with clarity, confidence, and a child-first plan.",
  },
  "before-you-begin": {
    id: "before-you-begin",
    eyebrow: "Watch first · 70 seconds",
    title: "Before you begin — a message for you",
    blurb:
      "A short coaching message from us. Slow down, reflect, and answer honestly — SA CoParents is a journey, not a form.",
    videoSrc: "/videos/before-you-begin.mp4",
    posterSrc: "/images/before-you-begin-poster.png",
    downloadName: "sa-coparents-before-you-begin.mp4",
    shareText:
      "A short coaching message that primes parents to slow down, reflect, and start their SA CoParents journey with intention.",
    chapters: [
      { label: "Welcome",           at: 0 },
      { label: "Take your time",    at: 14 },
      { label: "Discover strengths", at: 28 },
      { label: "Each section builds", at: 42 },
      { label: "Reflection & growth", at: 56 },
      { label: "Let's begin",       at: 64 },
    ],
  },
  "dashboard-welcome": {
    id: "dashboard-welcome",
    eyebrow: "Watch first · 70 seconds",
    title: "Welcome — better co-parenting starts with a plan",
    blurb:
      "Take 70 seconds. Slow down, reflect, and answer honestly. SA CoParents is a guided journey — not a form to fill out.",
    videoSrc: "/videos/dashboard-welcome.mp4",
    posterSrc: "/images/dashboard-welcome-poster.jpg",
    downloadName: "sa-coparents-dashboard-welcome.mp4",
    shareText:
      "A 70-second welcome that shows how SA CoParents guides parents through a calmer, more child-focused mediation prep.",
    chapters: [
      { label: "Welcome",           at: 0 },
      { label: "Take your time",    at: 14 },
      { label: "Discover strengths", at: 26 },
      { label: "Each section builds", at: 38 },
      { label: "Reflection & growth", at: 52 },
      { label: "Let's begin",       at: 62 },
    ],
  },
};

async function shareTrailer(shareText, title = "SA Coparents") {
  const shareUrl = "https://sacoparentsapp.online";
  try {
    if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
      await navigator.share({ title, text: shareText, url: shareUrl });
      return { shared: true };
    }
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(`${shareText} ${shareUrl}`);
      return { copied: true };
    }
  } catch (e) {
    if (e?.name === "AbortError") return { aborted: true };
  }
  return { failed: true };
}

/**
 * Compact card that opens a brand trailer in a modal player.
 * Pass `trailerId` to select a trailer from the TRAILERS catalog; the MP4
 * doubles as a downloadable social asset for Facebook / Instagram.
 */
export default function MeetTheProgramCard({ trailerId = "meet-the-program" }) {
  const trailer = TRAILERS[trailerId] || TRAILERS["meet-the-program"];
  const [open, setOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const videoRef = useRef(null);

  const openPlayer = () => {
    setOpen(true);
    setCurrentTime(0);
    // Slight delay so the video mounts before we call .play()
    setTimeout(() => videoRef.current?.play().catch(() => {}), 60);
  };

  const closePlayer = () => {
    setOpen(false);
    videoRef.current?.pause();
  };

  const handleShare = async () => {
    const outcome = await shareTrailer(trailer.shareText, `SA Coparents — ${trailer.title}`);
    if (outcome.shared) toast.success("Shared. Thanks for spreading the word.");
    else if (outcome.copied) toast.success("Link copied — paste it anywhere.");
    else if (!outcome.aborted) toast.error("Couldn’t share on this device.");
  };

  // Find the next chapter whose start time is at least 0.5s ahead of the
  // current playback position so the button reveals the upcoming label.
  const nextChapter = React.useMemo(() => {
    if (!trailer.chapters?.length) return null;
    return trailer.chapters.find((c) => c.at > currentTime + 0.5) || null;
  }, [trailer.chapters, currentTime]);

  const currentChapterIndex = React.useMemo(() => {
    if (!trailer.chapters?.length) return -1;
    let idx = 0;
    for (let i = 0; i < trailer.chapters.length; i++) {
      if (currentTime + 0.05 >= trailer.chapters[i].at) idx = i;
      else break;
    }
    return idx;
  }, [trailer.chapters, currentTime]);

  const skipToNext = () => {
    const v = videoRef.current;
    if (!v || !nextChapter) return;
    v.currentTime = nextChapter.at;
    if (v.paused) v.play().catch(() => {});
  };

  const jumpToChapter = (at) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = at;
    if (v.paused) v.play().catch(() => {});
  };

  return (
    <>
      <section
        className="rounded-3xl bg-gradient-to-br from-[#1A1330] via-[#2A1057] to-[#3D1A78] text-white border border-[#3D1A78]/40 shadow-sm overflow-hidden"
        data-testid={`trailer-card-${trailer.id}`}
      >
        <div className="flex items-stretch gap-5 p-5 sm:p-6 flex-wrap sm:flex-nowrap">
          <button
            type="button"
            onClick={openPlayer}
            data-testid={`trailer-play-${trailer.id}`}
            aria-label={`Play the trailer: ${trailer.title}`}
            className="group relative shrink-0 rounded-2xl overflow-hidden border border-white/20 bg-white/10 hover:bg-white/15 transition-colors w-full sm:w-56 md:w-64 aspect-[16/10] sm:aspect-video"
          >
            {trailer.posterSrc && (
              <img
                src={trailer.posterSrc}
                alt=""
                aria-hidden="true"
                className="absolute inset-0 w-full h-full object-cover"
              />
            )}
            <span className="absolute inset-0 bg-black/25 group-hover:bg-black/15 transition-colors" />
            <span className="absolute inset-0 grid place-items-center">
              <span className="w-14 h-14 rounded-full bg-white/95 grid place-items-center shadow-xl group-hover:scale-105 transition-transform">
                <Play size={22} className="text-[#3D1A78] translate-x-0.5" />
              </span>
            </span>
          </button>
          <div className="flex-1 min-w-[220px]">
            <div className="inline-flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] font-bold text-[#FFD766] mb-1">
              <Film size={12} /> {trailer.eyebrow}
            </div>
            <h3 className="font-serif text-xl sm:text-2xl leading-tight">
              {trailer.title}
            </h3>
            <p className="text-sm text-white/75 mt-1 leading-relaxed">
              {trailer.blurb}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0 flex-wrap">
            <button
              type="button"
              onClick={handleShare}
              data-testid={`trailer-share-${trailer.id}`}
              className="inline-flex items-center gap-2 rounded-full bg-white/10 hover:bg-white/20 text-white px-4 py-2 text-xs font-bold uppercase tracking-wider transition-colors"
            >
              <Share2 size={12} />
              Share
            </button>
            <a
              href={trailer.videoSrc}
              download={trailer.downloadName}
              data-testid={`trailer-download-${trailer.id}`}
              className="inline-flex items-center gap-2 rounded-full bg-[#FFD766] hover:bg-white text-[#1A1330] px-4 py-2 text-xs font-bold uppercase tracking-wider transition-colors"
            >
              <Download size={12} />
              Download
            </a>
          </div>
        </div>
      </section>

      {open && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-black/80 backdrop-blur-sm px-4"
          role="dialog"
          aria-modal="true"
          aria-label={trailer.title}
          onClick={closePlayer}
          data-testid={`trailer-modal-${trailer.id}`}
        >
          <div
            className="relative w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={closePlayer}
              aria-label="Close video"
              data-testid={`trailer-close-${trailer.id}`}
              className="absolute -top-3 -right-3 w-9 h-9 rounded-full bg-white text-[#1A1330] grid place-items-center shadow-lg hover:bg-[#EFE9F9]"
            >
              <X size={16} />
            </button>
            <video
              ref={videoRef}
              src={trailer.videoSrc}
              poster={trailer.posterSrc}
              controls
              playsInline
              onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime || 0)}
              onSeeked={(e) => setCurrentTime(e.currentTarget.currentTime || 0)}
              onLoadedMetadata={(e) => setDuration(e.currentTarget.duration || 0)}
              className="w-full rounded-2xl shadow-2xl bg-black"
              data-testid={`trailer-video-${trailer.id}`}
            />
            {nextChapter && (
              <button
                type="button"
                onClick={skipToNext}
                data-testid={`trailer-skip-next-${trailer.id}`}
                aria-label={`Skip to ${nextChapter.label}`}
                className="absolute bottom-16 right-4 inline-flex items-center gap-2 rounded-full bg-black/70 hover:bg-black/90 backdrop-blur-sm text-white pl-3 pr-4 py-2 text-xs font-bold shadow-lg transition-colors"
              >
                <SkipForward size={14} />
                <span className="hidden sm:inline">Skip to</span> {nextChapter.label}
              </button>
            )}

            {trailer.chapters?.length > 1 && (() => {
              // Duration might not be set until onLoadedMetadata fires; fall
              // back to the last chapter's timestamp + a small tail so the
              // markers always render at meaningful positions.
              const totalSeconds =
                duration > 0
                  ? duration
                  : trailer.chapters[trailer.chapters.length - 1].at + 8;
              return (
              <div
                className="mt-3 px-1"
                data-testid={`trailer-chapter-bar-${trailer.id}`}
              >
                <div
                  className="relative h-2 rounded-full bg-white/15 overflow-hidden"
                  aria-label="Chapters"
                >
                  {/* Elapsed fill */}
                  <div
                    className="absolute top-0 left-0 h-full bg-gradient-to-r from-[#FFD766] to-[#F5A623] transition-[width] duration-200"
                    style={{ width: `${Math.min(100, (currentTime / totalSeconds) * 100)}%` }}
                  />
                  {/* Chapter markers */}
                  {trailer.chapters.map((c, i) => {
                    const pct = Math.min(100, (c.at / totalSeconds) * 100);
                    const active = i === currentChapterIndex;
                    return (
                      <button
                        key={c.at}
                        type="button"
                        onClick={() => jumpToChapter(c.at)}
                        data-testid={`trailer-chapter-dot-${trailer.id}-${i}`}
                        aria-label={`Jump to ${c.label}`}
                        title={c.label}
                        className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 rounded-full transition-all ${
                          active
                            ? "w-4 h-4 bg-white ring-2 ring-[#FFD766]"
                            : "w-2.5 h-2.5 bg-white/70 hover:bg-white hover:scale-125"
                        }`}
                        style={{ left: `${pct}%` }}
                      />
                    );
                  })}
                </div>
                <div className="mt-2 flex items-center justify-between text-[10px] uppercase tracking-[0.18em] font-bold text-white/70">
                  <span data-testid={`trailer-chapter-current-${trailer.id}`}>
                    {trailer.chapters[currentChapterIndex]?.label || trailer.chapters[0].label}
                  </span>
                  <span>
                    {currentChapterIndex + 1} / {trailer.chapters.length}
                  </span>
                </div>
              </div>
              );
            })()}
          </div>
        </div>
      )}
    </>
  );
}
