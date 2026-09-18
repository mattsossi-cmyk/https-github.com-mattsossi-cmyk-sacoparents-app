/**
 * lib/pdf.js — Shared PDF download helper.
 *
 * Iter204. Every PDF download page previously rolled its own
 * axios.blob + generic toast on failure. When the backend refused
 * with a 404/409 "please complete the assessment first" state, the
 * parent saw a bare "Could not download the PDF" error with no
 * useful next step. This helper unifies:
 *
 *   * Blob-safe axios request + browser download.
 *   * Friendly empty-state toast — surfaces the backend `detail`
 *     ("Your Foundation Statement is empty…") and adds a "Take me
 *     there" action button that deep-links to the assessment.
 *   * Best-effort URL → assessment-route mapping so we never have
 *     to hand-thread the route through every call site.
 *
 * Non-goals:
 *   * Doesn't retry (network errors bubble up with a plain toast).
 *   * Doesn't cache (each click hits the server fresh — the report
 *     bytes can be signed and personalised).
 */
import { toast } from "sonner";
import { api } from "./api";

/**
 * Map a PDF endpoint URL prefix to the parent-facing assessment route
 * we should link them to when the endpoint refuses with 404/409.
 *
 * Order matters — the first matching prefix wins. Keep the most-
 * specific paths first (e.g. `/api/complete-report/joint/` before
 * the more general `/api/complete-report/`).
 */
const EMPTY_STATE_ROUTES = [
  // Foundation Statement — write a prompt on the reflection page.
  { prefix: "/api/mediation/foundation-statement",     route: "/reflection",         label: "Write your first prompt" },
  // Child Needs (SNC v2) individual report.
  { prefix: "/api/snc2/report",                         route: "/special-needs-v2",   label: "Complete the assessment" },
  // Deep-dive individual reports.
  { prefix: "/api/edu-deep/report",                     route: "/special-needs-v2/educational-deep-dive",   label: "Complete the Educational deep-dive" },
  { prefix: "/api/med-deep/report",                     route: "/special-needs-v2/medical-deep-dive",       label: "Complete the Medical deep-dive" },
  { prefix: "/api/psych-deep/report",                   route: "/special-needs-v2/psychological-deep-dive", label: "Complete the Psychological deep-dive" },
  // Joint Alignment Report + Joint Agreement — dual-consent gated,
  // routes them to the SNC v2 comparison page where the Compare
  // share flow lives.
  { prefix: "/api/joint-professional-report",           route: "/special-needs-v2",   label: "Set up Compare with my co-parent" },
  { prefix: "/api/joint-agreement",                     route: "/summary?tab=agreement", label: "Generate my agreement draft" },
  // Pathway Report — safety assessment is the front door.
  { prefix: "/api/pathway-report",                      route: "/safety-assessment",  label: "Complete Safety Assessment" },
  // Complete Alignment (individual + joint) — no single assessment
  // gates this; the friendliest next step is the dashboard itself
  // where every lane is enumerated.
  { prefix: "/api/complete-report",                     route: "/dashboard",          label: "Open my dashboard" },
  // Co-Parenting Assessment.
  { prefix: "/api/coparenting/report",                  route: "/coparenting",        label: "Complete the assessment" },
  // Bundle Download — sends the parent back to the dashboard where
  // they can see each lane's status.
  { prefix: "/api/bundle/my-completed",                 route: "/dashboard",          label: "Open my dashboard" },
  // Mediation summary — user is missing pieces of the readiness flow.
  { prefix: "/api/mediation/summary",                   route: "/dashboard",          label: "Open my dashboard" },
];

/**
 * Best-effort match of a URL to a parent-facing route. Returns
 * `null` when no mapping is registered — the caller shows a plain
 * toast in that case.
 */
export function resolveEmptyStateRoute(url) {
  if (typeof url !== "string" || !url) return null;
  const path = url.startsWith("http")
    ? new URL(url).pathname
    : url;
  return (
    EMPTY_STATE_ROUTES.find((entry) => path.startsWith(entry.prefix)) || null
  );
}

/**
 * Blob-safe download for a parent-facing PDF endpoint.
 *
 * @param {string} url       Relative path (e.g. `/mediation/foundation-statement.pdf`)
 *                           or an absolute URL. Relative paths are sent
 *                           via the shared axios instance (`api`) so the
 *                           `/api` prefix and cookies are added.
 * @param {object} [opts]
 * @param {string} [opts.filename]  Filename used for the browser download.
 * @param {object} [opts.params]    Query params forwarded to axios.
 * @param {string} [opts.testid]    data-testid value for the toast (helps E2E).
 * @param {()=>void} [opts.onSuccess] Optional callback after the download fires.
 * @param {(msg:string)=>void} [opts.onError]  Optional caller callback for
 *                                             non-empty-state failures — the
 *                                             helper still toasts.
 * @returns {Promise<boolean>} Resolves true on success, false on any error
 *          (the helper already surfaced a toast; caller doesn't need to).
 */
export async function downloadPdf(url, opts = {}) {
  const {
    filename = "report.pdf",
    params,
    testid = "pdf-download",
    onSuccess,
    onError,
  } = opts;
  // Relative paths (leading slash w/o protocol) go through the shared
  // axios instance so cookies + baseURL are applied. Absolute URLs are
  // sent as-is (e.g. explicit CDN links).
  const cfg = { responseType: "blob" };
  if (params) cfg.params = params;
  const req = url.startsWith("http")
    ? api.get(url, { ...cfg, baseURL: "" })
    : api.get(url, cfg);
  try {
    const res = await req;
    const blob = new Blob([res.data], { type: "application/pdf" });
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    // Delay revoke so slow browsers finish the download stream first.
    setTimeout(() => URL.revokeObjectURL(objectUrl), 2000);
    onSuccess?.();
    return true;
  } catch (err) {
    const status = err?.response?.status;
    // Blob-typed 4xx: axios delivers the error body as a Blob, not JSON.
    // Peek inside to surface the backend's friendly `detail` string.
    let detail = "";
    if (err?.response?.data instanceof Blob) {
      try {
        const txt = await err.response.data.text();
        detail = JSON.parse(txt)?.detail || "";
      } catch (_e) { /* silently drop parse failures */ }
    } else if (typeof err?.response?.data?.detail === "string") {
      detail = err.response.data.detail;
    }
    // 404 / 409 are the "please complete the assessment first" family.
    if (status === 404 || status === 409) {
      const route = resolveEmptyStateRoute(url);
      const message = detail || "Finish this assessment to unlock the PDF.";
      toast.info(message, {
        action: route
          ? {
              label: route.label,
              onClick: () => { window.location.href = route.route; },
            }
          : undefined,
        duration: 8000,
      });
      onError?.(message);
      return false;
    }
    // Everything else — network error, 500, revoked share, safety
    // block — falls through to a generic toast so the user isn't left
    // wondering. The detail string (when present) still leads.
    const msg = detail || "Could not download the PDF.";
    toast.error(msg, { duration: 6000 });
    onError?.(msg);
    return false;
  }
}
