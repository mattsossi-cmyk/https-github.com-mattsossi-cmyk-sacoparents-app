/**
 * safeNdContent.js — SAFE-ND™ Functional Map content
 * Put in the SACOparentsAlign project: frontend/src/data/safeNdContent.js
 *
 * SAFE-ND™ © Trisha Wright, www.atipcommunity.com. Used with permission.
 * This file holds the licensed SAFE-ND content; SafeNdReview.jsx only displays it.
 * It currently matches the EXAMPLE version, which does not include every domain
 * or question. Add the remaining licensed domains/questions here (same format).
 * Do not share this file outside SACOparentsAlign.
 *
 * Field types:
 *   text      one line            textarea  several lines        date
 *   checks    tick boxes (+ optional "Other" box)
 *   domains   table: domain · what to identify · priority L/M/H · observations
 *   homes     table: area · Home A · Home B · planning implication
 * Note types: info (green), warn (red), scope (sand), plain (gray)
 */

export const SAFE_ND = {
  title: 'SAFE-ND™ Functional Map',
  subtitle: 'Neurodevelopmentally Informed Parenting-Plan Review',
  description:
    'A structured professional form for mapping child functioning, environmental load, household supports, cross-home consistency, and review triggers.',
  credit: 'SAFE-ND™ © Trisha Wright · www.atipcommunity.com · Used with permission. Reproduction or sharing is prohibited.',
  finalScope:
    'The SAFE-ND™ Functional Map organizes functional, developmental, neurodevelopmental, environmental, and parenting-plan information for planning purposes. It is not a diagnosis, parenting-capacity assessment, custody / parenting-time recommendation, judicial finding, or legal opinion. Findings should be read within the information sources and limitations documented in the review.',

  sections: [
    {
      id: 'case',
      title: 'Case Information',
      notes: [
        {
          type: 'info',
          title: 'Central question',
          text: 'What does this child need in order to function successfully across two homes, and what can the parenting system do to reduce unnecessary load?',
        },
      ],
      fields: [
        { id: 'child', type: 'text', label: 'Child / young person' },
        { id: 'dobAge', type: 'text', label: 'Date of birth / age' },
        { id: 'parents', type: 'text', label: 'Parents / caregivers' },
        { id: 'reviewer', type: 'text', label: 'Reviewer' },
        { id: 'reviewDate', type: 'date', label: 'Date of review' },
        { id: 'referral', type: 'text', label: 'Referral source / lawyer' },
        { id: 'arrangement', type: 'text', label: 'Current parenting arrangement' },
      ],
      notesAfter: [
        {
          type: 'scope',
          title: 'Scope',
          text: 'This Functional Map is a non-diagnostic parenting-plan review. It does not determine parenting capacity, decide which parent is right, select a preferred home, establish causation, or replace medical, psychological, legal, or child-protection decision-making where those are required.',
        },
      ],
    },
    {
      id: 'referral',
      title: 'Referral Question',
      fields: [
        {
          id: 'question',
          type: 'textarea',
          label: 'What specific parenting-plan problem, behavioural change, implementation difficulty, or neurodevelopmental need requires review?',
          rows: 5,
        },
        {
          id: 'sources',
          type: 'checks',
          label: 'Information Sources',
          options: [
            'Parent A interview',
            'Parent B interview',
            'Child-inclusive interview / voice work',
            'School records / educator input',
            'Medical information',
            'Therapy / service-provider information',
            'Existing parenting plan / order',
            'Direct observation',
            'Other collateral information',
          ],
          other: true,
        },
      ],
      notesAfter: [
        {
          type: 'plain',
          title: 'Evidence discipline',
          text: 'Distinguish parent report, direct observation, documented information, collateral information, professional interpretation, and unresolved factual dispute.',
        },
      ],
    },
    {
      id: 'require',
      number: 1,
      title: 'What Does This Child Require?',
      notes: [
        {
          type: 'info',
          title: 'Functional needs, not diagnostic labels',
          text: 'Identify the conditions that help this child communicate, regulate, learn, transition, recover, and participate successfully. Two children with the same diagnosis may require very different supports.',
        },
      ],
      fields: [
        {
          id: 'domains',
          type: 'domains',
          label: 'Functional domains',
          rows: [
            {
              id: 'communication',
              name: 'Communication',
              identify: 'Concrete/direct language; visual support; processing time; AAC/device; reduced verbal demand; comprehension checks.',
            },
            {
              id: 'executive',
              name: 'Executive functioning',
              identify: 'Checklists; visual schedules; reminders; task breakdown; adult prompting; organization support.',
            },
            // Add the remaining licensed domains here, e.g.
            // { id: '...', name: '...', identify: '...' },
          ],
        },
      ],
    },
    {
      id: 'load',
      number: 2,
      title: 'What Creates Additional Load?',
      notes: [
        {
          type: 'warn',
          title: 'Load question',
          text: "What demands are currently using more of this child's coping capacity than they can comfortably manage? Behaviour may reflect multiple interacting factors rather than one simple cause.",
        },
      ],
      fields: [
        {
          id: 'loads',
          type: 'checks',
          label: 'Load factors',
          options: [
            'Frequent / long / rushed transitions',
            'Unpredictable exchanges or schedule changes',
            'Different household rules or routines',
            'Sensory differences between homes',
          ],
        },
        { id: 'heading', type: 'heading', label: 'Behaviour-in-Context Analysis' },
        { id: 'behaviour', type: 'textarea', label: 'Behaviour / change being reviewed', rows: 3 },
        { id: 'before', type: 'textarea', label: 'What happened immediately before?', rows: 3 },
        { id: 'understood', type: 'textarea', label: 'What did the child appear to understand?', rows: 3 },
      ],
    },
    {
      id: 'support',
      number: 3,
      title: 'What Support Exists in Each Home?',
      notes: [
        {
          type: 'info',
          title: 'Support ecology',
          text: 'Map supports and barriers without ranking parental love, character, or worth. The question is what resources, routines, people, and systems are available to help this child function in each household.',
        },
      ],
      fields: [
        {
          id: 'homes',
          type: 'homes',
          label: 'Supports by home',
          rows: [
            { id: 'availability', name: 'Adult availability', detail: 'Work flexibility, caregiving time, high-demand availability' },
            { id: 'community', name: 'Family / community', detail: 'Grandparents, relatives, friends, respite, backup care' },
            // Add the remaining licensed areas here.
          ],
        },
      ],
    },
    {
      id: 'summary',
      title: 'SAFE-ND™ Practitioner Summary',
      notes: [
        {
          type: 'info',
          title: 'Signature practice principle',
          text: "I do not determine which parent should win. I help families understand what a child's behaviour may be communicating, what functional demands are affecting the child, what supports are required in each home, and how the parenting system can be designed to reduce unnecessary stress and improve day-to-day functioning.",
        },
      ],
      fields: [
        { id: 'functioning', type: 'textarea', label: 'Child functioning summary', rows: 3 },
        { id: 'demands', type: 'textarea', label: 'Key parenting-system demands', rows: 3 },
        { id: 'findings', type: 'textarea', label: 'Two-home support and demand findings', rows: 3 },
        { id: 'consistency', type: 'textarea', label: 'Consistency / alignment / autonomy conclusions', rows: 3 },
        { id: 'strategy', type: 'textarea', label: 'Priority strategy recommendations', rows: 3 },
        { id: 'indicators', type: 'textarea', label: 'Indicators for future review', rows: 3 },
        { id: 'limitations', type: 'textarea', label: 'Limitations / unresolved factual questions', rows: 3 },
      ],
    },
    {
      id: 'disposition',
      title: 'Disposition / Next Step',
      fields: [
        {
          id: 'next',
          type: 'checks',
          label: 'Disposition',
          options: [
            'No parenting-plan change identified at this time',
            'Targeted adjustment recommended',
            'Broader parenting-plan revision recommended',
            'SAFE™ Functional Change Review indicated',
            'SAFE™ Neurodevelopmental Parenting Plan Review indicated',
            'Mediation / structured design recommended',
            'Independent legal review required',
            'Medical / psychological / allied professional input required',
            'Child-protection / safety response required where legally indicated',
          ],
          other: true,
          safetyOption: 'Child-protection / safety response required where legally indicated',
        },
        { id: 'signature', type: 'text', label: 'Reviewer signature (type full name)' },
        { id: 'signedDate', type: 'date', label: 'Date' },
      ],
    },
  ],
};
