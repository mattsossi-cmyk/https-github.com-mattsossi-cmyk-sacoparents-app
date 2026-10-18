import React, { useEffect, useRef, useState } from "react";

import { api } from "../../lib/api";

const POLL_MS = 2000;
const POLL_TRIES = 15;

const selfMessage = (r) => {
  if (r.ok) return { tone: "ok", text: `This side works. Our webhook accepted a signed test message in ${r.round_trip_ms} ms.` };
  if (r.reason === "not_configured") return { tone: "warn", text: "This app's webhook secret or public address isn't set." };
  if (r.reason === "refused_signature") return { tone: "warn", text: "Our webhook refused the test message. Check that ALIGN_WEBHOOK_SECRET is set on this app." };
  return { tone: "warn", text: `Couldn't confirm our webhook at ${r.webhook_url}${r.status_code ? ` (status ${r.status_code})` : ""}.` };
};

function Result({ msg, testid }) {
  if (!msg) return null;
  const tone = msg.tone === "ok" ? "border-emerald-200 bg-emerald-50 text-emerald-900" : msg.tone === "wait" ? "border-[#E5E0EE] bg-[#F8F7FC] text-[#3B3552]" : "border-amber-200 bg-amber-50 text-[#7A4A00]";
  return <p role="status" data-testid={testid} className={`mt-2 rounded-xl border px-3 py-2 text-sm ${tone}`}>{msg.text}</p>;
}

// Two link checks: our own webhook right now, and a round trip that asks Align to send a test message back.
export function AlignTestButtons({ onDone }) {
  const [selfMsg, setSelfMsg] = useState(null);
  const [alignMsg, setAlignMsg] = useState(null);
  const [busy, setBusy] = useState("");
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);

  const checkSelf = async () => {
    setBusy("self");
    setSelfMsg({ tone: "wait", text: "Sending a signed test message to our webhook…" });
    try {
      setSelfMsg(selfMessage((await api.post("/admin/safety-audit-log/self-test")).data));
      onDone();
    } catch {
      setSelfMsg({ tone: "warn", text: "Couldn't run the check. Please try again." });
    }
    setBusy("");
  };

  const waitForAlign = async (testId) => {
    for (let i = 0; i < POLL_TRIES && alive.current; i += 1) {
      await new Promise((r) => setTimeout(r, POLL_MS));
      const { data } = await api.get(`/admin/safety-audit-log/test-status/${testId}`);
      if (data.received) {
        const secs = data.round_trip_ms == null ? "" : ` after ${(data.round_trip_ms / 1000).toFixed(1)} s`;
        return { tone: "ok", text: `Align's test message arrived${secs}. The link works both ways.` };
      }
    }
    return { tone: "warn", text: "Align accepted the request, but no test message came back within 30 seconds." };
  };

  const askAlign = async () => {
    setBusy("align");
    setAlignMsg({ tone: "wait", text: "Asking Align for a test message…" });
    try {
      const { data } = await api.post("/admin/safety-audit-log/align-ping");
      if (!data.configured) setAlignMsg({ tone: "warn", text: "Align's test address isn't set up yet." });
      else if (data.reason === "unreachable") setAlignMsg({ tone: "warn", text: "Couldn't reach Align's test address." });
      else if (!data.accepted) setAlignMsg({ tone: "warn", text: `Align didn't accept the request (status ${data.status_code}). Check Align's test address and that both apps share the same secret.` });
      else {
        setAlignMsg({ tone: "wait", text: "Align accepted. Waiting for its test message…" });
        setAlignMsg(await waitForAlign(data.test_id));
        onDone();
      }
    } catch (e) {
      setAlignMsg({ tone: "warn", text: e?.response?.status === 429 ? "Please wait a few seconds before asking again." : "Couldn't run the check. Please try again." });
    }
    setBusy("");
  };

  const btn = "inline-flex min-h-6 items-center rounded-full px-4 py-2 text-xs font-bold transition-colors disabled:opacity-60";
  return (
    <div className="mt-3 border-t border-[#F0EDF6] pt-3" data-testid="align-test-buttons">
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={checkSelf} disabled={!!busy} data-testid="align-self-test-btn" className={`${btn} border border-[#D9D3EA] bg-white text-[#3D1A78] hover:bg-[#F8F7FC]`}>
          {busy === "self" ? "Checking…" : "Check this side"}
        </button>
        <button type="button" onClick={askAlign} disabled={!!busy} data-testid="align-ping-btn" className={`${btn} bg-[#3D1A78] text-white hover:bg-[#2A0F5F]`}>
          {busy === "align" ? "Waiting for Align…" : "Ask Align for a test"}
        </button>
      </div>
      <Result msg={selfMsg} testid="align-self-test-result" />
      <Result msg={alignMsg} testid="align-ping-result" />
      <p className="mt-2 text-xs text-[#4B4567]">Test messages never change a case and aren&apos;t counted as updates.</p>
    </div>
  );
}
