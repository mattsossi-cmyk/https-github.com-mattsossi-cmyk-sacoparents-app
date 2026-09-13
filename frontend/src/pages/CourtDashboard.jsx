import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Gavel, ArrowLeft, Clock } from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { PacketViewer } from "@/components/PacketViewer";
import { ReferCaseForm } from "@/components/ReferCaseForm";
import { CaseProgress } from "@/components/CaseProgress";
import { CourtStatusSummary } from "@/components/CourtStatusSummary";

const STATUS = {
  sent: ["New", "bg-align-yellow/30 text-yellow-900"],
  opened: ["Opened", "bg-align-blue/15 text-align-blue"],
  acknowledged: ["Acknowledged", "bg-align-green/15 text-green-900"],
  clarification_requested: ["Clarification requested", "bg-secondary text-muted-foreground"],
  revoked: ["Revoked", "bg-red-50 text-red-700"],
};

export default function CourtDashboard() {
  const { user, logout } = useAuth();
  const [data, setData] = useState(null);
  const [refs, setRefs] = useState([]);
  const [showRefer, setShowRefer] = useState(false);
  const [active, setActive] = useState(null);
  const [packet, setPacket] = useState(null);

  const load = () => {
    api.get("/court-dashboard/packets").then((r) => setData(r.data)).catch(() => setData({ approved: false, packets: [] }));
    api.get("/court-dashboard/referrals").then((r) => setRefs(r.data)).catch(() => setRefs([]));
  };
  useEffect(() => { load(); }, []);

  const open = (p) => {
    setActive(p.id); setPacket(null);
    api.get(`/court-dashboard/packets/${p.id}`).then((r) => setPacket(r.data)).catch(() => setActive(null));
  };
  const back = () => { setActive(null); setPacket(null); load(); };

  return (
    <div className="min-h-screen bg-background" data-testid="court-dashboard">
      <header className="border-b border-border bg-white"><div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between gap-3"><BrandLogo size="text-xl" /><div className="flex items-center gap-3 text-sm"><span className="text-muted-foreground hidden sm:inline" data-testid="court-dashboard-user">{user?.name}</span><Button size="sm" variant="ghost" onClick={logout} data-testid="court-logout-btn">Sign out</Button></div></div></header>
      <main className="max-w-5xl mx-auto px-6 py-10">
        {active ? (
          <>
            <button type="button" onClick={back} className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground" data-testid="court-back-btn"><ArrowLeft className="h-4 w-4" /> All packets</button>
            {packet ? (
              <PacketViewer packet={packet} setPacket={setPacket} downloadHref={`${process.env.REACT_APP_BACKEND_URL}/api/court-dashboard/packets/${active}/pdf`} respondFn={(body) => api.post(`/court-dashboard/packets/${active}/respond`, body)} />
            ) : <p className="text-muted-foreground">Loading packet…</p>}
          </>
        ) : (
          <>
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-widest text-accent font-semibold flex items-center gap-1.5"><Gavel className="h-3.5 w-3.5" /> Court Dashboard</p>
                <h1 className="text-3xl font-semibold mt-1">Referrals and submissions</h1>
                <p className="mt-1 text-sm text-muted-foreground">Signed in as {user?.email}. Read-only; every opening is logged for the sending professional.</p>
              </div>
              {data?.approved && <Button onClick={() => setShowRefer((v) => !v)} className="bg-brand-purple hover:bg-brand-purple/90 text-white" data-testid="refer-case-toggle-btn">{showRefer ? "Close" : "Refer Case to Professional"}</Button>}
            </div>
            {data?.approved && showRefer && <div className="mt-6"><ReferCaseForm defaultCourt={user?.profile?.organization} onCreated={() => { setShowRefer(false); load(); }} /></div>}
            {data?.approved && refs.length > 0 && (
              <section className="mt-8" data-testid="court-referrals-section">
                <h2 className="text-lg font-semibold">Your referrals</h2>
                <ul className="mt-3 divide-y divide-border rounded-lg border border-border bg-white">
                  {refs.map((x) => (
                    <li key={x.id} className="px-5 py-4" data-testid={`court-referral-row-${x.id}`}>
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-semibold">Cause No. {x.cause_number} <span className="ml-2 text-sm font-normal text-muted-foreground">→ {x.professional_name}{x.case_code ? ` · ${x.case_code}` : ""}</span></p>
                        <span className="text-xs text-muted-foreground">{x.status === "declined" ? `Declined: ${x.decline_reason}` : `referred ${x.created_at?.slice(0, 10)}`}</span>
                      </div>
                      <CaseProgress stage={x.stage} />
                      <CourtStatusSummary referralId={x.id} summary={x.status_summary} onRefreshed={(s) => setRefs((rs) => rs.map((y) => (y.id === x.id ? { ...y, status_summary: s } : y)))} />
                    </li>
                  ))}
                </ul>
              </section>
            )}
            <h2 className="mt-10 text-lg font-semibold">Court Packets addressed to you</h2>
            {data === null ? <p className="mt-8 text-muted-foreground">Loading…</p> : !data.approved ? (
              <div className="mt-8 rounded-lg border border-align-yellow/60 bg-align-yellow/10 p-5 text-sm" data-testid="court-pending-approval"><Clock className="h-4 w-4 inline mr-1.5" /> Your court account is awaiting verification by SA CoParents. You'll receive an email when it's approved; packets addressed to your email will then appear here.</div>
            ) : data.packets.length === 0 ? (
              <p className="mt-8 text-sm text-muted-foreground" data-testid="court-packets-empty">No Court Packets have been addressed to {user?.email} yet.</p>
            ) : (
              <ul className="mt-8 divide-y divide-border rounded-lg border border-border bg-white" data-testid="court-packets-list">
                {data.packets.map((p) => {
                  const [label, cls] = STATUS[p.state === "active" ? p.status : p.state] || STATUS.sent;
                  const dead = p.state !== "active";
                  return (
                    <li key={p.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4" data-testid={`court-dash-packet-${p.id}`}>
                      <div className="min-w-0">
                        <p className="font-semibold">{p.cause_number ? `Cause No. ${p.cause_number}` : p.court_name || "Court Packet"} <span className="ml-2 text-sm font-normal text-muted-foreground">{p.subject_label}{p.case_code ? ` · ${p.case_code}` : ""}</span></p>
                        <p className="text-xs text-muted-foreground mt-0.5">From {p.professional_name} · sent {p.created_at?.slice(0, 10)} · {p.report_count} report{p.report_count === 1 ? "" : "s"} · {dead ? p.state : `expires ${p.expires_at?.slice(0, 10)}`}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`} data-testid={`court-dash-status-${p.id}`}>{label}</span>
                        <Button size="sm" disabled={dead} onClick={() => open(p)} data-testid={`court-dash-open-${p.id}`}>Open</Button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
            <p className="mt-10 text-xs text-muted-foreground">Received a packet link with an access code instead? You can still open it directly from the email. <Link to="/methodology" className="text-primary hover:underline">About the Align methodology</Link>.</p>
          </>
        )}
      </main>
    </div>
  );
}
