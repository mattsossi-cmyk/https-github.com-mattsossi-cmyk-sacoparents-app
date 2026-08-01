import React from "react";
import DeepDiveCompareView from "../components/deepdive/DeepDiveCompareView";

export default function SpecialNeedsV2PsychologicalDeepDiveCompareView() {
  return (
    <DeepDiveCompareView
      pathway={{
        testidPrefix: "psych-deep-compare",
        eyebrow: "Psychological Deep Dive · Co-Parent Comparison",
        apiPrefix: "/psych-deep/compare",
        hubRoute: "/special-needs-v2/psychological-deep-dive/compare",
        hubLabel: "Back to comparisons",
        downloadFilename: "PsychDeep_Comparison.pdf",
      }}
    />
  );
}
