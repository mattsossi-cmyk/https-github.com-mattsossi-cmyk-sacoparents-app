// Ready-made Journey Guide answers for the reading Self Journey. Nothing here is sent anywhere.
// `page` puts that question first on the matching page; `link` adds a button under the answer.

export const GUIDE_LOGO = '/images/guide-avatar.webp';

export const READY = [
  {
    id: 'safety',
    page: 'safety-first',
    q: 'Why does Safety First come before choosing a path?',
    a:
      'Because the right path depends on safety. If there has been violence, threats, stalking or control, advice about ' +
      'working closely with the other parent may not be safe for you. Safety First is a private check-in on ' +
      'SACOparentsAlign, and SA CoParents never sees your answers. If you are in danger, call 911, or the National DV ' +
      'Hotline at 1-800-799-7233 (text START to 88788).',
    link: { to: '/start-with-safety', label: 'Go to Start with Safety' },
  },
  {
    id: 'coparenting',
    page: 'coparenting',
    q: 'What is Co-Parenting?',
    a:
      'Both parents talk directly, coordinate schedules and make the big decisions together, keeping the focus on your ' +
      'child. It tends to work when you both feel safe, can disagree respectfully and put your child’s needs first.',
    link: { to: '/self-journey/coparenting', label: 'Read the Co-Parenting page' },
  },
  {
    id: 'parallel',
    page: 'parallel-parenting',
    q: 'What is Parallel Parenting?',
    a:
      'Each parent makes everyday decisions during their own time, with as little direct contact as possible. Messages ' +
      'are short, written and only about your child. It can help when conversations often turn into conflict, when one ' +
      'parent feels unsafe or pressured, or when you need a cooling-off period.',
    link: { to: '/self-journey/parallel-parenting', label: 'Read the Parallel Parenting page' },
  },
  {
    id: 'choose',
    q: 'How do I choose between them?',
    a:
      'Start with Safety First. Then think about how your conversations usually go. If you can talk calmly and settle ' +
      'disagreements, Co-Parenting may fit. If talks often turn into conflict, or you feel pressured, Parallel Parenting ' +
      'gives more distance. Many families use a mix, or start with Parallel Parenting and move closer over time. A ' +
      'mediator, attorney or advocate can help you decide what fits your family.',
  },
  { id: 'pages', q: 'What do the pages cover, and how long do they take?' },
  {
    id: 'switch',
    q: 'Can I switch paths later?',
    a:
      'Yes. Families change, and your path can too. You can come back to any page whenever you like. If safety becomes a ' +
      'concern, go back to Start with Safety. If things calm down, you might move from Parallel Parenting toward ' +
      'Co-Parenting. Any change to a court order should go through your attorney or the court.',
  },
  {
    id: 'report',
    q: 'Where is the PDF report?',
    a:
      'Your Journey Report PDF is on the summary page of the guided Self Journey (you sign in to use it). It gathers ' +
      'your progress so you can bring it to a mediator, attorney or counselor. On any page here you can also tap ' +
      '“Print this page” for a one-page handout.',
    link: { to: '/self-journey/guided/summary', label: 'Open the Journey Report page' },
  },
  {
    id: 'help',
    q: 'Where can I get help?',
    a:
      'The Get help page lists mediators and local services. In danger, call 911. National DV Hotline: 1-800-799-7233, ' +
      'or text START to 88788. For emotional support, call or text 988 any time.',
    link: { to: '/help', label: 'Open Get help' },
  },
];

export function pagesAnswer(steps) {
  const total = steps.reduce((sum, s) => sum + s.minutes, 0);
  const list = steps.map((s, i) => `${i + 1}. ${s.title} (about ${s.minutes} min): ${s.summary}`).join('\n');
  return `The Self Journey has ${steps.length} pages, about ${total} minutes in all, and you can read them in any order.\n${list}`;
}

// Short page list sent with signed-in questions so the AI guide knows the pages and times.
export const pagesContext = (steps) => steps.map((s) => `${s.title} (${s.minutes} min)`).join(', ');

export function orderedFor(stepId) {
  const first = READY.filter((r) => r.page && r.page === stepId);
  return [...first, ...READY.filter((r) => !first.includes(r))];
}
