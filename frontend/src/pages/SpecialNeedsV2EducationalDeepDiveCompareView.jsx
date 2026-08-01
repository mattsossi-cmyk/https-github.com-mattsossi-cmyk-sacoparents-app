import React from "react";
import DeepDiveCompareView from "../components/deepdive/DeepDiveCompareView";

export default function SpecialNeedsV2EducationalDeepDiveCompareView() {
  return (
    <DeepDiveCompareView
      pathway={{
        testidPrefix: "edu-deep-compare",
        eyebrow: "Educational Deep Dive · Co-Parent Comparison",
        apiPrefix: "/edu-deep/compare",
        hubRoute: "/special-needs-v2/educational-deep-dive/compare",
        hubLabel: "Back to comparisons",
        downloadFilename: "EduDeep_Comparison.pdf",
      }}
    />
  );
}
