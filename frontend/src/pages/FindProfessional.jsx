import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Search } from "lucide-react";
import api from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { PublicProCard } from "@/components/PublicProCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function FindProfessional() {
  const { proId } = useParams();
  const [one, setOne] = useState(null);
  const [data, setData] = useState(null);
  const [zip, setZip] = useState("");
  const [q, setQ] = useState("");

  useEffect(() => {
    if (!proId) { setOne(null); return; }
    api.get(`/public/professionals/${proId}`).then((r) => setOne(r.data)).catch(() => setOne({ missing: true }));
  }, [proId]);

  useEffect(() => {
    if (proId) return undefined;
    const t = setTimeout(() => api.get("/public/professionals", { params: { zip: zip.trim(), q } }).then((r) => setData(r.data)).catch(() => setData({ professionals: [], count: 0, note: "" })), 250);
    return () => clearTimeout(t);
  }, [zip, q, proId]);

  if (proId) {
    return (
      <div className="min-h-screen bg-background" data-testid="find-professional-single-page">
        <header className="bg-white border-b border-border"><div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-2">
          <Link to="/find-a-professional" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground shrink-0" data-testid="find-pro-single-back-link"><ArrowLeft className="h-4 w-4" /> All professionals</Link><BrandLogo size="text-xl" /><span /></div></header>
        <main className="max-w-2xl mx-auto px-4 sm:px-6 py-12">
          {!one ? <p className="text-muted-foreground">Loading…</p> : one.missing ? <p className="rounded-lg border border-dashed border-border p-8 text-center text-muted-foreground" data-testid="find-pro-single-missing">This professional is not currently listed.</p>
            : <ul><PublicProCard p={one} testId="find-pro-single-card" /></ul>}
          <p className="mt-8 text-xs text-muted-foreground">Listing on SA CoParents Align is voluntary and indicates an approved account; it is not an endorsement, referral, or recommendation.</p>
        </main>
      </div>
    );
  }

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
          <ul className="grid gap-4 sm:grid-cols-2" data-testid="find-pro-list">{data.professionals.map((p) => <PublicProCard key={p.id} p={p} testId={`find-pro-card-${p.id}`} />)}</ul>
        )}
        {data?.note && <p className="mt-8 text-xs text-muted-foreground" data-testid="find-pro-note">{data.note}</p>}
      </main>
    </div>
  );
}
