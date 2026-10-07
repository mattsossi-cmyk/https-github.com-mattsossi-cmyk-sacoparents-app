// Founder "Welcome to SA CoParents" artwork; the three pictured cards are tappable shortcuts.
const HOTSPOTS = [
  { id: "self", label: "Open Individual Journey", left: "2%", width: "31.5%" },
  { id: "court", label: "Open Court Ordered Path", left: "35%", width: "30.5%" },
  { id: "comm", label: "Open the Communication Builder", left: "66.5%", width: "31.5%" },
];

export const WelcomeArtwork = ({ testid, actions }) => (
  <section
    data-testid={testid}
    className="relative overflow-hidden rounded-2xl border border-purple-100 shadow-sm bg-purple-50"
  >
    <img
      src="/images/sa-welcome.webp"
      srcSet="/images/sa-welcome-768.webp 768w, /images/sa-welcome.webp 1024w"
      sizes="(max-width: 640px) 100vw, 640px"
      width={1024}
      height={1536}
      alt="Welcome to SA CoParents. Choose your path: Individual Journey, Court Ordered Path, or the SA CoParent Communication Builder. Same goals, a brighter future."
      className="block w-full h-auto"
      loading="lazy"
    />
    {HOTSPOTS.map((h) => (
      <button
        key={h.id}
        type="button"
        data-testid={`${testid.replace(/-image$/, "")}-hotspot-${h.id}`}
        aria-label={h.label}
        onClick={actions[h.id]}
        className="absolute rounded-2xl focus-visible:outline focus-visible:outline-4 focus-visible:outline-purple-600 hover:bg-white/10 transition-colors"
        style={{ left: h.left, width: h.width, top: "32.5%", height: "53%" }}
      />
    ))}
  </section>
);
