import { useEffect, useState } from 'react';

// Reading-voice speed, remembered on this device and shared by every Listen button.
const KEY = 'sacp_voice_speed';
const EVENT = 'sacp-voice-speed';
export const SPEEDS = [
  { id: 'slower', label: 'Slower', rate: 0.75 },
  { id: 'normal', label: 'Normal', rate: 0.95 },
  { id: 'faster', label: 'Faster', rate: 1.2 },
];

export function getSpeed() {
  try {
    const id = localStorage.getItem(KEY);
    return SPEEDS.some((s) => s.id === id) ? id : 'normal';
  } catch {
    return 'normal';
  }
}

export const speedRate = () => SPEEDS.find((s) => s.id === getSpeed()).rate;

export function useVoiceSpeed() {
  const [speed, setSpeedState] = useState(getSpeed);
  useEffect(() => {
    const sync = () => setSpeedState(getSpeed());
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, []);
  const setSpeed = (id) => {
    try { localStorage.setItem(KEY, id); } catch {}
    window.dispatchEvent(new Event(EVENT));
  };
  return [speed, setSpeed];
}
