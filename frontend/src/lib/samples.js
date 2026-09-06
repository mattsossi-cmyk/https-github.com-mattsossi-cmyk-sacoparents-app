export const SAMPLE_REPORTS = [
  { key: "co_parenting", label: "General Co-Parenting", blurb: "Routines, rules, and day-to-day decisions across both homes." },
  { key: "communication", label: "Communication", blurb: "How parents share information, updates, and everyday messages." },
  { key: "education", label: "Educational Needs", blurb: "School, homework, tutoring, and academic support alignment." },
  { key: "medical", label: "Medical Needs", blurb: "Healthcare routines, medication, appointments, and care decisions." },
  { key: "psychological", label: "Psychological Needs", blurb: "Emotional wellbeing, counseling, and support strategies." },
  { key: "safety", label: "Safety / Family Violence", blurb: "Controlled preview of the professional-mediated safety report format.", safety: true },
  { key: "mediation", label: "Mediation Statement", blurb: "Pre-mediation comparison statement for session preparation." },
];

export const samplePdfUrl = (key) => `${process.env.REACT_APP_BACKEND_URL}/api/joint/sample/${key}/pdf`;
