/**
 * ScreenGuardrailPanel — Prominent post-result panel making explicit
 * what this screen does NOT decide (mediation, custody, visitation,
 * protective orders). Reinforces that the screen recommends a
 * communication *structure*, not clinical or legal outcomes.
 *
 * When `level` is 1 or 2 (highest concern), an additional
 * anti-mutualization block appears: communication coaching between the
 * parent and an abusive co-parent is NOT recommended. See a DV
 * advocate first.
 */
import { ShieldAlert, AlertTriangle } from "lucide-react";

export default function ScreenGuardrailPanel({ level }) {
  const highConcern = level === 1 || level === 2;
  return (
    <div className="mt-6 space-y-4" data-testid="screen-guardrail-panel">
      <div className="rounded-3xl border-2 border-[#3D1A78] bg-[#F8F5FF] p-5 sm:p-7">
        <div className="flex items-center gap-2 mb-3">
          <ShieldAlert size={14} className="text-[#3D1A78]" />
          <div className="text-[0.6875rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            What this screen decides — and what it does not
          </div>
        </div>
        <p className="text-sm text-[#1A1330] leading-relaxed mb-3">
          This screen recommends a <strong>communication structure</strong>{" "}
          for you to consider. It does <strong>not</strong> decide
          mediation suitability, visitation, custody, protective orders,
          or any other legal or clinical outcome.
        </p>
        <p className="text-sm text-[#4B4567] leading-relaxed mb-3">
          Decisions of that weight require a qualified human assessment.
          Please review this result with:
        </p>
        <ul className="text-sm text-[#4B4567] space-y-1.5 mb-3">
          <li className="flex gap-2"><span className="text-[#3D1A78] mt-1">•</span>a <strong>family law attorney</strong> — for legal rights and protections</li>
          <li className="flex gap-2"><span className="text-[#3D1A78] mt-1">•</span>a <strong>licensed clinician or forensic evaluator</strong> — for clinical judgement</li>
          <li className="flex gap-2"><span className="text-[#3D1A78] mt-1">•</span>a <strong>domestic-violence advocate</strong> — for safety planning</li>
        </ul>
        <p className="text-[0.6875rem] text-[#6A5799] italic">
          This screen has not been independently validated in custody or
          mediation populations. It is not the Danger Assessment,
          MASIC-S, or HITS. Its scoring is heuristic.
        </p>
      </div>

      {highConcern && (
        <div
          className="rounded-3xl border-2 border-[#9A3A23] bg-[#FCE3DC] p-5 sm:p-7"
          data-testid="anti-mutualization-panel"
        >
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={14} className="text-[#9A3A23]" />
            <div className="text-[0.6875rem] uppercase tracking-[0.22em] font-bold text-[#9A3A23]">
              A note about communication coaching
            </div>
          </div>
          <p className="text-sm text-[#1A1330] leading-relaxed mb-2">
            Your responses raised concerns that indicate coercive control,
            intimidation, or family violence may be present. In situations
            like these, communication coaching between you and the other
            parent is <strong>not the right first step</strong>.
          </p>
          <p className="text-sm text-[#1A1330] leading-relaxed mb-2">
            Coaching a survivor to communicate "better" with someone who
            is coercive can shift responsibility onto the person who is
            experiencing harm. It is not what you need right now.
          </p>
          <p className="text-sm text-[#1A1330] leading-relaxed">
            Please speak with a <strong>domestic-violence advocate</strong>{" "}
            or a <strong>licensed clinician with intimate-partner violence
            expertise</strong> before making decisions about direct
            communication. The National DV Hotline is{" "}
            <a href="tel:18007997233" className="underline font-bold">
              1-800-799-7233
            </a>.
          </p>
        </div>
      )}
    </div>
  );
}
