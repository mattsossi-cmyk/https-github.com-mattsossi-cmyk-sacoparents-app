import React from "react";
import { Link } from "react-router-dom";

/**
 * DoorsGateway — landing screen with two entry doors (Self-Guided /
 * Court Ordered) plus a sync-status chip and (when applicable) a
 * kudos-streak "tone-safe streak" badge.
 */
export function DoorsGateway({
  onEnterParent,
  onEnterCourt,
  user,
  syncStatus,
  kudosStreak,
}) {
  return (
    <div className="space-y-4" data-testid="screen-gateway">
      <div className="text-center py-2">
        <span className="bg-purple-100 text-purple-900 text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider border border-purple-200">
          San Antonio, TX Methodology
        </span>
        <h2 className="text-xl font-bold text-slate-800 mt-2">
          Welcome to SA CoParents
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Select your entry path to access official assessments, foundation
          statements, and de-escalation tools.
        </p>
      </div>

      {/* Kudos streak badge (only when >=2 consecutive kudos days) */}
      {kudosStreak >= 2 && (
        <div
          data-testid="kudos-streak-badge"
          className="mx-auto max-w-xs flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-900 px-3 py-2 rounded-2xl shadow-sm"
        >
          <span className="text-lg" aria-hidden>🔥</span>
          <div className="flex-1">
            <div
              data-testid="kudos-streak-count"
              className="font-bold text-sm leading-tight"
            >
              {kudosStreak}-day tone-safe streak
            </div>
            <div className="text-[10px] text-amber-800">
              Consecutive days you kept a hot message BIFF-safe. Keep it going.
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-4">
        {/* DOOR 1 */}
        <div
          onClick={onEnterParent}
          data-testid="door-parent-journey"
          className="bg-white p-5 rounded-2xl shadow-sm border-2 border-purple-100 hover:border-purple-600 cursor-pointer transition flex flex-col justify-between space-y-3 group"
        >
          <div className="flex justify-between items-start">
            <div className="p-3 bg-purple-50 text-purple-700 rounded-xl group-hover:bg-purple-800 group-hover:text-white transition">
              <i className="fa-solid fa-heart-pulse text-2xl"></i>
            </div>
            <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2.5 py-0.5 rounded-full">
              Door 1 · Self-Guided
            </span>
          </div>
          <div>
            <h3 className="font-bold text-slate-800 text-base">Coparenting Journey</h3>
            <p className="text-xs text-slate-500 mt-1">
              Reflect independently, access existing co-parenting assessments,
              create a Foundation Statement PDF, and utilize BIFF tools.
            </p>
          </div>
          <div className="flex items-center text-xs font-bold text-purple-700 group-hover:translate-x-1 transition">
            <span>Enter Coparenting Path</span>{" "}
            <i className="fa-solid fa-arrow-right ml-1"></i>
          </div>
        </div>

        {/* DOOR 2 */}
        <div
          onClick={onEnterCourt}
          data-testid="door-court-path"
          className="bg-white p-5 rounded-2xl shadow-sm border-2 border-slate-200 hover:border-purple-900 cursor-pointer transition flex flex-col justify-between space-y-3 group"
        >
          <div className="flex justify-between items-start">
            <div className="p-3 bg-slate-100 text-slate-700 rounded-xl group-hover:bg-purple-950 group-hover:text-white transition">
              <i className="fa-solid fa-gavel text-2xl"></i>
            </div>
            <span className="bg-purple-100 text-purple-900 text-[10px] font-bold px-2.5 py-0.5 rounded-full">
              Door 2 · Professional Key
            </span>
          </div>
          <div>
            <h3 className="font-bold text-slate-800 text-base">Court Ordered Path</h3>
            <p className="text-xs text-slate-500 mt-1">
              Accept professional key from mediator or attorney at{" "}
              <strong>sacoparentsalign.com</strong> for connected joint
              assessments.
            </p>
          </div>
          <div className="flex items-center text-xs font-bold text-slate-700 group-hover:translate-x-1 transition">
            <span>Enter Professional Key Door</span>{" "}
            <i className="fa-solid fa-arrow-right ml-1"></i>
          </div>
        </div>
      </div>

      {/* Sync / Sign-in chip */}
      <div className="text-center pt-2" data-testid="sync-chip">
        {user ? (
          <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-800 px-3 py-1.5 rounded-full text-[11px] font-semibold">
            <i className="fa-solid fa-cloud-arrow-up"></i>
            <span data-testid="sync-status">
              {syncStatus === "syncing"
                ? "Syncing across devices…"
                : syncStatus === "offline"
                ? "Offline — changes will sync when you're back"
                : syncStatus === "error"
                ? "Sync paused — your work is safe locally"
                : `Synced as ${user.email || user.name || "your account"}`}
            </span>
          </div>
        ) : (
          <Link
            to="/login"
            data-testid="sync-signin-link"
            className="inline-flex items-center gap-2 bg-white border border-purple-200 text-purple-800 px-3 py-1.5 rounded-full text-[11px] font-semibold hover:bg-purple-50 transition"
          >
            <i className="fa-solid fa-cloud"></i>
            Sign in to sync across devices
          </Link>
        )}
      </div>
    </div>
  );
}
