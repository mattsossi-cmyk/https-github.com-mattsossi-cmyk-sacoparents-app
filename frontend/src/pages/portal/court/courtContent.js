export const AI_GRADIENT = "linear-gradient(135deg, #4a148c 0%, #7b2cbf 50%, #3a86ff 100%)";

// Court artwork hotspots: [top, left, width, height] in % of the image.
export const MAIN_SPOT = [39.8, 11.5, 77, 5.6];

export const STEPS = [
  {
    n: 1,
    card: "card2",
    spot: [54.2, 2.5, 46.5, 12.8],
    title: "Complete Your CoParenting Assessment",
    short: "Complete Your CoParenting Assessment",
    icon: "fa-clipboard-list",
    tone: { card: "bg-purple-100/70 border-purple-200/80", tile: "bg-purple-600", heading: "text-[#3B1C6B]" },
    body: "Tell us about your current parenting situation, your strengths, your challenges, and the areas where you believe support may be needed.",
  },
  {
    n: 2,
    card: "card1",
    spot: [54.2, 51, 46.5, 12.8],
    title: "Reflect on Your Parenting",
    short: "Reflect on Your Parenting",
    icon: "fa-comment-dots",
    tone: { card: "bg-sky-50 border-sky-200/80", tile: "bg-indigo-500", heading: "text-indigo-950" },
    body: "Complete your Self Assessment to consider how you are currently responding to conflict, communication, decision-making, and your child's changing needs.",
  },
  {
    n: 3,
    card: "card3",
    spot: [68.4, 2.5, 46.5, 14.5],
    title: "Identify Your Child's Specific Needs",
    short: "Identify Your Child's Specific Needs",
    icon: "fa-book-open-reader",
    tone: { card: "bg-emerald-50 border-emerald-200/80", tile: "bg-emerald-600", heading: "text-emerald-950" },
    body: "You may be asked to complete additional assessments involving educational, medical, psychological or emotional needs, and other child-specific concerns.",
  },
  {
    n: 4,
    card: "card4",
    spot: [68.4, 51, 46.5, 14.5],
    title: "Create Your Foundation Statement",
    short: "Create Your Foundation Statement",
    icon: "fa-file-signature",
    tone: { card: "bg-orange-50 border-orange-200/80", tile: "bg-orange-500", heading: "text-orange-950" },
    body: "Identify the principles you want to guide your parenting relationship. Your Foundation Statement focuses on your child, your parenting goals, and the values you want to carry forward.",
  },
];

export const PILLARS = [
  {
    key: "alignment",
    spot: [88, 3.5, 22.5, 9.8],
    title: "Areas of Alignment",
    sub: "Where both parents have similar perspectives",
    icon: "fa-check",
    tile: "bg-emerald-500",
    intro: "Where your own answers show the most strength. These are good starting points for agreement.",
    empty: "Finish the Co-Parenting Assessment or Self-Assessment to see your strongest areas here.",
    emptyStep: 1,
  },
  {
    key: "difference",
    spot: [88, 27.5, 22.5, 9.8],
    title: "Areas of Difference",
    sub: "Where perspectives do not match",
    icon: "fa-right-left",
    tile: "bg-amber-400",
    intro: "The areas you rated lowest. These may be where you and your co-parent see things differently.",
    empty: "Finish the Co-Parenting Assessment or Self-Assessment to see the areas to work on here.",
    emptyStep: 1,
  },
  {
    key: "child",
    spot: [88, 50.5, 22.5, 9.8],
    title: "Child-Focused Needs",
    sub: "What may need additional attention",
    icon: "fa-people-group",
    tile: "bg-purple-500",
    intro: "What you've recorded about your child's needs so far.",
    empty: "Start an Educational, Medical or Psychological assessment to record your child's needs.",
    emptyStep: 3,
  },
  {
    key: "resources",
    spot: [88, 74, 22.5, 9.8],
    title: "Options and Resources",
    sub: "To support you and your child moving forward",
    icon: "fa-gear",
    tile: "bg-blue-600",
    intro: "Tools and support you can use right now.",
  },
];

// Court page menu (any order; the professional picks which ones apply).
export const MENU = [
  { key: "coparent", title: "Co-Parenting Assessment", icon: "fa-clipboard-list", tile: "bg-purple-600", body: "Your current parenting situation, strengths, challenges, and where support may help." },
  { key: "self", title: "Self-Assessment", icon: "fa-comment-dots", tile: "bg-indigo-500", body: "Reflect on how you respond to conflict, communication, decision-making and your child's changing needs." },
  { key: "educational", title: "Educational Assessment", icon: "fa-book-open", tile: "bg-[#2f9e44]", body: "School performance, learning needs, school support and special programs (IEP/ARD)." },
  { key: "medical", title: "Medical Assessment", icon: "fa-stethoscope", tile: "bg-[#1a73d9]", body: "Health history, current medications, allergies and physical health needs." },
  { key: "psychological", title: "Psychological Assessment", icon: "fa-brain", tile: "bg-[#6b2fb3]", body: "Emotional well-being, behavior, social relationships and coping." },
  { key: "foundation", title: "Foundation Statement", icon: "fa-file-signature", tile: "bg-orange-500", body: "The principles and values you want to guide your parenting relationship." },
  { key: "parallel", title: "Parallel Parenting Plan", icon: "fa-people-arrows", tile: "bg-[#4a1d7a]", body: "Plan communication, exchanges and decisions with less direct contact." },
];

export const STATUS_PILL = {
  done: ["Completed", "bg-emerald-600 text-white", "fa-circle-check"],
  in_progress: ["In progress", "bg-amber-400 text-amber-950", "fa-circle-half-stroke"],
  todo: ["Not started", "bg-white/95 text-slate-700", "fa-circle"],
  loading: ["Checking", "bg-white/95 text-slate-500", "fa-spinner fa-spin"],
};

export const POINTS = [
  ["fa-user", "You complete your work individually."],
  ["fa-users", "You are not required to agree with the other parent."],
  ["fa-shield-halved", "SA CoParents helps identify where perspectives may align, where they may differ, and what issues may need additional attention."],
];
