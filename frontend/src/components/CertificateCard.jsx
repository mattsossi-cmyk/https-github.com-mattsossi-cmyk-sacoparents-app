import { useEffect, useState } from "react";
import { Award, Download, Loader2, Lock, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, API } from "../lib/api";

/**
 * CertificateCard — surface for the Certificate of Completion.
 *
 * Flow:
 *   1. On mount, ask the backend whether this parent is eligible and grab a
 *      preview blob URL so we can render the personalised PNG inline.
 *   2. Renders a locked state when the parent still needs to finish steps.
 *   3. On "Download PDF", POST to /mediation/certificate/download and
 *      trigger a native file download.
 *
 * The card is drop-in — no props required. It shows itself on both
 * /my-plan and inside the Reports tab of /summary.
 */

async function fetchBlob(url) {
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.blob();
}

async function postForBlob(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.blob();
}

export default function CertificateCard() {
  const [state, setState] = useState({
    loading: true,
    eligible: false,
    isGuest: false,
    completedSteps: [],
    requiredSteps: [],
    threshold: 5,
    displayName: "",
  });
  const [previewUrl, setPreviewUrl] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [customName, setCustomName] = useState("");
  const [editingName, setEditingName] = useState(false);

  // Load eligibility on mount.
  useEffect(() => {
    let cancelled = false;
    api
      .get("/mediation/certificate/eligibility")
      .then((r) => {
        if (cancelled) return;
        const d = r.data || {};
        setState({
          loading: false,
          eligible: !!d.eligible,
          isGuest: !!d.is_guest,
          completedSteps: d.completed_steps || [],
          requiredSteps: d.required_steps || [],
          threshold: d.threshold || 5,
          displayName: d.display_name || "",
        });
        setCustomName(d.display_name || "");
      })
      .catch(() => {
        if (!cancelled) setState((s) => ({ ...s, loading: false }));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load preview (PNG) whenever the name changes and we're eligible.
  useEffect(() => {
    if (!state.eligible) return;
    let cancelled = false;
    const name = (customName || state.displayName || "").trim();
    const url = `${API}/mediation/certificate/preview${
      name ? `?name=${encodeURIComponent(name)}` : ""
    }`;
    fetchBlob(url)
      .then((blob) => {
        if (cancelled) return;
        const obj = URL.createObjectURL(blob);
        setPreviewUrl((prev) => {
          if (prev) URL.revokeObjectURL(prev);
          return obj;
        });
      })
      .catch(() => {
        /* preview is best-effort; download still works */
      });
    return () => {
      cancelled = true;
    };
  }, [state.eligible, state.displayName, customName]);

  // Cleanup blob URL on unmount.
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  async function handleDownload() {
    setDownloading(true);
    try {
      const name = (customName || state.displayName || "").trim();
      const blob = await postForBlob("/mediation/certificate/download", {
        name: name || null,
      });
      const objUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objUrl;
      const safe = (name || "certificate").replace(/[^a-z0-9]/gi, "_");
      a.download = `SA_CoParents_Certificate_${safe}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(objUrl);
      toast.success("Certificate downloaded — congratulations!");
    } catch (err) {
      toast.error("Couldn't generate certificate. Please try again.");
    } finally {
      setDownloading(false);
    }
  }

  if (state.loading) {
    return (
      <div
        className="rounded-3xl border border-[#E5E0EE] bg-white p-6 shadow-sm"
        data-testid="certificate-card-loading"
      >
        <div className="flex items-center gap-2 text-sm text-[#6E6787]">
          <Loader2 size={14} className="animate-spin" /> Checking your progress…
        </div>
      </div>
    );
  }

  const stepsRemaining = Math.max(
    0,
    state.threshold - state.completedSteps.length
  );

  if (!state.eligible) {
    return (
      <div
        className="rounded-3xl border border-[#E5E0EE] bg-gradient-to-br from-[#FFF9F1] to-white p-6 shadow-sm"
        data-testid="certificate-card-locked"
      >
        <div className="flex items-start gap-4">
          <div className="shrink-0 w-12 h-12 rounded-2xl bg-[#C28771]/15 grid place-items-center">
            <Lock size={20} className="text-[#9A5D47]" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="eyebrow text-[#9A5D47]">Almost there</div>
            <h3 className="font-serif text-xl text-[#1A1330] mt-1">
              Certificate of Completion
            </h3>
            <p className="text-sm text-[#4B4567] mt-2">
              Complete{" "}
              <span className="font-semibold">
                {stepsRemaining} more step{stepsRemaining === 1 ? "" : "s"}
              </span>{" "}
              to unlock your personalised certificate. You&apos;ve done{" "}
              {state.completedSteps.length} of {state.threshold}.
            </p>
            <div className="mt-3 h-1.5 rounded-full bg-[#F3E7DC] overflow-hidden">
              <div
                className="h-full bg-[#9A5D47] transition-all"
                style={{
                  width: `${Math.min(
                    100,
                    (state.completedSteps.length / state.threshold) * 100
                  )}%`,
                }}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="rounded-3xl border border-[#E5E0EE] bg-gradient-to-br from-[#FFF9F1] via-white to-[#F5F2FA] p-6 shadow-sm"
      data-testid="certificate-card-earned"
    >
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-start gap-4">
          <div className="shrink-0 w-12 h-12 rounded-2xl bg-[#3D1A78]/12 grid place-items-center">
            <Award size={22} className="text-[#3D1A78]" />
          </div>
          <div>
            <div className="eyebrow text-[#3D1A78] flex items-center gap-1.5">
              <Sparkles size={12} /> You&apos;ve earned this
            </div>
            <h3 className="font-serif text-xl text-[#1A1330] mt-1">
              Certificate of Completion
            </h3>
            <p className="text-sm text-[#4B4567] mt-1 max-w-md">
              Committed to your child&apos;s future. Download a signed
              certificate to keep, print, or share with your mediator.
            </p>
          </div>
        </div>
      </div>

      {previewUrl ? (
        <div className="rounded-2xl overflow-hidden border border-[#E5E0EE] bg-[#FDFBF6]">
          <img
            src={previewUrl}
            alt="Your certificate preview"
            className="w-full h-auto block"
            data-testid="certificate-preview-image"
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-[#E5E0EE] bg-white p-8 text-center text-sm text-[#6E6787]">
          Generating your preview…
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        {!editingName ? (
          <button
            type="button"
            className="text-xs text-[#3D1A78] hover:underline font-medium"
            onClick={() => setEditingName(true)}
            data-testid="certificate-edit-name-btn"
          >
            Change the name on the certificate
          </button>
        ) : (
          <div className="flex items-center gap-2 flex-1 min-w-[220px]">
            <input
              type="text"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              onBlur={() => setEditingName(false)}
              placeholder="Your name"
              maxLength={80}
              className="flex-1 px-3 py-2 rounded-xl border border-[#E5E0EE] text-sm bg-white focus:outline-none focus:border-[#3D1A78]"
              data-testid="certificate-name-input"
              autoFocus
            />
            <button
              type="button"
              className="text-xs text-[#3D1A78] hover:underline"
              onClick={() => setEditingName(false)}
            >
              Done
            </button>
          </div>
        )}

        <button
          type="button"
          onClick={handleDownload}
          disabled={downloading}
          className="ml-auto inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2D0F63] disabled:opacity-50 transition-colors"
          data-testid="certificate-download-btn"
        >
          {downloading ? (
            <>
              <Loader2 size={14} className="animate-spin" /> Preparing PDF…
            </>
          ) : (
            <>
              <Download size={14} /> Download certificate (PDF)
            </>
          )}
        </button>
      </div>

      {state.isGuest && (
        <p
          className="text-xs text-[#6E6787] mt-3 italic"
          data-testid="certificate-demo-note"
        >
          Demo mode — save your account to have this certificate emailed to
          you on completion.
        </p>
      )}
    </div>
  );
}
