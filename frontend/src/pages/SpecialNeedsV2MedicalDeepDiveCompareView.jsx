import React from "react";
import DeepDiveCompareView from "../components/deepdive/DeepDiveCompareView";

export default function SpecialNeedsV2MedicalDeepDiveCompareView() {
  return (
    <DeepDiveCompareView
      pathway={{
        testidPrefix: "med-deep-compare",
        eyebrow: "Medical Deep Dive · Co-Parent Comparison",
        apiPrefix: "/med-deep/compare",
        hubRoute: "/special-needs-v2/medical-deep-dive/compare",
        hubLabel: "Back to comparisons",
        downloadFilename: "MedDeep_Comparison.pdf",
      }}
    />
  );
}
