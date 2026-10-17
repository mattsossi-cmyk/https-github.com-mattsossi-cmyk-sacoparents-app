/**
 * InterventionComplianceCard — Compact Dashboard widget that shows the
 * parent's weekly intervention compliance %. Self-hides for parents with
 * no interventions yet (i.e., who have not completed any assessment
 * that produces enforced interventions).
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, ArrowRight, Loader2, Flame, Award } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

export default function InterventionComplianceCard() {
  const [log, setLog] = useState(null);
  const [streak, setStreak] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [logRes, streakRes] = await Promise.all([
          api.get("/interventions/log"),
          api.get("/interventions/streak"),
        ]);
        setLog(logRes.data);
        setStreak(streakRes.data);
      } catch (err) {
        logError("Compliance card load failed", err);
        setLog(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className="rounded-3xl border border-[#E5E0EE] bg-white p-5 inline-flex items-center gap-2 text-xs text-[#4B4567]">
        <Loader2 size={12} className="animate-spin" /> Loading compliance…
      </div>
    );
  }
  if (!log || log.summary.total === 0) return null;

  const pct = log.summary.compliance_pct;
  const current = streak?.current_streak || 0;
  const earnedCount = (streak?.badges || []).filter((b) => b.earned).length;

  return (
    <Link
      to="/interventions"
      className="block rounded-3xl border border-[#E5E0EE] bg-white p-5 hover:border-[#3D1A78] transition"
      data-testid="compliance-dashboard-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="inline-flex items-center gap-2">
          <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-[#F0EEF8] text-[#3D1A78]">
            <CheckCircle2 size={16} />
          </span>
          <div>
            <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
              This week's compliance
            </div>
            <div className="font-serif text-lg text-[#1A1330]">
              Interventions you're actually following
            </div>
          </div>
        </div>
        <span
          className="text-2xl font-bold text-[#1A1330]"
          data-testid="compliance-card-pct"
        >
          {pct.toFixed(0)}%
        </span>
      </div>

      <div className="h-2 mt-3 rounded-full bg-[#F0EEF8] overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5]"
          style={{ width: `${Math.max(1, pct)}%` }}
        />
      </div>

      {/* Streak + badges row */}
      {streak && (
        <div
          className="mt-3 flex items-center gap-3 flex-wrap"
          data-testid="compliance-card-streak"
        >
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.6875rem] font-bold ${
              current > 0
                ? "bg-[#FFF5DA] text-[#8A5B00]"
                : "bg-[#F0EEF8] text-[#4B4567]"
            }`}
          >
            <Flame size={12} className={current > 0 ? "text-[#E8A628]" : "text-[#B7AECC]"} />
            {current} wk streak
          </span>
          {earnedCount > 0 && (
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.6875rem] font-bold bg-[#F0EEF8] text-[#3D1A78]"
              data-testid="compliance-card-badges"
            >
              <Award size={12} className="text-[#E8A628]" />
              {earnedCount} badge{earnedCount === 1 ? "" : "s"}
            </span>
          )}
          {streak.next_badge && (
            <span className="text-[0.6875rem] text-[#4B4567]">
              Next: {streak.next_badge.label} ({current}/{streak.next_badge.weeks})
            </span>
          )}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between gap-2 text-xs text-[#4B4567]">
        <span>
          {log.summary.followed} of {log.summary.total} interventions ticked
        </span>
        <span className="inline-flex items-center gap-1.5 text-[#3D1A78] font-bold">
          Log this week <ArrowRight size={12} />
        </span>
      </div>
    </Link>
  );
}
