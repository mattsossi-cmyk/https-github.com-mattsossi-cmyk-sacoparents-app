import { useCallback, useEffect, useMemo, useState } from "react";
import { ProSeeLink } from "./privacy/ProSeeLink";
import { EyeOff, Eye, Download, Share2, Loader2, Save, Lock, Clock, Trash2, ChevronDown, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { api, API } from "../lib/api";
import { requestPreShareConsent } from "@/components/PreShareConsentDialog";

/**
 * ReportShareControls — reusable "customize what to share" panel used on every
 * report page (Mediation Summary, Co-Parenting Agreement, Special Needs Care
 * Plan, and Family Violence and Communication Safety Screen).
 *
 * The parent chooses per-section visibility once. That preference is:
 *   1. Persisted on the report via a PATCH (optional — via `visibilityUrl`)
 *   2. Applied when downloading the PDF (`pdfUrl` gets `?excluded=csv`)
 *   3. Snapshotted into the JWT-signed share link (POST `shareUrl` body)
 *
 * All handlers are self-contained so pages only pass URLs + the report type.
 * Safety-locked sections (Texas hotlines, pathway) are rendered but disabled.
 *
 * Props:
 *   reportType     "summary" | "agreement" | "sn_report" | "safety"
 *   pdfUrl         Fully-qualified absolute URL for the auth'd PDF endpoint
 *   shareUrl       Relative api path for the share-link POST (e.g. "/mediation/summary/xxx/share-link")
 *   visibilityUrl  Optional relative api path for the PATCH endpoint. Omit for no-persist.
 *   initialExcluded  Optional starting list from the doc.
 *   filename       Suggested download filename.
 *   testIdPrefix   Prefix for data-testid attributes (unique per page).
 */
export default function ReportShareControls({
  reportType,
  pdfUrl,
  shareUrl,
  visibilityUrl,
  initialExcluded,
  filename,
  testIdPrefix = "report-share",
}) {
  const [sections, setSections] = useState([]);
  const [excluded, setExcluded] = useState(() => new Set(initialExcluded || []));
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [expireDays, setExpireDays] = useState(7); // 1 | 7 | 30 | null (never)
  const [shareLabel, setShareLabel] = useState("");
  const [existingLinks, setExistingLinks] = useState([]);
  const [linksLoading, setLinksLoading] = useState(false);
  const [linksExpanded, setLinksExpanded] = useState(false);
  const [revokingJti, setRevokingJti] = useState(null);

  const loadExistingLinks = useCallback(async () => {
    setLinksLoading(true);
    try {
      const { data } = await api.get("/share/mine");
      const active = (data?.active || []).filter((r) => r.doc_type === reportType);
      setExistingLinks(active);
    } catch {
      // silent — non-critical
    } finally {
      setLinksLoading(false);
    }
  }, [reportType]);

  useEffect(() => { loadExistingLinks(); }, [loadExistingLinks]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const { data } = await api.get(`/mediation/reports/sections/${reportType}`);
        if (alive) setSections(data?.sections || []);
      } catch {
        if (alive) toast.error("Couldn't load section options.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [reportType]);

  // Reset excluded when parent re-mounts with new initial value
  useEffect(() => {
    setExcluded(new Set(initialExcluded || []));
  }, [initialExcluded]);

  const totalVisible = useMemo(() => {
    const total = sections.length;
    const hidden = sections.filter((s) => excluded.has(s.key)).length;
    return { total, visible: total - hidden, hidden };
  }, [sections, excluded]);

  const toggle = (key, locked) => {
    if (locked) return;
    setExcluded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const exList = () => Array.from(excluded);

  const savePreference = useCallback(async () => {
    if (!visibilityUrl) return;
    setSaving(true);
    try {
      await api.patch(visibilityUrl, { excluded: exList() });
      toast.success("Sharing preferences saved.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't save preferences.");
    } finally {
      setSaving(false);
    }
  }, [visibilityUrl, excluded]);

  const downloadPdf = useCallback(async () => {
    setDownloading(true);
    try {
      const csv = exList().join(",");
      const sep = pdfUrl.includes("?") ? "&" : "?";
      const url = csv ? `${pdfUrl}${sep}excluded=${encodeURIComponent(csv)}` : pdfUrl;
      const res = await fetch(url, { credentials: "include" });
      if (!res.ok) throw new Error(`http_${res.status}`);
      const blob = await res.blob();
      const a = document.createElement("a");
      const objectUrl = URL.createObjectURL(blob);
      a.href = objectUrl;
      a.download = filename || `${reportType}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(objectUrl);
      toast.success(
        totalVisible.hidden > 0
          ? `Downloaded — ${totalVisible.hidden} section${totalVisible.hidden === 1 ? "" : "s"} hidden.`
          : "Full report downloaded."
      );
    } catch {
      toast.error("Couldn't download the PDF. Please try again.");
    } finally {
      setDownloading(false);
    }
  }, [pdfUrl, excluded, filename, reportType, totalVisible]);

  const copyShareLink = useCallback(async () => {
    // HB 300 + Privacy Policy pre-share consent gate. Show the
    // "YOU CONTROL THIS REPORT" bullets before the share link is minted.
    // Fail closed on cancel — no link is created and no toast fires.
    const consentLabels = {
      summary:    "the Mediation Prep Summary",
      agreement:  "the Co-Parenting Agreement",
      sn_report:  "the Special Needs Care Plan",
    };
    const consentLabel = consentLabels[reportType] || "this report";
    const consented = await requestPreShareConsent(consentLabel);
    if (!consented) return;

    setSharing(true);
    try {
      const { data } = await api.post(shareUrl, {
        excluded: exList(),
        expire_days: expireDays,  // null = never
        label: shareLabel.trim() || null,
      });
      const publicUrl = `${window.location.origin}${data.path}`;
      await navigator.clipboard.writeText(publicUrl);
      const windowLabel = expireDays === null ? "never expires" :
        expireDays === 1 ? "24-hour link" :
        expireDays === 30 ? "30-day link" : "7-day link";
      toast.success(
        totalVisible.hidden > 0
          ? `Share link copied — ${windowLabel}, ${totalVisible.hidden} section${totalVisible.hidden === 1 ? "" : "s"} hidden.`
          : `Share link copied — ${windowLabel}.`
      );
      setShareLabel("");
      loadExistingLinks();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't create the share link.");
    } finally {
      setSharing(false);
    }
  }, [shareUrl, expireDays, shareLabel, totalVisible, loadExistingLinks, reportType]);

  const revokeLink = useCallback(async (jti) => {
    setRevokingJti(jti);
    try {
      await api.post("/share/revoke", { jti });
      toast.success("Share link revoked. It can no longer be opened.");
      loadExistingLinks();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't revoke the link.");
    } finally {
      setRevokingJti(null);
    }
  }, [loadExistingLinks]);

  if (loading) {
    return (
      <div className="rounded-3xl border border-[#E5E0EE] bg-white p-6 text-sm text-[#6E6787]" data-testid={`${testIdPrefix}-loading`}>
        Loading share options…
      </div>
    );
  }

  return (
    <section
      className="rounded-3xl border border-[#E5E0EE] bg-gradient-to-br from-white to-[#F7F4FC] p-6 sm:p-8"
      data-testid={`${testIdPrefix}-panel`}
    >
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-[0.14em] font-bold text-[#3D1A78]">Selective sharing</div>
          <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] mt-1">Choose what to include</h3>
          <p className="text-sm text-[#4B4567] mt-1 max-w-2xl">
            Some readers only need the highlights. Hide any section before you
            download the PDF or generate a share link.
          </p>
          <p className="text-[0.8125rem] text-[#4B4567] mt-1 max-w-2xl" data-testid={`${testIdPrefix}-shared-rule`}>
            Shared links and emails never include your readiness score, safety notes or reflection answers.
          </p>
          <ProSeeLink testid={`${testIdPrefix}-pros-see-link`} className="text-[0.8125rem] mt-1.5" />
        </div>
        <div className="text-right">
          <div className="text-2xl font-serif text-[#3D1A78]" data-testid={`${testIdPrefix}-visible-count`}>
            {totalVisible.visible}<span className="text-[#6E6787] text-base">/{totalVisible.total}</span>
          </div>
          <div className="text-[0.6875rem] uppercase tracking-[0.12em] text-[#6E6787]">sections included</div>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="mt-4 text-sm text-[#3D1A78] hover:underline inline-flex items-center gap-1"
        data-testid={`${testIdPrefix}-toggle`}
      >
        {expanded ? <EyeOff size={14} /> : <Eye size={14} />}
        {expanded ? "Hide section list" : "Show section list"}
      </button>

      {expanded && (
        <ul className="mt-4 grid gap-2 sm:grid-cols-2" data-testid={`${testIdPrefix}-list`}>
          {sections.map((s) => {
            const locked = s.locked === "true" || s.locked === true;
            const included = !excluded.has(s.key);
            return (
              <li key={s.key}>
                <label
                  className={
                    "flex items-start gap-3 rounded-2xl border p-3 cursor-pointer transition " +
                    (locked
                      ? "border-[#E5E0EE] bg-[#F5F2FA] cursor-not-allowed opacity-90"
                      : included
                      ? "border-[#3D1A78]/30 bg-white hover:bg-[#F7F4FC]"
                      : "border-[#E5E0EE] bg-[#F5F2FA] hover:bg-white")
                  }
                  data-testid={`${testIdPrefix}-item-${s.key}`}
                >
                  <input
                    type="checkbox"
                    checked={included}
                    disabled={locked}
                    onChange={() => toggle(s.key, locked)}
                    className="mt-0.5 h-4 w-4 accent-[#3D1A78]"
                    data-testid={`${testIdPrefix}-check-${s.key}`}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold text-[#1A1330] flex items-center gap-1.5">
                      {s.label}
                      {locked && (
                        <span title="Cannot be hidden — safety-critical content." className="text-[#6E6787]">
                          <Lock size={12} />
                        </span>
                      )}
                    </div>
                    {(s.own_only === "true" || s.own_only === true) && (
                      <div className="text-[0.6875rem] font-semibold text-[#9A5D47] mt-0.5" data-testid={`${testIdPrefix}-own-only-${s.key}`}>
                        Only in your own download, never in a shared link or email.
                      </div>
                    )}
                    {s.description && (
                      <div className="text-xs text-[#4B4567] mt-0.5">{s.description}</div>
                    )}
                  </div>
                </label>
              </li>
            );
          })}
        </ul>
      )}

      <div className="mt-5 flex items-center gap-2 flex-wrap" data-testid={`${testIdPrefix}-window-selector`}>
        <span className="inline-flex items-center gap-1.5 text-xs uppercase tracking-[0.14em] font-bold text-[#3D1A78]">
          <Clock size={12} /> Link expires
        </span>
        {[
          { d: 1, label: "24h" },
          { d: 7, label: "7 days" },
          { d: 30, label: "30 days" },
          { d: null, label: "Never" },
        ].map((opt) => (
          <button
            key={String(opt.d)}
            type="button"
            onClick={() => setExpireDays(opt.d)}
            data-testid={`${testIdPrefix}-window-${opt.d ?? "never"}`}
            className={`px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
              expireDays === opt.d
                ? "bg-[#3D1A78] text-white border-[#3D1A78]"
                : "bg-white text-[#3D1A78] border-[#D6CFE8] hover:bg-[#F5F1FB]"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="mt-3">
        <label htmlFor={`${testIdPrefix}-nickname`} className="block text-[0.625rem] uppercase tracking-[0.14em] font-bold text-[#3D1A78] mb-1">
          Nickname (optional)
        </label>
        <input
          id={`${testIdPrefix}-nickname`}
          type="text"
          value={shareLabel}
          onChange={(e) => setShareLabel(e.target.value.slice(0, 60))}
          placeholder={'e.g. "Attorney · Aug 2026" or "Teacher"'}
          maxLength={60}
          data-testid={`${testIdPrefix}-nickname-input`}
          className="w-full max-w-md px-3 py-1.5 rounded-full border border-[#D6CFE8] bg-white text-sm text-[#1A1330] placeholder:text-[#B0A9C7] focus:outline-none focus:border-[#3D1A78]"
        />
        <p className="text-[0.625rem] text-[#6E6787] mt-1">Shown only to you — helps you find the right link months later.</p>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <button
          onClick={downloadPdf}
          disabled={downloading}
          className="inline-flex items-center gap-2 text-sm bg-[#3D1A78] text-white rounded-full px-5 py-2.5 font-semibold hover:bg-[#2A1256] disabled:opacity-60"
          data-testid={`${testIdPrefix}-download-btn`}
        >
          {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
          Download PDF
        </button>
        <button
          onClick={copyShareLink}
          disabled={sharing}
          className="inline-flex items-center gap-2 text-sm border border-[#3D1A78] text-[#3D1A78] rounded-full px-5 py-2.5 font-semibold hover:bg-[#F5F2FA] disabled:opacity-60"
          data-testid={`${testIdPrefix}-share-btn`}
        >
          {sharing ? <Loader2 size={14} className="animate-spin" /> : <Share2 size={14} />}
          Copy share link
        </button>
        {visibilityUrl && (
          <button
            onClick={savePreference}
            disabled={saving}
            className="inline-flex items-center gap-2 text-sm text-[#4B4567] hover:text-[#3D1A78] rounded-full px-4 py-2.5 disabled:opacity-60"
            data-testid={`${testIdPrefix}-save-btn`}
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            Save preference
          </button>
        )}
        <div className="text-xs text-[#6E6787] ml-auto" data-testid={`${testIdPrefix}-summary`}>
          {totalVisible.hidden === 0
            ? "Sharing the full report."
            : `${totalVisible.hidden} of ${totalVisible.total} section${totalVisible.total === 1 ? "" : "s"} hidden.`}
        </div>
      </div>

      {/* Existing / active share links — with revoke */}
      {(existingLinks.length > 0 || linksLoading) && (
        <div className="mt-6 border-t border-[#EFE9F9] pt-5" data-testid={`${testIdPrefix}-existing-links`}>
          <button
            type="button"
            onClick={() => setLinksExpanded((v) => !v)}
            data-testid={`${testIdPrefix}-existing-toggle`}
            className="text-sm text-[#3D1A78] hover:underline inline-flex items-center gap-1 font-semibold"
          >
            {linksExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            Your active share links ({existingLinks.length})
          </button>
          {linksExpanded && (
            <ul className="mt-3 space-y-2" data-testid={`${testIdPrefix}-existing-list`}>
              {existingLinks.map((row) => {
                const created = row.created_at ? new Date(row.created_at).toLocaleString() : "";
                const expires = row.expires_at ? new Date(row.expires_at).toLocaleString() : "Never expires";
                return (
                  <li
                    key={row.jti}
                    className="flex items-center gap-3 flex-wrap rounded-xl border border-[#E5E0EE] bg-white px-3 py-2"
                    data-testid={`${testIdPrefix}-existing-row-${row.jti}`}
                  >
                    <div className="text-xs text-[#4B4567] min-w-0 flex-1">
                      <div className="font-semibold text-[#1A1330]" data-testid={`${testIdPrefix}-row-label-${row.jti}`}>
                        {row.label || <span className="italic text-[#6E6787]">Untitled link</span>}
                      </div>
                      <div className="text-[0.6875rem] text-[#6E6787]">Created {created}</div>
                      <div className="text-[0.6875rem] text-[#6E6787]">Expires: {expires}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => revokeLink(row.jti)}
                      disabled={revokingJti === row.jti}
                      data-testid={`${testIdPrefix}-revoke-${row.jti}`}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#B02A2A] border border-[#EFB4B4] hover:bg-[#FBEFEF] rounded-full px-3 py-1.5 disabled:opacity-60"
                    >
                      {revokingJti === row.jti ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                      Revoke
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

// Named helper so callers can build absolute PDF URLs without repeating the API base.
export function pdfAbs(path) {
  return `${API}${path}`;
}
