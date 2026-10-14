import { useState } from "react";
import { Lock } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const LABELS = { method: "Method", address: "Address / number", safe_times: "Safe times", voicemail_ok: "Voicemail/message OK", code_word: "Code word" };

export const BridgeSafeContact = ({ rid, role }) => {
  const [state, setState] = useState({ status: "idle" });
  const load = async () => {
    setState({ status: "loading" });
    try { const { data } = await api.get(`/joint/reports/${rid}/bridge/safe-contact/${role}`); setState({ status: "done", sc: data.safe_contact }); }
    catch (e) { setState(e?.response?.status === 404 && e.response.data?.detail === "Not available" ? { status: "idle", hidden: true } : { status: "error", msg: formatApiError(e) }); }
  };
  if (state.hidden) return null;
  return (
    <div className="rounded-md border border-brand-purple/30 bg-white p-3 text-sm" data-testid="bridge-safe-contact">
      <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-brand-purple"><Lock className="h-3.5 w-3.5" /> SA CoParents App contact preference · professional-only · access logged</p>
      {state.status === "idle" && <Button size="sm" variant="outline" className="mt-2" onClick={load} data-testid="bridge-safe-contact-load">Show details from SA CoParents App</Button>}
      {state.status === "loading" && <p className="mt-2 text-xs text-muted-foreground">Checking…</p>}
      {state.status === "error" && <p className="mt-2 text-xs text-muted-foreground" data-testid="bridge-safe-contact-error">{state.msg}</p>}
      {state.status === "done" && (state.sc
        ? <dl className="mt-2 space-y-1" data-testid="bridge-safe-contact-view">{Object.entries(LABELS).filter(([k]) => state.sc[k]).map(([k, l]) => <div key={k}><dt className="inline font-medium">{l}: </dt><dd className="inline">{String(state.sc[k])}</dd></div>)}</dl>
        : <p className="mt-2 text-xs text-muted-foreground" data-testid="bridge-safe-contact-empty">No contact preference has been shared for this case.</p>)}
      <p className="mt-2 text-[11px] text-muted-foreground">Viewed live from SA CoParents App; not stored in Align and never included in reports, PDFs, emails or exports.</p>
    </div>
  );
};
