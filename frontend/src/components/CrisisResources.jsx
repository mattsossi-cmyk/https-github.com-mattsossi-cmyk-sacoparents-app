import { useEffect, useState } from "react";
import { LifeBuoy, Phone, Clock } from "lucide-react";
import api from "@/lib/api";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const Item = ({ it }) => (
  <li className={`rounded-xl border p-3 ${it.kind === "emergency" ? "border-red-300 bg-red-50" : it.kind === "office" ? "border-[#3D1A78]/20 bg-[#f6f3fb]" : "border-[#3D1A78]/15 bg-white"}`} data-testid={`crisis-item-${it.kind}-${it.tel}`}>
    <p className="text-sm font-bold text-slate-900">{it.name}</p>
    <a href={`tel:${it.tel}`} className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-[#3D1A78] underline-offset-2 hover:underline" data-testid={`crisis-call-${it.tel}`}><Phone className="h-3.5 w-3.5" aria-hidden="true" /> {it.contact}</a>
    <p className={`mt-1 flex items-start gap-1.5 text-xs ${it.kind === "office" ? "font-semibold text-amber-800" : "text-slate-600"}`} data-testid={`crisis-hours-${it.tel}`}><Clock className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" /> {it.hours}</p>
    {it.note && <p className="mt-1 text-xs text-slate-600">{it.note}</p>}
  </li>
);

export const CrisisResourcesButton = ({ version, className = "" }) => {
  const [open, setOpen] = useState(false);
  const [d, setD] = useState(null);
  useEffect(() => { setD(null); }, [version]);
  const show = async () => {
    setOpen(true);
    try { const r = await api.get("/safety/crisis-resources", { params: version ? { version } : {} }); setD(r.data); }
    catch { setD({ title: "Crisis Resources", items: [{ name: "Immediate danger", contact: "Call 911", tel: "911", hours: "Now", kind: "emergency" }] }); }
  };
  return (
    <>
      <button type="button" onClick={show} className={`font-jakarta inline-flex items-center gap-1.5 rounded-full border border-red-300 bg-white px-3 py-1.5 text-xs font-bold text-red-700 transition-colors hover:bg-red-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-500 ${className}`} data-testid="crisis-resources-btn"><LifeBuoy className="h-4 w-4" aria-hidden="true" /> Crisis Resources</button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="font-jakarta max-h-[90vh] overflow-y-auto sm:max-w-lg" data-testid="crisis-resources-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-[#3D1A78]" data-testid="crisis-resources-title"><LifeBuoy className="h-5 w-5" aria-hidden="true" /> {d?.title || "Crisis Resources"}</DialogTitle>
            <DialogDescription data-testid="crisis-resources-intro">{d?.intro || "Help is available any time."}</DialogDescription>
          </DialogHeader>
          {d ? <ul className="space-y-2" data-testid="crisis-resources-list">{d.items.map((it) => <Item key={it.tel} it={it} />)}</ul> : <p className="text-sm text-slate-600">Loading…</p>}
          <p className="text-[11px] text-slate-500" data-testid="crisis-resources-footer">Closing this window returns you to where you were. Your answers are kept.</p>
        </DialogContent>
      </Dialog>
    </>
  );
};
