import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { GraduationCap } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

export default function ProfessionalTraining() {
  const navigate = useNavigate();
  const [d, setD] = useState(null);
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get("/professional-training").then((r) => setD(r.data)).catch((e) => toast.error(formatApiError(e))); }, []);
  const go = async () => {
    setBusy(true);
    try {
      await api.post("/professional-training/acknowledge", { version: d.training.version, acknowledged: ok });
      toast.success("Training acknowledgment recorded");
      navigate(sessionStorage.getItem("post-training-redirect") || "/dashboard", { replace: true });
      sessionStorage.removeItem("post-training-redirect");
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  if (!d) return <div className="min-h-screen bg-[#f6f3fb]" data-testid="training-loading" />;
  const t = d.training;
  return (
    <div className="min-h-screen bg-[#f6f3fb] font-jakarta text-slate-900" data-testid="professional-training-page">
      <header className="bg-[#ece6f7]"><div className="mx-auto flex max-w-2xl flex-col items-center px-4 pb-8 pt-10 text-center sm:px-6"><BrandLogo size="text-3xl" />
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-[#3D1A78] sm:text-4xl" data-testid="training-title">{t.title}</h1>
        <p className="mt-2 text-xs font-mono text-[#3D1A78]/70" data-testid="training-version">Version {t.version}{d.current ? " · acknowledged" : ""}</p></div></header>
      <main className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        <p className="text-sm leading-relaxed text-slate-700 md:text-base" data-testid="training-intro">{t.intro}</p>
        {d.reason === "yearly" && <p className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm" data-testid="training-yearly-note">Yearly refresher: you last acknowledged this training on {d.acknowledged_at?.slice(0, 10)}. The content is unchanged; please re-read and re-acknowledge.</p>}
        {d.changes_since?.length > 0 && d.last_version && (
          <div className="mt-4 rounded-xl border border-[#3D1A78]/20 bg-white p-4" data-testid="training-changes">
            <p className="text-sm font-bold">What changed since your last version ({d.last_version})</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">{d.changes_since.flatMap((c) => c.changes.map((x, i) => <li key={c.version + i}><span className="font-mono text-xs text-slate-500">{c.version}</span> — {x}</li>))}</ul>
          </div>
        )}
        <ol className="mt-6 space-y-3" data-testid="training-modules">
          {t.modules.map((m, i) => (
            <li key={m.heading} className="flex gap-4 rounded-2xl border border-[#3D1A78]/10 bg-white p-4 shadow-sm" data-testid={`training-module-${i + 1}`}>
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#3D1A78]/10 text-sm font-bold text-[#3D1A78]">{i + 1}</span>
              <div><p className="text-sm font-bold md:text-base">{m.heading}</p><p className="mt-1 text-sm leading-relaxed text-slate-600">{m.body}</p></div>
            </li>
          ))}
        </ol>
        <label className="mt-6 flex items-start gap-3 rounded-2xl border border-[#3D1A78]/20 bg-white p-4 text-sm" data-testid="training-ack-label">
          <Checkbox checked={ok} onCheckedChange={(v) => setOk(Boolean(v))} data-testid="training-ack-checkbox" />
          <span>{t.acknowledgment}</span>
        </label>
        <Button className="mt-4 bg-[#3D1A78] hover:bg-[#2d1259]" disabled={!ok || busy} onClick={go} data-testid="training-continue-btn"><GraduationCap className="mr-1 h-4 w-4" /> Record acknowledgment and continue</Button>
      </main>
    </div>
  );
}
