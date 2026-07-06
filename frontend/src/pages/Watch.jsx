import React, { useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Play,
  Download,
  Share2,
  Film,
  ArrowRight,
  ExternalLink,
  Heart,
  Facebook,
} from "lucide-react";
import { toast } from "sonner";
import { TRAILERS } from "@/components/MeetTheProgramCard";

const FACEBOOK_URL = "https://www.facebook.com/61581958982281";
const SEEDS_URL = "https://www.seedsforsuccess.net";

/**
 * Public /watch page — no auth required. Designed as a soft-landing for
 * visitors coming from Facebook / Instagram / LinkedIn so they can preview
 * the program in ~66 seconds before choosing to sign up.
 */
function TrailerRow({ trailer, autoOpen = false }) {
  const [open, setOpen] = useState(autoOpen);
  const videoRef = useRef(null);

  const openPlayer = () => {
    setOpen(true);
    setTimeout(() => videoRef.current?.play().catch(() => {}), 60);
  };

  const closePlayer = () => {
    setOpen(false);
    videoRef.current?.pause();
  };

  const handleShare = async () => {
    const shareUrl = "https://sacoparentsapp.online/watch";
    try {
      if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
        await navigator.share({
          title: `SA Coparents — ${trailer.title}`,
          text: trailer.shareText,
          url: shareUrl,
        });
        toast.success("Shared. Thanks for spreading the word.");
        return;
      }
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(`${trailer.shareText} ${shareUrl}`);
        toast.success("Link copied — paste it anywhere.");
        return;
      }
    } catch (e) {
      if (e?.name === "AbortError") return;
    }
    toast.error("Couldn’t share on this device.");
  };

  return (
    <article
      className="rounded-3xl overflow-hidden bg-white border border-[#E5E0EE] shadow-sm"
      data-testid={`watch-trailer-${trailer.id}`}
    >
      <div className="relative bg-black">
        {open ? (
          <video
            ref={videoRef}
            src={trailer.videoSrc}
            poster={trailer.posterSrc}
            controls
            playsInline
            className="w-full aspect-[4/5] object-cover bg-black"
            data-testid={`watch-video-${trailer.id}`}
          />
        ) : (
          <button
            type="button"
            onClick={openPlayer}
            aria-label={`Play the trailer: ${trailer.title}`}
            data-testid={`watch-play-${trailer.id}`}
            className="group relative w-full aspect-[4/5] block overflow-hidden"
          >
            <img
              src={trailer.posterSrc}
              alt={trailer.title}
              className="w-full h-full object-cover transition-transform group-hover:scale-105"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent" />
            <div className="absolute inset-0 grid place-items-center">
              <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-white/95 backdrop-blur-sm grid place-items-center shadow-xl group-hover:scale-110 transition-transform">
                <Play size={38} className="text-[#3D1A78] translate-x-1" />
              </div>
            </div>
            <div className="absolute top-3 left-3 inline-flex items-center gap-2 rounded-full bg-white/90 backdrop-blur-sm px-3 py-1 text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              <Film size={12} /> {trailer.eyebrow}
            </div>
          </button>
        )}
        {open && (
          <button
            type="button"
            onClick={closePlayer}
            aria-label="Close video"
            data-testid={`watch-close-${trailer.id}`}
            className="absolute top-3 right-3 rounded-full bg-white/95 backdrop-blur-sm px-3 py-1 text-xs font-bold text-[#1A1330] hover:bg-white"
          >
            Close
          </button>
        )}
      </div>
      <div className="p-6 sm:p-7">
        <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
          {trailer.eyebrow}
        </div>
        <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight mb-2">
          {trailer.title}
        </h2>
        <p className="text-sm sm:text-base text-[#4B4567] leading-relaxed mb-5">
          {trailer.blurb}
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={handleShare}
            data-testid={`watch-share-${trailer.id}`}
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
          >
            <Share2 size={14} />
            Share
          </button>
          <a
            href={trailer.videoSrc}
            download={trailer.downloadName}
            data-testid={`watch-download-${trailer.id}`}
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
          >
            <Download size={14} />
            Download MP4
          </a>
        </div>
      </div>
    </article>
  );
}


