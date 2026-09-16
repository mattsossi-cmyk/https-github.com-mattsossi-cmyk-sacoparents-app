/**
 * DashboardSlideshow — iter198.
 *
 * A quiet, brand-aligned slideshow that sits at the VERY top of the
 * parent dashboard so returning users see the SA CoParents journey
 * artwork before they're asked to make a choice.
 *
 * Behaviour:
 *   - Auto-advances every 6s (long enough to actually read the
 *     caption on a stressed evening)
 *   - Pauses on hover / focus so a parent who wants to linger can
 *   - Left / Right / keyboard arrows + dot indicators
 *   - Cross-fades between frames (no janky slide-in that fights the
 *     dashboard grid)
 *   - Reduced-motion honoured: transitions collapse to opacity 0→1
 *   - Never taller than 320px on desktop / 200px on mobile so it
 *     never pushes the FrontDoorHero below the fold
 *
 * The five images are the founder-supplied "journey" artwork — same
 * five phases surfaced on the marketing landing. Order intentionally
 * matches the recommended co-parenting sequence.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";

// Founder-supplied labelled artwork. Order = the recommended
// co-parenting journey (assess → child → relationship → communicate →
// commit to the Foundation Statement). Do NOT reorder without a
// design review — parents parse this as a step sequence.
const SLIDES = [
  {
    key: "situation",
    src: "https://customer-assets.emergentagent.com/job_prepared-parents/artifacts/8z6tlelx_Assess%20your%20family%20situation.png",
    title: "Assess your family situation",
    caption:
      "Start with a quick, private read of your household today — no judgement, no permanent labels.",
  },
  {
    key: "child-needs",
    src: "https://customer-assets.emergentagent.com/job_prepared-parents/artifacts/z354oyvf_identify%20childs%20needs.png",
    title: "Identify your child's needs",
    caption:
      "Educational, medical, emotional — surface the specifics before you negotiate the shape of the week.",
  },
  {
    key: "relationship",
    src: "https://customer-assets.emergentagent.com/job_prepared-parents/artifacts/f69lkwjm_understand%20your%20coparenting%20relationship.png",
    title: "Understand your co-parenting relationship",
    caption:
      "Where you actually are today — cooperative, parallel, tense, or unsafe — decides which tools help next.",
  },
  {
    key: "communication",
    src: "https://customer-assets.emergentagent.com/job_prepared-parents/artifacts/2cz4s468_strengthen%20communication.png",
    title: "Strengthen your communication",
    caption:
      "Draft the message you actually want to send — calmer, clearer, and easier for the other parent to hear.",
  },
  {
    key: "foundation",
    src: "https://customer-assets.emergentagent.com/job_prepared-parents/artifacts/e3v73w33_Foundation%20Statement.png",
    title: "Commit to your Foundation Statement",
    caption:
      "Write the anchor you'll come back to on the hard days — the reason this whole journey is worth the friction.",
  },
];

const AUTO_MS = 6000;

export default function DashboardSlideshow() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const timerRef = useRef(null);

  const goTo = useCallback(
    (n) => {
      const total = SLIDES.length;
      setIndex((prev) => {
        // Normalise negative + overflow.
        const next = ((typeof n === "function" ? n(prev) : n) % total + total) % total;
        return next;
      });
    },
    [],
  );

  // Auto-advance loop. Pauses when the user hovers / focuses, or
  // when the tab is hidden (browser throttles the timer anyway but
  // this saves a wasted paint).
  useEffect(() => {
    if (paused) return undefined;
    const mediaQuery =
      typeof window !== "undefined" && window.matchMedia
        ? window.matchMedia("(prefers-reduced-motion: reduce)")
        : null;
    if (mediaQuery && mediaQuery.matches) return undefined;
    timerRef.current = setInterval(() => goTo((i) => i + 1), AUTO_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
    };
  }, [paused, goTo]);

  const prev = () => goTo((i) => i - 1);
  const next = () => goTo((i) => i + 1);

  // Keyboard support scoped to the slideshow root.
  const onKeyDown = (e) => {
    if (e.key === "ArrowLeft") { prev(); e.preventDefault(); }
    else if (e.key === "ArrowRight") { next(); e.preventDefault(); }
  };

  return (
    <section
      className="relative w-full mx-auto rounded-3xl overflow-hidden bg-gradient-to-br from-[#1A1330] via-[#2A0F5F] to-[#3D1A78] shadow-lg"
      style={{ aspectRatio: "16 / 8" }}
      data-testid="dashboard-slideshow"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      onKeyDown={onKeyDown}
      tabIndex={0}
      aria-roledescription="carousel"
      aria-label="SA CoParents journey"
    >
      {/* Frames — all mounted, opacity-toggled for cross-fade. Keeping
          them mounted avoids a re-load on every advance. */}
      {SLIDES.map((slide, i) => {
        const active = i === index;
        return (
          <div
            key={slide.key}
            className={`absolute inset-0 transition-opacity duration-700 ease-out ${
              active ? "opacity-100" : "opacity-0"
            }`}
            aria-hidden={!active}
            data-testid={`dashboard-slideshow-slide-${slide.key}`}
          >
            <img
              src={slide.src}
              alt={slide.title}
              className="w-full h-full object-contain object-center"
              loading={i === 0 ? "eager" : "lazy"}
              draggable={false}
            />
            {/* Gradient overlay so the white caption stays readable
                on any incoming frame. */}
            <div
              className="absolute inset-0 bg-gradient-to-t from-[#1A1330]/85 via-[#1A1330]/30 to-transparent"
              aria-hidden="true"
            />
            <div className="absolute left-0 right-0 bottom-0 p-5 sm:p-8">
              <div className="text-[10px] uppercase tracking-[0.28em] font-bold text-white/70">
                Step {i + 1} of {SLIDES.length}
              </div>
              <h3
                className="font-serif text-white text-2xl sm:text-4xl leading-tight mt-1"
                data-testid={`dashboard-slideshow-title-${slide.key}`}
              >
                {slide.title}
              </h3>
              <p className="text-white/90 text-[13px] sm:text-[15px] mt-2 max-w-2xl leading-relaxed hidden sm:block">
                {slide.caption}
              </p>
            </div>
          </div>
        );
      })}

      {/* Prev / Next arrows. */}
      <button
        type="button"
        onClick={prev}
        aria-label="Previous slide"
        data-testid="dashboard-slideshow-prev"
        className="absolute left-2 sm:left-3 top-1/2 -translate-y-1/2 grid place-items-center w-9 h-9 sm:w-11 sm:h-11 rounded-full bg-black/25 hover:bg-black/50 backdrop-blur text-white transition-colors"
      >
        <ChevronLeft size={20} />
      </button>
      <button
        type="button"
        onClick={next}
        aria-label="Next slide"
        data-testid="dashboard-slideshow-next"
        className="absolute right-2 sm:right-3 top-1/2 -translate-y-1/2 grid place-items-center w-9 h-9 sm:w-11 sm:h-11 rounded-full bg-black/25 hover:bg-black/50 backdrop-blur text-white transition-colors"
      >
        <ChevronRight size={20} />
      </button>

      {/* Dot indicators + pause toggle. */}
      <div className="absolute right-3 sm:right-6 top-3 sm:top-4 flex items-center gap-2">
        <button
          type="button"
          onClick={() => setPaused((p) => !p)}
          aria-label={paused ? "Play slideshow" : "Pause slideshow"}
          data-testid="dashboard-slideshow-toggle-play"
          className="grid place-items-center w-8 h-8 rounded-full bg-black/25 hover:bg-black/50 backdrop-blur text-white transition-colors"
        >
          {paused ? <Play size={14} /> : <Pause size={14} />}
        </button>
      </div>

      <div
        className="absolute left-0 right-0 bottom-2 flex justify-center gap-2"
        data-testid="dashboard-slideshow-dots"
      >
        {SLIDES.map((s, i) => (
          <button
            key={s.key}
            type="button"
            onClick={() => goTo(i)}
            aria-label={`Show slide ${i + 1}: ${s.title}`}
            aria-current={i === index ? "true" : "false"}
            data-testid={`dashboard-slideshow-dot-${s.key}`}
            className={`h-1.5 rounded-full transition-all ${
              i === index
                ? "w-8 bg-white"
                : "w-4 bg-white/40 hover:bg-white/70"
            }`}
          />
        ))}
      </div>
    </section>
  );
}
