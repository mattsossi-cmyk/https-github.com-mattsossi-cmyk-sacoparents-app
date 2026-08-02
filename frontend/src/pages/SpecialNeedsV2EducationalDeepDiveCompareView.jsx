import React from "react";
import DeepDiveCompareView from "../components/deepdive/DeepDiveCompareView";

export default function SpecialNeedsV2EducationalDeepDiveCompareView() {
  return (
    <DeepDiveCompareView
      pathway={{
        testidPrefix: "edu-deep-compare",
        eyebrow: "Educational Assessment Alignment Report",
        apiPrefix: "/edu-deep/compare",
        hubRoute: "/special-needs-v2/educational-deep-dive/compare",
        hubLabel: "Back to alignment reports",
        downloadFilename: "Educational_Assessment_Alignment_Report.pdf",
      }}
    />
  );
}
