/**
 * DashboardSlideshow — iter198 (+ iter200 refinements).
 *
 * Quiet, brand-aligned slideshow at the very top of the parent
 * dashboard. Cycles through the SA CoParents journey artwork so
 * returning users see the pathway before they make a choice.
 *
 * Iter200 improvements:
 *   * Uniform 16:9 assets — the 5 portrait originals are pre-padded
 *     to a common 1600×900 canvas with the SA dark-purple background
 *     so `object-cover` shows the entire founder image edge-to-edge
 *     with no crop. Served locally as WebP (~60KB each) instead of
 *     the 1MB PNGs on the CDN.
 *   * Slide linking — clicking a frame opens the matching pathway.
 *   * Mobile min-height (260px) so the caption never crushes the
 *     image at 390px viewports.
 *   * Auto-pause when the OS `prefers-reduced-motion` flag is set,
 *     and the play/pause button reflects that state so vestibular-
 *     sensitive users can still opt in.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight, Pause, Play, Check } from "lucide-react";
import { personaliseSlides } from "../lib/personaliseSlides";
import { useSlideProgress } from "../hooks/useSlideProgress";

// Founder-supplied journey artwork, pre-padded to 16:9 with the
// section's dark-purple background (see scripts/pad-slides.py in
// commit history for the exact PIL recipe). Order = recommended
// co-parenting sequence — do NOT reorder without a design review,
// parents parse this as a step sequence.
//
// Iter201 · this list is the BASELINE. `personaliseSlides()`
// rotates one slide to the front based on the parent's situation
// choice + court-ordered case link. Adding a slide here
// automatically shows it in personalised orderings too.
const BASE_SLIDES = [
  {
    key: "situation",
    src: "/slides/assess-family-situation.webp",
    title: "Assess your family situation",
    caption:
      "Start with a quick, private read of your household today — no judgement, no permanent labels.",
    route: "/situation",
  },
  {
    key: "child-needs",
    src: "/slides/identify-childs-needs.webp",
    title: "Identify your child's needs",
    caption:
      "Educational, medical, emotional — surface the specifics before you negotiate the shape of the week.",
    route: "/special-needs-v2",
  },
  {
    key: "relationship",
    src: "/slides/understand-coparenting-relationship.webp",
    title: "Understand your co-parenting relationship",
    caption:
      "Where you actually are today — cooperative, parallel, tense, or unsafe — decides which tools help next.",
    route: "/special-needs-v2",
  },
  {
    key: "communication",
    src: "/slides/strengthen-communication.webp",
    title: "Strengthen your communication",
    caption:
      "Draft the message you actually want to send — calmer, clearer, and easier for the other parent to hear.",
    route: "/communication",
  },
  {
    key: "foundation",
    src: "/slides/foundation-statement.webp",
    title: "Commit to your Foundation Statement",
    caption:
      "Write the anchor you'll come back to on the hard days — the reason this whole journey is worth the friction.",
    route: "/foundation/demo",
  },
];

const AUTO_MS = 6000;

// Detect the OS reduced-motion preference. Returns null on the
// server / when matchMedia is unavailable so consumers can distinguish
// "not asked yet" from "user prefers motion".
function _prefersReducedMotion() {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export default function DashboardSlideshow() {
  const navigate = useNavigate();
  const [index, setIndex] = useState(0);
  // Iter200 · start paused when the OS asks us to. Users can still
  // click Play to opt in.
  const [paused, setPaused] = useState(() => _prefersReducedMotion());
  const timerRef = useRef(null);

  // Iter201 · personalise slide order. Reads localStorage synchronously
  // on mount so the first paint already reflects the parent's stage.
  // Memoised so a re-render (e.g. progress fetch resolves) doesn't
  // shuffle the sequence out from under an active viewer.
  const SLIDES = useMemo(() => {
    let situation = null;
    let courtOrdered = false;
    try {
      situation = localStorage.getItem("sacoparents_situation_choice_v1") || null;
      courtOrdered = !!localStorage.getItem("sacoparents_court_ordered_case_id");
    } catch {
      /* private-browsing — best-effort only */
    }
    return personaliseSlides(BASE_SLIDES, { courtOrdered, situation });
  }, []);

  // Iter201 · completion flags for the small green ring on each frame.
  // Hook is safe to call unconditionally — it caches per session.
  const progress = useSlideProgress();

  // React to a live reduced-motion preference change (rare in
  // practice — user toggles the OS setting with the page open).
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return undefined;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = (e) => {
      if (e.matches) setPaused(true);
    };
    // addEventListener is the modern API; addListener is Safari-legacy.
    if (mq.addEventListener) mq.addEventListener("change", onChange);
    else if (mq.addListener) mq.addListener(onChange);
    return () => {
      if (mq.removeEventListener) mq.removeEventListener("change", onChange);
      else if (mq.removeListener) mq.removeListener(onChange);
    };
  }, []);

  const goTo = useCallback((n) => {
    const total = SLIDES.length;
    setIndex((prev) => {
      const next =
        ((typeof n === "function" ? n(prev) : n) % total + total) % total;
      return next;
    });
  }, [SLIDES.length]);

  // Auto-advance loop. Pauses when the user hovers / focuses / has
  // reduced-motion enabled.
  useEffect(() => {
    if (paused) return undefined;
    timerRef.current = setInterval(() => goTo((i) => i + 1), AUTO_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
    };
  }, [paused, goTo]);

  const prev = () => goTo((i) => i - 1);
  const next = () => goTo((i) => i + 1);

  const onKeyDown = (e) => {
    if (e.key === "ArrowLeft") { prev(); e.preventDefault(); }
    else if (e.key === "ArrowRight") { next(); e.preventDefault(); }
    else if (e.key === "Enter" || e.key === " ") {
      const active = SLIDES[index];
      if (active?.route) {
        navigate(active.route);
        e.preventDefault();
      }
    }
  };

  const openActive = () => {
    const active = SLIDES[index];
    if (active?.route) navigate(active.route);
  };

  return (
    <section
      // Iter200 · min-height keeps the frame readable at 390px where
      // 16:8 aspect otherwise collapses the caption into the image.
      className="relative w-full mx-auto rounded-3xl overflow-hidden bg-gradient-to-br from-[#1A1330] via-[#2A0F5F] to-[#3D1A78] shadow-lg min-h-[260px] sm:min-h-0"
      style={{ aspectRatio: "16 / 8" }}
      data-testid="dashboard-slideshow"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => {
        // Don't resume if the OS asked us not to. The play button is
        // the only way back once reduced-motion is on.
        if (!_prefersReducedMotion()) setPaused(false);
      }}
      onFocus={() => setPaused(true)}
      onBlur={() => {
        if (!_prefersReducedMotion()) setPaused(false);
      }}
      onKeyDown={onKeyDown}
      tabIndex={0}
      role="region"
      aria-roledescription="carousel"
      aria-label="SA CoParents journey"
    >
      {/* Frames — all mounted, opacity-toggled for a clean cross-fade.
          Keeping them mounted avoids a reload on every advance. Each
          frame is a clickable card routing to its pathway. */}
      {SLIDES.map((slide, i) => {
        const active = i === index;
        return (
          <button
            type="button"
            key={slide.key}
            onClick={() => active && openActive()}
            disabled={!active}
            aria-hidden={!active}
            aria-label={`Open ${slide.title}`}
            data-testid={`dashboard-slideshow-slide-${slide.key}`}
            className={`absolute inset-0 w-full h-full block text-left transition-opacity duration-700 ease-out focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70 ring-inset ${
              active ? "opacity-100 cursor-pointer" : "opacity-0 pointer-events-none"
            }`}
          >
            <img
              src={slide.src}
              alt={slide.title}
              className="w-full h-full object-contain object-center"
              loading={i === 0 ? "eager" : "lazy"}
              draggable={false}
            />
            {/* Gradient overlay for caption readability. */}
            <div
              className="absolute inset-0 bg-gradient-to-t from-[#1A1330]/85 via-[#1A1330]/25 to-transparent"
              aria-hidden="true"
            />
            {/* Iter201 · progress ring at the top-left of each frame.
                Green with a checkmark when the underlying assessment
                is done, soft white outline when still open. */}
            <ProgressRing
              done={!!progress[slide.key]}
              testid={`dashboard-slideshow-ring-${slide.key}`}
            />
            <div className="absolute left-0 right-0 bottom-0 p-5 sm:p-8">
              <div className="text-[10px] uppercase tracking-[0.28em] font-bold text-white/70">
                Step {i + 1} of {SLIDES.length}
              </div>
              <h3
                className="font-serif text-white text-xl sm:text-3xl lg:text-4xl leading-tight mt-1"
                data-testid={`dashboard-slideshow-title-${slide.key}`}
              >
                {slide.title}
              </h3>
              <p className="text-white/90 text-[13px] sm:text-[15px] mt-2 max-w-2xl leading-relaxed hidden sm:block">
                {slide.caption}
              </p>
            </div>
          </button>
        );
      })}

      {/* Prev / Next arrows — stop-propagation so a click on them
          doesn't also fire the frame click. */}
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); prev(); }}
        aria-label="Previous slide"
        data-testid="dashboard-slideshow-prev"
        className="absolute left-2 sm:left-3 top-1/2 -translate-y-1/2 grid place-items-center w-9 h-9 sm:w-11 sm:h-11 rounded-full bg-black/25 hover:bg-black/50 backdrop-blur text-white transition-colors z-10"
      >
        <ChevronLeft size={20} />
      </button>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); next(); }}
        aria-label="Next slide"
        data-testid="dashboard-slideshow-next"
        className="absolute right-2 sm:right-3 top-1/2 -translate-y-1/2 grid place-items-center w-9 h-9 sm:w-11 sm:h-11 rounded-full bg-black/25 hover:bg-black/50 backdrop-blur text-white transition-colors z-10"
      >
        <ChevronRight size={20} />
      </button>

      {/* Pause / play toggle. When reduced-motion is on we still
          allow the user to opt IN by clicking play — but we don't
          silently override their OS preference. */}
      <div className="absolute right-3 sm:right-6 top-3 sm:top-4 flex items-center gap-2 z-10">
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); setPaused((p) => !p); }}
          aria-label={paused ? "Play slideshow" : "Pause slideshow"}
          aria-pressed={paused}
          data-testid="dashboard-slideshow-toggle-play"
          title={
            paused && _prefersReducedMotion()
              ? "Auto-paused (your OS prefers reduced motion). Click to opt in."
              : paused
              ? "Play slideshow"
              : "Pause slideshow"
          }
          className="grid place-items-center w-8 h-8 rounded-full bg-black/25 hover:bg-black/50 backdrop-blur text-white transition-colors"
        >
          {paused ? <Play size={14} /> : <Pause size={14} />}
        </button>
      </div>

      <div
        className="absolute left-0 right-0 bottom-2 flex justify-center gap-2 z-10"
        data-testid="dashboard-slideshow-dots"
      >
        {SLIDES.map((s, i) => (
          <button
            key={s.key}
            type="button"
            onClick={(e) => { e.stopPropagation(); goTo(i); }}
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

/**
 * ProgressRing (iter201) — small circular badge in the top-left of
 * each slideshow frame.
 *   * `done=true`  → filled green ring with a white checkmark
 *   * `done=false` → soft white outline (subtle, non-blocking)
 * SVG-only, no external icons for the ring itself so it stays crisp
 * on every viewport. Never captures pointer events — the frame's
 * click stays intact.
 */
function ProgressRing({ done, testid }) {
  return (
    <div
      className="absolute top-4 left-4 sm:top-5 sm:left-5 pointer-events-none"
      data-testid={testid}
      data-done={done ? "true" : "false"}
    >
      <div
        className={`w-9 h-9 sm:w-11 sm:h-11 rounded-full grid place-items-center transition-all shadow-md ${
          done
            ? "bg-[#186142] border-2 border-[#3AAE7A]"
            : "bg-white/10 backdrop-blur border-2 border-white/40"
        }`}
        aria-hidden="true"
      >
        {done ? (
          <Check size={16} className="text-white" strokeWidth={3} />
        ) : (
          <span className="w-2 h-2 rounded-full bg-white/60" />
        )}
      </div>
      {/* Screen-reader label — the visual ring is decorative. */}
      <span className="sr-only">
        {done ? "Assessment completed" : "Not started yet"}
      </span>
    </div>
  );
}
