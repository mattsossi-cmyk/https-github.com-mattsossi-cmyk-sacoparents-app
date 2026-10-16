import React, { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

// Overlay + box from the file, with a keyboard focus trap. `onEscape` closes it.
function TrapModal({ testid, labelledBy, initialRef, onEscape, children }) {
  const boxRef = useRef(null);
  useEffect(() => {
    (initialRef?.current || boxRef.current?.querySelector(FOCUSABLE))?.focus();
  }, [initialRef]);
  const onKeyDown = (e) => {
    if (e.key === "Escape") {
      e.stopPropagation();
      onEscape();
      return;
    }
    if (e.key !== "Tab") return;
    const els = [...boxRef.current.querySelectorAll(FOCUSABLE)];
    if (!els.length) return;
    const first = els[0];
    const last = els[els.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };
  return createPortal(
    <div className="sa-ai-modal" data-testid={testid} role="dialog" aria-modal="true" aria-labelledby={labelledBy} onKeyDown={onKeyDown}>
      <div className="sa-ai-modal__box" ref={boxRef}>
        {children}
      </div>
    </div>,
    document.body
  );
}

export function AiNoticeModal({ onContinue, onClose, busy }) {
  const titleId = useId();
  const agreeRef = useRef(null);
  const [agree, setAgree] = useState(false);
  return (
    <TrapModal testid="ai-notice-modal" labelledBy={titleId} initialRef={agreeRef} onEscape={onClose}>
      <div className="sa-ai-modal__icon" aria-hidden="true">!</div>
      <h2 id={titleId}>Before you use the AI Communication Builder</h2>
      <p>This tool uses artificial intelligence to help you write messages. What you type is sent to our AI service provider to generate a draft.</p>
      <p><strong>Please do not enter:</strong></p>
      <ul>
        <li>Your child&apos;s or your own full name, birth date, or Social Security number</li>
        <li>Student ID, Medicaid, insurance, or case numbers</li>
        <li>Home address, phone number, or email</li>
        <li>Specific diagnoses, medications, or therapy and psychological details</li>
      </ul>
      <p>
        <strong>Instead,</strong> use general wording like &quot;my child,&quot; &quot;their school,&quot; or &quot;a health condition.&quot; You can add
        personal details yourself after the draft is written, right before you send it.
      </p>
      <p className="sa-ai-modal__fine">
        See our{" "}
        <a href="/privacy-notice#ai" target="_blank" rel="noopener" data-testid="ai-notice-privacy-link">
          Privacy Notice
        </a>
        .
      </p>
      <label className="sa-ai-modal__check">
        <input type="checkbox" ref={agreeRef} data-testid="ai-notice-agree" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
        I understand and will not enter personal or sensitive information into the AI tool.
      </label>
      <button type="button" className="sa-ai-btn" data-testid="ai-notice-continue" disabled={!agree || busy} onClick={onContinue}>
        Continue to AI Communication Builder
      </button>
    </TrapModal>
  );
}

export function AiConfirmModal({ labels, onEdit, onSendAnyway }) {
  const titleId = useId();
  const editRef = useRef(null);
  return (
    <TrapModal testid="ai-confirm-modal" labelledBy={titleId} initialRef={editRef} onEscape={onEdit}>
      <div className="sa-ai-modal__icon" aria-hidden="true">!</div>
      <h2 id={titleId}>Your message may contain personal information</h2>
      <p>We found:</p>
      <ul data-testid="ai-confirm-list">
        {labels.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
      <p>We recommend removing these details before sending your text to the AI.</p>
      <div className="sa-ai-modal__actions">
        <button type="button" className="sa-ai-btn" ref={editRef} data-testid="ai-confirm-edit" onClick={onEdit}>
          Go back and edit
        </button>
        <button type="button" className="sa-ai-btn sa-ai-btn--ghost" data-testid="ai-confirm-send-anyway" onClick={onSendAnyway}>
          Send anyway
        </button>
      </div>
    </TrapModal>
  );
}
