import { speechSupported } from './ListenButton';
import { SPEEDS, useVoiceSpeed } from './voiceSpeed';

// Slower / Normal / Faster for the reading voice; the choice is saved on this device.
export default function VoiceSpeed({ testid = 'voice-speed' }) {
  const [speed, setSpeed] = useVoiceSpeed();
  if (!speechSupported()) return null;
  return (
    <div className="sj-speed" role="group" aria-label="Reading voice speed" data-testid={testid}>
      <span className="sj-speed-label">Voice speed</span>
      {SPEEDS.map((s) => (
        <button
          key={s.id}
          type="button"
          className={speed === s.id ? 'is-on' : ''}
          aria-pressed={speed === s.id}
          onClick={() => setSpeed(s.id)}
          data-testid={`${testid}-${s.id}`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
