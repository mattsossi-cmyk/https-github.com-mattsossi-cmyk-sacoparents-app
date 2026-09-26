import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BadgeCheck, MapPin, ArrowRight } from "lucide-react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";

export const ListedProsTeaser = () => {
  const [pros, setPros] = useState([]);
  useEffect(() => { api.get("/public/professionals").then((r) => setPros(r.data.professionals.slice(0, 3))).catch(() => {}); }, []);
  if (pros.length === 0) return null;
  return (
    <section className="max-w-6xl mx-auto px-6 py-16" data-testid="listed-pros-teaser">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl md:text-4xl font-semibold" data-testid="listed-pros-heading">Find a Professional</h2>
          <p className="mt-3 text-muted-foreground max-w-2xl">Approved co-parenting professionals who chose to be listed. Sort by your ZIP to find someone nearby.</p>
        </div>
        <Link to="/find-a-professional" data-testid="listed-pros-view-all-link"><Button className="bg-brand-purple hover:bg-brand-purple/90 text-white" data-testid="listed-pros-view-all-btn">Find a Professional <ArrowRight className="h-4 w-4" /></Button></Link>
      </div>
      <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {pros.map((p) => {
          const loc = [[p.city, p.state].filter(Boolean).join(", "), p.zip].filter(Boolean).join(" ");
          return (
            <li key={p.id} className="rounded-xl border border-border bg-white p-5" data-testid={`listed-pro-teaser-${p.id}`}>
              <div className="flex items-start justify-between gap-2">
                <div><p className="font-semibold leading-tight">{p.name}</p><p className="text-sm text-muted-foreground">{[p.pro_role, p.organization].filter(Boolean).join(" · ")}</p></div>
                {p.credentials_verified && <span className="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-accent shrink-0"><BadgeCheck className="h-3 w-3" /> Verified</span>}
              </div>
              {loc && <p className="mt-2 text-xs text-muted-foreground inline-flex items-center gap-1"><MapPin className="h-3 w-3" /> {loc}</p>}
              {p.bio && <p className="mt-2 text-sm line-clamp-3">{p.bio}</p>}
            </li>
          );
        })}
      </ul>
      <p className="mt-4 text-xs text-muted-foreground">Listing is voluntary and indicates an approved account; it is not an endorsement or referral.</p>
    </section>
  );
};
