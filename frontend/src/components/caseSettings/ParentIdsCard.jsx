import React, { useCallback, useEffect, useState } from "react";
import { Fingerprint } from "lucide-react";

import { api } from "../../lib/api";

// Admin-only: adds the per-parent Align ID (align_ref) where it's missing. Run by hand, after a database backup.
export function ParentIdsCard({ onForbidden }) {
  const [counts, setCounts] = useState(null);
  const [backedUp, setBackedUp] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = useCallback(() => {
    api
      .get("/admin/align-refs")
      .then((r) => setCounts(r.data))
      .catch((e) => (e?.response?.status === 403 ? onForbidden?.() : setMsg("Couldn't load the counts.")));
  }, [onForbidden]);
  useEffect(load, [load]);

  const run = async () => {
    setBusy(true);
    setMsg("");
    try {
      const { data } = await api.post("/admin/align-refs/backfill");
      setCounts(data);
      setMsg(`Done. Added ${data.users} account IDs and ${data.case_parents} case-entry IDs. Existing IDs were not changed.`);
      setBackedUp(false);
    } catch {
      setMsg("Couldn't add the IDs. Nothing was changed. Please try again.");
    }
    setBusy(false);
  };

  const missing = counts ? counts.accounts_missing + counts.case_entries_missing : null;
  return (
    <section data-testid="parent-ids-card" className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5 space-y-3">
      <h2 className="text-base font-bold text-[#1A1330] inline-flex items-center gap-2">
        <Fingerprint size={16} aria-hidden="true" /> Parent IDs for Align
      </h2>
      <p className="text-sm text-[#4B4567]">
        Each parent gets one Align ID, used only in their check-in link. New accounts get one automatically. This button adds IDs to older
        accounts and case entries that don&apos;t have one. It never changes an existing ID.
      </p>
      {counts && (
        <p data-testid="parent-ids-missing" className="text-sm font-semibold text-[#1A1330]">
          Missing: {counts.accounts_missing} accounts, {counts.case_entries_missing} case entries
        </p>
      )}
      {missing > 0 && (
        <>
          <p className="text-sm text-[#7A4A00] bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
            Take a database backup first: Republish, then Database, then Go to database, then Dump DB.
          </p>
          <label className="flex items-center gap-2 text-sm text-[#1A1330] min-h-[44px]">
            <input type="checkbox" className="w-5 h-5" checked={backedUp} onChange={(e) => setBackedUp(e.target.checked)} data-testid="parent-ids-backup-confirm" />
            I&apos;ve taken a database backup
          </label>
          <button type="button" onClick={run} disabled={!backedUp || busy} data-testid="parent-ids-run" className="btn-gradient px-6 disabled:opacity-50">
            {busy ? "Adding…" : "Add parent IDs"}
          </button>
        </>
      )}
      {missing === 0 && <p data-testid="parent-ids-all-set" className="text-sm text-emerald-800">Every account and case entry has an ID.</p>}
      {msg && <p role="status" data-testid="parent-ids-result" className="text-sm text-[#3B3552]">{msg}</p>}
    </section>
  );
}
