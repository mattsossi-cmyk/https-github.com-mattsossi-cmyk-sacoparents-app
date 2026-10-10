// Founder artwork for each Child Needs form page. Panels are [top, left, width, height] in %.
// Each icon's `fields` are the questions it jumps to; "start" is the round › button (first question).
const ICON = (top, height) => [top, 3.5, 20, height];
const START = { key: "start", name: "the first question", panel: [74.6, 79.7, 14.8, 11], fields: [] };

export const NEEDS_PAGE_ART = {
  educational: {
    name: "sa-needs-educational",
    width: 1083,
    height: 1452,
    alt: "Educational Assessment. A boy writes in a notebook beside four icons: School Performance, Learning Needs, School Support, and Special Programs (IEP/ARD).",
    items: [
      { key: "performance", name: "School Performance questions", panel: ICON(4, 15.5), fields: ["edu_attention", "edu_independent", "edu_academic"] },
      { key: "learning", name: "Learning Needs questions", panel: ICON(20.7, 15), fields: ["edu_strengths"] },
      { key: "support", name: "School Support questions", panel: ICON(37.2, 14.8), fields: ["edu_communication", "edu_goal"] },
      { key: "programs", name: "Special Programs (IEP/ARD) questions", panel: ICON(52.6, 15.8), fields: ["edu_iep"] },
      START,
    ],
  },
  medical: {
    name: "sa-needs-medical",
    width: 1083,
    height: 1452,
    alt: "Medical Assessment. A doctor listens to a smiling girl's heartbeat beside four icons: Health Care, Medications, Ongoing Conditions, and Preventive Care.",
    items: [
      { key: "care", name: "Health Care questions", panel: ICON(4.5, 15), fields: ["med_provider"] },
      { key: "medications", name: "Medications questions", panel: ICON(21, 13.5), fields: ["med_prescriptions"] },
      { key: "conditions", name: "Ongoing Conditions questions", panel: ICON(35.5, 15.8), fields: ["med_conditions", "med_allergies"] },
      { key: "preventive", name: "Preventive Care questions", panel: ICON(52.3, 15), fields: ["med_preventive"] },
      START,
    ],
  },
  psychological: {
    name: "sa-needs-psychological",
    width: 1083,
    height: 1452,
    alt: "Psychological Assessment. A thoughtful girl sits on her bed beside four icons: Emotional Well-Being, Behavior & Mood, Social Relationships, and Strengths & Support.",
    items: [
      { key: "emotional", name: "Emotional Well-Being questions", panel: ICON(4.3, 15.2), fields: ["psy_triggers", "psych_transitions"] },
      { key: "behavior", name: "Behavior & Mood questions", panel: ICON(20.8, 15.5), fields: ["psych_needs", "psy_goal"] },
      { key: "social", name: "Social Relationships questions", panel: ICON(37, 14.8), fields: ["psy_household"] },
      { key: "strengths", name: "Strengths & Support questions", panel: ICON(52.5, 15.3), fields: ["psych_therapy", "psych_goal"] },
      START,
    ],
  },
};
