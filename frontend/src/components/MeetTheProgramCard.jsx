import React, { useRef, useState } from "react";
import { Play, X, Download, Share2, Film } from "lucide-react";
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
  const videoRef = useRef(null);

  const openPlayer = () => {
    setOpen(true);
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

  return (
    <>
      <section
        className="rounded-3xl bg-gradient-to-br from-[#1A1330] via-[#2A1057] to-[#3D1A78] text-white border border-[#3D1A78]/40 shadow-sm overflow-hidden"
        data-testid={`trailer-card-${trailer.id}`}
      >
        <div className="flex items-center gap-5 p-5 sm:p-6 flex-wrap sm:flex-nowrap">
          <button
            type="button"
            onClick={openPlayer}
            data-testid="meet-the-program-play"
            aria-label={`Play the trailer: ${trailer.title}`}
            className="shrink-0 w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-white/10 hover:bg-white/20 backdrop-blur-sm border border-white/20 grid place-items-center transition-colors"
          >
            <Play size={28} className="text-white translate-x-0.5" />
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
              className="w-full rounded-2xl shadow-2xl bg-black"
              data-testid={`trailer-video-${trailer.id}`}
            />
          </div>
        </div>
      )}
    </>
  );
}
