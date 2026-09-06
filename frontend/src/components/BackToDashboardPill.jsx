/**
 * BackToDashboardPill.jsx — floating "← Dashboard" pill that appears on
 * every authenticated page so users can never get trapped mid-flow.
 *
 * Behaviour:
 *   - Fixed bottom-left, above the footer.
 *   - Hidden when there is no signed-in user (public routes: landing,
 *     login, register, marketing, verify links, shared reports, etc.).
 *   - Hidden on the dashboard itself (would be a no-op).
 *   - Hidden on the onboarding intake screen (a modal-like flow that
 *     must be completed before returning).
 *   - Keyboard accessible; skips print output.
 */
import React from "react";
import { Link, useLocation } from "react-router-dom";
import { Home } from "lucide-react";

import { useAuth } from "../context/AuthContext";

// Routes where we intentionally do NOT show the pill even if the user is
// signed in — they are either the dashboard itself or a modal-like flow
// (auth callback, onboarding) where the primary action must be taken first.
const HIDDEN_PREFIXES = [
  "/dashboard",
  "/onboarding/",
  "/auth/callback",
  "/auth/magic",
  "/auth/setup",
];

// Public / share routes — never show the pill even if a user cookie is
// present, because these pages are shared with people outside the app
// (mediators, attorneys) who shouldn't see internal navigation.
const PUBLIC_PREFIXES = [
  "/login",
  "/register",
  "/signup",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
  "/verify",
  "/invite",
  "/join",
  "/joint-report/shared",
  "/joint-agreement/shared",
  "/shared",
  "/survey",
  "/mediator-badge",
  "/privacy",
  "/terms",
  "/accessibility",
  "/methodology",
  "/data-retention",
  "/legal",
  "/foundation/demo",
  "/safety", // public safety resources page (not /safety-assessment)
  "/watch",
];

function matchesPrefix(pathname, p) {
  // Exact match or a proper sub-route (never a partial-word match).
  return pathname === p || pathname.startsWith(`${p}/`);
}

function isHidden(pathname) {
  if (pathname === "/") return true;
  for (const p of HIDDEN_PREFIXES) {
    if (matchesPrefix(pathname, p.replace(/\/$/, ""))) return true;
  }
  return false;
}

function isPublicRoute(pathname) {
  if (pathname === "/") return true;
  for (const p of PUBLIC_PREFIXES) {
    if (matchesPrefix(pathname, p)) return true;
  }
  return false;
}

export default function BackToDashboardPill() {
  const location = useLocation();
  const { user } = useAuth();

  // No pill for signed-out visitors on public routes.
  if (!user) return null;
  if (isHidden(location.pathname)) return null;
  if (isPublicRoute(location.pathname)) return null;

  return (
    <Link
      to="/dashboard"
      data-testid="back-to-dashboard-pill"
      aria-label="Back to main menu"
      title="Back to main menu"
      className="fixed left-4 bottom-4 sm:left-5 sm:bottom-5 z-40 inline-flex items-center gap-2 h-11 px-4 rounded-full bg-[#1A1330] text-white shadow-lg shadow-[#1A1330]/25 hover:bg-[#2A1F52] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3D1A78] focus-visible:ring-offset-2 transition-colors print:hidden"
    >
      <Home size={16} strokeWidth={2.2} />
      <span className="text-sm font-semibold">Main menu</span>
    </Link>
  );
}
