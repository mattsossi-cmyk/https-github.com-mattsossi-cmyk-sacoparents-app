import React from "react";
import DeepDiveCompareView from "../components/deepdive/DeepDiveCompareView";

export default function SpecialNeedsV2PsychologicalDeepDiveCompareView() {
  return (
    <DeepDiveCompareView
      pathway={{
        testidPrefix: "psych-deep-compare",
        eyebrow: "Checkin - Psychological Needs Report",
        apiPrefix: "/psych-deep/compare",
        hubRoute: "/special-needs-v2/psychological-deep-dive/compare",
        hubLabel: "Back to comparisons",
        downloadFilename: "Checkin_Psychological_Needs_Report.pdf",
        showMatrix: true,
      }}
    />
  );
}
