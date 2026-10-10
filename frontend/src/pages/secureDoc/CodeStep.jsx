import { useState } from "react";
import { Loader2, Mail } from "lucide-react";
import { api } from "../../lib/api";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "../../components/ui/input-otp";

const btn = "inline-flex items-center justify-center gap-2 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-5 py-2.5 text-sm font-semibold transition-colors disabled:opacity-50";
const errText = (e, fallback) => e?.response?.data?.detail || fallback;

export function CodeStep({ token, info, onGrant }) {
  const [sent, setSent] = useState(false);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const sendCode = async () => {
    setBusy(true); setMsg("");
    try { await api.post(`/secure-docs/open/${token}/code`); setSent(true); setCode(""); }
    catch (e) { setMsg(errText(e, "We couldn't send the code. Please try again.")); }
    finally { setBusy(false); }
  };
  const verify = async () => {
    setBusy(true); setMsg("");
    try { const r = await api.post(`/secure-docs/open/${token}/verify`, { code }); onGrant(r.data.grant); }
    catch (e) { setCode(""); setMsg(errText(e, "That code didn't work. Please try again.")); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="secure-doc-code-step">
      <h1 className="font-serif text-3xl text-[#1A1330] leading-tight" data-testid="secure-doc-title">
        {info.sender_name} sent you a document
      </h1>
      <p className="text-[#4B4567] mt-3 leading-relaxed">
        To keep it private, we&rsquo;ll email a one-time code to <strong data-testid="secure-doc-masked-email">{info.masked_email}</strong>.
      </p>
      {!sent ? (
        <button type="button" onClick={sendCode} disabled={busy} className={`${btn} mt-6`} data-testid="secure-doc-send-code-btn">
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Mail size={15} />} Email me a code
        </button>
      ) : (
        <div className="mt-6 space-y-4">
          <p className="text-sm text-[#4B4567]" data-testid="secure-doc-code-sent">Code sent. It expires in 10 minutes.</p>
          <InputOTP maxLength={6} value={code} onChange={setCode} autoFocus data-testid="secure-doc-code-input">
            <InputOTPGroup>
              {[0, 1, 2, 3, 4, 5].map((i) => <InputOTPSlot key={i} index={i} className="h-12 w-11 text-lg" />)}
            </InputOTPGroup>
          </InputOTP>
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" onClick={verify} disabled={busy || code.length !== 6} className={btn} data-testid="secure-doc-verify-btn">
              {busy && <Loader2 size={15} className="animate-spin" />} Open document
            </button>
            <button type="button" onClick={sendCode} disabled={busy} className="text-sm font-semibold text-[#3D1A78] hover:underline" data-testid="secure-doc-resend-code-btn">
              Send a new code
            </button>
          </div>
        </div>
      )}
      {msg && <p className="text-sm text-[#9A3A23] mt-4" role="alert" data-testid="secure-doc-error">{msg}</p>}
    </div>
  );
}
