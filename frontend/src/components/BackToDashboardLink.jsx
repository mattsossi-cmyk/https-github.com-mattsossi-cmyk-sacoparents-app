/**
 * BackToDashboardLink.jsx — a small, standardised inline link placed
 * near the top of every report / assessment page. Complements the
 * floating pill (`BackToDashboardPill`) so users can always find their
 * way back to the main menu without scrolling.
 *
 * The link is deliberately understated so it never competes with the
 * report content, but it is always the first focusable element on the
 * page for keyboard users.
 */
import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

export default function BackToDashboardLink({
  label = "Back to main menu",
  className = "",
  testId = "back-to-dashboard-link",
}) {
  return (
    <Link
      to="/dashboard"
      data-testid={testId}
      className={`inline-flex items-center gap-1.5 text-xs sm:text-sm text-[#4B4567] hover:text-[#3D1A78] transition-colors ${className}`}
    >
      <ArrowLeft size={14} strokeWidth={2.2} />
      <span>{label}</span>
    </Link>
  );
}
