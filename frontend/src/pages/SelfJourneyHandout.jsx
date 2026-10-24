import { useEffect } from 'react';
import { createPortal } from 'react-dom';

import { DISCLAIMER_TEXT } from '../components/Disclaimer';
import './SelfJourneyHandout.css';

const LINES_PER_QUESTION = 3;
// Printable height of the smaller of Letter / A4 with 0.55in margins (9.9in at 96px/in), minus a little room.
const PAGE_HEIGHT_PX = 930;
const MIN_ZOOM = 0.5;

// Shrinks the handout just enough to stay on one page, even with large text settings.
export function fitHandoutToPage() {
  const el = document.querySelector('.sjh-root');
  if (!el) return;
  el.style.zoom = '';
  const height = el.scrollHeight;
  el.style.zoom = height > PAGE_HEIGHT_PX ? String(Math.max(MIN_ZOOM, PAGE_HEIGHT_PX / height).toFixed(3)) : '';
}

const lines = () =>
  Array.from({ length: LINES_PER_QUESTION }, (_, i) => <span key={i} className="sjh-line" aria-hidden="true" />);

// Print-only one-page handout of a Self Journey page. Kept off screen; printing shows only this.
export default function SelfJourneyHandout({ step, reviewer }) {
  const origin = window.location.origin;
  // Also fits when printing from the browser menu instead of the Print button.
  useEffect(() => {
    window.addEventListener('beforeprint', fitHandoutToPage);
    return () => window.removeEventListener('beforeprint', fitHandoutToPage);
  }, []);

  return createPortal(
    <div className="sjh-root" data-testid="sjr-handout" aria-hidden="true">
      <p className="sjh-private" data-testid="sjr-handout-private">
        <strong>Keep this handout somewhere private.</strong> It lists help line numbers and this site&apos;s web address.
      </p>
      <p className="sjh-brand">SA CoParents · Self Journey · Handout</p>
      <h1 className="sjh-title" data-testid="sjr-handout-title">{step.title}</h1>
      <p className="sjh-summary">{step.summary}</p>
      {reviewer && <p className="sjh-reviewed">Reviewed by {reviewer.name}, {reviewer.role} · {reviewer.date}</p>}

      {step.sections.map((sec) => (
        <section key={sec.heading} className="sjh-section">
          <h2>{sec.heading}</h2>
          <p>{sec.body}</p>
        </section>
      ))}

      {step.prompts && (
        <section className="sjh-section" data-testid="sjr-handout-questions">
          <h2>Questions to think about</h2>
          <ol className="sjh-questions">
            {step.prompts.map((p) => (
              <li key={p}>
                {p}
                <span className="sjh-lines">{lines()}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {step.cta && <p className="sjh-cta">{step.cta.label.replace(' →', '')}: {origin}{step.cta.href}</p>}

      <footer className="sjh-foot">
        <p><strong>Please note:</strong> {DISCLAIMER_TEXT}</p>
        <p>In danger? Call 911 · National DV Hotline 1-800-799-7233 (text START to 88788) · Call or text 988</p>
        <p>{origin}/self-journey/{step.id}</p>
        <p data-testid="sjr-handout-copyright">© {new Date().getFullYear()} SA CoParents · sacoparentsapp.online · All rights reserved.</p>
      </footer>
    </div>,
    document.body,
  );
}
