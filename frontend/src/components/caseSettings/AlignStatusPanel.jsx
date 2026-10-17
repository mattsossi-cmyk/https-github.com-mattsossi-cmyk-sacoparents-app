import React, { useEffect, useState } from "react";

import { api } from "../../lib/api";

const REASONS = {
  bad_signature: "Wrong signature",
  old_timestamp: "Too old",
  invalid_body: "Unreadable",
  replay: "Sent twice",
};
const when = (iso) => (iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "—");

function Row({ label, children, testid }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 py-2 border-t border-[#F0EDF6] first:border-t-0">
      <dt className="text-xs font-semibold uppercase tracking-wider text-[#4B4567]">{label}</dt>
      <dd className="text-sm text-[#1A1330]" data-testid={testid}>{children}</dd>
    </div>
  );
}

// Admin-only: are Align's updates arriving and being accepted? Times and reasons only, no case details.
export function AlignStatusPanel({ onForbidden }) {
  const [s, setS] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.get("/admin/safety-audit-log/align-status")
      .then((r) => setS(r.data))
      .catch((e) => (e?.response?.status === 403 ? onForbidden() : setFailed(true)));
  }, [onForbidden]);

  if (failed) return <p className="text-sm text-[#A93636]" data-testid="align-status-error">Couldn&apos;t load the Align status.</p>;
  if (!s) return <p className="text-sm text-[#4B4567]" data-testid="align-status-loading">Loading Align status…</p>;

  const refused = Object.values(s.rejected_30d).reduce((a, b) => a + b, 0);
  const quiet = s.silence?.warn;
  const result = s.last_update?.result;
  return (
    <section data-testid="align-status-panel" className="rounded-2xl border border-[#E5E0EE] bg-white px-4 py-3">
      <h2 className="text-base md:text-lg font-semibold text-[#1A1330]">Updates from Align</h2>
      {quiet && (
        <p role="status" data-testid="align-status-silence" className="mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-[#7A4A00]">
          {s.silence.days_since == null
            ? "No updates from Align yet. Check that Align has the webhook address and secret."
            : `No updates from Align in ${s.silence.days_since} days. If cases have changed in Align since then, check that Align has the webhook address and secret.`}
        </p>
      )}
      <dl className="mt-2">
        <Row label="Last update" testid="align-status-last-update">
          {s.last_update ? (
            <>
              {when(s.last_update.at)}{" "}
              <span data-testid="align-status-last-result" className={`ml-1 rounded-full px-2 py-0.5 text-xs font-bold ${result === "applied" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"}`}>
                {result === "applied" ? "Applied" : "Ignored"}
              </span>
            </>
          ) : "No updates received yet"}
        </Row>
        <Row label="Last applied" testid="align-status-last-applied">{when(s.last_applied_at)}</Row>
        <Row label="Refused, last 30 days" testid="align-status-refused-total">{refused}</Row>
      </dl>
      {refused > 0 && (
        <ul className="mt-1 flex flex-wrap gap-2" data-testid="align-status-reasons">
          {Object.entries(s.rejected_30d).filter(([, n]) => n).map(([k, n]) => (
            <li key={k} data-testid={`align-status-reason-${k}`} className="rounded-full bg-[#F8F7FC] border border-[#E5E0EE] px-2.5 py-1 text-xs text-[#3B3552]">
              {REASONS[k]}: <span className="font-bold">{n}</span>
            </li>
          ))}
        </ul>
      )}
      {s.last_rejected && (
        <p className="mt-2 text-xs text-[#4B4567]" data-testid="align-status-last-rejected">
          Last refused: {when(s.last_rejected.at)} ({REASONS[s.last_rejected.reason] || s.last_rejected.reason})
        </p>
      )}
      {s.rejected_30d.bad_signature > 0 && (
        <p className="mt-2 text-xs text-[#8A5500]" data-testid="align-status-secret-hint">
          Wrong-signature refusals usually mean Align and this app are using different webhook secrets.
        </p>
      )}
    </section>
  );
}
