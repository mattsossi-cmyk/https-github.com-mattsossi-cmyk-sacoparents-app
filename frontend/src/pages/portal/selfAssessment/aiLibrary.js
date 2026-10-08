// Curated communication examples + quick templates for the AI Insight panel.
// `grey` variants are shown to safety-flagged parents (grey-rock: logistics only).
export const EXAMPLES = [
  {
    key: "handover",
    title: "Neutral Handover Confirmation",
    before: "You were 30 minutes late AGAIN. Do you even care about our child's schedule?",
    after:
      "Confirming Saturday's handover at 10:00 am at the school parking lot. If anything changes, please text me by Friday evening. Thanks.",
    grey: "Saturday handover: 10:00 am, school parking lot.",
  },
  {
    key: "expense",
    title: "Expense Notice",
    before: "I'm not paying for another one of your 'extras'. You never ask me first.",
    after:
      "[Child]'s soccer registration is $120, due May 1. Per our agreement, your half is $60. The receipt is attached. Let me know if you have questions.",
    grey: "Soccer registration: $120, due May 1. Your share per our order: $60. Receipt attached.",
  },
  {
    key: "schedule",
    title: "Schedule Adjustment Request",
    before: "I need the kids next weekend and I don't want an argument about it.",
    after:
      "My family reunion is on June 14. Would you be open to swapping weekends, so I have June 14–15 and you have June 21–22? Please let me know by Wednesday.",
    grey: "Requesting a swap: I take June 14–15, you take June 21–22. Please reply yes or no by Wednesday.",
  },
];

export const TEMPLATES = [
  {
    key: "school",
    title: "School Event Coordination",
    body:
      "Hi, [child]'s [event] is on [date] at [time] at [location]. I plan to attend. Let me know if you'd like me to forward the school's details.",
    grey: "[Child]'s [event]: [date], [time], [location]. The school's details are attached.",
  },
  {
    key: "medical",
    title: "Medical / Appointment Update",
    body:
      "[Child] had a [type] appointment on [date]. The [provider] said [summary]. The next appointment is [date/time]. Paperwork is attached.",
    grey: "[Child]: [type] appointment on [date]. Outcome: [summary]. Next: [date/time].",
  },
  {
    key: "holiday",
    title: "Holiday Schedule Proposal",
    body:
      "For [holiday], I'd like to propose that [child] spends [dates/times] with me and [dates/times] with you, following our plan. Please let me know by [date] if that works.",
    grey: "[Holiday] proposal per our order: with me [dates/times]; with you [dates/times]. Please confirm by [date].",
  },
];
