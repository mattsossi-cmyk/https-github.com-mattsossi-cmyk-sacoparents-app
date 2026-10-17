import React, { useCallback, useEffect, useState } from "react";
import { Activity, CheckCircle2, XCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const TRIGGER_LABEL = { release: "After release", daily: "Daily check", manual: "Manual run" };

const fmt = (iso) => (iso ? new Date(iso).toLocaleString() : "");

const CheckRow = ({ r }) => (
  <li
    data-testid={`admin-release-check-row-${r.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
    className="flex items-start gap-2 text-sm py-1.5 border-b border-[#F0ECF6] last:border-0"
  >
    {r.ok ? (
      <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" />
    ) : (
      <XCircle size={16} className="text-rose-600 shrink-0 mt-0.5" />
    )}
    <span className="font-semibold text-[#1A1330]">{r.name}</span>
    <span className={`ml-auto text-xs text-right ${r.ok ? "text-[#6E6787]" : "text-rose-700"}`}>
      {r.detail} · {r.ms} ms
    </span>
  </li>
);

const History = ({ runs }) => (
  <div className="flex items-center gap-1.5 mt-4" data-testid="admin-release-check-history">
    <span className="text-[0.625rem] uppercase tracking-[0.15em] text-[#6E6787] mr-1">Recent</span>
    {runs.map((r) => (
      <span
        key={r.id}
        title={`${TRIGGER_LABEL[r.trigger] || r.trigger} · ${fmt(r.started_at)} · ${r.ok ? "passed" : "failed"}`}
        className={`w-3 h-3 rounded-full ${r.ok ? "bg-emerald-500" : "bg-rose-500"}`}
      />
    ))}
  </div>
);

export default function ReleaseCheckTile() {
  const [runs, setRuns] = useState([]);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/release-checks?limit=10");
      setRuns(data.runs || []);
    } catch (e) {
      logError("release checks load failed", e);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runNow = async () => {
    setRunning(true);
    try {
      const { data } = await api.post("/admin/release-checks/run");
      toast[data.ok ? "success" : "error"](data.ok ? "All checks passed" : "Some checks failed");
      await load();
    } catch (e) {
      logError("release check run failed", e);
      toast.error("Could not run the check right now.");
    } finally {
      setRunning(false);
    }
  };

  const latest = runs[0];
  const failed = latest ? latest.results.filter((r) => !r.ok).length : 0;
  return (
    <div className="card-soft p-6" data-testid="admin-release-check-tile">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
        <div>
          <div className="eyebrow flex items-center gap-2">
            <Activity size={12} className="text-[#3D1A78]" />
            Release check · Pages + PDFs
          </div>
          <div className="font-serif text-xl text-[#1A1330] mt-1" data-testid="admin-release-check-status">
            {!latest ? "No checks yet" : latest.ok ? "All checks passed" : `${failed} problem${failed === 1 ? "" : "s"} found`}
          </div>
          {latest && (
            <p className="text-xs text-[#6E6787] mt-1" data-testid="admin-release-check-meta">
              {TRIGGER_LABEL[latest.trigger] || latest.trigger} · {fmt(latest.started_at)} · {latest.base_url}
              {latest.alerted ? " · admin emailed" : ""}
            </p>
          )}
          <p className="text-xs text-[#6E6787] mt-1">Runs about 90 seconds after every release and once a day. Emails the admin only if something fails.</p>
        </div>
        <button
          type="button"
          onClick={runNow}
          disabled={running}
          data-testid="admin-release-check-run"
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-full bg-[#3D1A78] hover:bg-[#2c1259] text-white text-xs font-semibold disabled:opacity-60 transition-colors"
        >
          <RefreshCw size={13} className={running ? "animate-spin" : ""} />
          {running ? "Checking…" : "Run check now"}
        </button>
      </div>
      {latest && (
        <ul data-testid="admin-release-check-results">
          {latest.results.map((r) => (
            <CheckRow key={r.name} r={r} />
          ))}
        </ul>
      )}
      {runs.length > 1 && <History runs={runs} />}
    </div>
  );
}
