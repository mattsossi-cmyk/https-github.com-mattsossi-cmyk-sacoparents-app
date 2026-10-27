import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, Download, Save, Share2 } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/Brand";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { AiPrivacyWarning } from "@/components/AiPrivacyWarning";
import { WorkflowGuide } from "@/components/WorkflowGuide";
import { ListenButton } from "@/components/ListenButton";
import { FoundationAttachments } from "@/components/FoundationAttachments";
import { WellnessTemplatePicker } from "@/components/WellnessTemplatePicker";

const STEPS = [
  { key: "shared_purpose", n: 1, title: "Shared Purpose", hint: "Regardless of what brought your family here, what does your child deserve from both parents?" },
  { key: "vision", n: 2, title: "My Vision for My Child", hint: "The future you want for your child — how you hope they feel and grow." },
  { key: "priorities", n: 3, title: "Parenting Priorities", hint: "One priority per line, e.g. “Protect my child from adult conflict.”", list: true },
  { key: "strengths", n: 4, title: "My Child's Strengths", hint: "What your child is good at, enjoys, and benefits from." },
  { key: "needs", n: 4, title: "My Child's Current Needs", hint: "One need per line, e.g. “Calm transitions.”", list: true },
  { key: "concerns", n: 5, title: "Areas of Concern", hint: "One concern per line, stated without blame.", list: true },
  { key: "wellness_tech", n: 6, title: "Wellness, Phones & Social Media", hint: "One item per line: your child's sleep, meals, activity and emotional wellness, and their access to smartphones, social media, games and screens — what you hope both homes can agree on, stated without blame.", list: true },
  { key: "child_may_need", n: 7, title: "What My Child May Need", hint: "How these concerns should be addressed, from the child's point of view." },
  { key: "commitments", n: 8, title: "Commitments I Am Making", hint: "One commitment per line, e.g. “Speak respectfully about the other parent in my child's presence.”", list: true },
  { key: "goals", n: 9, title: "Goals for the Next 12 Months", hint: "One goal per line.", list: true },
  { key: "future", n: 10, title: "My Child's Future", hint: "When your child looks back on this period, what do you hope they remember?" },
  { key: "parent_commitment", n: 11, title: "Parent Commitment", hint: "Your one-paragraph Foundation Statement." },
];
const EMPTY = Object.fromEntries(STEPS.map((s) => [s.key, s.list ? [] : ""]));

