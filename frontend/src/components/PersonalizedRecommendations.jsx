import { Link } from "react-router-dom";
import { Compass, ArrowRight, Sparkles } from "lucide-react";

/**
 * PersonalizedRecommendations
 *
 * A compact card that sits above the generated Mediation Summary and tells
 * the parent — in plain, non-judgmental language — where their preparation
 * shows the most room to grow and which resources will help most.
 *
 * Detection is intentionally *deterministic* (no LLM call): it uses signals
 * that already exist on the summary payload (readiness_score, top_concerns,
 * communication_goals, flexibility_areas, priority_agenda). This keeps the
 * card fast, private, and free.
 *
 * The five focus areas map to concrete next actions inside the app so the
 * recommendation feels actionable, not academic.
 */

const AREAS = {
  communication: {
    label: "Communication",
    diagnosis:
      "Communication appears to be your greatest opportunity for growth. Small, structured changes in how you exchange information can dramatically reduce conflict for your child.",
    actions: [
      { text: "Revisit your Communication Style reflection", to: "/comm-style", testid: "reco-comm" },
      { text: "Read the Parallel Parenting resource", to: "/safety", testid: "reco-parallel" },
      { text: "Sharpen your Foundation Statement — what you'll say and how", to: "/reflection", testid: "reco-foundation" },
      { text: "Refresh the Readiness Check before mediation", to: "/readiness-check", testid: "reco-readiness" },
    ],
  },
  issues: {
    label: "Conflict & concerns",
    diagnosis:
      "You surfaced a heavy set of concerns — more than most parents at this stage. Naming them was courageous. The next step is to hold them alongside safety planning and a clear priority agenda.",
    actions: [
      { text: "Review your Issues & Concerns list — what belongs in mediation?", to: "/issues", testid: "reco-issues" },
      { text: "Read the Family Violence / IPV guide", to: "/safety", testid: "reco-fv" },
      { text: "Prepare your Foundation Statement", to: "/reflection", testid: "reco-foundation" },
    ],
  },
  priority: {
    label: "Priority & flexibility",
    diagnosis:
      "Your priorities are still being sorted. A mediator will move faster when your top three priorities and your flexibility areas are crisp and specific.",
    actions: [
      { text: "Re-rank your Priority Agenda — top 3 non-negotiables", to: "/priority", testid: "reco-priority" },
      { text: "Name at least two flexibility areas", to: "/reflection", testid: "reco-foundation" },
      { text: "Sharpen your Communication Style plan", to: "/comm-style", testid: "reco-comm" },
    ],
  },
  readiness: {
    label: "Mediation readiness",
    diagnosis:
      "You've done real work — and you've also flagged that you're not fully ready yet. That self-awareness is exactly what mediators hope for. A few targeted refreshers will close the gap.",
    actions: [
      { text: "Retake the Readiness Check", to: "/readiness-check", testid: "reco-readiness" },
      { text: "Refine your Foundation Statement", to: "/reflection", testid: "reco-foundation" },
      { text: "Review Parallel Parenting", to: "/safety", testid: "reco-parallel" },
    ],
  },
  strength: {
    label: "You're ready",
    diagnosis:
      "Your preparation is unusually strong — priorities, flexibility areas, and communication goals all line up. Focus now shifts from preparing to arriving well.",
    actions: [
      { text: "Download your summary as a PDF", to: "/summary", testid: "reco-download" },
      { text: "Email your Foundation Statement to your mediator", to: "/summary", testid: "reco-email" },
      { text: "Share the app with your co-parent (invite)", to: "/dashboard", testid: "reco-invite" },
    ],
  },
};

function pickArea(summary) {
  if (!summary) return null;

  const readiness = Number(summary.readiness_score ?? 100);
  const concerns = (summary.top_concerns || []).length;
  const commGoals = (summary.communication_goals || []).length;
  const flex = (summary.flexibility_areas || []).length;
  const priorities = (summary.priority_agenda || []).length;

  // Ordered heuristic: check strongest signals first.
  // These thresholds are intentionally forgiving — the card should surface a
  // useful recommendation for most parents, not just a small edge case.
  if (readiness < 55) return "readiness";
  if (concerns >= 4) return "issues";
  if (commGoals >= 3) return "communication";
  if (priorities < 2 || flex <= 1) return "priority";
  return "strength";
}

export default function PersonalizedRecommendations({ summary }) {
  const areaKey = pickArea(summary);
  if (!areaKey) return null;
  const area = AREAS[areaKey];

  const isStrength = areaKey === "strength";
  const accent = isStrength ? "#2DB5B5" : "#3D1A78";
  const bg = isStrength ? "#E7F7F7" : "#F1EBFA";

  return (
    <div
      className="rounded-2xl p-6 sm:p-7 border border-black/5 shadow-sm"
      style={{ background: bg }}
      data-testid="personalized-recommendations"
    >
      <div className="flex items-center gap-2 text-[0.625rem] uppercase tracking-[0.22em] font-bold" style={{ color: accent }}>
        {isStrength ? <Sparkles size={12} /> : <Compass size={12} />}
        Based on your responses
      </div>
      <h3
        className="font-serif text-2xl sm:text-3xl mt-1 leading-tight"
        style={{ color: "#1A1330" }}
        data-testid="personalized-recommendations-headline"
      >
        {area.label}
      </h3>
      <p className="text-[#4B4567] mt-2 leading-relaxed max-w-2xl">
        {area.diagnosis}
      </p>

      <div className="mt-5">
        <div className="text-xs uppercase tracking-[0.2em] text-[#6E6787] mb-2">
          We recommend
        </div>
        <ul className="space-y-2">
          {area.actions.map((a) => (
            <li key={a.testid}>
              <Link
                to={a.to}
                data-testid={a.testid}
                className="group inline-flex items-center gap-2 text-[#1A1330] hover:text-[#3D1A78] transition-colors"
              >
                <span
                  className="w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ background: accent }}
                  aria-hidden="true"
                />
                <span className="underline-offset-4 group-hover:underline">
                  {a.text}
                </span>
                <ArrowRight
                  size={14}
                  className="shrink-0 opacity-0 -translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all"
                />
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
