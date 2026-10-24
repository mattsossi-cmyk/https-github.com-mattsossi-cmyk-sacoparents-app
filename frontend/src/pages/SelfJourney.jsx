import { useEffect, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import Disclaimer from '../components/Disclaimer';
import StartWithSafetyBanner from '../components/startWithSafety/StartWithSafetyBanner';
import SelfJourneyHandout from './SelfJourneyHandout';

/**
 * SelfJourney — SA CoParents (the reading Self Journey, open to anyone)
 * The guided Self Journey (saved privately to the parent's account) lives at /self-journey/guided.
 *
 * Routes (frontend/src/App.js, above the catch-all "*" route):
 *   <Route path="/self-journey" element={<SelfJourney />} />
 *   <Route path="/self-journey/:stepId" element={<SelfJourney />} />
 *
 * PRIVACY: this page never asks for, shows or stores Safety First answers.
 * The only thing remembered is WHICH pages a parent marked complete (page ids),
 * on their own device, so the percentage survives a refresh. Quick Exit and
 * "Clear my progress" erase it.
 *
 * TO EDIT CONTENT: change the STEPS list below. Add, remove or reorder pages
 * there, and the menu, progress bar, times and Back/Next buttons update themselves.
 */

const BASE = '/self-journey';
const GUIDED = '/self-journey/guided';
// Old guided-journey links (/self-journey/safety, …) open the same page in the guided journey.
const GUIDED_ONLY_SLUGS = ['safety', 'situation', 'child-needs', 'foundation', 'mediation', 'summary'];
const STORAGE_KEY = 'sacp_self_journey_done';
// The retired Journey library's ticks (same page ids) carry over once, then the old key is removed.
const OLD_LIBRARY_KEY = 'sacp_journey_library_done';
const START_WITH_SAFETY = '/start-with-safety';
const EXIT_URL = 'https://www.google.com/search?q=weather';

// "Reviewed by" line on pages marked reviewed: true.
// Leave as null until a real professional has actually reviewed the text.
// Example: const REVIEWER = { name: 'Jane Doe, LPC', role: 'Licensed Professional Counselor', date: 'November 2026' };
const REVIEWER = null;

// ─────────────── FINISH PAGE: "WHAT'S NEXT" LINKS (edit these) ───────────────
// Set each href to the real page in your app. Links starting with http open in a new tab.
const NEXT_STEPS = [
  {
    icon: '💬',
    title: 'Communication Builder & BIFF Tool',
    text: 'Write calm, child-focused messages to the other parent: Brief, Informative, Friendly, Firm.',
    href: '/dashboard?open=comm-builder',
    testid: 'biff',
  },
  {
    icon: '📄',
    title: 'Export your Journey Report (PDF)',
    text: 'Save a summary to bring to a mediator, attorney or counselor.',
    href: `${GUIDED}/summary`, // the guided journey's summary page has "Download my PDF" (sign-in needed)
    testid: 'report',
  },
  {
    icon: '🧑‍⚖️',
    title: 'Find a mediator or legal help',
    text: 'A family mediator can help you turn priorities into a written parenting plan.',
    href: '/help',
    testid: 'help',
  },
  {
    icon: '⚖️',
    title: 'Court Ordered Path',
    text: 'If a court has ordered co-parenting education or mediation, continue on that path.',
    href: '/dashboard?open=court',
    testid: 'court',
  },
];
const FINISH_ID = 'complete';

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
    banner: true, // shows the Start with Safety picture banner at the top of the page
    reviewed: true,
  },
  {
    id: 'parallel-parenting',
    title: 'Parallel Parenting',
    icon: '↔️',
    minutes: 12,
    summary: 'A low-contact option for high-conflict or unsafe situations.',
    reviewed: true,
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
    reviewed: true,
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

function readIds(key) {
  try {
    const saved = JSON.parse(localStorage.getItem(key));
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

function readDone() {
  const ids = new Set([...readIds(STORAGE_KEY), ...readIds(OLD_LIBRARY_KEY)]);
  return STEPS.filter((s) => ids.has(s.id)).map((s) => s.id);
}

function quickExit() {
  try { localStorage.removeItem(STORAGE_KEY); localStorage.removeItem(OLD_LIBRARY_KEY); } catch {}
  window.location.replace(EXIT_URL);
}

// Prints only the one-page handout (see SelfJourneyHandout), named after the page for "Save as PDF".
function printHandout(step) {
  const title = document.title;
  document.title = `SA CoParents Self Journey - ${step.title}`;
  document.body.classList.add('sjr-printing');
  const cleanup = () => {
    document.body.classList.remove('sjr-printing');
    document.title = title;
    window.removeEventListener('afterprint', cleanup);
  };
  window.addEventListener('afterprint', cleanup);
  window.print();
}

export default function SelfJourney() {
  const { stepId } = useParams();
  const navigate = useNavigate();
  const [done, setDone] = useState(readDone);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(done));
      localStorage.removeItem(OLD_LIBRARY_KEY);
    } catch {}
  }, [done]);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [stepId]);

  const isFinish = stepId === FINISH_ID;
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
    navigate(next ? `${BASE}/${next.id}` : `${BASE}/${FINISH_ID}`);
  };

  const clearProgress = () => {
    if (window.confirm('Clear your progress on this device?')) setDone([]);
  };

  if (GUIDED_ONLY_SLUGS.includes(stepId)) return <Navigate to={`${GUIDED}/${stepId}`} replace />;

  return (
    <div style={st.page} data-testid="sjr-page">
      <header style={st.header}>
        <Link to={BASE} style={st.brand} data-testid="sjr-brand">SA CoParents · Self Journey</Link>
        <button type="button" onClick={quickExit} style={st.exitBtn} aria-label="Quick exit: leave this site now" data-testid="sjr-quick-exit">
          Quick Exit ✕
        </button>
      </header>
      <div style={st.helpBar} role="note" data-testid="sjr-help-bar">
        In danger? <a href="tel:911" style={st.helpLink} data-testid="sjr-call-911">Call 911</a> · DV{' '}
        <a href="tel:18007997233" style={st.helpLink} data-testid="sjr-call-dv">1-800-799-7233</a> · Text START to 88788 ·{' '}
        <a href="tel:988" style={st.helpLink} data-testid="sjr-call-988">988</a>
      </div>

      <ProgressBar percent={percent} doneCount={done.length} minutesLeft={minutesLeft} />

      <main style={st.main}>
        {isFinish ? (
          <FinishPage done={done} />
        ) : step ? (
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

      <footer style={st.footer} data-testid="sjr-footer">
        <Disclaimer />
        <Link to="/privacy-notice" style={st.footerLink} data-testid="sjr-footer-privacy">Privacy Notice</Link> ·{' '}
        <Link to="/who-can-see-my-information" style={st.footerLink} data-testid="sjr-footer-who-can-see">Who can see my information</Link> ·{' '}
        <Link to="/help" style={st.footerLink} data-testid="sjr-footer-help">Get help</Link>
      </footer>
    </div>
  );
}

function ProgressBar({ percent, doneCount, minutesLeft }) {
  return (
    <div style={st.progressWrap} data-testid="sjr-progress" data-percent={percent}>
      <div style={st.progressText}>
        <strong data-testid="sjr-progress-percent">{percent}% complete</strong>
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
      <h1 style={st.h1} data-testid="sjr-hub-title">Your Self Journey</h1>
      <p style={st.lead}>
        Go at your own pace, in any order. Pick a page below, and come back here any time with{' '}
        <em>“My Self Journey”</em>. The whole journey takes about {TOTAL_MINUTES} minutes.
      </p>

      {nextUnfinished ? (
        <Link to={`${BASE}/${nextUnfinished.id}`} style={st.primaryLink} data-testid="sjr-start">
          {done.length === 0 ? 'Start' : 'Continue'}: {nextUnfinished.title} →
        </Link>
      ) : (
        <Link to={`${BASE}/${FINISH_ID}`} style={st.primaryLink} data-testid="sjr-start">
          🎉 You've finished, see your next steps →
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
                data-testid={`sjr-card-${s.id}`}
                data-done={isDone ? 'true' : 'false'}
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
        <button type="button" onClick={onClear} style={st.textBtn} data-testid="sjr-clear">
          Clear my progress
        </button>
      )}
      <p style={st.note} data-testid="sjr-device-note">
        Only which pages you've finished is remembered, on this device only. None of your thoughts or
        answers are saved. Quick Exit erases your progress.
      </p>

      <section style={st.section} data-testid="sjr-guided">
        <h2 style={st.h2}>Want a guided version?</h2>
        <p style={{ margin: '0 0 8px' }}>
          The guided Self Journey walks you through each step with your own private notes, saved to your account.
        </p>
        <Link to={GUIDED} style={{ color: PURPLE, fontWeight: 700 }} data-testid="sjr-open-guided">
          Open the guided Self Journey →
        </Link>
      </section>
    </>
  );
}

function StepPage({ step, index, isDone, onToggleDone, onCompleteAndNext, onJump, done }) {
  const prev = STEPS[index - 1];
  const next = STEPS[index + 1];

  return (
    <>
      <div style={st.topNav}>
        <Link to={BASE} style={st.backLink} data-testid="sjr-back-to-hub">← My Self Journey</Link>
        <label style={st.jumpLabel}>
          <span style={st.srOnly}>Jump to a page</span>
          <select value={step.id} onChange={(e) => onJump(e.target.value)} style={st.select} data-testid="sjr-jump">
            <option value="">☰ All pages</option>
            {STEPS.map((s, i) => (
              <option key={s.id} value={s.id}>
                {i + 1}. {s.title} {done.includes(s.id) ? '✓' : ''}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p style={st.stepMeta} data-testid="sjr-step-meta">
        Page {index + 1} of {STEPS.length} · ⏱ about {step.minutes} min
        {isDone && <span style={st.doneBadge} data-testid="sjr-done-badge">✓ Completed</span>}
      </p>
      <h1 style={st.h1} data-testid="sjr-step-title">
        <span aria-hidden="true">{step.icon} </span>
        {step.title}
      </h1>
      <p style={st.lead}>{step.summary}</p>
      {step.banner && (
        <div style={{ marginBottom: 16 }}>
          <StartWithSafetyBanner testid="sjr-safety-banner" />
        </div>
      )}
      {step.reviewed && REVIEWER && (
        <p style={st.reviewed}>
          ✓ Reviewed by {REVIEWER.name}, {REVIEWER.role} · {REVIEWER.date}
        </p>
      )}

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
        <a href={step.cta.href} style={{ ...st.primaryLink, ...(step.alert ? { background: RED } : null) }} data-testid="sjr-cta">
          {step.cta.label}
        </a>
      )}

      <div style={st.completeRow}>
        {isDone ? (
          <button type="button" onClick={onToggleDone} style={st.textBtn} data-testid="sjr-mark-not-finished">
            Mark as not finished
          </button>
        ) : (
          <button type="button" onClick={onCompleteAndNext} style={st.completeBtn} data-testid="sjr-complete">
            ✓ I've finished this page{next ? ' — next' : ' — see my next steps'}
          </button>
        )}
      </div>

      <div style={{ textAlign: 'center', marginBottom: 8 }}>
        <button type="button" onClick={() => printHandout(step)} style={st.printBtn} data-testid="sjr-print">
          🖨️ Print this page (one-page handout)
        </button>
      </div>
      <SelfJourneyHandout step={step} reviewer={step.reviewed ? REVIEWER : null} />

      <nav style={st.bottomNav} aria-label="Page navigation">
        {prev ? (
          <Link to={`${BASE}/${prev.id}`} style={st.navBtn} data-testid="sjr-prev">‹ {prev.title}</Link>
        ) : (
          <Link to={BASE} style={st.navBtn} data-testid="sjr-prev">‹ My Self Journey</Link>
        )}
        {next ? (
          <Link to={`${BASE}/${next.id}`} style={{ ...st.navBtn, textAlign: 'right' }} data-testid="sjr-next">{next.title} ›</Link>
        ) : (
          <Link to={`${BASE}/${FINISH_ID}`} style={{ ...st.navBtn, textAlign: 'right' }} data-testid="sjr-next">My next steps ›</Link>
        )}
      </nav>
    </>
  );
}

function FinishPage({ done }) {
  const remaining = STEPS.filter((s) => !done.includes(s.id));
  const allDone = remaining.length === 0;

  return (
    <>
      <div style={st.topNav}>
        <Link to={BASE} style={st.backLink} data-testid="sjr-finish-back">← My Self Journey</Link>
      </div>

      <div style={st.celebrate} data-testid="sjr-finish" data-all-done={allDone ? 'true' : 'false'}>
        <div style={{ fontSize: 44, lineHeight: 1 }} aria-hidden="true">{allDone ? '🎉' : '🧭'}</div>
        <h1 style={{ ...st.h1, margin: '10px 0 6px' }} data-testid="sjr-finish-title">
          {allDone ? 'You finished your Self Journey' : 'Almost there'}
        </h1>
        <p style={{ margin: 0 }}>
          {allDone
            ? 'That took real courage and care for your child. Here is what you can do next.'
            : `You have ${remaining.length} page${remaining.length === 1 ? '' : 's'} left. You can finish them now, or look at your next steps first.`}
        </p>
      </div>

      {!allDone && (
        <section style={st.section}>
          <h2 style={st.h2}>Pages left</h2>
          <ul style={st.promptList}>
            {remaining.map((s) => (
              <li key={s.id} style={{ marginBottom: 6 }}>
                <Link to={`${BASE}/${s.id}`} style={{ color: PURPLE, fontWeight: 600 }} data-testid={`sjr-left-${s.id}`}>
                  {s.title}
                </Link>{' '}
                <span style={{ color: GRAY, fontSize: 14 }}>· about {s.minutes} min</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <h2 style={{ ...st.h2, marginTop: 20 }}>Your next steps</h2>
      <ul style={st.cardList}>
        {NEXT_STEPS.map((n) => {
          const external = /^https?:/.test(n.href);
          const inner = (
            <>
              <span style={st.cardIcon} aria-hidden="true">{n.icon}</span>
              <span style={{ flex: 1 }}>
                <span style={st.cardTitle}>{n.title}</span>
                <span style={st.cardSummary}>{n.text}</span>
              </span>
              <span aria-hidden="true" style={st.chevron}>›</span>
            </>
          );
          return (
            <li key={n.title}>
              {external ? (
                <a href={n.href} target="_blank" rel="noopener noreferrer" style={st.card} data-testid={`sjr-next-${n.testid}`}>{inner}</a>
              ) : (
                <Link to={n.href} style={st.card} data-testid={`sjr-next-${n.testid}`}>{inner}</Link>
              )}
            </li>
          );
        })}
      </ul>

      <section style={st.sectionAlert}>
        <h2 style={{ ...st.h2, color: RED }}>If safety becomes a concern</h2>
        <p style={{ margin: 0 }}>
          Things can change. You can return to{' '}
          <a href={START_WITH_SAFETY} style={{ color: RED, fontWeight: 700 }} data-testid="sjr-finish-safety">Start with Safety</a> any time, or
          call the National DV Hotline at <a href="tel:18007997233" style={{ color: RED, fontWeight: 700 }} data-testid="sjr-finish-dv">1-800-799-7233</a>.
        </p>
      </section>

      <p style={{ ...st.note, textAlign: 'center' }}>
        You can come back and review any page of your Self Journey whenever you like.
      </p>
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
  printBtn: {
    background: PURPLE_LIGHT, color: PURPLE, border: '1px solid #E2DAF0', borderRadius: 99,
    padding: '10px 16px', fontSize: 15, fontWeight: 600, cursor: 'pointer', minHeight: 44,
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
  celebrate: {
    textAlign: 'center', background: PURPLE_LIGHT, border: `2px solid ${PURPLE}`,
    borderRadius: 14, padding: '22px 16px', marginBottom: 16,
  },
  reviewed: {
    fontSize: 14, color: PURPLE, background: PURPLE_LIGHT, borderRadius: 8,
    padding: '6px 10px', margin: '-8px 0 16px', display: 'inline-block',
  },
};
