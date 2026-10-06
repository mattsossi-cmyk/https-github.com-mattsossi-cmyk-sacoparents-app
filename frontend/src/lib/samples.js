const API = process.env.REACT_APP_BACKEND_URL;

export const SAMPLE_REPORTS = [
  { key: "co_parenting", label: "General Co-Parenting", blurb: "Routines, rules, and day-to-day decisions across both homes." },
  { key: "communication", label: "Communication", blurb: "How parents share information, updates, and everyday messages." },
  { key: "education", label: "Educational Needs", blurb: "School, homework, tutoring, and academic support alignment." },
  { key: "medical", label: "Medical Needs", blurb: "Healthcare routines, medication, appointments, and care decisions." },
  { key: "psychological", label: "Psychological Needs", blurb: "Emotional wellbeing, counseling, and support strategies." },
  { key: "safety", label: "Safety / Family Violence", blurb: "Two private self-assessments — Version A (women) and Version B (men), assigned by the professional. Each parent answers alone; only the assigned professional sees responses. Reports show receipt, version and tier — never answers. Screening questions, not a diagnostic tool.", safety: true, tag: "Private self-assessments · Version A / B" },
  { key: "mediation", label: "Mediation Statement", blurb: "Pre-mediation comparison statement for session preparation." },
  { key: "foundation-statement", label: "Child-Focused Foundation Statement", blurb: "One parent's statement of shared purpose, vision, priorities, the child's strengths and needs, concerns, commitments and 12-month goals.",
    to: "/samples/foundation-statement", pdf: `${API}/api/joint/sample-foundation-statement/pdf`, emailEndpoint: "/joint/sample-extra/foundation-statement/email", tag: "For parents" },
  { key: "coparenting-agreement", label: "Co-Parenting Agreement", blurb: "Built from both parents' private proposals across 10 areas — matching answers become specific agreements; differences are listed for discussion.",
    to: "/samples/coparenting-agreement", pdf: `${API}/api/joint/sample-agreement/pdf`, emailEndpoint: "/joint/sample-extra/coparenting-agreement/email", tag: "For parents · Joint Agreement" },
];

export const samplePdfUrl = (key) => `${API}/api/joint/sample/${key}/pdf`;
