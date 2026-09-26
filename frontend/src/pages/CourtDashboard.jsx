import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Gavel, ArrowLeft, Clock, MessageSquare } from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { PacketViewer } from "@/components/PacketViewer";
import { ReferCaseForm } from "@/components/ReferCaseForm";
import { CourtThread } from "@/components/CourtThread";
import { HearingDate } from "@/components/CourtCaseCard";
import { CaseSidebar, CaseOverview, ParentStatus, ReportsAvailable, PortalCard, HowItWorks } from "@/components/JudgePortal";
import { WorkflowGuide } from "@/components/WorkflowGuide";
import { UrgentMessages } from "@/components/UrgentMessages";
import { UrgentSmsSettings } from "@/components/UrgentSmsSettings";

const STATUS = {
  sent: ["New", "bg-align-yellow/30 text-yellow-900"],
  opened: ["Opened", "bg-align-blue/15 text-align-blue"],
  acknowledged: ["Acknowledged", "bg-align-green/15 text-green-900"],
  clarification_requested: ["Clarification requested", "bg-secondary text-muted-foreground"],
  revoked: ["Revoked", "bg-red-50 text-red-700"],
};

function PacketsList({ data, email, onOpen }) {
  if (data === null) return <p className="mt-4 text-muted-foreground">Loading…</p>;
  if (!data.approved) return <div className="mt-4 rounded-lg border border-align-yellow/60 bg-align-yellow/10 p-5 text-sm" data-testid="court-pending-approval"><Clock className="h-4 w-4 inline mr-1.5" /> Your court account is awaiting verification by SA CoParents. You'll receive an email when it's approved; packets addressed to your email will then appear here.</div>;
  if (data.packets.length === 0) return <p className="mt-4 text-sm text-muted-foreground" data-testid="court-packets-empty">No Court Packets have been addressed to {email} yet.</p>;
  return (
    <ul className="mt-4 divide-y divide-border rounded-lg border border-border bg-white" data-testid="court-packets-list">
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
              <Button size="sm" disabled={dead} onClick={() => onOpen(p)} data-testid={`court-dash-open-${p.id}`}>Open</Button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function CaseDetail({ x, onHearingSaved }) {
  const [d, setD] = useState(null);
  const [thread, setThread] = useState(false);
  useEffect(() => { setD(null); setThread(false); api.get(`/court-dashboard/cases/${x.id}`).then((r) => setD(r.data)).catch(() => setD({})); }, [x.id]);
  return (
    <section className="space-y-6" data-testid={`court-case-detail-${x.id}`}>
      <CaseOverview x={x} d={d} hearing={<HearingDate x={x} onSaved={onHearingSaved} />} />
      <ParentStatus x={x} d={d} />
      <ReportsAvailable x={x} d={d} />
      <PortalCard title="Professional Communication" testId="court-communication">
        <div className="rounded-xl bg-brand-purple/5 p-4"><p className="text-sm text-foreground/80">Secure case communication is limited to case status, report delivery, requests for additional information, and administrative court–professional matters.</p></div>
        <div className="mt-4 flex flex-wrap gap-3">
          <Button onClick={() => setThread((v) => !v)} className="bg-brand-purple text-white hover:bg-brand-purple/90" data-testid="court-message-pro-btn"><MessageSquare className="h-4 w-4 mr-1" /> {thread ? "Hide thread" : "Message Assigned Professional"}</Button>
          <Button variant="outline" asChild data-testid="court-comm-summary-btn"><Link to={`/court/case/${x.id}#thread`}>View Communication Summary</Link></Button>
        </div>
        {thread && <div className="mt-4" data-testid="court-inline-thread"><CourtThread baseUrl={`/court-dashboard/cases/${x.id}`} side="court" /></div>}
      </PortalCard>
    </section>
  );
}

export default function CourtDashboard() {
  const { user, logout } = useAuth();
  const [data, setData] = useState(null);
  const [refs, setRefs] = useState(null);
  const [showRefer, setShowRefer] = useState(false);
  const [selected, setSelected] = useState(null);
  const [search, setSearch] = useState("");
  const [active, setActive] = useState(null);
  const [packet, setPacket] = useState(null);

  const load = () => {
    api.get("/court-dashboard/packets").then((r) => setData(r.data)).catch(() => setData({ approved: false, packets: [] }));
    api.get("/court-dashboard/referrals").then((r) => { setRefs(r.data); setSelected((s) => s || r.data[0]?.id || null); }).catch(() => setRefs([]));
  };
  useEffect(() => { load(); }, []);

  const open = (p) => { setActive(p.id); setPacket(null); api.get(`/court-dashboard/packets/${p.id}`).then((r) => setPacket(r.data)).catch(() => setActive(null)); };
  const back = () => { setActive(null); setPacket(null); load(); };
  const current = (refs || []).find((x) => x.id === selected);
  const onHearingSaved = (hd) => setRefs((rs) => rs.map((x) => (x.id === selected ? { ...x, hearing_date: hd } : x)));

  return (
    <div className="min-h-screen bg-background" data-testid="court-dashboard">
      <header className="border-b border-border bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-6 py-4">
          <div><BrandLogo size="text-xl" /><p className="mt-1 text-xs font-semibold uppercase tracking-widest text-accent flex items-center gap-1.5"><Gavel className="h-3.5 w-3.5" /> Judicial Case Review Portal</p></div>
          <div className="flex items-center gap-3 text-sm"><span className="text-muted-foreground hidden sm:inline" data-testid="court-dashboard-user">{user?.name}</span><Button size="sm" variant="outline" onClick={logout} data-testid="court-logout-btn">Sign out</Button></div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6"><WorkflowGuide kind="judge" /></div>
        <UrgentMessages onOpen={(refId) => { setActive(null); setSelected(refId); window.location.hash = "thread"; }} />
        <UrgentSmsSettings />
        {active ? (
          <>
            <button type="button" onClick={back} className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground" data-testid="court-back-btn"><ArrowLeft className="h-4 w-4" /> Back to portal</button>
            {packet ? <PacketViewer packet={packet} setPacket={setPacket} downloadHref={`${process.env.REACT_APP_BACKEND_URL}/api/court-dashboard/packets/${active}/pdf`} respondFn={(body) => api.post(`/court-dashboard/packets/${active}/respond`, body)} /> : <p className="text-muted-foreground">Loading packet…</p>}
          </>
        ) : (
          <>
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div><h1 className="text-3xl font-semibold">Court-Referred Cases</h1><p className="mt-1 text-sm text-muted-foreground">Signed in as {user?.email}. Read-only; every opening is logged for the sending professional. Raw parent answers are never shown.</p></div>
              {data?.approved && <Button onClick={() => setShowRefer((v) => !v)} className="bg-brand-purple hover:bg-brand-purple/90 text-white" data-testid="refer-case-toggle-btn">{showRefer ? "Close" : "Refer Case to Professional"}</Button>}
            </div>
            {data?.approved && showRefer && <div className="mt-6"><ReferCaseForm defaultCourt={user?.profile?.organization} onCreated={() => { setShowRefer(false); load(); }} /></div>}

            {data?.approved && refs && (
              refs.length === 0 ? (
                <div className="mt-8 grid gap-6 lg:grid-cols-2" data-testid="court-empty-state">
                  <HowItWorks />
                  <PortalCard title="Refer your first case"><ReferCaseForm defaultCourt={user?.profile?.organization} onCreated={load} /></PortalCard>
                </div>
              ) : (
                <div className="mt-8 grid gap-6 lg:grid-cols-[320px_1fr]" data-testid="court-portal-grid">
                  <aside><CaseSidebar refs={refs} selectedId={selected} onSelect={setSelected} search={search} setSearch={setSearch} /></aside>
                  {current ? <CaseDetail x={current} onHearingSaved={onHearingSaved} /> : <p className="text-sm text-muted-foreground">Select a case.</p>}
                </div>
              )
            )}

            <h2 className="mt-12 text-lg font-semibold">Court Packets addressed to you</h2>
            <PacketsList data={data} email={user?.email} onOpen={open} />
            <p className="mt-10 text-xs text-muted-foreground">Received a packet link with an access code instead? You can still open it directly from the email. <Link to="/methodology" className="text-primary hover:underline">About the Align methodology</Link>.</p>
          </>
        )}
      </main>
    </div>
  );
}
