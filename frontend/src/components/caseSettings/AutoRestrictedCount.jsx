import React, { useEffect, useState } from "react";

import { api } from "../../lib/api";

// Admin-only: how many cases are still restricted by an older automatic (auto_red) update. A number only.
export function AutoRestrictedCount({ onForbidden }) {
  const [count, setCount] = useState(null);
  useEffect(() => {
    api
      .get("/admin/safety-audit-log/auto-restricted")
      .then((r) => setCount(r.data?.count ?? 0))
      .catch((e) => e?.response?.status === 403 && onForbidden?.());
  }, [onForbidden]);
  if (count === null) return null;
  return (
    <section data-testid="auto-restricted-card" className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5">
      <p className="text-base font-bold text-[#1A1330]" data-testid="auto-restricted-count">
        Cases restricted automatically: {count}
      </p>
    </section>
  );
}
