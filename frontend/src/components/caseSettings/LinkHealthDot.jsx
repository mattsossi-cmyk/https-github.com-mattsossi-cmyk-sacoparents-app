import React from "react";

// Green when the Align link looks healthy, amber when it needs a look. Text for screen readers and on hover.
export function LinkHealthDot({ ok, testid = "align-link-dot" }) {
  if (ok === null || ok === undefined) return null;
  const label = ok ? "Align link OK" : "Align link needs attention";
  return (
    <span title={label} data-testid={testid} data-ok={ok ? "true" : "false"} className="inline-flex items-center">
      <span aria-hidden="true" className={`inline-block h-2 w-2 rounded-full ring-2 ring-white ${ok ? "bg-emerald-500" : "bg-amber-500"}`} />
      <span className="sr-only">{label}</span>
    </span>
  );
}
