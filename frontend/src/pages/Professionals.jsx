import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Mail, Phone, MapPin, Send, Search } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { VerifiedBadge } from "@/components/VerifiedBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";

export function ProfessionalCard({ p, isMe, onRefer, compact = false }) {
  return (
    <div className="bg-white border border-border rounded-lg p-5 flex flex-col min-w-0 overflow-hidden" data-testid={`pro-card-${p.id}`}>
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-1.5 sm:gap-2">
        <div className="min-w-0">
          <p className="font-semibold break-words" data-testid={`pro-name-${p.id}`}>{p.name}{isMe && <span className="ml-2 text-xs text-muted-foreground font-normal">(you)</span>}</p>
          <p className="text-sm text-muted-foreground break-words">{[p.pro_role, p.organization].filter(Boolean).join(" · ") || "Professional"}</p>
        </div>
        {p.credentials_verified && <VerifiedBadge testId={`pro-verified-${p.id}`} className="shrink-0 self-start" />}
      </div>
      {!compact && (
        <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
          <li className="flex items-center gap-2 min-w-0"><Mail className="h-3.5 w-3.5 shrink-0" /><a href={`mailto:${p.email}`} className="break-all hover:text-foreground" data-testid={`pro-email-${p.id}`}>{p.email}</a></li>
          {p.phone && <li className="flex items-center gap-2"><Phone className="h-3.5 w-3.5 shrink-0" /><a href={`tel:${p.phone}`} className="hover:text-foreground">{p.phone}</a></li>}
          {(p.city || p.state) && <li className="flex items-center gap-2"><MapPin className="h-3.5 w-3.5 shrink-0" />{[p.city, p.state].filter(Boolean).join(", ")}</li>}
        </ul>
      )}
      {!isMe && onRefer && (
        <Button size="sm" variant="outline" className="mt-4 gap-1.5 self-start" onClick={() => onRefer(p)} data-testid={`pro-refer-btn-${p.id}`}><Send className="h-3.5 w-3.5" /> Refer a case</Button>
      )}
    </div>
  );
}

function ReferDialog({ target, matters, onClose }) {
  const [message, setMessage] = useState("");
  const [reportId, setReportId] = useState("");
  const [busy, setBusy] = useState(false);
  const send = async () => {
    setBusy(true);
    try {
      await api.post(`/professionals/${target.id}/refer`, { message, report_id: reportId || null });
      toast.success(`Referral sent to ${target.name}`);
      onClose();
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="refer-dialog">
        <DialogHeader>
          <DialogTitle>Refer a case to {target.name}</DialogTitle>
          <DialogDescription>Your colleague receives your contact details and optional matter reference only. No parent information or report content is shared.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium" htmlFor="refer-matter">Matter (optional)</label>
            <select id="refer-matter" value={reportId} onChange={(e) => setReportId(e.target.value)} className="mt-1 w-full h-10 rounded-md border border-input bg-background px-3 text-sm" data-testid="refer-matter-select">
              <option value="">No specific matter</option>
              {matters.map((m) => <option key={m.id} value={m.id}>{m.case_code || m.id.slice(0, 8)} — {m.subject_label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="refer-message">Message</label>
            <Textarea id="refer-message" rows={4} value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Brief, neutral note about why you're referring (no parent names or allegations)." className="mt-1" data-testid="refer-message-input" />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose} data-testid="refer-cancel-btn">Cancel</Button>
            <Button onClick={send} disabled={busy} className="gap-1.5" data-testid="refer-send-btn"><Send className="h-4 w-4" /> {busy ? "Sending…" : "Send referral"}</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function Professionals() {
  const { user } = useAuth();
  const [pros, setPros] = useState(null);
  const [matters, setMatters] = useState([]);
  const [q, setQ] = useState("");
  const [target, setTarget] = useState(null);

  useEffect(() => {
    api.get("/professionals/directory").then((r) => setPros(r.data)).catch((e) => { toast.error(formatApiError(e)); setPros([]); });
    api.get("/joint/reports").then((r) => setMatters((r.data || []).filter((m) => m.is_creator && !m.archived))).catch(() => {});
  }, []);

  const shown = useMemo(() => {
    const n = q.trim().toLowerCase();
    return (pros || []).filter((p) => !n || [p.name, p.pro_role, p.organization, p.city, p.state, p.email].join(" ").toLowerCase().includes(n));
  }, [pros, q]);

  return (
    <div className="min-h-screen bg-background" data-testid="professionals-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/dashboard" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="professionals-back-link"><ArrowLeft className="h-4 w-4" /> Dashboard</Link>
          <BrandLogo size="text-xl" />
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-6 py-10">
        <h1 className="text-4xl font-extrabold text-brand-purple" data-testid="professionals-heading">Professional Directory</h1>
        <p className="text-muted-foreground mt-2 max-w-2xl">Approved SA CoParents Align professionals. Refer a matter to a colleague — they receive your contact details and the case reference only.</p>
        <div className="relative mt-6 max-w-md">
          <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, role, organization or city" className="pl-9" data-testid="professionals-search" />
        </div>
        {pros === null ? (
          <p className="text-sm text-muted-foreground mt-8" data-testid="professionals-loading">Loading…</p>
        ) : shown.length === 0 ? (
          <p className="text-sm text-muted-foreground mt-8" data-testid="professionals-empty">No professionals match.</p>
        ) : (
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="professionals-grid">
            {shown.map((p) => <ProfessionalCard key={p.id} p={p} isMe={p.id === user?.id} onRefer={setTarget} />)}
          </div>
        )}
        <p className="mt-8 text-xs text-muted-foreground" data-testid="professionals-count">{pros ? `${pros.length} approved professional${pros.length === 1 ? "" : "s"}` : ""}</p>
      </main>
      {target && <ReferDialog target={target} matters={matters} onClose={() => setTarget(null)} />}
    </div>
  );
}
