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

export const NEEDS_ART = {
  name: "sa-child-needs-assess",
  width: 848,
  height: 1264,
  alt: "Your Child's Needs. Educational Assessment: learning, school support and routines. Psychological Assessment: emotions, behaviour and wellbeing. Medical Assessment: health, care and medical routines.",
  items: [
    { key: "educational", label: "Educational", icon: "fa-graduation-cap", tone: "bg-[#6b2fb3] hover:bg-[#5a2697]", panel: [38.8, 2.4, 95.3, 15.4], arrow: [48.3, 87, 8.3, 5.5] },
    { key: "psychological", label: "Psychological", icon: "fa-brain", tone: "bg-[#2f9e44] hover:bg-[#268539]", panel: [55.8, 2.4, 95.3, 15.3], arrow: [64.5, 87, 8.3, 5.5] },
    { key: "medical", label: "Medical", icon: "fa-stethoscope", tone: "bg-[#e0702b] hover:bg-[#c75f20]", panel: [72.2, 2.4, 95.3, 15.3], arrow: [81.3, 87, 8.3, 5.5] },
  ],
};
