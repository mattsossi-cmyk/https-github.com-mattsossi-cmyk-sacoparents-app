import React, { useEffect, useState } from "react";

import { api } from "../../lib/api";

const fmt = (d) => new Date(`${d}T00:00:00Z`).toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" });

// Admin-only: how many case setting changes arrived each day. Counts only.
export function DailyCountsTable({ onForbidden }) {
  const [days, setDays] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.get("/admin/safety-audit-log/daily-counts")
      .then((r) => setDays(r.data.days))
      .catch((e) => (e?.response?.status === 403 ? onForbidden() : setFailed(true)));
  }, [onForbidden]);

  if (failed) return <p className="text-sm text-[#7A2E2E]" data-testid="admin-daily-counts-error">Couldn&apos;t load the daily counts.</p>;
  if (!days) return <p className="text-sm text-[#6E6787]" data-testid="admin-daily-counts-loading">Loading daily counts…</p>;

  const total = (k) => days.reduce((s, d) => s + d[k], 0);
  return (
    <section data-testid="admin-daily-counts" className="rounded-2xl border border-[#E5E0EE] bg-white overflow-hidden">
      <header className="px-4 py-3 border-b border-[#E5E0EE]">
        <h2 className="text-base md:text-lg font-semibold text-[#1A1330]">Daily changes, last 30 days</h2>
        <p className="text-xs text-[#6E6787]">Counts only (UTC days). Updates from Align that were applied or ignored, refused attempts, and audit log downloads.</p>
      </header>
      <div tabIndex={0} role="region" aria-label="Daily changes table" className="max-h-96 overflow-auto">
        <table className="w-full text-xs sm:text-sm" data-testid="admin-daily-counts-table">
          <thead className="sticky top-0 bg-[#F8F7FC] text-left text-[0.625rem] sm:text-xs uppercase sm:tracking-wider text-[#4B4567]">
            <tr>
              <th className="px-2 sm:px-4 py-2">Day</th>
              <th className="px-2 sm:px-4 py-2 text-right">Applied</th>
              <th className="px-2 sm:px-4 py-2 text-right">Ignored</th>
              <th className="px-2 sm:px-4 py-2 text-right">Refused</th>
              <th className="px-2 sm:px-4 py-2 text-right">Downloads</th>
            </tr>
          </thead>
          <tbody>
            <tr className="font-semibold bg-[#FBFAFE]" data-testid="admin-daily-counts-total">
              <td className="px-2 sm:px-4 py-2">Total</td>
              <td className="px-2 sm:px-4 py-2 text-right" data-testid="admin-daily-total-applied">{total("applied")}</td>
              <td className="px-2 sm:px-4 py-2 text-right" data-testid="admin-daily-total-ignored">{total("ignored")}</td>
              <td className="px-2 sm:px-4 py-2 text-right" data-testid="admin-daily-total-rejected">{total("rejected")}</td>
              <td className="px-2 sm:px-4 py-2 text-right" data-testid="admin-daily-total-downloads">{total("downloads")}</td>
            </tr>
            {days.map((d) => (
              <tr key={d.date} className="border-t border-[#F0EDF6]" data-testid={`admin-daily-row-${d.date}`}>
                <td className="px-2 sm:px-4 py-2 whitespace-nowrap text-[#4B4567]">{fmt(d.date)}</td>
                <td className="px-2 sm:px-4 py-2 text-right tabular-nums">{d.applied}</td>
                <td className="px-2 sm:px-4 py-2 text-right tabular-nums">{d.ignored}</td>
                <td className="px-2 sm:px-4 py-2 text-right tabular-nums">{d.rejected}</td>
                <td className="px-2 sm:px-4 py-2 text-right tabular-nums">{d.downloads}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
