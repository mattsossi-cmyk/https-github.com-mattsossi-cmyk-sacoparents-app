import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";

const Ctx = createContext(null);

export function FooterLinkProvider({ children }) {
  const [count, setCount] = useState(0);
  const value = useMemo(() => ({ count, add: () => setCount((n) => n + 1), drop: () => setCount((n) => n - 1) }), [count]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

// Footers that already show "Who can see my information" call this so the global line stays hidden.
export function useOwnFooterLink() {
  const ctx = useContext(Ctx);
  useEffect(() => {
    if (!ctx) return undefined;
    ctx.add();
    return ctx.drop;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

// "Who can see my information" on every page that has no footer of its own.
export function GlobalFooterLink() {
  const ctx = useContext(Ctx);
  const { pathname } = useLocation();
  if (!ctx || ctx.count > 0 || pathname === "/who-can-see-my-information") return null;
  return (
    <div className="no-print py-4 text-center text-xs" data-testid="global-who-can-see-footer">
      <Link
        to="/who-can-see-my-information"
        data-testid="global-who-can-see-footer-link"
        className="font-semibold text-[#3D1A78] underline underline-offset-2"
      >
        Who can see my information
      </Link>
    </div>
  );
}
