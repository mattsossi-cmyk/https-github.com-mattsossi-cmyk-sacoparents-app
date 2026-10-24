import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

/**
 * Journey library — SA CoParents (the founder's reading hub; the guided Self Journey stays at /self-journey)
 *
 * Routes (frontend/src/App.js, above the catch-all "*" route):
 *   <Route path="/journey-library" element={<JourneyLibrary />} />
 *   <Route path="/journey-library/:stepId" element={<JourneyLibrary />} />
 *
 * PRIVACY: this page never asks for, shows or stores Family check-in answers.
 * The only thing remembered is WHICH pages a parent marked complete (page ids),
 * on their own device, so the percentage survives a refresh. Quick Exit and
 * "Clear my progress" erase it.
 *
 * TO EDIT CONTENT: change the STEPS list below. Add, remove or reorder pages
 * there, and the menu, progress bar, times and Back/Next buttons update themselves.
 */

const BASE = '/journey-library';
const STORAGE_KEY = 'sacp_journey_library_done';
const START_WITH_SAFETY = '/start-with-safety';
const EXIT_URL = 'https://www.google.com/search?q=weather';

const PURPLE = '#3D1A78';
const PURPLE_LIGHT = '#F4EFFB';
const RED = '#B42318';
const RED_LIGHT = '#FEF3F2';
const GRAY = '#6B6480';

// ─────────────────────────── EDIT YOUR PAGES HERE ───────────────────────────
const STEPS = [
  {
    id: 'self-assessment',
    title: 'Self Assessment',
    icon: '🪞',
    minutes: 10,
    summary: 'Take a quiet look at where you are right now, for you and your child.',
    sections: [
      {
        heading: 'Why start here',
        body: 'Before choosing a path, it helps to understand your own needs, worries and hopes. There are no right or wrong answers, and nothing here is saved or shared.',
      },
    ],
    prompts: [
      'What does my child need most from both parents right now?',
      'What are my biggest worries about the coming months?',
      'Which parts of parenting with the other parent are working, even a little?',
      'What would a good day look like for my child a year from now?',
      'What support do I need for myself?',
    ],
  },
  {
    id: 'safety-first',
    title: 'Safety First',
    icon: '🛡️',
    minutes: 5,
    summary: 'Make sure working with the other parent is safe before choosing a path.',
    sections: [
      {
        heading: 'Safety comes before any plan',
        body: 'If there has been violence, threats, stalking or control, standard co-parenting advice may not be safe for you. Parallel parenting, separate mediation sessions or a protective order may be better options.',
      },
      {
        heading: 'Take Safety First',
        body: 'Safety First happens privately on SACOparentsAlign. SA CoParents never sees your answers.',
      },
    ],
    cta: { label: 'Go to Start with Safety →', href: START_WITH_SAFETY },
    alert: true,
  },
  {
    id: 'parallel-parenting',
    title: 'Parallel Parenting',
    icon: '↔️',
    minutes: 12,
    summary: 'A low-contact option for high-conflict or unsafe situations.',
    sections: [
      {
        heading: 'What it is',
        body: 'Each parent makes everyday decisions during their own time, with as little direct contact as possible. Communication is short, written and about the child only.',
      },
      {
        heading: 'When it can help',
        body: 'When conversations often turn into conflict, when one parent feels unsafe or pressured, or when a cooling-off period is needed.',
      },
      {
        heading: 'Common tools',
        body: 'A detailed written parenting plan, exchanges at a neutral or public place, a co-parenting app for messages, and BIFF responses (Brief, Informative, Friendly, Firm).',
      },
    ],
  },
  {
    id: 'coparenting',
    title: 'Co-Parenting',
    icon: '🤝',
    minutes: 12,
    summary: 'Working together on shared decisions when it is safe to do so.',
    sections: [
      {
        heading: 'What it is',
        body: 'Both parents communicate directly, coordinate schedules and make major decisions together, keeping the focus on the child.',
      },
      {
        heading: 'When it can help',
        body: 'When both parents feel safe, can disagree respectfully and are willing to put the child’s needs first.',
      },
      {
        heading: 'Habits that help',
        body: 'Regular check-ins, consistent rules across both homes, never using the child as a messenger, and agreeing ahead of time how to handle disagreements.',
      },
    ],
  },
  {
    id: 'medical',
    title: 'Medical',
    icon: '🩺',
    minutes: 8,
    summary: 'Keeping your child’s health care consistent across two homes.',
    sections: [
      {
        heading: 'Things to agree on',
        body: 'Who the doctors and dentists are, how appointments are scheduled and shared, how medications travel between homes, and who has access to records.',
      },
      {
        heading: 'Special health needs',
        body: 'If your child has a chronic condition, disability or special needs, write down care routines, emergency contacts and equipment so both homes can follow them.',
      },
    ],
  },
  {
    id: 'educational',
    title: 'Educational',
    icon: '🎒',
    minutes: 8,
    summary: 'Supporting school, learning and activities from both homes.',
    sections: [
      {
        heading: 'Things to agree on',
        body: 'School choice, who attends conferences, how report cards and school messages are shared, homework routines, and activities and their costs.',
      },
      {
        heading: 'IEPs and 504 plans',
        body: 'If your child has an IEP or 504 plan, both parents can usually ask the school to include them in meetings and communications.',
      },
    ],
  },
  {
    id: 'psychological',
    title: 'Psychological',
    icon: '💜',
    minutes: 10,
    summary: 'Your child’s emotional well-being, and yours.',
    sections: [
      {
        heading: 'How children may react',
        body: 'Children can show stress through sleep changes, clinginess, anger, falling grades or physical complaints. Reactions often depend on age and on how much conflict they see.',
      },
      {
        heading: 'What helps',
        body: 'Predictable routines, permission to love both parents, keeping adult conflict away from the child, and a counselor when needed.',
      },
      {
        heading: 'Caring for yourself',
        body: 'Your well-being affects your child. Support from a counselor, a support group or trusted friends counts as part of the plan. If you are struggling, call or text 988 any time.',
      },
    ],
  },
];
// ────────────────────────────────────────────────────────────────────────────

