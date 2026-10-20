import React, { useEffect, useRef, useState } from "react";
import { Copy, KeyRound, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";
import { NotAvailableNote } from "../NotAvailableNote";

const ALIGN_SITE = "sacoparentsalign.com";
const mmss = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

function CodePanel({ code, left }) {
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      toast.success("Code copied.");
    } catch {
      toast.error("Couldn't copy. Please write the code down.");
    }
  };
  return (
    <div data-testid="align-link-code-panel" className="order-last basis-full mt-1 rounded-2xl border border-[#D9CCF0] bg-[#F8F5FD] p-4">
      <div className="flex flex-wrap items-center gap-3">
        <span data-testid="align-link-code" className="font-mono text-2xl font-bold tracking-[0.25em] text-[#2A0F5F] select-all">{code}</span>
        <button type="button" data-testid="align-link-code-copy" onClick={copy} className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#D9CCF0] px-3 py-1.5 text-xs font-bold text-[#3D1A78] hover:bg-[#F1EAFB]">
          <Copy size={12} /> Copy
        </button>
      </div>
      <p className="text-xs text-[#4B4567] mt-2 leading-relaxed">
        Type this code on{" "}
        <a href={`https://${ALIGN_SITE}`} target="_blank" rel="noopener noreferrer" data-testid="align-link-site" className="font-semibold text-[#3D1A78] underline">{ALIGN_SITE}</a>{" "}
        within <span data-testid="align-link-code-timer" className="font-semibold">{mmss(left)}</span>. It works once. We&rsquo;ll show &ldquo;Linked&rdquo; here when Align has used it.
      </p>
    </div>
  );
}

// "Get a link code" button + the code panel. Polls the link status while a code is showing.
export function AlignLinkCode({ onPoll }) {
  const [code, setCode] = useState(null);
  const [left, setLeft] = useState(0);
  const [busy, setBusy] = useState(false);
  const [blocked, setBlocked] = useState(null);
  const mintedAt = useRef(0);

  const mint = async () => {
    setBusy(true);
    setBlocked(null);
    try {
      const { data } = await api.post("/link-codes", { context: "account" });
      mintedAt.current = Date.now() - 2000;
      setCode(data);
    } catch (e) {
      const d = e?.response?.data?.detail;
      if (d?.code === "not_available") setBlocked(d);
      else toast.error("Couldn't create a code. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!code) return undefined;
    const tick = () => {
      const s = Math.max(0, Math.round((new Date(code.expires_at) - Date.now()) / 1000));
      setLeft(s);
      if (!s) setCode(null);
    };
    tick();
    const t = setInterval(tick, 1000);
    const p = setInterval(async () => {
      const st = await onPoll();
      if (st?.linked_at && new Date(st.linked_at).getTime() >= mintedAt.current) {
        setCode(null);
        toast.success("SA CoParents Align is linked.");
      }
    }, 8000);
    return () => { clearInterval(t); clearInterval(p); };
  }, [code, onPoll]);

  return (
    <>
      <button type="button" data-testid="align-get-code-button" onClick={mint} disabled={busy} className="shrink-0 inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] text-white px-4 py-2 text-xs font-bold hover:bg-[#2A0F5F] disabled:opacity-60">
        {busy ? <Loader2 size={12} className="animate-spin" /> : <KeyRound size={12} />}
        {code ? "New code" : "Get a link code"}
      </button>
      {code && <CodePanel code={code.code} left={left} />}
      {blocked && <NotAvailableNote testid="align-link-code-blocked" className="order-last basis-full mt-1" />}
    </>
  );
}
