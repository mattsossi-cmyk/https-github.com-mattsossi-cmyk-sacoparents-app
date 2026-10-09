export const ASSESS_ORDER = ["self", "coparent", "educational", "medical", "psychological"];
export const ASSESS_NAMES = {
  self: "Self-Assessment",
  coparent: "Co-Parenting Assessment",
  educational: "Educational Assessment",
  psychological: "Psychological Assessment",
  medical: "Medical Assessment",
};

// Hotspots are [top%, left%, width%, height%] over each artwork; `arrow` is the round chevron button in the picture.
export const ASSESS_ART = {
  name: "sa-journey-assess",
  width: 941,
  height: 1672,
  alt: "Your Journey Starts Here. Self Assessment: reflect on your situation, identify your strengths and challenges, and track your progress. CoParenting Assessment: explore your co-parenting situation, communication patterns, decision-making, and areas for improvement.",
  items: [
    { key: "self", label: "Self-Assessment", icon: "fa-user-check", tone: "bg-[#6b2fb3] hover:bg-[#5a2697]", panel: [36.5, 2.5, 95, 23.3], arrow: [50, 87, 8.5, 4.8] },
    { key: "coparent", label: "Co-Parenting Assessment", icon: "fa-people-arrows", tone: "bg-[#2f9e44] hover:bg-[#268539]", panel: [61.2, 2.5, 95, 26.4], arrow: [76.6, 87, 8.5, 4.8] },
  ],
};

// Founder artwork: the round icon + label bubbles are the tap targets (no arrow buttons).
export const NEEDS_ART = {
  name: "sa-child-needs-steps",
  width: 1024,
  height: 1536,
  alt: "Identify Your Child's Needs. A young child ties his shoe beside three bubbles: Educational Needs, Medical Needs, and Psychological Needs. Small steps today, a brighter tomorrow.",
  items: [
    { key: "educational", label: "Educational", icon: "fa-book-open", tone: "bg-[#2f9e44] hover:bg-[#268539]", panel: [3.6, 68.7, 26.6, 17.9] },
    { key: "medical", label: "Medical", icon: "fa-stethoscope", tone: "bg-[#1a73d9] hover:bg-[#1561b8]", panel: [25.1, 73.9, 24.4, 18.4] },
    { key: "psychological", label: "Psychological", icon: "fa-brain", tone: "bg-[#6b2fb3] hover:bg-[#5a2697]", panel: [48.5, 73, 26.6, 17.4] },
  ],
};