const TOTAL_MINUTES = STEPS.reduce((sum, s) => sum + s.minutes, 0);

function readDone() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return Array.isArray(saved) ? saved.filter((id) => STEPS.some((s) => s.id === id)) : [];
  } catch {
    return [];
  }
}

function quickExit() {
  try { localStorage.removeItem(STORAGE_KEY); } catch {}
  window.location.replace(EXIT_URL);
}

export default function JourneyLibrary() {
  const { stepId } = useParams();
  const navigate = useNavigate();
  const [done, setDone] = useState(readDone);

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(done)); } catch {}
  }, [done]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [stepId]);

  const index = STEPS.findIndex((s) => s.id === stepId);
  const step = index >= 0 ? STEPS[index] : null;

  const percent = Math.round((done.length / STEPS.length) * 100);
  const minutesLeft = STEPS.filter((s) => !done.includes(s.id)).reduce((sum, s) => sum + s.minutes, 0);
  const nextUnfinished = STEPS.find((s) => !done.includes(s.id));

  const toggleDone = (id) =>
    setDone((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]));

  const completeAndNext = () => {
    if (!done.includes(step.id)) setDone((prev) => [...prev, step.id]);
    const next = STEPS[index + 1];
    navigate(next ? `${BASE}/${next.id}` : BASE);
  };

  const clearProgress = () => {
    if (window.confirm('Clear your progress on this device?')) setDone([]);
  };

  return (
    <div style={st.page} data-testid="journey-library">
      <header style={st.header}>
        <Link to={BASE} style={st.brand} data-testid="jl-brand">SA CoParents · Journey library</Link>
        <button type="button" onClick={quickExit} style={st.exitBtn} aria-label="Quick exit: leave this site now" data-testid="jl-quick-exit">
          Quick Exit ✕
        </button>
      </header>
      <div style={st.helpBar} role="note" data-testid="jl-help-bar">
        In danger? <a href="tel:911" style={st.helpLink}>Call 911</a> · DV{' '}
        <a href="tel:18007997233" style={st.helpLink}>1-800-799-7233</a> · Text START to 88788 ·{' '}
        <a href="tel:988" style={st.helpLink}>988</a>
      </div>

      <ProgressBar percent={percent} doneCount={done.length} minutesLeft={minutesLeft} />

      <main style={st.main}>
        {step ? (
          <StepPage
            step={step}
            index={index}
            isDone={done.includes(step.id)}
            onToggleDone={() => toggleDone(step.id)}
            onCompleteAndNext={completeAndNext}
            onJump={(id) => navigate(id ? `${BASE}/${id}` : BASE)}
            done={done}
          />
        ) : (
          <Hub done={done} nextUnfinished={nextUnfinished} onClear={clearProgress} />
        )}
      </main>

      <footer style={st.footer}>
        <Link to="/privacy-notice" style={st.footerLink} data-testid="jl-footer-privacy">Privacy Notice</Link> ·{' '}
        <Link to="/who-can-see-my-information" style={st.footerLink} data-testid="jl-footer-who-can-see">Who can see my information</Link> ·{' '}
        <Link to="/help" style={st.footerLink} data-testid="jl-footer-help">Get help</Link>
      </footer>
    </div>
  );
}

