import React from "react";
import DeepDiveCompareHub from "../components/deepdive/DeepDiveCompareHub";

export default function SpecialNeedsV2EducationalDeepDiveCompare() {
  return (
    <DeepDiveCompareHub
      pathway={{
        testidPrefix: "edu-deep-compare",
        eyebrow: "Coparenting Education Check In Summary",
        hero: "See where you and your co-parent already agree.",
        description:
          "When both parents complete their own Coparenting Education Check In and each of you explicitly opts in, " +
          "you can view a neutral, side-by-side Coparenting Education Check In Summary. Nothing is ever labeled as " +
          '"correct" or "wrong" — the goal is to spotlight your shared ground and the areas where a ' +
          "coordinated conversation with the school will help most.",
        safetyNoun: "Coparenting Education Check In answers",
        backTo: "/special-needs-v2/educational-deep-dive",
        backLabel: "Back to Educational Deep Dive",
        apiPrefix: "/edu-deep/compare",
        viewRouteBase: "/special-needs-v2/educational-deep-dive/compare",
      }}
    />
  );
}
