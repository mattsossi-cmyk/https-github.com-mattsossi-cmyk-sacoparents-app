import { BadgeCheck, MapPin, Phone, Globe } from "lucide-react";

export function PublicProCard({ p, testId }) {
  const loc = [[p.city, p.state].filter(Boolean).join(", "), p.zip].filter(Boolean).join(" ");
  return (
    <li className="rounded-xl border border-border bg-white p-5 flex flex-col gap-2 list-none" data-testid={testId}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-base leading-tight">{p.name}</h3>
          <p className="text-sm text-muted-foreground">{[p.pro_role, p.organization].filter(Boolean).join(" · ")}</p>
        </div>
        {p.credentials_verified && <span className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-accent shrink-0"><BadgeCheck className="h-3 w-3" /> Verified</span>}
      </div>
      {loc && <p className="text-xs text-muted-foreground inline-flex items-center gap-1"><MapPin className="h-3 w-3" /> {loc}{p.distance_miles != null && <span className="ml-1 text-brand-purple font-medium">· {p.distance_miles} mi</span>}</p>}
      {p.bio && <p className="text-sm mt-1 whitespace-pre-line">{p.bio}</p>}
      <div className="mt-auto flex flex-wrap gap-3 pt-2 text-sm">
        {p.phone && <a href={`tel:${p.phone}`} className="inline-flex items-center gap-1 text-brand-purple hover:underline"><Phone className="h-3.5 w-3.5" /> {p.phone}</a>}
        {p.website && <a href={p.website} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-purple hover:underline"><Globe className="h-3.5 w-3.5" /> Website</a>}
      </div>
    </li>
  );
}
