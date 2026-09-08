import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, Archive, ArchiveRestore, Search, CheckCircle2, Clock, ShieldAlert, AlertTriangle, StickyNote, RefreshCw } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { ReminderPreviewButton } from "@/components/ReminderPreview";
import { MatterNotes } from "@/components/MatterNotes";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const FILTERS = [
  ["all", "All Active"],
  ["awaiting_parents", "Awaiting Both Parents"],
  ["awaiting_a", "Awaiting Parent 1"],
  ["awaiting_b", "Awaiting Parent 2"],
  ["ready", "Report Ready"],
  ["expiring", "Expiring Invitations"],
  ["archived", "Archived"],
];

const DAY = 86400000;
export function expiringInvites(j) {
  return (j.pending_invitations || []).filter((i) => i.expires_at && new Date(i.expires_at).getTime() - Date.now() <= 4 * DAY);
}
const daysLeft = (iso) => Math.ceil((new Date(iso).getTime() - Date.now()) / DAY);

export function matterStatus(j) {
  if (j.archived) return { key: "archived", label: "Archived" };
  if (j.status === "ready") return { key: "ready", label: "Report Ready" };
  const a = j.participants?.a?.completed, b = j.participants?.b?.completed;
  if (a && !b) return { key: "awaiting_b", label: "Awaiting Parent 2" };
  if (b && !a) return { key: "awaiting_a", label: "Awaiting Parent 1" };
  return { key: "awaiting_parents", label: "Awaiting Both Parents" };
}

const childRef = (name) => (name ? `${name.trim().charAt(0).toUpperCase()}.` : "Child");

const badgeClass = {
  ready: "bg-align-green/15 text-align-green",
  archived: "bg-muted text-muted-foreground",
  awaiting_a: "bg-align-yellow/20 text-yellow-800",
  awaiting_b: "bg-align-yellow/20 text-yellow-800",
  awaiting_parents: "bg-secondary text-foreground",
};

function MatterRow({ j, onToggle, onReissue }) {
  const s = matterStatus(j);
  const done = ["a", "b"].filter((r) => j.participants?.[r]?.completed).length;
  const [showNotes, setShowNotes] = useState(false);
  return (
    <li className="bg-white border border-border rounded-lg px-5 py-4" data-testid={`matter-row-${j.id}`}>
    <div className="flex flex-col sm:flex-row sm:items-center gap-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-[11px] font-semibold uppercase tracking-wider rounded-full px-2.5 py-0.5 ${badgeClass[s.key]}`} data-testid={`matter-status-${j.id}`}>{s.label}</span>
          {j.is_safety && <span className="text-[11px] font-semibold uppercase tracking-wider rounded-full px-2.5 py-0.5 bg-red-100 text-red-800 inline-flex items-center gap-1"><ShieldAlert className="h-3 w-3" /> Safety</span>}
          <span className="text-xs text-muted-foreground">{j.subject_label}</span>
        </div>
        <p className="font-semibold mt-1.5" data-testid={`matter-title-${j.id}`}>Matter for {childRef(j.child_name)}{j.case_code ? <span className="text-muted-foreground font-normal"> · {j.case_code}</span> : null}</p>
        <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1.5">
          {s.key === "ready" ? <CheckCircle2 className="h-3.5 w-3.5 text-align-green" /> : <Clock className="h-3.5 w-3.5" />}
          {done}/2 parent assessments complete · opened {new Date(j.created_at).toLocaleDateString()}
        </p>
        {expiringInvites(j).map((i) => {
          const d = daysLeft(i.expires_at);
          const expired = i.expired || d <= 0;
          return (
            <div key={i.id} className={`mt-2 flex flex-wrap items-center gap-2 text-xs rounded-md px-3 py-1.5 border ${expired ? "bg-red-50 border-red-200" : "bg-align-yellow/15 border-align-yellow/40"}`} data-testid={`matter-expiring-${i.id}`}>
              <AlertTriangle className={`h-3.5 w-3.5 ${expired ? "text-red-700" : "text-yellow-800"}`} />
              <span>Invitation to Parent {i.role === "a" ? "1" : "2"} {expired ? "has expired — the link no longer works" : `expires in ${d} day${d === 1 ? "" : "s"}`}</span>
              {!expired && <ReminderPreviewButton iid={i.id} label="Send Reminder" testId={`matter-remind-btn-${i.id}`} />}
              <Button size="sm" variant={expired ? "default" : "outline"} className="h-7 gap-1.5" onClick={() => onReissue(i)} data-testid={`matter-reissue-btn-${i.id}`}><RefreshCw className="h-3 w-3" /> Reissue Invitation</Button>
            </div>
          );
        })}
      </div>
      <div className="flex gap-2 shrink-0">
        <Link to={`/joint/${j.id}`} data-testid={`matter-open-link-${j.id}`}><Button size="sm" variant={s.key === "ready" ? "default" : "outline"} data-testid={`matter-open-btn-${j.id}`}>{s.key === "ready" ? "View Report" : "Open"}</Button></Link>
        <Button size="sm" variant="ghost" onClick={() => setShowNotes((v) => !v)} className="gap-1.5" data-testid={`matter-notes-btn-${j.id}`}><StickyNote className="h-3.5 w-3.5" /> Notes</Button>
        <Button size="sm" variant="ghost" onClick={() => onToggle(j)} className="gap-1.5" data-testid={`matter-archive-btn-${j.id}`}>
          {j.archived ? <><ArchiveRestore className="h-3.5 w-3.5" /> Restore</> : <><Archive className="h-3.5 w-3.5" /> Archive</>}
        </Button>
      </div>
    </div>
    {showNotes && <MatterNotes rid={j.id} />}
    </li>
  );
}