function ProgressBar({ percent, doneCount, minutesLeft }) {
  return (
    <div style={st.progressWrap} data-testid="jl-progress" data-percent={percent}>
      <div style={st.progressText}>
        <strong>{percent}% complete</strong>
        <span>
          {doneCount} of {STEPS.length} pages · {minutesLeft > 0 ? `about ${minutesLeft} min left` : 'all done 🎉'}
        </span>
      </div>
      <div
        style={st.track}
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Self Journey progress"
      >
        <div style={{ ...st.fill, width: `${percent}%` }} />
      </div>
    </div>
  );
}

function Hub({ done, nextUnfinished, onClear }) {
  return (
    <>
      <h1 style={st.h1} data-testid="jl-hub-title">Your Journey library</h1>
      <p style={st.lead}>
        Go at your own pace, in any order. Pick a page below, and come back here any time with{' '}
        <em>“My Journey library”</em>. The whole journey takes about {TOTAL_MINUTES} minutes.
      </p>

      {nextUnfinished && (
        <Link to={`${BASE}/${nextUnfinished.id}`} style={st.primaryLink} data-testid="jl-start">
          {done.length === 0 ? 'Start' : 'Continue'}: {nextUnfinished.title} →
        </Link>
      )}

      <ol style={st.cardList}>
        {STEPS.map((s, i) => {
          const isDone = done.includes(s.id);
          return (
            <li key={s.id}>
              <Link
                to={`${BASE}/${s.id}`}
                style={{ ...st.card, ...(s.alert ? st.cardAlert : null), ...(isDone ? st.cardDone : null) }}
                data-testid={`jl-card-${s.id}`}
              >
                <span style={st.cardIcon} aria-hidden="true">{s.icon}</span>
                <span style={{ flex: 1 }}>
                  <span style={st.cardTitle}>
                    {i + 1}. {s.title}
                  </span>
                  <span style={st.cardSummary}>{s.summary}</span>
                  <span style={st.cardMeta}>
                    ⏱ about {s.minutes} min · {isDone ? '✓ Completed' : 'Not started'}
                  </span>
                </span>
                <span aria-hidden="true" style={st.chevron}>›</span>
              </Link>
            </li>
          );
        })}
      </ol>

      {done.length > 0 && (
        <button type="button" onClick={onClear} style={st.textBtn} data-testid="jl-clear">
          Clear my progress
        </button>
      )}
      <p style={st.note}>
        Only which pages you've finished is remembered, on this device only. None of your thoughts or
        answers are saved. Quick Exit erases your progress.
      </p>
    </>
  );
}

