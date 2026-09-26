import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, BadgeCheck, MapPin, Phone, Globe, Search } from "lucide-react";
import api from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function ProCard({ p }) {
  const loc = [[p.city, p.state].filter(Boolean).join(", "), p.zip].filter(Boolean).join(" ");
  return (
    <li className="rounded-xl border border-border bg-white p-5 flex flex-col gap-2" data-testid={`find-pro-card-${p.id}`}>
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

export default function FindProfessional() {
  const [data, setData] = useState(null);
  const [zip, setZip] = useState("");
  const [q, setQ] = useState("");

  useEffect(() => {
    const t = setTimeout(() => api.get("/public/professionals", { params: { zip: zip.trim(), q } }).then((r) => setData(r.data)).catch(() => setData({ professionals: [], count: 0, note: "" })), 250);
    return () => clearTimeout(t);
  }, [zip, q]);

  return (
    <div className="min-h-screen bg-background" data-testid="find-professional-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-2">
          <Link to="/" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground shrink-0" data-testid="find-pro-back-link"><ArrowLeft className="h-4 w-4" /> Home</Link>
          <BrandLogo size="text-xl" />
          <Link to="/auth?mode=register" data-testid="find-pro-register-link" className="shrink-0"><Button size="sm"><span className="hidden sm:inline">I'm a Professional</span><span className="sm:hidden">Join</span></Button></Link>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
        <div className="max-w-2xl mb-8">
          <h1 className="text-4xl sm:text-5xl font-extrabold text-brand-purple" data-testid="find-pro-heading">Find a Professional</h1>
          <p className="text-base md:text-lg text-muted-foreground mt-4">Approved co-parenting professionals who chose to be listed on SA CoParents Align. Enter your ZIP to sort by distance.</p>
        </div>
        <div className="flex flex-wrap gap-2 mb-6">
          <Input placeholder="Your ZIP" value={zip} onChange={(e) => setZip(e.target.value)} inputMode="numeric" maxLength={10} className="w-[140px]" data-testid="find-pro-zip" />
          <div className="relative flex-1 min-w-[200px]"><Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" /><Input placeholder="Search name, role, organization, city…" value={q} onChange={(e) => setQ(e.target.value)} className="pl-8" data-testid="find-pro-search" /></div>
        </div>
        {!data ? <p className="text-muted-foreground">Loading…</p> : data.count === 0 ? (
          <p className="rounded-lg border border-dashed border-border p-8 text-center text-muted-foreground" data-testid="find-pro-empty">No listed professionals match yet.</p>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2" data-testid="find-pro-list">{data.professionals.map((p) => <ProCard key={p.id} p={p} />)}</ul>
        )}
        {data?.note && <p className="mt-8 text-xs text-muted-foreground" data-testid="find-pro-note">{data.note}</p>}
      </main>
    </div>
  );
}
