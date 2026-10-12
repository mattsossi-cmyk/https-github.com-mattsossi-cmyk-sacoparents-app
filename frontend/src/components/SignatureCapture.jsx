import { useRef, useState } from "react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const upload = async (blob, type) => {
  const fd = new FormData();
  fd.append("file", blob, `signature.${type === "image/png" ? "png" : "jpg"}`);
  await api.post("/me/profile/image/signature", fd, { headers: { "Content-Type": "multipart/form-data" } });
};

export const SignatureCapture = ({ hasSignature, onChanged, testId = "signature-capture" }) => {
  const canvas = useRef(null);
  const drawing = useRef(false);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const pos = (e) => { const r = canvas.current.getBoundingClientRect(); const t = e.touches?.[0] || e; return [(t.clientX - r.left) * (canvas.current.width / r.width), (t.clientY - r.top) * (canvas.current.height / r.height)]; };
  const start = (e) => { drawing.current = true; const c = canvas.current.getContext("2d"); c.lineWidth = 3; c.lineCap = "round"; c.strokeStyle = "#1a1a2e"; c.beginPath(); c.moveTo(...pos(e)); };
  const move = (e) => { if (!drawing.current) return; e.preventDefault(); const c = canvas.current.getContext("2d"); c.lineTo(...pos(e)); c.stroke(); setDirty(true); };
  const end = () => { drawing.current = false; };
  const clear = () => { canvas.current.getContext("2d").clearRect(0, 0, canvas.current.width, canvas.current.height); setDirty(false); };
  const run = async (fn, msg) => { setBusy(true); try { await fn(); toast.success(msg); onChanged?.(); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); } };
  const saveDrawn = () => run(() => new Promise((res, rej) => canvas.current.toBlob((b) => (b ? upload(b, "image/png").then(res, rej) : rej(new Error("Draw a signature first"))), "image/png")), "Signature saved to your profile");
  const saveFile = (e) => { const f = e.target.files?.[0]; if (f) run(() => upload(f, f.type), "Signature uploaded"); e.target.value = ""; };
  const remove = () => run(() => api.delete("/me/profile/image/signature"), "Signature removed");
  return (
    <div className="space-y-2" data-testid={testId}>
      <p className="text-xs text-muted-foreground">Draw with your mouse or finger, or upload an image (JPG/PNG/WebP, 2 MB max). The signature prints on finalized reports only.</p>
      <canvas ref={canvas} width={600} height={180} className="h-28 w-full max-w-md touch-none rounded-md border border-dashed border-border bg-white" data-testid={`${testId}-canvas`}
        onMouseDown={start} onMouseMove={move} onMouseUp={end} onMouseLeave={end} onTouchStart={start} onTouchMove={move} onTouchEnd={end} />
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={saveDrawn} disabled={!dirty || busy} data-testid={`${testId}-save`}>Save drawn signature</Button>
        <Button size="sm" variant="outline" onClick={clear} disabled={busy} data-testid={`${testId}-clear`}>Clear</Button>
        <label className="inline-flex h-9 cursor-pointer items-center rounded-md border border-input bg-white px-3 text-sm font-medium"><input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={saveFile} data-testid={`${testId}-file`} />Upload image</label>
        {hasSignature && <Button size="sm" variant="ghost" onClick={remove} disabled={busy} data-testid={`${testId}-remove`}>Remove saved signature</Button>}
      </div>
    </div>
  );
};
