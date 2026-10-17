import React, { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

/**
 * DomainGuard — iter249 DevOps Split (code-side preparation).
 *
 * NORTH_STAR.md commits to a rigid two-site split:
 *   • sacoparentsapp.online    → parent journey only
 *   • sacoparentsalign.online  → professional (Align + admin) only
 *
 * This component enforces that split at the ROUTE level, so that
 * even if DNS misconfiguration or a sticky bookmark sends a parent
 * to the Align hostname (or a professional to the parent hostname),
 * they're bounced to the correct site with a human-readable
 * explainer card before the auto-redirect fires.
 *
 * In the current (preview/local) environment both hostnames are
 * unknown — `window.location.hostname` is
 * `prepared-parents.preview.emergentagent.com`. The guard is a
 * no-op there: every route works exactly as it did before.
 *
 * Env config (frontend/.env):
 *   REACT_APP_PARENT_HOSTNAME   e.g. sacoparentsapp.online
 *   REACT_APP_ALIGN_HOSTNAME    e.g. sacoparentsalign.online
 *   REACT_APP_PARENT_URL        e.g. https://sacoparentsapp.online
 *   REACT_APP_ALIGN_URL         e.g. https://sacoparentsalign.online
 *
 * Usage in App.js:
 *   <Route path="/" element={<DomainGuard side="parent"><SacoparentsPortal/></DomainGuard>}/>
 *   <Route path="/align" element={<DomainGuard side="align"><Align/></DomainGuard>}/>
 *   <Route path="/admin" element={<DomainGuard side="align"><Admin/></DomainGuard>}/>
 */

const AUTO_REDIRECT_MS = 2500;

function readHostname() {
  if (typeof window === "undefined") return "";
  return (window.location.hostname || "").toLowerCase();
}

function envHost(name) {
  return (process.env[name] || "").toLowerCase().trim();
}

function envUrl(name) {
  return (process.env[name] || "").trim();
}

/**
 * `verdict` returns one of:
 *   { ok: true }                              — current host matches the required side (or no enforcement)
 *   { ok: false, otherSide, otherUrl, msg }   — redirect needed
 */
export function evaluateDomainVerdict({ side, hostname = readHostname() }) {
  const parentHost = envHost("REACT_APP_PARENT_HOSTNAME");
  const alignHost = envHost("REACT_APP_ALIGN_HOSTNAME");
  const parentUrl = envUrl("REACT_APP_PARENT_URL");
  const alignUrl = envUrl("REACT_APP_ALIGN_URL");

  // If either hostname isn't configured (preview / local / staging),
  // the guard is a no-op. This matters: dev loops should never hit a
  // redirect card.
  if (!parentHost || !alignHost) return { ok: true };

  // If the current hostname isn't one of the two production
  // hostnames (preview, staging, localhost), also no-op.
  if (hostname !== parentHost && hostname !== alignHost) {
    return { ok: true };
  }

  // We're on a production hostname. Enforce the split.
  if (side === "parent" && hostname === alignHost) {
    return {
      ok: false,
      otherSide: "parent",
      otherUrl: parentUrl,
      msg: "This page is for parents working on their own co-parenting journey. We'll send you to the right site now.",
    };
  }
  if (side === "align" && hostname === parentHost) {
    return {
      ok: false,
      otherSide: "align",
      otherUrl: alignUrl,
      msg: "This page is for professionals reviewing a case. We'll send you to the right site now.",
    };
  }
  return { ok: true };
}

export default function DomainGuard({ side, children }) {
  const location = useLocation();
  const verdict = useMemo(
    () => evaluateDomainVerdict({ side }),
    // Re-evaluate on route change; `hostname` doesn't change at
    // runtime, but reading it inside the memo keeps the verdict
    // deterministic across hot reloads.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [side, location.pathname]
  );
  const [countdown, setCountdown] = useState(
    Math.ceil(AUTO_REDIRECT_MS / 1000)
  );

  useEffect(() => {
    if (verdict.ok) return undefined;
    if (!verdict.otherUrl) return undefined; // nothing to redirect TO
    const start = Date.now();
    const tick = setInterval(() => {
      const remaining = Math.max(
        0,
        Math.ceil((AUTO_REDIRECT_MS - (Date.now() - start)) / 1000)
      );
      setCountdown(remaining);
      if (remaining <= 0) {
        clearInterval(tick);
        // Preserve the path on the other site so a mediator who
        // bookmarked `/admin/reviewers` lands there, not just at
        // the Align root.
        window.location.replace(
          verdict.otherUrl.replace(/\/$/, "") + location.pathname + location.search
        );
      }
    }, 250);
    return () => clearInterval(tick);
  }, [verdict, location.pathname, location.search]);

  if (verdict.ok) return children;

  const label =
    verdict.otherSide === "parent"
      ? "SA CoParents (parent journey)"
      : "SA CoParents Align (professional view)";
  const tint =
    verdict.otherSide === "parent"
      ? "bg-purple-50 border-purple-300 text-purple-900"
      : "bg-emerald-50 border-emerald-300 text-emerald-900";
  const btnTint =
    verdict.otherSide === "parent"
      ? "bg-purple-700 hover:bg-purple-800"
      : "bg-emerald-700 hover:bg-emerald-800";

  return (
    <div
      className="min-h-screen bg-slate-50 flex items-center justify-center p-6"
      data-testid="domain-guard-redirect"
    >
      <div
        className={`max-w-md w-full rounded-2xl border-2 p-6 shadow-sm space-y-4 ${tint}`}
      >
        <div className="text-[0.625rem] uppercase tracking-widest font-bold opacity-70">
          Wrong site
        </div>
        <h1 className="text-lg font-bold leading-tight">
          You're a step away.
        </h1>
        <p className="text-sm leading-snug">{verdict.msg}</p>
        <p className="text-xs opacity-75">
          You'll be sent to <span className="font-mono">{label}</span>{" "}
          in <span className="font-bold">{countdown}s</span>.
        </p>
        {verdict.otherUrl && (
          <a
            href={
              verdict.otherUrl.replace(/\/$/, "") +
              location.pathname +
              location.search
            }
            data-testid="domain-guard-go-now"
            className={`block text-center ${btnTint} text-white font-bold py-2.5 rounded-xl text-sm transition`}
          >
            Take me there now →
          </a>
        )}
      </div>
    </div>
  );
}
