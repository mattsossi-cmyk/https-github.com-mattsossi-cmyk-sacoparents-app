import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import { useAuth } from "../context/AuthContext";

/**
 * SignedInEscapeHatch — a subtle "Back to your dashboard" affordance for
 * public shared-view pages.
 *
 * Public shared views (`/joint-report/shared/:token`,
 * `/joint-agreement/shared/:token`) are designed for reviewers
 * (mediators / attorneys) who aren't logged in — so we intentionally
 * omit app navigation. But if a signed-in parent lands there (e.g. by
 * opening the link they just copied to send to their mediator, or from
 * a bookmark), there is no in-app way back — closing the tab is the
 * only exit. On a PWA / installed webview that reads as "the app is
 * stuck," which is what parents were reporting.
 *
 * This component renders only when the AuthContext has a real user;
 * for anonymous reviewers it returns null so their view stays clean.
 * Both shared views are inside <AuthProvider> in App.js so the hook
 * call is safe unconditionally.
 */
export default function SignedInEscapeHatch({
  to = "/dashboard",
  label = "Back to your dashboard",
  testid = "signed-in-escape-hatch",
}) {
  const { user } = useAuth();
  if (!user) return null;
  if (user.is_guest) return null;
  return (
    <div className="mb-4">
      <Link
        to={to}
        className="inline-flex items-center gap-1.5 text-xs text-[#4B4567] hover:text-[#3D1A78] underline underline-offset-2"
        data-testid={testid}
      >
        <ArrowLeft size={12} /> {label}
      </Link>
    </div>
  );
}
