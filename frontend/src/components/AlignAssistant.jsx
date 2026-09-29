import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Bot, Send, X, Sparkles, FileText } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const sessionKey = (uid) => `align-assistant-session-${uid}`;
const getSession = (uid) => { const k = sessionKey(uid); let s = localStorage.getItem(k); if (!s) { s = crypto.randomUUID(); localStorage.setItem(k, s); } return s; };

const DRAFT_RE = /\[\[DRAFT section=([a-z_]+)\]\]\s*([\s\S]*?)\s*(?:\[\[\/DRAFT\]\]|$)/g;
const splitDrafts = (text) => { const out = []; let last = 0; for (const m of text.matchAll(DRAFT_RE)) { if (m.index > last) out.push({ text: text.slice(last, m.index) }); out.push({ field: m[1], text: m[2] }); last = m.index + m[0].length; } if (last < text.length) out.push({ text: text.slice(last) }); return out; };

const DraftCard = ({ part, caseId, sections, streaming }) => {
  const [state, setState] = useState(null);
  const insert = async () => {
    setState("busy");
    try { const { data } = await api.post("/assistant/insert-draft", { case_id: caseId, field: part.field, text: part.text }); setState({ url: data.editor_url, label: data.label }); toast.success(`Draft placed in ${data.label} — review it in the editor`); }
    catch (e) { setState(null); toast.error(formatApiError(e)); }
  };
  return (
    <div className="mt-2 rounded-lg border border-brand-blue/40 bg-white p-2" data-testid={`assistant-draft-${part.field}`}>
      <p className="text-[11px] font-bold uppercase tracking-widest text-brand-blue">Draft · {sections[part.field] || part.field}</p>
      <p className="mt-1 whitespace-pre-wrap text-sm">{part.text}</p>
      {!streaming && caseId && (state?.url ? (
        <Link to={state.url} className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-brand-blue hover:underline" data-testid={`assistant-draft-${part.field}-open`}><FileText className="h-3.5 w-3.5" /> Inserted — open {state.label} in the editor →</Link>
      ) : (
        <button type="button" onClick={insert} disabled={state === "busy"} className="mt-2 inline-flex items-center gap-1 rounded-full bg-brand-blue px-3 py-1 text-xs font-semibold text-white hover:bg-brand-blue/90 disabled:opacity-60" data-testid={`assistant-draft-${part.field}-insert`}><FileText className="h-3.5 w-3.5" /> {state === "busy" ? "Inserting…" : "Insert into Professional Report for review"}</button>
      ))}
    </div>
  );
};

const Msg = ({ m, caseId, sections, streaming }) => {
  if (m.role === "user") return <div className="ml-auto max-w-[90%] whitespace-pre-wrap rounded-xl bg-brand-purple px-3 py-2 text-white" data-testid="assistant-msg-user">{m.content}</div>;
  const parts = splitDrafts(m.content || "");
  return <div className="max-w-[90%] rounded-xl bg-secondary/70 px-3 py-2" data-testid="assistant-msg-assistant">{parts.map((p, i) => p.field ? <DraftCard key={i} part={p} caseId={caseId} sections={sections} streaming={streaming} /> : <span key={i} className="whitespace-pre-wrap">{p.text}</span>)}{!m.content && streaming ? "…" : ""}</div>;
};

