import React from "react";
import DeepDiveCompareHub from "../components/deepdive/DeepDiveCompareHub";

export default function SpecialNeedsV2PsychologicalDeepDiveCompare() {
  return (
    <DeepDiveCompareHub
      pathway={{
        testidPrefix: "psych-deep-compare",
        eyebrow: "Psychological Deep Dive · Co-Parent Comparison",
        hero: "See where you and your co-parent already agree on emotional and behavioural care.",
        description:
          "When both parents complete the Psychological / Behavioural Deep Dive and each of you " +
          "explicitly opts in, you can view a neutral, side-by-side comparison. This is not a " +
          "diagnosis and never labels one parent as right — its purpose is to help a mediator, " +
          "therapist, or family professional focus the conversation on the child.",
        safetyNoun: "psychological / behavioural notes",
        backTo: "/special-needs-v2/psychological-deep-dive",
        backLabel: "Back to Psychological Deep Dive",
        apiPrefix: "/psych-deep/compare",
        viewRouteBase: "/special-needs-v2/psychological-deep-dive/compare",
      }}
    />
  );
}
