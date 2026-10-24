import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';

import GuideAvatar from '../selfJourney/GuideAvatar';
import GuideAskBox from './GuideAskBox';
import { GUIDE_LOGO, readyQuestions } from './guideAnswers';
import ListenButton, { stopReading } from './ListenButton';

const OPENING = 'Hi, I’m the Journey Guide. I can explain the Self Journey paths. Tap a question below.';

export default function GuideSheet({ steps, step, onClose }) {
  const calm = step?.id === 'safety-first';
  const [messages, setMessages] = useState([{ role: 'guide', text: OPENING }]);
  const [asked, setAsked] = useState([]);
  const [busy, setBusy] = useState(false);
  const listRef = useRef(null);
  const closeRef = useRef(null);

  useEffect(() => {
    closeRef.current?.focus();
    return stopReading;
  }, []);
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  useEffect(() => {
    listRef.current?.scrollTo?.(0, listRef.current.scrollHeight);
  }, [messages, busy]);

  const add = (...msgs) => setMessages((m) => [...m, ...msgs]);
  const askReady = (r) => {
    setAsked((a) => [...a, r.id]);
    add({ role: 'user', text: r.q }, { role: 'guide', text: r.a, link: r.link });
  };
  const chips = readyQuestions({ steps, stepId: step?.id }).filter((r) => !asked.includes(r.id));

  return (
    <>
      <div className="sj-scrim" onClick={onClose} aria-hidden="true" />
      <div className="sj-sheet sjg-sheet" role="dialog" aria-modal="true" aria-labelledby="sjg-title" data-testid="sjr-guide">
        <div className="sj-sheet-head">
          <div className="sjg-head">
            <GuideAvatar size={44} logoSrc={GUIDE_LOGO} calm={calm} speaking={busy} decorative testid="sjr-guide-avatar" />
            <div>
              <h2 id="sjg-title">Journey Guide</h2>
              <span className="sjg-muted">Helping with: {step ? step.title : 'Your Self Journey'}</span>
            </div>
          </div>
          <button type="button" ref={closeRef} className="sj-icon-btn" onClick={onClose} aria-label="Close the Journey Guide" data-testid="sjr-guide-close">
            ✕
          </button>
        </div>
        <div className="sj-sheet-body" ref={listRef} aria-live="polite" data-testid="sjr-guide-messages">
          {messages.map((m, i) => <Bubble key={i} m={m} i={i} calm={calm} onClose={onClose} />)}
          {busy && <Bubble m={{ role: 'guide', text: 'Thinking…' }} calm={calm} speaking />}
          {chips.length > 0 && (
            <div className="sj-suggestions" data-testid="sjr-guide-questions">
              {chips.map((r) => (
                <button key={r.id} type="button" onClick={() => askReady(r)} data-testid={`sjr-guide-q-${r.id}`}>{r.q}</button>
              ))}
            </div>
          )}
          <p className="sjg-note" data-testid="sjr-guide-note">The questions above are answered on your device. Nothing you tap is sent anywhere.</p>
        </div>
        <GuideAskBox steps={steps} step={step} busy={busy} setBusy={setBusy} add={add} />
      </div>
    </>
  );
}

function Bubble({ m, i, calm, speaking = false, onClose }) {
  if (m.role === 'user') return <div className="sj-bubble is-user" data-testid="sjr-guide-bubble-user">{m.text}</div>;
  return (
    <div className="sjg-row">
      <GuideAvatar size={26} logoSrc={GUIDE_LOGO} calm={calm} speaking={speaking} decorative />
      <div className="sj-bubble" data-testid={speaking ? 'sjr-guide-thinking' : 'sjr-guide-bubble'}>
        {m.text}
        {m.link && (
          <Link to={m.link.to} className="sjg-link" onClick={onClose} data-testid="sjr-guide-answer-link">{m.link.label} →</Link>
        )}
        {!speaking && <ListenButton text={m.text} testid={`sjr-guide-listen-${i}`} />}
      </div>
    </div>
  );
}