export default function FamilyMatters() {
  const [joints, setJoints] = useState(null);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState(() => new URLSearchParams(window.location.search).get("filter") || "all");

  const load = () => api.get("/joint/reports").then((r) => setJoints(r.data)).catch((e) => toast.error(formatApiError(e)));
  useEffect(() => { load(); }, []);

  const toggle = async (j) => {
    try {
      await api.patch(`/joint/reports/${j.id}/archive`, { archived: !j.archived });
      toast.success(j.archived ? "Matter restored" : "Matter archived");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const reissue = async (i) => {
    try {
      await api.post(`/joint/invitations/${i.id}/reissue`);
      toast.success("Fresh invitation sent — the old link no longer works");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const counts = useMemo(() => {
    const c = { all: 0, expiring: 0 };
    (joints || []).forEach((j) => { const k = matterStatus(j).key; c[k] = (c[k] || 0) + 1; if (k !== "archived") { c.all += 1; if (expiringInvites(j).length) c.expiring += 1; } });
    return c;
  }, [joints]);

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (joints || []).filter((j) => {
      const k = matterStatus(j).key;
      if (filter === "expiring") { if (k === "archived" || !expiringInvites(j).length) return false; }
      else if (filter === "all" ? k === "archived" : k !== filter) return false;
      if (!needle) return true;
      return [j.case_code, j.subject_label, j.child_name, j.case_reference, j.participants?.a?.name, j.participants?.b?.name].some((v) => (v || "").toLowerCase().includes(needle));
    });
  }, [joints, q, filter]);

  return (
    <div className="min-h-screen bg-background" data-testid="family-matters-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between gap-3">
          <Link to="/dashboard" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="matters-back-link"><ArrowLeft className="h-4 w-4" /> Dashboard</Link>
          <BrandLogo size="text-xl" />
          <Link to="/joint/new" data-testid="matters-new-link"><Button size="sm" data-testid="matters-new-btn">New Matter</Button></Link>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10 space-y-6">
        <div>
          <h1 className="text-4xl font-semibold" data-testid="matters-heading">My Family Matters</h1>
          <p className="text-muted-foreground mt-2">Track parent participation and report readiness. Children are shown by initial only.</p>
        </div>
        <div className="relative max-w-md">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by case code, subject, reference or parent" className="pl-9 h-11" data-testid="matters-search-input" />
        </div>
        <div className="flex flex-wrap gap-2" data-testid="matters-filters">
          {FILTERS.map(([k, label]) => (
            <button key={k} onClick={() => setFilter(k)} className={`text-xs font-medium rounded-full px-3 py-1.5 border transition-colors ${filter === k ? "bg-primary text-white border-primary" : "bg-white border-border hover:border-primary/50"}`} data-testid={`matters-filter-${k}`}>
              {label} <span className="opacity-70">({counts[k] || 0})</span>
            </button>
          ))}
        </div>
        {joints === null ? (
          <p className="text-muted-foreground" data-testid="matters-loading">Loading…</p>
        ) : shown.length === 0 ? (
          <p className="text-sm text-muted-foreground bg-white border border-border rounded-lg p-6" data-testid="matters-empty">No family matters match this view.</p>
        ) : (
          <ul className="space-y-3" data-testid="matters-list">{shown.map((j) => <MatterRow key={j.id} j={j} onToggle={toggle} onReissue={reissue} />)}</ul>
        )}
      </main>
    </div>
  );
}
