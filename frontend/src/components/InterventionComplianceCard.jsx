/**
 * InterventionComplianceCard — Compact Dashboard widget that shows the
 * parent's weekly intervention compliance %. Self-hides for parents with
 * no interventions yet (i.e., who have not completed any assessment
 * that produces enforced interventions).
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, ArrowRight, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

export default function InterventionComplianceCard() {
  const [log, setLog] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/interventions/log");
        setLog(data);
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
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
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
