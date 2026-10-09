export const ASSESS_ORDER = ["self", "coparent", "educational", "medical", "psychological"];
export const ASSESS_NAMES = {
  self: "Self-Assessment",
  coparent: "Co-Parenting Assessment",
  educational: "Educational Assessment",
  psychological: "Psychological Assessment",
  medical: "Medical Assessment",
};

const PURPLE = "bg-[#6b2fb3] hover:bg-[#5a2697]";

// Hotspots are [top%, left%, width%, height%] over each artwork; `arrow` is the round chevron button in the picture.
export const ASSESS_ART = {
  name: "sa-journey-assess",
  width: 941,
  height: 1672,
  alt: "Your Journey Starts Here. Self Assessment: reflect on your situation, identify your strengths and challenges, and track your progress. CoParenting Assessment: explore your co-parenting situation, communication patterns, decision-making, and areas for improvement.",
  items: [
    { key: "self", name: ASSESS_NAMES.self, label: "Self-Assessment", icon: "fa-user-check", tone: PURPLE, panel: [36.5, 2.5, 95, 23.3], arrow: [50, 87, 8.5, 4.8] },
    { key: "coparent", name: ASSESS_NAMES.coparent, label: "Co-Parenting Assessment", icon: "fa-people-arrows", tone: "bg-[#2f9e44] hover:bg-[#268539]", panel: [61.2, 2.5, 95, 26.4], arrow: [76.6, 87, 8.5, 4.8] },
  ],
};

// Self-Assessment page artwork: four panels jump to that part of the latest results.
export const SA_ART = {
  name: "sa-self-assessment",
  width: 1024,
  height: 1536,
  alt: "Self Assessment: reflect on your strengths, identify growth areas, set personal goals and track your progress. Your journey. Your growth. A brighter future for your child.",
  items: [
    { key: "strengths", name: "Reflect on Your Strengths", panel: [28, 2.1, 47.6, 10.4] },
    { key: "growth", name: "Identify Growth Areas", panel: [39.6, 2.1, 47.6, 10.2] },
    { key: "goals", name: "Set Personal Goals", panel: [51.1, 2.1, 47.6, 9.9] },
    { key: "progress", name: "Track Your Progress", panel: [62, 2.1, 47.6, 11] },
  ],
};

// Founder artwork: the round icon + label bubbles are the tap targets (no arrow buttons).
export const NEEDS_ART = {
  name: "sa-child-needs-steps",
  width: 1024,
  height: 1536,
  alt: "Identify Your Child's Needs. A young child ties his shoe beside three bubbles: Educational Needs, Medical Needs, and Psychological Needs. Small steps today, a brighter tomorrow.",
  items: [
    { key: "educational", name: ASSESS_NAMES.educational, label: "Educational", icon: "fa-book-open", tone: "bg-[#2f9e44] hover:bg-[#268539]", panel: [3.6, 68.7, 26.6, 17.9] },
    { key: "medical", name: ASSESS_NAMES.medical, label: "Medical", icon: "fa-stethoscope", tone: "bg-[#1a73d9] hover:bg-[#1561b8]", panel: [25.1, 73.9, 24.4, 18.4] },
    { key: "psychological", name: ASSESS_NAMES.psychological, label: "Psychological", icon: "fa-brain", tone: PURPLE, panel: [48.5, 73, 26.6, 17.4] },
  ],
};

// Founder artwork. `screen` is the Parallel Parenting builder screen each spot opens (step index or quick check).
export const PP_ART = {
  name: "sa-parallel-builder",
  width: 1024,
  height: 1536,
  alt: "Parallel Parenting Option Builder. Create a child-focused parallel parenting plan that works for your family. Communication Options, Exchange Options and Decision-Making Options, plus Child-Focused Considerations, Safeguards and Boundaries, Texas Court-Order Compatibility Check, and Areas for Professional Review.",
  items: [
    { key: "communication", name: "Communication Options", label: "Communication", icon: "fa-comments", tone: PURPLE, screen: 0, panel: [49.8, 3.4, 31, 33.9] },
    { key: "exchanges", name: "Exchange Options", label: "Exchanges", icon: "fa-car", tone: PURPLE, screen: 1, panel: [49.8, 35.4, 29.9, 33.9] },
    { key: "decisions", name: "Decision-Making Options", label: "Decision-Making", icon: "fa-file-lines", tone: PURPLE, screen: 2, panel: [49.8, 66.4, 30.3, 33.9] },
    { key: "child_focus", name: "Child-Focused Considerations", label: "Child-Focused", icon: "fa-children", small: true, screen: "check:child_focus", panel: [85.3, 3.9, 21, 11.4] },
    { key: "safeguards", name: "Safeguards and Boundaries", label: "Safeguards", icon: "fa-shield-halved", small: true, screen: "check:safeguards", panel: [85.3, 25.6, 22, 11.4] },
    { key: "court_check", name: "Texas Court-Order Compatibility Check", label: "Court-Order Check", icon: "fa-file-circle-check", small: true, screen: "check:court_check", panel: [85.3, 48.3, 24.4, 11.4] },
    { key: "professional_review", name: "Areas for Professional Review", label: "Professional Review", icon: "fa-users", small: true, screen: "check:professional_review", panel: [85.3, 73.4, 23.3, 11.4] },
  ],
};
