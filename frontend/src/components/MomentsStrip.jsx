const MOMENTS = [
  { img: "/moment-school.jpg", title: "At school", text: "Both parents in the same conference, hearing the same plan." },
  { img: "/moment-doctor.jpg", title: "At the doctor", text: "One shared record of what the child needs — no relaying, no gaps." },
  { img: "/moment-graduation.jpg", title: "At graduation", text: "Two proud parents in the room, and a child who never had to choose." },
  { img: "/moment-certificate.jpg", title: "Aligned", text: "A completed SA CoParents pathway the court can rely on." },
];

export function MomentsStrip() {
  return (
    <section className="max-w-6xl mx-auto px-6 py-16" data-testid="moments-section">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-brand-teal">Moments that matter</p>
      <h2 className="mt-2 text-base md:text-lg font-semibold text-foreground/80 max-w-2xl">Alignment is not about the parents getting along. It is about the child seeing both of them show up — calmly, predictably, together.</h2>
      <div className="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-4">
        {MOMENTS.map((m, i) => (
          <figure key={m.title} className="group overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition-transform duration-200 hover:-translate-y-1" style={{ animationDelay: `${i * 80}ms` }} data-testid={`moment-${i}`}>
            <img src={m.img} alt={`${m.title}: co-parents with their child`} loading="lazy" className="aspect-[3/2] w-full object-cover transition-transform duration-300 group-hover:scale-105" />
            <figcaption className="p-4"><p className="font-semibold text-brand-purple">{m.title}</p><p className="mt-1 text-sm text-muted-foreground">{m.text}</p></figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}
