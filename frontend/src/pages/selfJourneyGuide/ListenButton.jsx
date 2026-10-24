import { useEffect, useRef, useState } from 'react';

import { speedRate } from './voiceSpeed';

export const speechSupported = () =>
  typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;

// Stops any answer or page being read aloud (Quick Exit, closing the chat).
export const stopReading = () => {
  if (speechSupported()) window.speechSynthesis.cancel();
};

// Short sentence groups: some browsers stop long single utterances part-way.
function chunks(text) {
  const sentences = text.replace(/[→↗›‹]/g, '').match(/[^.!?\n]+[.!?]*\s*/g) || [text];
  const out = [];
  sentences.forEach((s) => {
    const last = out[out.length - 1];
    if (last && last.length + s.length < 220) out[out.length - 1] = last + s;
    else out.push(s);
  });
  return out.map((c) => c.trim()).filter(Boolean);
}

// Reads text aloud with the device's own voice. Nothing leaves the device; only plays when tapped.
export default function ListenButton({ text, testid = 'listen-btn', label = 'Listen', stopLabel = 'Stop', ariaLabel = 'Listen to this answer' }) {
  const [speaking, setSpeaking] = useState(false);
  const mine = useRef(null);

  useEffect(() => () => {
    if (mine.current && window.speechSynthesis?.speaking) window.speechSynthesis.cancel();
  }, []);

  if (!speechSupported()) return null;

  const toggle = () => {
    window.speechSynthesis.cancel();
    if (speaking) return;
    const parts = chunks(text).map((c) => {
      const u = new SpeechSynthesisUtterance(c);
      u.lang = document.documentElement.lang || 'en-US';
      u.rate = speedRate();
      return u;
    });
    if (!parts.length) return;
    const done = () => {
      mine.current = null;
      setSpeaking(false);
    };
    parts.forEach((u) => { u.onerror = done; });
    parts[parts.length - 1].onend = done;
    mine.current = parts[parts.length - 1];
    setSpeaking(true);
    parts.forEach((u) => window.speechSynthesis.speak(u));
  };

  return (
    <button
      type="button"
      className={`sj-listen${speaking ? ' is-on' : ''}`}
      onClick={toggle}
      aria-pressed={speaking}
      aria-label={speaking ? `${stopLabel} reading aloud` : ariaLabel}
      data-testid={testid}
      data-speaking={speaking ? 'true' : 'false'}
    >
      <span aria-hidden="true">{speaking ? '■' : '🔊'}</span> {speaking ? stopLabel : label}
    </button>
  );
}