export default function Watch() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#F8F7FC] via-white to-[#EFE9F9]" data-testid="watch-page">
      <header className="border-b border-[#E5E0EE] bg-white/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-4">
          <Link
            to="/"
            data-testid="watch-home-link"
            className="flex items-center gap-2 group"
          >
            <span className="font-serif text-xl sm:text-2xl font-bold text-[#1A1330] group-hover:text-[#3D1A78]">
              SA<span className="text-[#3D1A78]"> Coparents</span>
            </span>
          </Link>
          <div className="flex items-center gap-2 sm:gap-3">
            <a
              href={FACEBOOK_URL}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="watch-facebook-header-link"
              className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#1877F2] px-3 sm:px-4 py-2 text-xs sm:text-sm font-semibold hover:bg-[#F8F7FC]"
            >
              <Facebook size={14} />
              <span className="hidden sm:inline">Follow on Facebook</span>
              <span className="sm:hidden">Facebook</span>
            </a>
            <Link
              to="/signup"
              data-testid="watch-signup-link"
              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-4 sm:px-5 py-2 text-xs sm:text-sm font-semibold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
            >
              Start free
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        <section className="max-w-3xl mb-10 sm:mb-14">
          <div className="inline-flex items-center gap-2 rounded-full bg-[#EFE9F9] text-[#3D1A78] px-4 py-1.5 text-[10px] uppercase tracking-[0.22em] font-bold mb-4">
            <Heart size={12} /> A preview of the program
          </div>
          <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl text-[#1A1330] leading-tight mb-4">
            Walk into mediation with clarity — not a fight.
          </h1>
          <p className="text-base sm:text-lg text-[#4B4567] leading-relaxed">
            SA Coparents is a private, guided prep tool that helps parents move
            from emotionally reactive to child-centered before they ever sit at
            the mediation table. Take a minute to see how it works — then start
            free when you’re ready.
          </p>
        </section>

        <section className="grid gap-8 md:grid-cols-2 mb-14">
          <TrailerRow trailer={TRAILERS["meet-the-program"]} />
          <TrailerRow trailer={TRAILERS["three-reports"]} />
        </section>

        <section
          className="rounded-3xl bg-gradient-to-br from-[#1A1330] via-[#2A1057] to-[#3D1A78] text-white p-8 sm:p-12 mb-14"
          data-testid="watch-cta"
        >
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 border border-white/20 px-3 py-1 text-[10px] uppercase tracking-[0.22em] font-bold text-[#FFD766] mb-4">
              <Heart size={12} /> Different parents. Same goal — our children.
            </div>
            <h2 className="font-serif text-3xl sm:text-4xl leading-tight mb-3">
              Try the full program — free
            </h2>
            <p className="text-white/80 text-base sm:text-lg leading-relaxed mb-6">
              Sign up in seconds. Complete all seven modules at your own pace,
              generate your Conflict Assessment, Foundation Statement, and
              Mediation Declaration, and walk in prepared.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/signup"
                data-testid="watch-cta-signup"
                className="inline-flex items-center gap-2 rounded-full bg-[#FFD766] hover:bg-white text-[#1A1330] px-6 py-3 text-sm font-bold shadow-md hover:shadow-xl hover:-translate-y-0.5 transition-all"
              >
                Start free
                <ArrowRight size={14} />
              </Link>
              <Link
                to="/login"
                data-testid="watch-cta-login"
                className="inline-flex items-center gap-2 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 text-white px-6 py-3 text-sm font-bold transition-colors"
              >
                Sign in
              </Link>
            </div>
          </div>
        </section>

        <section className="grid gap-6 sm:grid-cols-2 mb-14">
          <a
            href={FACEBOOK_URL}
            target="_blank"
            rel="noopener noreferrer"
            data-testid="watch-facebook-card"
            className="group rounded-3xl bg-white border border-[#E5E0EE] p-6 sm:p-8 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-2xl bg-[#1877F2]/10 grid place-items-center text-[#1877F2] group-hover:bg-[#1877F2] group-hover:text-white transition-colors">
                <Facebook size={22} />
              </div>
              <div className="flex-1">
                <div className="text-[11px] uppercase tracking-[0.22em] text-[#1877F2] font-bold mb-1">
                  Facebook
                </div>
                <div className="font-serif text-xl text-[#1A1330] mb-1">
                  Seeds for Success · Facebook
                </div>
                <p className="text-sm text-[#4B4567] leading-relaxed">
                  Follow for weekly co-parenting encouragement, live sessions, and community stories.
                </p>
                <div className="mt-3 inline-flex items-center gap-1 text-[#3D1A78] text-xs font-bold">
                  Open on Facebook <ExternalLink size={12} />
                </div>
              </div>
            </div>
          </a>
          <a
            href={SEEDS_URL}
            target="_blank"
            rel="noopener noreferrer"
            data-testid="watch-seeds-card"
            className="group rounded-3xl bg-white border border-[#E5E0EE] p-6 sm:p-8 hover:shadow-lg transition-shadow"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-2xl bg-[#2DB5B5]/10 grid place-items-center text-[#2DB5B5] group-hover:bg-[#2DB5B5] group-hover:text-white transition-colors">
                <Heart size={22} />
              </div>
              <div className="flex-1">
                <div className="text-[11px] uppercase tracking-[0.22em] text-[#2DB5B5] font-bold mb-1">
                  Website
                </div>
                <div className="font-serif text-xl text-[#1A1330] mb-1">
                  seedsforsuccess.net
                </div>
                <p className="text-sm text-[#4B4567] leading-relaxed">
                  Learn about the Seeds for Success mediation practice behind SA Coparents.
                </p>
                <div className="mt-3 inline-flex items-center gap-1 text-[#3D1A78] text-xs font-bold">
                  Open in a new tab <ExternalLink size={12} />
                </div>
              </div>
            </div>
          </a>
        </section>
      </main>

      <footer className="border-t border-[#E5E0EE] bg-white/60">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 flex flex-wrap items-center justify-between gap-4 text-xs text-[#857E9C]">
          <div>© SA Coparents · A Seeds for Success project</div>
          <div className="flex items-center gap-4">
            <Link to="/privacy" className="hover:text-[#3D1A78]" data-testid="watch-privacy-link">
              Privacy
            </Link>
            <Link to="/terms" className="hover:text-[#3D1A78]" data-testid="watch-terms-link">
              Terms
            </Link>
            <Link to="/safety" className="hover:text-[#3D1A78]" data-testid="watch-safety-link">
              Safety
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
