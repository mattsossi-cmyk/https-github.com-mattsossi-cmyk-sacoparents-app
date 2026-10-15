// Plain-language facts for the "What professionals can see" page and the in-app sharing notices.
// Keep every line true to how the app works today. `review: true` = wording pending attorney review.

export const PROS_PAGE_PATH = "/what-professionals-see";

// Single switch: set to false once the attorney approves this wording (hides the draft label and review tags).
export const ATTORNEY_REVIEW_PENDING = false;

// Case invitations and court codes are the one exception to "nothing leaves until you send it". Keep it first.
export const CASE_EXCEPTION =
  "One exception: if you accept a professional's case invitation or enter their court code, they can see whether each step they asked for is done, in progress or not started, with the dates. Shared co-parenting results reach them only after both parents finish. Your Self-Assessment answers are never shared.";

export const SHORT_VERSION = [
  "Apart from the exception above, nothing in your account goes to a professional until you choose who gets it, choose what to include, and tap Send or Share.",
  "They get only the document or report you picked, never your whole account.",
  "Your Guide (AI) chats and journal entries are never sent to a professional.",
  "Your safety answers stay private. When you email your Safety Assessment to a mediator they're left out unless you tick the box to include them, and the court report never includes them.",
  "SA CoParents doesn't keep your child's medical, educational or psychological records or documents. Only the answers you type into the assessment forms are saved.",
];

export const METHODS = [
  {
    key: "secure-document",
    icon: "fa-envelope-circle-check",
    title: "Documents you send by email",
    lead: "For example your Child Needs report, Journey certificate, Foundation Statement or Safety Assessment PDF.",
    points: [
      "The email never contains the document. It only says who sent it and that a document is waiting.",
      "They open a private page and enter a one-time code we email to their address, so a forwarded email doesn't open it.",
      "The link works for 7 days. You can cancel it any time before it's opened, from Shared with professionals.",
      "Once they download it, SA CoParents can't take that copy back.",
    ],
  },
  {
    key: "invitation",
    icon: "fa-user-shield",
    title: "Inviting a professional to view reports",
    lead: "From Share with a professional.",
    points: [
      "You pick the professional and the finished reports they can see: Foundation Statement, Co-Parenting Assessment Report, Medical, Educational or Psychological Needs Report, or Special Needs Report.",
      "You choose view-only or view and download, and how long access lasts (7, 30, 60 or 90 days).",
      "You can turn access off at any time, and we let you know when they first open a report.",
      "Your raw answers, journal, Guide chats, unfinished drafts and safety answers are not included.",
    ],
  },
  {
    key: "share-link",
    icon: "fa-link",
    title: "Share links you copy yourself",
    lead: "Some PDFs, like your Foundation Statement or a progress report, can be shared as a link.",
    points: [
      "Anyone who has the link (and the passphrase, if you add one) can open it until it expires after 7 or 30 days.",
      "Treat a share link like a key and only send it to people you trust.",
    ],
  },
  {
    key: "joint",
    icon: "fa-people-arrows",
    title: "Joint reports with your co-parent",
    lead: "Comparisons and joint reports.",
    points: [
      "A joint report only exists after both parents agree to compare.",
      "It never includes either parent's safety answers. It can include a short summary of what the safety results mean for a parenting plan.",
    ],
  },
  {
    key: "case",
    icon: "fa-briefcase",
    title: "When a professional invites you to a case",
    lead: "A mediator or attorney can start a case and invite you, or give you a court code.",
    points: [
      "Nothing from your account reaches them until you accept the invitation or enter the code.",
      "After that, they see whether each step they asked for is done, in progress or not started, with the dates. They don't see your answers.",
      "Shared co-parenting results reach them only after both parents finish.",
      "Your Self-Assessment answers are never shared.",
    ],
  },
  {
    key: "align",
    icon: "fa-arrows-left-right",
    title: "SA CoParents Align",
    lead: "Our companion site for professionals.",
    review: true,
    points: [
      "Only after you link your account with a link code can Align read your Situation Snapshot, Foundation Statement and Special Needs summaries.",
      "You can unlink at any time from your Account page. After that Align can't read anything until you link again with a new code.",
      "If your safety results show a concern, Align only sees which sections are finished and the dates, not your answers or anything you wrote.",
      "Align never receives your co-parent's information or your safety answers.",
    ],
  },
];

export const COURT_POINTS = [
  "SA CoParents does not file or send anything to a court. A court only sees a document if you, your attorney or someone you gave it to files it.",
  "The Family Safety and Functioning court report includes four summary findings: the family-violence pattern, trauma impact, parenting-plan implications and your child's experience. It leaves out your individual answers.",
  "The Safety Assessment PDF you download for yourself includes your answers. When you email it to a mediator, your answers are left out unless you tick the box to include them.",
  "The Complete Report shows whether your Quick Safety Check was completed and whether it was cleared or flagged, without the answers.",
  "Parallel Parenting Court-Order Notes list the choices you made so you can compare them with your own court order. You download them yourself.",
  "Court-facing PDFs carry a notice that they are a parent's own reflection, not an evaluation and not legal advice.",
];

// Shown inside each assessment and repeated on the page under "Assessment by assessment".
export const SHARING_NOTICES = {
  "self-assessment": {
    title: "Self-Assessment",
    stays: "Your answers, scores, reflections and goals are private to your account.",
    leaves: "Your answers are never shared with a professional. If you accepted a professional's case invitation or court code and they asked for this step, they see only whether it's done and the date. You can download your own PDF.",
    ai: "If you ask for a tip or use the Guide, the text needed for that reply goes to our AI provider to write it.",
  },
  "communication-builder": {
    title: "Communication Builder",
    stays: "Your drafts and saved messages stay in your account.",
    leaves: "Nothing is sent to your co-parent. You copy the message and send it yourself.",
    ai: "When you tap Get suggested wording, your draft goes to our AI provider to suggest calmer wording. Leave out names and sensitive details.",
  },
  "child-needs": {
    title: "Educational, Medical and Psychological",
    stays: "Your answers are private to your account. SA CoParents doesn't keep your child's records or documents.",
    leaves: "Only the finished forms you tick are sent, and only to a professional who accepted your invitation, when you tap Send to a provider. If you accepted a professional's case invitation or court code and they asked for this step, they also see whether it's done and the date.",
    ai: "If you ask the Guide, your question goes to our AI provider to answer it.",
  },
  "parallel-parenting": {
    title: "Parallel Parenting",
    stays: "Your plan choices and notes are private to your account.",
    leaves: "Nothing is sent from here, apart from one exception: if you accepted a professional's case invitation or court code and they asked for this step, they see whether it's done and the date. You can download your plan or Court-Order Notes PDF yourself.",
    ai: "If you ask the Guide or for a tip, your question and the step you're on go to our AI provider.",
  },
  "safety-check": {
    title: "Safety Assessment",
    stays: "Your answers are private. Your co-parent never sees them.",
    leaves: "When you email your Safety Assessment to a mediator, your answers are left out unless you choose to include them. The court report includes summary findings only.",
    ai: "Short summaries in your PDF may be written by our AI provider from your results.",
  },
  "foundation-statement": {
    title: "Foundation Statement",
    stays: "Private until you share it.",
    leaves: "You can download it, email it, copy a share link, or include it when you invite a professional. If you link your account to SA CoParents Align, Align can read it. In a professional's joint case, it can be part of the shared co-parenting results that reach them after both parents finish.",
    ai: "If you use guided help, your answers go to our AI provider to draft wording.",
  },
};