function StepPage({ step, index, isDone, onToggleDone, onCompleteAndNext, onJump, done }) {
  const prev = STEPS[index - 1];
  const next = STEPS[index + 1];

  return (
    <>
      <div style={st.topNav}>
        <Link to={BASE} style={st.backLink} data-testid="jl-back-to-hub">← My Journey library</Link>
        <label style={st.jumpLabel}>
          <span style={st.srOnly}>Jump to a page</span>
          <select value={step.id} onChange={(e) => onJump(e.target.value)} style={st.select} data-testid="jl-jump">
            <option value="">☰ All pages</option>
            {STEPS.map((s, i) => (
              <option key={s.id} value={s.id}>
                {i + 1}. {s.title} {done.includes(s.id) ? '✓' : ''}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p style={st.stepMeta}>
        Page {index + 1} of {STEPS.length} · ⏱ about {step.minutes} min
        {isDone && <span style={st.doneBadge}>✓ Completed</span>}
      </p>
      <h1 style={st.h1} data-testid="jl-step-title">
        <span aria-hidden="true">{step.icon} </span>
        {step.title}
      </h1>
      <p style={st.lead}>{step.summary}</p>

      {step.sections.map((sec) => (
        <section key={sec.heading} style={step.alert ? st.sectionAlert : st.section}>
          <h2 style={{ ...st.h2, ...(step.alert ? { color: RED } : null) }}>{sec.heading}</h2>
          <p style={{ margin: 0 }}>{sec.body}</p>
        </section>
      ))}

      {step.prompts && (
        <section style={st.section}>
          <h2 style={st.h2}>Questions to think about</h2>
          <p style={{ ...st.note, marginTop: 0 }}>Just for reflection. Nothing is typed in or saved.</p>
          <ul style={st.promptList}>
            {step.prompts.map((p) => (
              <li key={p} style={{ marginBottom: 6 }}>{p}</li>
            ))}
          </ul>
        </section>
      )}

      {step.cta && (
        <a href={step.cta.href} style={{ ...st.primaryLink, ...(step.alert ? { background: RED } : null) }} data-testid="jl-cta">
          {step.cta.label}
        </a>
      )}

      <div style={st.completeRow}>
        {isDone ? (
          <button type="button" onClick={onToggleDone} style={st.textBtn} data-testid="jl-mark-not-finished">
            Mark as not finished
          </button>
        ) : (
          <button type="button" onClick={onCompleteAndNext} style={st.completeBtn} data-testid="jl-complete">
            ✓ I've finished this page{next ? ' — next' : ''}
          </button>
        )}
      </div>

      <nav style={st.bottomNav} aria-label="Page navigation">
        {prev ? (
          <Link to={`${BASE}/${prev.id}`} style={st.navBtn} data-testid="jl-prev">‹ {prev.title}</Link>
        ) : (
          <Link to={BASE} style={st.navBtn} data-testid="jl-prev">‹ My Journey library</Link>
        )}
        {next ? (
          <Link to={`${BASE}/${next.id}`} style={{ ...st.navBtn, textAlign: 'right' }} data-testid="jl-next">{next.title} ›</Link>
        ) : (
          <Link to={BASE} style={{ ...st.navBtn, textAlign: 'right' }} data-testid="jl-next">My Journey library ›</Link>
        )}
      </nav>
    </>
  );
}

const st = {
  page: {
    minHeight: '100vh',
    background: '#FFFFFF',
    color: '#1F1A2E',
    fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
    lineHeight: 1.6,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
    padding: '10px 16px',
    background: PURPLE,
    position: 'sticky',
    top: 0,
    zIndex: 10,
  },
  brand: { color: '#FFFFFF', fontWeight: 700, fontSize: 17, textDecoration: 'none' },
  exitBtn: {
    background: RED, color: '#FFFFFF', border: 'none', borderRadius: 8,
    padding: '10px 14px', fontWeight: 700, fontSize: 15, cursor: 'pointer', minHeight: 44, flexShrink: 0,
  },
  helpBar: { background: RED_LIGHT, color: RED, fontSize: 13, padding: '6px 16px', textAlign: 'center' },
  helpLink: { color: RED, fontWeight: 700 },
  progressWrap: { maxWidth: 680, margin: '0 auto', padding: '14px 16px 0' },
  progressText: {
    display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 4,
    fontSize: 14, color: GRAY, marginBottom: 6,
  },
  track: { height: 10, background: '#E9E3F4', borderRadius: 99, overflow: 'hidden' },
  fill: { height: '100%', background: PURPLE, borderRadius: 99, transition: 'width 0.4s ease' },
  main: { maxWidth: 680, margin: '0 auto', padding: '20px 16px 40px' },
  h1: { color: PURPLE, fontSize: 28, lineHeight: 1.25, margin: '0 0 8px' },
  h2: { color: PURPLE, fontSize: 19, margin: '0 0 6px' },
  lead: { fontSize: 17, margin: '0 0 18px' },
  note: { fontSize: 14, color: GRAY },
  primaryLink: {
    display: 'block', textAlign: 'center', background: PURPLE, color: '#FFFFFF', borderRadius: 10,
    padding: '14px 16px', fontWeight: 700, fontSize: 17, textDecoration: 'none', margin: '8px 0 20px',
  },
  cardList: { listStyle: 'none', padding: 0, margin: '0 0 16px', display: 'grid', gap: 10 },
  card: {
    display: 'flex', alignItems: 'center', gap: 12, padding: 14, borderRadius: 12,
    border: '2px solid #E2DAF0', textDecoration: 'none', color: 'inherit', background: '#FFFFFF',
  },
  cardAlert: { borderColor: '#F3B8B2', background: RED_LIGHT },
  cardDone: { borderColor: PURPLE, background: PURPLE_LIGHT },
  cardIcon: { fontSize: 26, width: 34, textAlign: 'center', flexShrink: 0 },
  cardTitle: { display: 'block', fontWeight: 700, color: PURPLE, fontSize: 17 },
  cardSummary: { display: 'block', fontSize: 15 },
  cardMeta: { display: 'block', fontSize: 13, color: GRAY, marginTop: 2 },
  chevron: { fontSize: 28, color: PURPLE, flexShrink: 0 },
  topNav: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    gap: 10, flexWrap: 'wrap', marginBottom: 14,
  },
  backLink: { color: PURPLE, fontWeight: 700, textDecoration: 'none', padding: '8px 0', minHeight: 44, display: 'inline-flex', alignItems: 'center' },
  jumpLabel: { flex: '0 1 220px' },
  select: {
    width: '100%', minHeight: 44, borderRadius: 8, border: `2px solid #D9D2E9`,
    padding: '8px 10px', fontSize: 15, background: '#FFFFFF', color: '#1F1A2E',
  },
  srOnly: { position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' },
  stepMeta: { fontSize: 14, color: GRAY, margin: '0 0 4px', display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' },
  doneBadge: { background: PURPLE_LIGHT, color: PURPLE, fontWeight: 700, borderRadius: 99, padding: '2px 10px', fontSize: 13 },
  section: { background: PURPLE_LIGHT, borderRadius: 12, padding: 16, marginBottom: 12 },
  sectionAlert: { background: RED_LIGHT, border: `1px solid #F3B8B2`, borderRadius: 12, padding: 16, marginBottom: 12 },
  promptList: { paddingLeft: 20, margin: '8px 0 0' },
  completeRow: { margin: '20px 0 8px', textAlign: 'center' },
  completeBtn: {
    width: '100%', background: '#FFFFFF', color: PURPLE, border: `2px solid ${PURPLE}`, borderRadius: 10,
    padding: '13px 16px', fontSize: 16, fontWeight: 700, cursor: 'pointer', minHeight: 48,
  },
  textBtn: {
    background: 'none', border: 'none', color: GRAY, textDecoration: 'underline',
    cursor: 'pointer', fontSize: 15, padding: 8, minHeight: 44,
  },
  bottomNav: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10,
    borderTop: '1px solid #EEE9F6', paddingTop: 16, marginTop: 8,
  },
  navBtn: {
    color: PURPLE, fontWeight: 600, textDecoration: 'none', padding: '10px 4px', minHeight: 44,
    display: 'block', fontSize: 15,
  },
  footer: { borderTop: '1px solid #EEE9F6', padding: 16, fontSize: 14, color: GRAY, textAlign: 'center' },
  footerLink: { color: PURPLE },
};
