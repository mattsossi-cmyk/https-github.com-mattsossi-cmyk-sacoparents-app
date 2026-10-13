import { useRef, useState } from "react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

const upload = async (blob, type) => {
  const fd = new FormData();
  fd.append("file", blob, `signature.${type === "image/png" ? "png" : "jpg"}`);
  await api.post("/me/profile/image/signature", fd, { headers: { "Content-Type": "multipart/form-data" } });
  const { data } = await api.get("/me/profile/contact");
  if (!data?.images?.signature) throw new Error("The signature did not save. Please try again.");
};

const hasInk = (canvas) => {
  const px = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data;
  for (let i = 3; i < px.length; i += 4) if (px[i] > 0) return true;
  return false;
};

const toPng = (canvas) => new Promise((res, rej) => {
  const out = document.createElement("canvas");
  out.width = canvas.width; out.height = canvas.height;
  const c = out.getContext("2d");
  c.fillStyle = "#ffffff"; c.fillRect(0, 0, out.width, out.height);
  c.drawImage(canvas, 0, 0);
  out.toBlob((b) => (b ? res(b) : rej(new Error("Could not read the drawing"))), "image/png");
});

export const SignatureCapture = ({ hasSignature, onChanged, testId = "signature-capture" }) => {
  const canvas = useRef(null);
  const drawing = useRef(false);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const pos = (e) => { const r = canvas.current.getBoundingClientRect(); return [(e.clientX - r.left) * (canvas.current.width / r.width), (e.clientY - r.top) * (canvas.current.height / r.height)]; };
  const start = (e) => { e.preventDefault(); canvas.current.setPointerCapture?.(e.pointerId); drawing.current = true; const c = canvas.current.getContext("2d"); c.lineWidth = 3; c.lineCap = "round"; c.lineJoin = "round"; c.strokeStyle = "#1a1a2e"; c.beginPath(); c.moveTo(...pos(e)); c.lineTo(...pos(e)); c.stroke(); setDirty(true); };
  const move = (e) => { if (!drawing.current) return; e.preventDefault(); const c = canvas.current.getContext("2d"); c.lineTo(...pos(e)); c.stroke(); };
  const end = () => { drawing.current = false; };
  const clear = () => { canvas.current.getContext("2d").clearRect(0, 0, canvas.current.width, canvas.current.height); setDirty(false); };
  const run = async (fn, msg) => { setBusy(true); try { await fn(); toast.success(msg); onChanged?.(); } catch (e) { toast.error(e?.response ? formatApiError(e) : e.message); } finally { setBusy(false); } };
  const saveDrawn = () => run(async () => { if (!hasInk(canvas.current)) throw new Error("Draw a signature first"); await upload(await toPng(canvas.current), "image/png"); }, "Signature saved to your profile");
  const saveFile = (e) => { const f = e.target.files?.[0]; if (f) run(() => upload(f, f.type), "Signature uploaded"); e.target.value = ""; };
  const remove = () => run(() => api.delete("/me/profile/image/signature"), "Signature removed");
  return (
    <div className="space-y-2" data-testid={testId}>
      <p className="text-xs text-muted-foreground">Draw with your mouse or finger, or upload an image (JPG/PNG/WebP, 2 MB max). The signature prints on finalized reports only.</p>
      <canvas ref={canvas} width={600} height={180} className="h-28 w-full max-w-md touch-none rounded-md border border-dashed border-border bg-white" data-testid={`${testId}-canvas`}
        onPointerDown={start} onPointerMove={move} onPointerUp={end} onPointerCancel={end} onPointerLeave={end} />
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={saveDrawn} disabled={!dirty || busy} data-testid={`${testId}-save`}>{busy ? "Saving…" : "Save drawn signature"}</Button>
        <Button size="sm" variant="outline" onClick={clear} disabled={busy} data-testid={`${testId}-clear`}>Clear</Button>
        <label className="inline-flex h-9 cursor-pointer items-center rounded-md border border-input bg-white px-3 text-sm font-medium"><input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={saveFile} data-testid={`${testId}-file`} />Upload image</label>
        {hasSignature && <Button size="sm" variant="ghost" onClick={remove} disabled={busy} data-testid={`${testId}-remove`}>Remove saved signature</Button>}
      </div>
    </div>
  );
};
