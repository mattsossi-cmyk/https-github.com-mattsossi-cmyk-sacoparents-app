import { useEffect, useRef, useState } from 'react';

const supported = () => typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;

// Stops any answer being read aloud (Quick Exit, closing the chat).
export const stopReading = () => {
  if (supported()) window.speechSynthesis.cancel();
};

// Reads one answer aloud with the device's own voice. Nothing leaves the device; only plays when tapped.
export default function ListenButton({ text, testid = 'listen-btn' }) {
  const [speaking, setSpeaking] = useState(false);
  const mine = useRef(null);

  useEffect(() => () => {
    if (mine.current && window.speechSynthesis?.speaking) window.speechSynthesis.cancel();
  }, []);

  if (!supported()) return null;

  const toggle = () => {
    if (speaking) {
      window.speechSynthesis.cancel();
      return;
    }
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/[→↗]/g, ''));
    u.lang = document.documentElement.lang || 'en-US';
    u.rate = 0.95;
    u.onend = u.onerror = () => {
      if (mine.current === u) mine.current = null;
      setSpeaking(false);
    };
    mine.current = u;
    setSpeaking(true);
    window.speechSynthesis.speak(u);
  };

  return (
    <button
      type="button"
      className={`sj-listen${speaking ? ' is-on' : ''}`}
      onClick={toggle}
      aria-pressed={speaking}
      aria-label={speaking ? 'Stop reading this answer aloud' : 'Listen to this answer'}
      data-testid={testid}
      data-speaking={speaking ? 'true' : 'false'}
    >
      <span aria-hidden="true">{speaking ? '■' : '🔊'}</span> {speaking ? 'Stop' : 'Listen'}
    </button>
  );
}
