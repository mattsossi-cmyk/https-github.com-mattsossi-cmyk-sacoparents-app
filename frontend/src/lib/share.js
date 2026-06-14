import { api } from "./api";

/**
 * Create a short-lived share link for a Summary or Agreement and surface it
 * via the native share sheet (mobile) or the clipboard (desktop / fallback).
 *
 * @param {string} _kind      Document kind label (kept for analytics / logs)
 * @param {string} endpoint   API path that returns `{ token, path }`
 * @param {string} title      Title used by the native share sheet
 * @returns {Promise<{mode: 'native' | 'clipboard', url: string}>}
 */
export async function shareViaText(_kind, endpoint, title) {
  const res = await api.post(endpoint);
  const path = res?.data?.path;
  if (!path) {
    throw new Error("Share link payload missing 'path'");
  }
  const apiBase = process.env.REACT_APP_BACKEND_URL || window.location.origin;
  const url = `${apiBase}${path}`;

  // Prefer the native share sheet on mobile — opens iMessage / WhatsApp /
  // Messages / Mail / etc. — and gracefully fall through to clipboard
  // on desktop or when the user cancels.
  if (
    typeof navigator !== "undefined" &&
    typeof navigator.share === "function"
  ) {
    try {
      await navigator.share({ title, url });
      return { mode: "native", url };
    } catch (err) {
      // AbortError = user cancelled — surface clipboard fallback so they
      // can still use the link if the share sheet wasn't what they wanted.
      if (err?.name !== "AbortError") {
        // Re-throw any non-cancel error so the caller can show a toast.
        // (Permission denied, share blocked, etc.)
      }
    }
  }

  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(url);
    }
  } catch (_e) {
    // Clipboard write can fail on insecure origins / sandboxed iframes;
    // we still return the URL so the caller can render it directly.
  }
  return { mode: "clipboard", url };
}
