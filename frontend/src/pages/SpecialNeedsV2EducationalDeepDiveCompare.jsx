import React from "react";
import DeepDiveCompareHub from "../components/deepdive/DeepDiveCompareHub";

export default function SpecialNeedsV2EducationalDeepDiveCompare() {
  return (
    <DeepDiveCompareHub
      pathway={{
        testidPrefix: "edu-deep-compare",
        eyebrow: "Educational Deep Dive · Co-Parent Comparison",
        hero: "See where you and your co-parent already agree.",
        description:
          'When both parents complete their own Educational Deep Dive and each of you explicitly opts in, ' +
          "you can view a neutral, side-by-side comparison of every section. Nothing is ever labeled as " +
          '"correct" or "wrong" — the goal is to spotlight your shared ground and the areas where a ' +
          "coordinated conversation with the school will help most.",
        safetyNoun: "Educational Deep Dive answers",
        backTo: "/special-needs-v2/educational-deep-dive",
        backLabel: "Back to Educational Deep Dive",
        apiPrefix: "/edu-deep/compare",
        viewRouteBase: "/special-needs-v2/educational-deep-dive/compare",
      }}
    />
  );
}
