import { useEffect, useRef, useState } from "react";

// Founder "Welcome to SA CoParents" artwork; the three pictured cards are tappable shortcuts.
const HOTSPOTS = [
  { id: "self", label: "Open Self Journey", left: "2%", width: "31.5%" },
  { id: "court", label: "Open Court Ordered Path", left: "35%", width: "30.5%" },
  { id: "comm", label: "Open the Communication Builder, a message tool for either path", left: "66.5%", width: "31.5%" },
];

export const WelcomeArtwork = ({ testid, actions }) => {
  const imgRef = useRef(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    if (imgRef.current?.complete) setLoaded(true);
  }, []);
  const prefix = testid.replace(/-image$/, "");
  return (
    <figure className="space-y-2">
      <section
        data-testid={testid}
        className="relative overflow-hidden rounded-2xl border border-purple-100 shadow-sm bg-purple-50"
      >
        <img
          ref={imgRef}
          onLoad={() => setLoaded(true)}
          src="/images/sa-welcome.webp?v=3"
          srcSet="/images/sa-welcome-768.webp?v=3 768w, /images/sa-welcome.webp?v=3 1024w"
          sizes="(max-width: 640px) 100vw, 640px"
          width={1024}
          height={1536}
          alt="Welcome to SA CoParents. Two paths: Self Journey or Court Ordered Path. The SA CoParent Communication Builder is a message tool you can use with either path. Same goals, a brighter future."
          className="block w-full h-auto"
          loading="lazy"
        />
        {HOTSPOTS.map((h, i) => (
          <button
            key={h.id}
            type="button"
            data-testid={`${prefix}-hotspot-${h.id}`}
            aria-label={h.label}
            onClick={actions[h.id]}
            className={`sa-hotspot absolute rounded-2xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-purple-600 ${loaded ? "sa-hotspot-pulse" : ""}`}
            style={{ left: h.left, width: h.width, top: "32.5%", height: "53%", animationDelay: `${0.4 + i * 0.3}s` }}
          />
        ))}
        <span
          data-testid={`${prefix}-comm-badge`}
          aria-hidden="true"
          className="pointer-events-none absolute flex justify-center"
          style={{ left: "66.5%", width: "31.5%", top: "33.6%" }}
        >
          <span className="rounded-full bg-sky-700/95 text-white font-bold uppercase tracking-wide shadow px-2 py-0.5 text-[0.5625rem] sm:text-[0.625rem] leading-tight text-center">
            Tool for either path
          </span>
        </span>
      </section>
      <figcaption data-testid={`${prefix}-caption`} className="text-[0.6875rem] text-slate-600 text-center leading-snug px-2">
        Tap a picture to open it. The third picture, the Communication Builder, isn&rsquo;t a separate path: it&rsquo;s a message tool you can use with either one.
      </figcaption>
    </figure>
  );
};
