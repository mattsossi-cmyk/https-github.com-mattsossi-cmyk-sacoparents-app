/**
 * ShareManagementPanel — dashboard tile that lists the parent's active
 * share links (Joint Agreement + Joint Report) with view analytics and
 * a one-tap revoke. Hidden entirely when there are no active tokens so
 * it never clutters the dashboard for parents who haven't shared.
 *
 * Data source: `GET /api/share/mine` (enriched in iter127 with
 * `view_count`, `download_count`, and `last_opened_at` per jti).
 * Revocation: `POST /api/share/revoke` with the jti.
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  Link2, Copy, Trash2, Eye, Download, Clock, ExternalLink,
} from "lucide-react";
import { api } from "../lib/api";
import { toast } from "sonner";

const DOC_TYPE_META = {
  joint_agreement: {
    label: "Co-Parenting Agreement",
    accent: "#3D1A78",
    accentBg: "#F5F1FB",
    accentBorder: "#D6CFE8",
    previewBase: "/api/joint-agreement/preview",
    spaBase: "/joint-agreement/shared",
  },
  joint_report: {
    label: "Joint Summary for Professional Review",
    accent: "#0F6F6F",
    accentBg: "#EAF7F7",
    accentBorder: "#B5DFC5",
    previewBase: "/api/joint-professional-report/preview",
    spaBase: "/joint-report/shared",
  },
};


function formatRelative(iso) {
  if (!iso) return null;
  try {
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return null;
    const diff = Date.now() - then;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 7) return `${days}d ago`;
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short", day: "numeric",
    });
  } catch {
    return null;
  }
}


function formatExpiry(iso) {
  if (!iso) return "no expiry";
  try {
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return "no expiry";
    const diff = then - Date.now();
    const days = Math.ceil(diff / 86400000);
    if (days < 1) return "expires today";
    if (days === 1) return "expires tomorrow";
    if (days < 30) return `expires in ${days}d`;
    return `expires ${new Date(iso).toLocaleDateString(undefined, {
      month: "short", day: "numeric",
    })}`;
  } catch {
    return "no expiry";
  }
}


function ShareRow({ row, onRevoke, revoking }) {
  const meta = DOC_TYPE_META[row.doc_type] || DOC_TYPE_META.joint_agreement;
  const previewUrl = `${window.location.origin}${meta.previewBase}/${row.token || ""}`;
  const spaUrl = `${window.location.origin}${meta.spaBase}/${row.token || ""}`;
  const hasToken = Boolean(row.token);

  const copyLink = async () => {
    // We prefer copying the OG-aware preview URL because that's the URL
    // parents originally pasted into messages. Fallback to SPA URL if
    // the token was minted before this UI existed.
    const url = hasToken ? previewUrl : spaUrl;
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Share link copied");
    } catch {
      toast.error("Couldn't copy — long-press the link to copy manually");
    }
  };

  return (
    <div
      className="rounded-2xl border p-4 bg-white/70"
      style={{ borderColor: meta.accentBorder }}
      data-testid={`share-row-${row.jti}`}
    >
      <div className="flex items-start gap-3">
        <div
          className="shrink-0 h-9 w-9 rounded-full grid place-items-center text-white"
          style={{ backgroundColor: meta.accent }}
          aria-hidden
        >
          <Link2 size={15} />
        </div>
        <div className="min-w-0 flex-1">
          <div
            className="text-[0.625rem] uppercase tracking-[0.18em] font-bold"
            style={{ color: meta.accent }}
          >
            {meta.label}
          </div>
          <div className="text-sm text-[#1A1330] mt-0.5 leading-tight truncate">
            {row.label || "Untitled share"}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[0.6875rem] font-medium">
            <span
              className="inline-flex items-center gap-1 rounded-full px-2 py-0.5"
              style={{
                backgroundColor: meta.accentBg,
                color: meta.accent,
              }}
              data-testid={`share-row-${row.jti}-views`}
              title={`${row.view_count || 0} views · ${row.download_count || 0} downloads`}
            >
              <Eye size={11} strokeWidth={2.4} />
              {row.view_count || 0}
              {row.last_opened_at && (
                <span className="opacity-80">
                  · opened {formatRelative(row.last_opened_at)}
                </span>
              )}
            </span>
            {(row.download_count || 0) > 0 && (
              <span
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 bg-white text-[#4B4567] border"
                style={{ borderColor: meta.accentBorder }}
                title="PDF downloads"
              >
                <Download size={11} strokeWidth={2.4} />
                {row.download_count}
              </span>
            )}
            <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 bg-white text-[#6E6787] border border-[#E5E0EE]">
              <Clock size={11} strokeWidth={2.4} />
              {formatExpiry(row.expires_at)}
            </span>
            {(row.view_count || 0) === 0 && (
              <span
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 bg-[#FFF6D8] text-[#8A6B12] border border-[#E4D8B8]"
                data-testid={`share-row-${row.jti}-not-opened`}
                title="No one has opened this link yet"
              >
                not opened yet
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {hasToken && (
          <a
            href={spaUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[0.6875rem] font-semibold border border-[#E5E0EE] bg-white text-[#3D1A78] hover:bg-[#F5F1FB] transition-colors"
            data-testid={`share-row-${row.jti}-open`}
          >
            <ExternalLink size={11} strokeWidth={2.4} />
            Open
          </a>
        )}
        <button
          type="button"
          onClick={copyLink}
          className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[0.6875rem] font-semibold border border-[#E5E0EE] bg-white text-[#3D1A78] hover:bg-[#F5F1FB] transition-colors"
          data-testid={`share-row-${row.jti}-copy`}
        >
          <Copy size={11} strokeWidth={2.4} />
          Copy link
        </button>
        <button
          type="button"
          onClick={() => onRevoke(row)}
          disabled={revoking}
          className="ml-auto inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[0.6875rem] font-semibold border border-[#EFB4B4] bg-white text-[#B02A2A] hover:bg-[#FCEDEB] transition-colors disabled:opacity-60"
          data-testid={`share-row-${row.jti}-revoke`}
        >
          <Trash2 size={11} strokeWidth={2.4} />
          {revoking ? "Revoking..." : "Revoke"}
        </button>
      </div>
    </div>
  );
}


export default function ShareManagementPanel() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [active, setActive] = useState([]);
  const [revoking, setRevoking] = useState(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get("/share/mine");
      const data = res?.data || {};
      setActive(Array.isArray(data.active) ? data.active : []);
    } catch (e) {
      setError(e?.message || "Could not load your share links.");
      setActive([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const revokeOne = async (row) => {
    const confirmed = window.confirm(
      `Revoke this ${DOC_TYPE_META[row.doc_type]?.label || "share"} link?\n\n` +
      "Anyone with the link will lose access immediately. This can't be undone."
    );
    if (!confirmed) return;
    setRevoking(row.jti);
    try {
      await api.post("/share/revoke", { jti: row.jti });
      toast.success("Link revoked");
      await reload();
    } catch {
      toast.error("Couldn't revoke the link right now. Please try again.");
    } finally {
      setRevoking(null);
    }
  };

  // Hide the tile entirely for parents who never shared anything —
  // keeps the dashboard uncluttered until it has value to add.
  if (loading || error) return null;
  if (active.length === 0) return null;

  return (
    <section
      className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6"
      data-testid="share-management-panel"
    >
      <div className="flex items-baseline justify-between flex-wrap gap-2 mb-4">
        <div>
          <div className="text-[0.6875rem] uppercase tracking-[0.16em] font-bold text-[#3D1A78]">
            Active share links
          </div>
          <div className="text-sm text-[#4B4567] mt-0.5 leading-relaxed">
            Who is currently able to open your joint drafts. Revoke any link
            you no longer want live.
          </div>
        </div>
        <span
          className="rounded-full bg-[#EFE9F9] text-[#3D1A78] px-2.5 py-0.5 text-xs font-bold"
          data-testid="share-management-active-count"
        >
          {active.length} active
        </span>
      </div>
      <div className="space-y-2.5">
        {active.map((row) => (
          <ShareRow
            key={row.jti}
            row={row}
            onRevoke={revokeOne}
            revoking={revoking === row.jti}
          />
        ))}
      </div>
    </section>
  );
}
