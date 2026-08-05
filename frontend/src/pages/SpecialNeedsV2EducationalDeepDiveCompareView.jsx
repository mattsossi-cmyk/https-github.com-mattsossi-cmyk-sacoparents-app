import React from "react";
import DeepDiveCompareView from "../components/deepdive/DeepDiveCompareView";

export default function SpecialNeedsV2EducationalDeepDiveCompareView() {
  return (
    <DeepDiveCompareView
      pathway={{
        testidPrefix: "edu-deep-compare",
        eyebrow: "Coparenting Education Check In Summary",
        apiPrefix: "/edu-deep/compare",
        hubRoute: "/special-needs-v2/educational-deep-dive/compare",
        hubLabel: "Back to check-in summaries",
        downloadFilename: "Coparenting_Education_CheckIn_Summary.pdf",
        showMatrix: true,
      }}
    />
  );
}