export const AlignAssistant = ({ userId, caseId, caseLabel, trigger, open, onOpenChange }) => {
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [chips, setChips] = useState({});
  const [sections, setSections] = useState({});
  const [chip, setChip] = useState(null);
  const session = getSession(userId);
  const endRef = useRef(null);

  useEffect(() => { api.get("/assistant/history", { params: { session_id: session } }).then((r) => setMsgs(r.data)).catch(() => {}); api.get("/assistant/triggers").then((r) => setChips(r.data)).catch(() => {}); api.get("/assistant/draft-sections").then((r) => setSections(r.data)).catch(() => {}); }, [session]);
  useEffect(() => { if (trigger?.key && chips[trigger.key]) { setChip(trigger.key); if (trigger.mode === "click") onOpenChange(true); } }, [trigger, chips]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, open]);

  const send = async (text) => {
    const t = (text || input).trim();
    if (!t || busy) return;
    setInput(""); setChip(null); setBusy(true);
    setMsgs((m) => [...m, { role: "user", content: t }, { role: "assistant", content: "" }]);
    try {
      const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/assistant/chat`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: session, message: t, case_id: caseId || null }) });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
      const reader = res.body.getReader(); const dec = new TextDecoder(); let buf = "";
      for (;;) {
        const { value, done } = await reader.read(); if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split("\n\n"); buf = lines.pop();
        for (const l of lines) {
          if (!l.startsWith("data: ")) continue;
          const ev = JSON.parse(l.slice(6));
          if (ev.delta || ev.error) setMsgs((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", content: c[c.length - 1].content + (ev.delta || ev.error) }; return c; });
        }
      }
    } catch (e) {
      setMsgs((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", content: `Assistant unavailable: ${e.message}` }; return c; });
    } finally { setBusy(false); }
  };

  return (
    <>
      {!open && (
        <button type="button" onClick={() => onOpenChange(true)} className="fixed bottom-5 right-5 z-40 inline-flex items-center gap-2 rounded-full bg-brand-purple px-4 py-3 text-sm font-semibold text-white shadow-xl transition-transform hover:scale-105" data-testid="assistant-open-btn">
          <Bot className="h-5 w-5" /> Align Assistant{chip && <span className="ml-1 h-2 w-2 rounded-full bg-align-yellow animate-pulse" data-testid="assistant-chip-dot" />}
        </button>
      )}
      {open && (
        <aside className="fixed bottom-0 right-0 z-40 flex h-[min(80vh,640px)] w-full flex-col rounded-t-2xl border border-border bg-white shadow-2xl sm:bottom-5 sm:right-5 sm:w-[400px] sm:rounded-2xl" data-testid="assistant-panel">
          <header className="flex items-center justify-between gap-2 rounded-t-2xl bg-brand-purple px-4 py-3 text-white">
            <div className="flex items-center gap-2 min-w-0"><Bot className="h-5 w-5 shrink-0" /><div className="min-w-0"><p className="text-sm font-bold leading-tight">Align Assistant</p><p className="truncate text-[11px] opacity-80" data-testid="assistant-case-label">{caseLabel ? `Case ${caseLabel}` : "No case selected"} · advisory only</p></div></div>
            <button type="button" onClick={() => onOpenChange(false)} className="rounded-md p-1 hover:bg-white/15" aria-label="Close assistant" data-testid="assistant-close-btn"><X className="h-4 w-4" /></button>
          </header>
          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3 text-sm" data-testid="assistant-messages">
            {msgs.length === 0 && <p className="rounded-lg bg-secondary/60 p-3 text-xs text-muted-foreground" data-testid="assistant-empty">Ask about intake status, the alignment delta (Agreed / Minor Gap / High Discrepancy), pathway options or memo drafts for the selected case. Everything here is a suggestion for your review — nothing is filed or decided by the assistant.</p>}
            {msgs.map((m, i) => <Msg key={i} m={m} caseId={caseId} sections={sections} streaming={busy && i === msgs.length - 1} />)}
            <div ref={endRef} />
          </div>
          {chip && chips[chip] && (
            <button type="button" onClick={() => send(chips[chip])} className="mx-4 mb-2 flex items-start gap-2 rounded-lg border border-align-yellow/60 bg-align-yellow/15 p-2 text-left text-xs hover:bg-align-yellow/30" data-testid={`assistant-chip-${chip}`}>
              <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-yellow-800" /><span>{chips[chip]}</span>
            </button>
          )}
          <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex gap-2 border-t border-border p-3">
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder={caseId ? "Ask about this case…" : "Select a case above, or ask a general question…"} className="h-10 flex-1 rounded-md border border-input px-3 text-sm" data-testid="assistant-input" />
            <Button type="submit" size="sm" disabled={busy || !input.trim()} className="h-10 bg-brand-purple text-white hover:bg-brand-purple/90" data-testid="assistant-send-btn"><Send className="h-4 w-4" /></Button>
          </form>
        </aside>
      )}
    </>
  );
};