export default function FoundationEditor() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const caseId = search.get("case");
  const [f, setF] = useState({ child_name: "", ...EMPTY });
  const [meta, setMeta] = useState(null);
  const [safety, setSafety] = useState({});
  const [safetyQs, setSafetyQs] = useState([]);
  const safetyFlagged = Object.values(safety).some((v) => v === true);
  const safetyComplete = safetyQs.length > 0 && safetyQs.every((q) => typeof safety[q.key] === "boolean");
  const [busy, setBusy] = useState(false);
  const [shared, setShared] = useState(false);
  const [blame, setBlame] = useState(null);
  const [voice, setVoice] = useState(() => localStorage.getItem("tts_voice") || "sage");
  const [rate, setRate] = useState(() => Number(localStorage.getItem("tts_rate")) || 1);
  const checkBlame = async () => {
    const lines = (f.concerns || []).filter((x) => x.trim());
    if (!lines.length) return true;
    try {
      const { data } = await api.post("/foundation/mine/blame-check", { lines });
      const flagged = data.results.filter((r) => r.focus === "blaming" && r.confidence >= 0.6);
      setBlame(flagged);
      return flagged.length === 0;
    } catch { return true; }
  };
  const shareToCase = async () => {
    setBusy(true);
    try { await api.post(`/joint/reports/${caseId}/foundation/share`); setShared(true); toast.success("Shared into your case. The professional can now see it."); }
    catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  useEffect(() => {
    api.get("/foundation/mine").then(({ data }) => { setSafetyQs(data.safety_questions || []); if (data.statement) { setSafety(data.statement.safety || {}); setF({ ...EMPTY, ...data.statement.fields }); setMeta(data.statement); } }).catch(() => {});
  }, []);
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const save = async (force = false) => {
    setBusy(true);
    try {
      if (!force && blame === null && !(await checkBlame())) { toast.info("Some concerns read as blaming the other parent — see the suggestions, or save anyway."); return; }
      const { data } = await api.put("/foundation/mine", { fields: f, safety });
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
            <Button size="sm" onClick={() => save()} disabled={busy} data-testid="foundation-save-btn"><Save className="h-4 w-4 mr-1" /> {busy ? "Saving…" : "Save"}</Button>
          </div>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10 text-[#2d2d34]">
        <AiPrivacyWarning testId="ai-privacy-warning-foundation" />
        <div className="rounded-lg overflow-hidden bg-white shadow-sm border border-border">
          <div className="bg-gradient-to-r from-[#2f174f] to-[#4b2a7b] px-8 py-6 text-white"><p className="text-[10px] uppercase tracking-[2px] opacity-85">SA CoParents Parent Report</p><h1 className="font-display text-3xl font-bold mt-1" data-testid="foundation-editor-title">My Child-Focused Foundation Statement</h1><p className="mt-1 text-sm opacity-90">Written by {user?.name || "you"} · private to you until you share it into a case.</p></div>
          <div className="p-6 sm:p-8 space-y-6">
            <WorkflowGuide kind="foundation" />
            <div className="rounded-md border-l-4 border-teal-600 bg-[#eaf7f7] p-4 text-sm">Your statement stays private. When a professional invites you to a joint case, you can share it so it appears in the Co-Parenting Agreement and in the professional's case file.</div>
            <section className="rounded-lg border border-[#f0d78a] bg-[#fff7df] p-4" data-testid="foundation-safety-screen">
              <p className="text-xs font-bold uppercase tracking-widest text-[#b07d10]">Safety first — private to you</p>
              <p className="mt-1 text-sm">Three quick questions before anything is shared. Your answers are never shown to the other parent.</p>
              <div className="mt-3 space-y-3">
                {safetyQs.map((q) => (
                  <div key={q.key} className="flex flex-wrap items-center justify-between gap-2 text-sm" data-testid={`foundation-safety-${q.key}`}>
                    <span className="flex-1 min-w-[200px]">{q.text}</span>
                    <div className="flex gap-2">{[["No", false], ["Yes", true]].map(([l, v]) => <button key={l} type="button" onClick={() => setSafety((x) => ({ ...x, [q.key]: v }))} className={`rounded-full border px-3 py-1 text-xs font-semibold ${safety[q.key] === v ? (v ? "bg-[#b07d10] text-white border-[#b07d10]" : "bg-align-green text-white border-align-green") : "bg-white border-border"}`} data-testid={`foundation-safety-${q.key}-${l.toLowerCase()}`}>{l}</button>)}</div>
                  </div>
                ))}
              </div>
              {safetyFlagged && <div className="mt-3 rounded-md border border-[#e0b04a] bg-white p-3 text-sm" data-testid="foundation-safety-route"><strong className="text-[#b07d10]">Safety pathway.</strong> Your statement stays private and will not be shared into a joint agreement. Your professional will use the Family Violence / Safety pathway with safeguards (written-only communication, neutral exchanges). If you are in immediate danger call 911; the National Domestic Violence Hotline is 1-800-799-7233.</div>}
            </section>
            {caseId && <div className="rounded-md border border-brand-purple/30 bg-[#f3edfb] p-4 text-sm flex flex-wrap items-center justify-between gap-3" data-testid="foundation-case-share-block"><span>{safetyFlagged ? "Sharing is paused because of your safety answers — your professional is notified to use the safety pathway." : shared ? "Shared into your case — you can re-share after edits." : "This statement was requested for one of your cases. Answer the safety questions, save, then share it into the case."}</span><Button size="sm" onClick={shareToCase} disabled={busy || !meta?.complete || !safetyComplete || safetyFlagged} data-testid="foundation-case-share-btn"><Share2 className="h-4 w-4 mr-1" /> {shared ? "Re-share" : "Share into case"}</Button></div>}
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm"><span className="font-medium">Child's name (or initials)</span><input value={f.child_name || ""} onChange={(e) => set("child_name", e.target.value)} className="mt-1 h-10 w-full rounded-md border border-input bg-white px-3 text-sm" data-testid="foundation-child_name" /></label>
              <div className="text-sm"><span className="font-medium">Status</span><p className="mt-2" data-testid="foundation-status">{meta ? (meta.complete ? <span className="rounded-full bg-[#eaf7f1] px-3 py-1 font-semibold text-align-green">Complete</span> : <span className="rounded-full bg-[#fff7df] px-3 py-1 font-semibold text-[#b07d10]">Draft</span>) : <span className="text-muted-foreground">Not started</span>}</p></div>
            </div>
            {STEPS.map((s) => (
              <section key={s.key} data-testid={`foundation-step-${s.key}`}>
                <div className="flex items-center gap-3"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#4b2a7b] text-sm font-bold text-white">{s.n}</span><h2 className="font-display text-lg font-bold text-[#2f174f] flex-1">{s.title}</h2><ListenButton text={`${s.title}. ${s.hint}`} label="Listen" variant="ghost" voice={voice} rate={rate} testId={`foundation-listen-${s.key}`} /></div>
                <p className="mt-1 text-xs text-muted-foreground">{s.hint}</p>
                <Textarea value={s.list ? (f[s.key] || []).join("\n") : (f[s.key] || "")} onChange={(e) => { set(s.key, s.list ? e.target.value.split("\n") : e.target.value); if (s.key === "concerns") setBlame(null); }} className="mt-2 min-h-[96px] bg-white" data-testid={`foundation-${s.key}`} />
                {s.key === "wellness_tech" && <WellnessTemplatePicker testIdPrefix="foundation-wellness-template" onPick={(t) => { set("wellness_tech", [...(f.wellness_tech || []).filter((l) => l.trim()), ...t.lines]); toast.success(`“${t.title}” added — edit the lines to fit your child.`); }} />}
                {s.key === "concerns" && blame?.length > 0 && (
                  <div className="mt-2 rounded-md border-l-4 border-amber-500 bg-amber-50 p-3 text-sm" data-testid="foundation-blame-nudge">
                    <p className="font-semibold">Try rephrasing from your child's point of view:</p>
                    <ul className="mt-1 list-disc pl-5 text-xs">{blame.map((b) => <li key={b.index} data-testid={`foundation-blame-line-${b.index}`}>“{b.line}” — describe what your child needs or experiences instead of the other parent's behavior or motives.</li>)}</ul>
                    <div className="mt-2 flex gap-2"><Button size="sm" variant="outline" onClick={() => setBlame(null)} data-testid="foundation-blame-edit-btn">I'll rephrase</Button><Button size="sm" variant="ghost" onClick={() => save(true)} data-testid="foundation-blame-save-anyway-btn">Save anyway</Button></div>
                  </div>
                )}
              </section>
            ))}
            <FoundationAttachments />
            <div className="rounded-lg border border-border bg-white p-4" data-testid="foundation-listen-panel">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div><p className="text-sm font-bold text-[#2f174f]">Hear it before you share it</p><p className="text-xs text-muted-foreground">Listening to your own words often reveals what sounds blaming or unclear. Nothing is shared.</p></div>
                <ListenButton key={`${voice}-${rate}`} voice={voice} rate={rate} text={STEPS.map((s) => `${s.title}. ${s.list ? (f[s.key] || []).filter(Boolean).join(". ") : (f[s.key] || "")}`).filter((t) => t.split(". ").slice(1).join("").trim()).join(" ")} label="Read my statement aloud" testId="foundation-listen-all" />
              </div>
              <div className="mt-3 flex flex-wrap gap-4 text-xs">
                <label className="flex items-center gap-2">Voice
                  <select value={voice} onChange={(e) => { setVoice(e.target.value); localStorage.setItem("tts_voice", e.target.value); }} className="h-8 rounded-md border border-input bg-white px-2 text-sm" data-testid="foundation-voice-select">
                    <option value="sage">Calm (Sage)</option><option value="coral">Warm (Coral)</option><option value="nova">Bright (Nova)</option><option value="echo">Steady (Echo)</option>
                  </select>
                </label>
                <label className="flex items-center gap-2">Speed
                  <select value={rate} onChange={(e) => { setRate(Number(e.target.value)); localStorage.setItem("tts_rate", e.target.value); }} className="h-8 rounded-md border border-input bg-white px-2 text-sm" data-testid="foundation-speed-select">
                    <option value={0.8}>Slower (0.8×)</option><option value={1}>Normal (1×)</option><option value={1.2}>Faster (1.2×)</option>
                  </select>
                </label>
              </div>
            </div>
            <div className="flex justify-end"><Button onClick={() => save()} disabled={busy} data-testid="foundation-save-bottom-btn"><Save className="h-4 w-4 mr-1" /> {busy ? "Saving…" : "Save Foundation Statement"}</Button></div>
          </div>
        </div>
      </main>
    </div>
  );
}
