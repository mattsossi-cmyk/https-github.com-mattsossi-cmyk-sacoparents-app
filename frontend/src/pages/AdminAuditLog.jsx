import React, { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { Download, FileLock2 } from "lucide-react";
import { toast } from "sonner";

import AppShell from "../components/AppShell";
import { AdminGate } from "../components/AdminGate";
import { DailyCountsTable } from "../components/caseSettings/DailyCountsTable";
import { api } from "../lib/api";

// Admin-only CSV download of the case-settings audit log. The server logs every export.
export default function AdminAuditLog() {
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [rev, setRev] = useState(0);
  const onForbidden = useCallback(() => setErr("forbidden"), []);
  const download = async () => {
    setBusy(true);
    try {
      const r = await api.get("/admin/safety-audit-log/export", { responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      const a = Object.assign(document.createElement("a"), { href: url, download: "safety_audit_log.csv" });
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Audit log downloaded. This export was logged.");
      setRev((n) => n + 1);
    } catch (e) {
      if (e?.response?.status === 403) setErr("forbidden");
      else toast.error("Couldn't export. Please try again.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <AdminGate tp="admin-audit" err={err}>
      <AppShell>
        <div className="max-w-2xl mx-auto px-1 py-6 space-y-5" data-testid="admin-audit-page">
          <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] inline-flex items-center gap-2">
            <FileLock2 size={12} /> Admin only
          </div>
          <h1 className="font-serif text-4xl text-[#1A1330]">Case settings audit log</h1>
          <p className="text-sm text-[#4B4567]">
            Every read and change of a case&apos;s settings (who, when, what). Parents never see this log. Each export is itself recorded.
          </p>
          <button type="button" onClick={download} disabled={busy} data-testid="admin-audit-export" className="btn-gradient inline-flex items-center gap-2 px-6 disabled:opacity-50">
            <Download size={15} /> {busy ? "Preparing…" : "Export CSV"}
          </button>
          <DailyCountsTable key={rev} onForbidden={onForbidden} />
          <p className="text-xs text-[#6E6787]">
            <Link to="/admin/help-services" className="underline text-[#3D1A78]" data-testid="admin-audit-help-link">Get help: local services</Link>
          </p>
        </div>
      </AppShell>
    </AdminGate>
  );
}
