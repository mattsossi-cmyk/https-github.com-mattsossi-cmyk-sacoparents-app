import React from "react";
import DeepDiveCompareHub from "../components/deepdive/DeepDiveCompareHub";

export default function SpecialNeedsV2MedicalDeepDiveCompare() {
  return (
    <DeepDiveCompareHub
      pathway={{
        testidPrefix: "med-deep-compare",
        eyebrow: "Checkin - Medical Needs Report",
        hero: "See where you and your co-parent already agree on your child's medication.",
        description:
          "When both parents complete the Medical / Prescription & Medication Coordination Deep Dive " +
          "and each of you explicitly opts in, you can view a neutral side-by-side comparison. This " +
          "does not replace guidance from your child's prescriber or pharmacist — it is a starting " +
          "point for aligning on doses, timing, and shared responsibilities.",
        safetyNoun: "medication and prescriber information",
        backTo: "/special-needs-v2/medical-deep-dive",
        backLabel: "Back to Medical Deep Dive",
        apiPrefix: "/med-deep/compare",
        viewRouteBase: "/special-needs-v2/medical-deep-dive/compare",
      }}
    />
  );
}
