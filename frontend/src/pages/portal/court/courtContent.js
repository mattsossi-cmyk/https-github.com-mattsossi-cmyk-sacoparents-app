// Court artwork hotspots: [top, left, width, height] in % of the image.
export const MAIN_SPOT = [39.8, 11.5, 77, 5.6];

export const STEPS = [
  {
    n: 1,
    card: "card2",
    spot: [54.2, 2.5, 46.5, 12.8],
    title: "Step 1: Complete Your CoParenting Assessment",
    body: "Answer the Co-Parenting Relationship questions about communication, transitions, school, health and routines. Your results show your strongest areas and where to focus.",
  },
  {
    n: 2,
    card: "card1",
    spot: [54.2, 51, 46.5, 12.8],
    title: "Step 2: Reflect on Your Parenting",
    body: "Take the Self-Assessment to reflect on your focus on your child, your self-awareness, your communication and how you work through differences.",
  },
  {
    n: 3,
    card: "card3",
    spot: [68.4, 2.5, 46.5, 14.5],
    title: "Step 3: Identify Your Child's Specific Needs",
    body: "Record your child's medical, educational and emotional needs so everyone caring for your child works from the same picture.",
  },
  {
    n: 4,
    card: "card4",
    spot: [68.4, 51, 46.5, 14.5],
    title: "Step 4: Create Your Foundation Statement",
    body: "Put your goals and values for your child into words, then download it with your signature and date line.",
  },
];

export const PILLARS = [
  {
    key: "alignment",
    spot: [88, 3.5, 22.5, 9.8],
    title: "Areas of Alignment",
    intro: "Where your own answers show the most strength. These are good starting points for agreement.",
    empty: "Finish Step 1 or Step 2 to see your strongest areas here.",
    emptyStep: 1,
  },
  {
    key: "difference",
    spot: [88, 27.5, 22.5, 9.8],
    title: "Areas of Difference",
    intro: "The areas you rated lowest. These may be where you and your co-parent see things differently.",
    empty: "Finish Step 1 or Step 2 to see the areas to work on here.",
    emptyStep: 1,
  },
  {
    key: "child",
    spot: [88, 50.5, 22.5, 9.8],
    title: "Child-Focused Needs",
    intro: "What you've recorded about your child's needs so far.",
    empty: "Start Step 3 to record your child's needs.",
    emptyStep: 3,
  },
  {
    key: "resources",
    spot: [88, 74, 22.5, 9.8],
    title: "Options and Resources",
    intro: "Tools and support you can use right now.",
  },
];

export const STATUS_PILL = {
  done: ["Completed", "bg-emerald-600 text-white", "fa-circle-check"],
  in_progress: ["In progress", "bg-amber-400 text-amber-950", "fa-circle-half-stroke"],
  todo: ["Not started", "bg-white/95 text-slate-700", "fa-circle"],
  loading: ["Checking", "bg-white/95 text-slate-500", "fa-spinner fa-spin"],
};
