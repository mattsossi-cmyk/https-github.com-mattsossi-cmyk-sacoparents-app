import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Download, Save } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const STEPS = [
  { key: "shared_purpose", n: 1, title: "Shared Purpose", hint: "Regardless of what brought your family here, what does your child deserve from both parents?" },
  { key: "vision", n: 2, title: "My Vision for My Child", hint: "The future you want for your child — how you hope they feel and grow." },
  { key: "priorities", n: 3, title: "Parenting Priorities", hint: "One priority per line, e.g. “Protect my child from adult conflict.”", list: true },
  { key: "strengths", n: 4, title: "My Child's Strengths", hint: "What your child is good at, enjoys, and benefits from." },
  { key: "needs", n: 4, title: "My Child's Current Needs", hint: "One need per line, e.g. “Calm transitions.”", list: true },
  { key: "concerns", n: 5, title: "Areas of Concern", hint: "One concern per line, stated without blame.", list: true },
  { key: "child_may_need", n: 6, title: "What My Child May Need", hint: "How these concerns should be addressed, from the child's point of view." },
  { key: "commitments", n: 7, title: "Commitments I Am Making", hint: "One commitment per line, e.g. “Speak respectfully about the other parent in my child's presence.”", list: true },
  { key: "goals", n: 8, title: "Goals for the Next 12 Months", hint: "One goal per line.", list: true },
  { key: "future", n: 9, title: "My Child's Future", hint: "When your child looks back on this period, what do you hope they remember?" },
  { key: "parent_commitment", n: 10, title: "Parent Commitment", hint: "Your one-paragraph Foundation Statement." },
];
const EMPTY = Object.fromEntries(STEPS.map((s) => [s.key, s.list ? [] : ""]));

export default function FoundationEditor() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [f, setF] = useState({ child_name: "", ...EMPTY });
  const [meta, setMeta] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api.get("/foundation/mine").then(({ data }) => { if (data.statement) { setF({ ...EMPTY, ...data.statement.fields }); setMeta(data.statement); } }).catch(() => {});
  }, []);
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.put("/foundation/mine", { fields: f });
      setMeta(data.statement);
      toast.success(data.statement.complete ? "Foundation Statement saved — complete and ready to share." : "Draft saved. Fill in child, shared purpose, vision, priorities, commitments and parent commitment to complete it.");
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  const pdf = `${process.env.REACT_APP_BACKEND_URL}/api/foundation/mine/pdf`;
  return (
    <div className="min-h-screen bg-[#f5f5f7]" data-testid="foundation-editor-page">
      <header className="bg-white border-b border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-3">
          <button onClick={() => navigate("/dashboard")} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground" data-testid="foundation-back-btn"><ArrowLeft className="h-4 w-4" /> Dashboard</button>
          <span className="hidden sm:block"><BrandLogo size="text-xl" /></span>
          <div className="flex flex-wrap gap-2">
            <Link to="/samples/foundation-statement" className="text-sm text-brand-purple underline self-center" data-testid="foundation-sample-link">See the sample</Link>
            <Button variant="outline" size="sm" asChild disabled={!meta} data-testid="foundation-my-pdf-link"><a href={pdf} download aria-disabled={!meta} onClick={(e) => { if (!meta) { e.preventDefault(); toast.error("Save your statement first."); } }}><Download className="h-4 w-4 mr-1" /> Download PDF</a></Button>
            <Button size="sm" onClick={save} disabled={busy} data-testid="foundation-save-btn"><Save className="h-4 w-4 mr-1" /> {busy ? "Saving…" : "Save"}</Button>
          </div>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10 text-[#2d2d34]">
        <div className="rounded-lg overflow-hidden bg-white shadow-sm border border-border">
          <div className="bg-gradient-to-r from-[#2f174f] to-[#4b2a7b] px-8 py-6 text-white"><p className="text-[10px] uppercase tracking-[2px] opacity-85">SA CoParents Parent Report</p><h1 className="font-display text-3xl font-bold mt-1" data-testid="foundation-editor-title">My Child-Focused Foundation Statement</h1><p className="mt-1 text-sm opacity-90">Written by {user?.name || "you"} · private to you until you share it into a case.</p></div>
          <div className="p-6 sm:p-8 space-y-6">
            <div className="rounded-md border-l-4 border-teal-600 bg-[#eaf7f7] p-4 text-sm">Your statement stays private. When a professional invites you to a joint case, you can share it so it appears in the Co-Parenting Agreement and in the professional's case file.</div>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm"><span className="font-medium">Child's name (or initials)</span><input value={f.child_name || ""} onChange={(e) => set("child_name", e.target.value)} className="mt-1 h-10 w-full rounded-md border border-input bg-white px-3 text-sm" data-testid="foundation-child_name" /></label>
              <div className="text-sm"><span className="font-medium">Status</span><p className="mt-2" data-testid="foundation-status">{meta ? (meta.complete ? <span className="rounded-full bg-[#eaf7f1] px-3 py-1 font-semibold text-align-green">Complete</span> : <span className="rounded-full bg-[#fff7df] px-3 py-1 font-semibold text-[#b07d10]">Draft</span>) : <span className="text-muted-foreground">Not started</span>}</p></div>
            </div>
            {STEPS.map((s) => (
              <section key={s.key} data-testid={`foundation-step-${s.key}`}>
                <div className="flex items-center gap-3"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#4b2a7b] text-sm font-bold text-white">{s.n}</span><h2 className="font-display text-lg font-bold text-[#2f174f]">{s.title}</h2></div>
                <p className="mt-1 text-xs text-muted-foreground">{s.hint}</p>
                <Textarea value={s.list ? (f[s.key] || []).join("\n") : (f[s.key] || "")} onChange={(e) => set(s.key, s.list ? e.target.value.split("\n") : e.target.value)} className="mt-2 min-h-[96px] bg-white" data-testid={`foundation-${s.key}`} />
              </section>
            ))}
            <div className="flex justify-end"><Button onClick={save} disabled={busy} data-testid="foundation-save-bottom-btn"><Save className="h-4 w-4 mr-1" /> {busy ? "Saving…" : "Save Foundation Statement"}</Button></div>
          </div>
        </div>
      </main>
    </div>
  );
}
