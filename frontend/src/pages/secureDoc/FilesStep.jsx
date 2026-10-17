import { useEffect, useState } from "react";
import { Download, FileText, Loader2 } from "lucide-react";
import { api } from "../../lib/api";

const kb = (n) => `${Math.max(1, Math.round(n / 1024))} KB`;

export function FilesStep({ token, info, grant }) {
  const [files, setFiles] = useState(null);
  const [busy, setBusy] = useState(null);
  const [msg, setMsg] = useState("");
  const headers = { "X-Doc-Grant": grant };

  useEffect(() => {
    api.get(`/secure-docs/open/${token}/files`, { headers })
      .then((r) => setFiles(r.data))
      .catch((e) => setMsg(e?.response?.data?.detail || "Couldn't load the document."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, grant]);

  const download = async (f) => {
    setBusy(f.index); setMsg("");
    try {
      const r = await api.get(`/secure-docs/open/${token}/files/${f.index}`, { headers, responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url; a.download = f.name; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch { setMsg("Couldn't download the file. Please try again."); }
    finally { setBusy(null); }
  };

  return (
    <div data-testid="secure-doc-files-step">
      <h1 className="font-serif text-3xl text-[#1A1330] leading-tight">From {info.sender_name}</h1>
      <p className="text-[#4B4567] mt-3">Please keep this private. Don&rsquo;t forward it.</p>
      {!files && !msg && <Loader2 size={18} className="animate-spin text-[#6E6787] mt-6" />}
      <ul className="mt-6 space-y-3" data-testid="secure-doc-file-list">
        {(files || []).map((f) => (
          <li key={f.index} className="flex items-center justify-between gap-3 rounded-2xl border border-[#E5E0EE] bg-[#F8F7FC] px-4 py-3">
            <span className="flex items-center gap-2 min-w-0 text-sm text-[#1A1330]">
              <FileText size={16} className="text-[#3D1A78] shrink-0" />
              <span className="truncate" data-testid={`secure-doc-file-name-${f.index}`}>{f.name}</span>
              <span className="text-[0.6875rem] text-[#6E6787] shrink-0">{kb(f.size)}</span>
            </span>
            <button type="button" onClick={() => download(f)} disabled={busy === f.index}
              className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-xs font-semibold shrink-0 disabled:opacity-50"
              data-testid={`secure-doc-download-${f.index}`}>
              {busy === f.index ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />} Download
            </button>
          </li>
        ))}
      </ul>
      {msg && <p className="text-sm text-[#9A3A23] mt-4" role="alert" data-testid="secure-doc-files-error">{msg}</p>}
    </div>
  );
}
