import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Download, Loader2, ArrowUpRight, ExternalLink, Share2 } from "lucide-react";
import { toast } from "sonner";
import { FamilyReportBody } from "../components/FamilyReportBody";

/**
 * Public shared Family Report viewer. Reuses <FamilyReportBody /> so it renders
 * identically to the authenticated /family-report page.
 */
export default function SharedFamilyReport() {
  const { token } = useParams();
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const backendUrl = process.env.REACT_APP_BACKEND_URL;
  const pdfUrl = `${backendUrl}/api/family-report/shared/${token}?format=pdf`;

  const load = useCallback(async () => {
    if (!token) return setState({ loading: false, error: "Missing share token.", data: null });
    try {
      const res = await fetch(`${backendUrl}/api/family-report/shared/${token}?format=json`, { credentials: "omit" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        return setState({ loading: false, error: body.detail || "This shared link is no longer valid.", data: null });
      }
      const data = await res.json();
      setState({ loading: false, error: null, data });
    } catch {
      setState({ loading: false, error: "Couldn't load the shared Family Report.", data: null });
    }
  }, [token, backendUrl]);

  useEffect(() => { load(); }, [load]);

  const copyLink = async () => {
    try { await navigator.clipboard.writeText(window.location.href); toast.success("Link copied to clipboard"); }
    catch { toast.error("Couldn't copy — please copy from the address bar."); }
  };

  if (state.loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[#F8F5FF] via-white to-white grid place-items-center px-6" data-testid="sharedfam-loading">
        <div className="flex items-center gap-2 text-[#3D1A78]"><Loader2 size={16} className="animate-spin" /> Loading Family Report…</div>
      </div>
    );
  }
  if (state.error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[#F8F5FF] via-white to-white grid place-items-center px-6" data-testid="sharedfam-error">
        <div className="max-w-md w-full rounded-3xl border border-[#F0B6A0] bg-[#FEF1EC] p-6 text-center">
          <div className="text-[#C2481F] font-bold mb-1">Link unavailable</div>
          <p className="text-sm text-[#4B4567]">{state.error}</p>
          <Link to="/" className="mt-4 inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline"><ArrowUpRight size={14} /> Visit SA CoParents</Link>
        </div>
      </div>
    );
  }

  const { report, shared_by: sharedBy, generated_at: generatedAt } = state.data || {};
  const date = generatedAt ? new Date(generatedAt).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) : null;

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#F8F5FF] via-white to-white">
      <header className="sticky top-0 z-10 bg-white/90 backdrop-blur border-b border-[#E5E0EE]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2" data-testid="sharedfam-brand">
            <img src="/icon-256.png" alt="SA CoParents" className="w-7 h-7 rounded-md" />
            <span className="font-serif text-[15px] text-[#1A1330]">SA CoParents</span>
          </Link>
          <div className="flex items-center gap-2">
            <button onClick={copyLink} className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3D1A78] border border-[#E5E0EE] hover:border-[#3D1A78] rounded-full px-3 py-1.5" data-testid="sharedfam-copy-btn">
              <Share2 size={12} /> Copy link
            </button>
            <a href={pdfUrl} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-[#3D1A78] hover:bg-[#2D0F63] rounded-full px-3 py-1.5" data-testid="sharedfam-pdf-btn">
              <Download size={12} /> PDF
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {sharedBy && (
          <div className="text-sm text-[#4B4567]" data-testid="sharedfam-sharedby-row">
            Shared by <span className="font-semibold text-[#1A1330]" data-testid="sharedfam-sharedby">{sharedBy}</span>
            {date && <> · {date}</>}
          </div>
        )}
        <FamilyReportBody report={report} />

        <div className="rounded-3xl bg-[#1A1330] text-white p-6 sm:p-8 mt-6" data-testid="sharedfam-cta">
          <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#CFC1EA] mb-2">Powered by SA CoParents</div>
          <div className="font-serif text-2xl leading-tight">One document. Three assessments. Real clarity.</div>
          <p className="text-sm text-[#CFC1EA] mt-2 max-w-lg">
            Build your own Family Report by completing the Co-Parenting, Special Needs, and Safety assessments — then share a single branded PDF with your co-parent, mediator, or attorney.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link to="/" className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#1A1330] bg-white hover:bg-[#EFE9F9] rounded-full px-4 py-2" data-testid="sharedfam-cta-primary">
              Explore SA CoParents <ExternalLink size={12} />
            </Link>
            <Link to="/signup" className="inline-flex items-center gap-1.5 text-sm font-semibold text-white border border-[#CFC1EA] hover:bg-[#3D1A78] rounded-full px-4 py-2" data-testid="sharedfam-cta-signup">
              Take the assessments
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
