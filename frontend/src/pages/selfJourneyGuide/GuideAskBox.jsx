import { useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { AiGuardFrame, useAiGuard } from '../../components/aiNotice/AiGuard';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../lib/api';
import { pagesContext } from './guideAnswers';

// Signed-in parents can type their own question to the AI guide; everyone else sees how to sign in.
export default function GuideAskBox({ steps, step, busy, setBusy, add }) {
  const { user } = useAuth();
  const { pathname } = useLocation();
  if (!user || user.is_guest) {
    return (
      <div className="sjg-signin" data-testid="sjr-guide-signin">
        Want to ask your own question?{' '}
        <Link to={`/login?redirect=${encodeURIComponent(pathname)}`} data-testid="sjr-guide-signin-link">Sign in</Link>{' '}
        to chat with the AI guide.
      </div>
    );
  }
  return <AskForm steps={steps} step={step} busy={busy} setBusy={setBusy} add={add} />;
}

function AskForm({ steps, step, busy, setBusy, add }) {
  const [input, setInput] = useState('');
  const session = useRef(null);
  const guard = useAiGuard('journey_guide', input);

  const send = async (e) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || busy || !(await guard.confirmSend(q))) return;
    add({ role: 'user', text: q });
    setInput('');
    setBusy(true);
    try {
      const { data } = await api.post('/journey-guide/self-journey-read/chat', {
        message: q, session_id: session.current, section: step ? step.title : 'Self Journey menu', pages: pagesContext(steps),
      });
      session.current = data.session_id;
      add({ role: 'guide', text: data.reply });
    } catch {
      add({ role: 'guide', text: 'Sorry, I couldn’t respond just now. Please try again.' });
    } finally {
      setBusy(false);
    }
  };

  return (
    <AiGuardFrame tp="sjr-guide" guard={guard} className="sjg-ask">
      <form className="sj-sheet-input" onSubmit={send}>
        <label htmlFor="sjr-guide-input" className="sjg-sr">Ask the Journey Guide</label>
        <input
          id="sjr-guide-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your own question…"
          maxLength={1000}
          data-testid="sjr-guide-input"
          {...guard.inputProps}
        />
        <button type="submit" className="sj-send" aria-label="Send" disabled={busy} data-testid="sjr-guide-send">➤</button>
      </form>
    </AiGuardFrame>
  );
}
