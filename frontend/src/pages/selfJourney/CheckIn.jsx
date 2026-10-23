/**
 * Monthly check-in inside the Self Journey (never on the safety page, never by email / text / push).
 * Due once the Self-Assessment is done and `checkInDays` have passed since the last check-in or Self-Assessment.
 * Answers stay private in progress.checkIns: [{ date, hardest, wentWell, helpNext, planFits }].
 */
import React, { useEffect, useState } from "react";
import { X } from "lucide-react";

const DAY = 86400000;

const QUESTIONS = [
  ["hardest", "What has been most challenging lately?"],
  ["wentWell", "What went well?"],
  ["helpNext", "What would you like help with next?"],
];

const PLAN_FITS = [
  { id: "yes", label: "Yes" },
  { id: "somewhat", label: "Somewhat" },
  { id: "no", label: "No, things have changed" },
];

export function isCheckInDue({ checkIns = [], lastSelfAssessmentAt, checkInDays }) {
  if (!lastSelfAssessmentAt) return false;
  const last = checkIns.length ? Date.parse(checkIns[checkIns.length - 1].date) || 0 : 0;
  const base = Math.max(Date.parse(lastSelfAssessmentAt) || 0, last);
  return Date.now() - base >= checkInDays * DAY;
}

export function CheckInCard({ onStart, onLater }) {
  return (
    <section className="sj-card sj-checkin-card" data-testid="sj-checkin-card">
      <h2 className="sj-card-title">Time for your monthly check-in</h2>
      <p className="sj-small" style={{ margin: "0 0 10px" }}>
        A few quick questions about how things are going. Everything is optional, and only you see your answers.
      </p>
      <div className="sj-checkin-card-actions">
        <button type="button" className="sj-open-btn" onClick={onStart} data-testid="sj-checkin-start">Start my check-in</button>
        <button type="button" className="sj-text-btn" onClick={onLater} data-testid="sj-checkin-later">Not now</button>
      </div>
    </section>
  );
}

export function CheckInDialog({ onClose, onSave, onRetake, onUpdateSituation }) {
  const [a, setA] = useState({ hardest: "", wentWell: "", helpNext: "", planFits: null });
  const entry = () => ({ date: new Date().toISOString(), ...a });

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="sj-scrim" onClick={onClose} aria-hidden="true" />
      <div className="sj-sheet sj-checkin" role="dialog" aria-modal="true" aria-labelledby="sj-checkin-title" data-testid="sj-checkin-dialog">
        <div className="sj-sheet-head">
          <div>
            <h2 id="sj-checkin-title">Your monthly check-in</h2>
            <span className="sj-muted">Everything is optional. Only you see your answers.</span>
          </div>
          <button type="button" className="sj-icon-btn" onClick={onClose} aria-label="Close check-in" data-testid="sj-checkin-close">
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <div className="sj-sheet-body">
          {QUESTIONS.map(([key, label]) => (
            <div key={key} className="sj-field">
              <label htmlFor={`ci-${key}`}>{label}</label>
              <textarea id={`ci-${key}`} rows={2} maxLength={3000} value={a[key]} data-testid={`ci-${key}`}
                onChange={(e) => setA((x) => ({ ...x, [key]: e.target.value }))} />
            </div>
          ))}
          <fieldset className="sj-field sj-checkin-plan">
            <legend>Is your journey plan still right for you?</legend>
            <div className="sj-choice-list" role="radiogroup" aria-label="Is your journey plan still right for you?">
              {PLAN_FITS.map((p) => (
                <button key={p.id} type="button" role="radio" aria-checked={a.planFits === p.id}
                  className={`sj-choice ${a.planFits === p.id ? "is-on" : ""}`} data-testid={`ci-plan-${p.id}`}
                  onClick={() => setA((x) => ({ ...x, planFits: x.planFits === p.id ? null : p.id }))}>
                  <strong>{p.label}</strong>
                </button>
              ))}
            </div>
          </fieldset>
          {a.planFits === "no" && (
            <div className="sj-notice" data-testid="ci-changed-notice">
              <p style={{ margin: "0 0 8px" }}>Thanks for telling us. You can update where things stand today.</p>
              <button type="button" className="sj-open-btn" style={{ width: "100%" }} onClick={() => onUpdateSituation(entry())}
                data-testid="sj-checkin-update-situation">
                Update where I am
              </button>
            </div>
          )}
        </div>
        <div className="sj-checkin-actions">
          <button type="button" className="sj-outline-btn" onClick={() => onRetake(entry())} data-testid="sj-checkin-retake">
            Retake Self Assessment
          </button>
          <button type="button" className="sj-next" onClick={() => onSave(entry())} data-testid="sj-checkin-save">
            Save check-in
          </button>
        </div>
      </div>
    </>
  );
}
