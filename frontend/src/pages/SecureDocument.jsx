import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";
import { CodeStep } from "./secureDoc/CodeStep";
import { FilesStep } from "./secureDoc/FilesStep";

const STATUS_COPY = {
  cancelled: "The sender cancelled this document.",
  expired: "This link has expired. Ask the sender to send it again.",
};

export default function SecureDocument() {
  const { token } = useParams();
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  const [grant, setGrant] = useState("");

  useEffect(() => {
    api.get(`/secure-docs/open/${token}`)
      .then((r) => {
        setInfo(r.data);
        if (r.data.status !== "ready") return;
        api.post(`/secure-docs/open/${token}/signed-in`).then((g) => setGrant(g.data.grant)).catch(() => {});
      })
      .catch((e) => setError(e?.response?.data?.detail || "This link isn't valid."));
  }, [token]);

  const blocked = error || (info && STATUS_COPY[info.status]);
  return (
    <main className="min-h-screen bg-[#F8F7FC] px-4 py-12 sm:py-20" data-testid="secure-doc-page">
      <div className="max-w-lg mx-auto">
        <div className="flex items-center gap-2 text-[0.6875rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-4">
          <ShieldCheck size={14} /> SA CoParents · Private document
        </div>
        <section className="rounded-3xl bg-white border border-[#E5E0EE] shadow-sm p-6 sm:p-8">
          {!info && !error && (
            <p className="text-[#6E6787] flex items-center gap-2" data-testid="secure-doc-loading">
              <Loader2 size={16} className="animate-spin" /> Loading…
            </p>
          )}
          {blocked && <p className="text-[#9A3A23] font-semibold" role="alert" data-testid="secure-doc-blocked">{blocked}</p>}
          {info && !blocked && !grant && <CodeStep token={token} info={info} onGrant={setGrant} />}
          {info && !blocked && grant && <FilesStep token={token} info={info} grant={grant} />}
        </section>
        <p className="text-[0.75rem] text-[#6E6787] mt-4 leading-relaxed">
          Documents sent through SA CoParents are never attached to emails. Only the person they were sent to can open them.
        </p>
      </div>
    </main>
  );
}
