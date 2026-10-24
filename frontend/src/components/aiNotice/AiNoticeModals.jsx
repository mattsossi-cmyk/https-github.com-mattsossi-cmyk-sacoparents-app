import React, { useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";

const stopEscape = (e) => e.key === "Escape" && e.stopPropagation();

// Radix modal (stacks above other Radix dialogs: takes focus, clicks and Escape). `onEscape` closes it; outside clicks do nothing.
function TrapModal({ testid, title, initialRef, onEscape, footer, children }) {
  return (
    <Dialog.Root open onOpenChange={(open) => !open && onEscape()}>
      <Dialog.Portal>
        <Dialog.Overlay className="sa-ai-modal" data-testid={`${testid}-overlay`}>
          <Dialog.Content
            className="sa-ai-modal__box"
            data-testid={testid}
            aria-describedby={undefined}
            onKeyDown={stopEscape}
            onEscapeKeyDown={(e) => e.stopPropagation()}
            onPointerDownOutside={(e) => e.preventDefault()}
            onInteractOutside={(e) => e.preventDefault()}
            onOpenAutoFocus={(e) => {
              if (!initialRef?.current) return;
              e.preventDefault();
              initialRef.current.focus();
            }}
            onCloseAutoFocus={(e) => e.preventDefault()}
          >
            <div className="sa-ai-modal__body">
              <div className="sa-ai-modal__icon" aria-hidden="true">!</div>
              <Dialog.Title asChild>
                <h2>{title}</h2>
              </Dialog.Title>
              {children}
            </div>
            {footer && <div className="sa-ai-modal__foot">{footer}</div>}
          </Dialog.Content>
        </Dialog.Overlay>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// The Journey Guide names itself; every other AI tool uses the general wording. One acknowledgment covers all.
const NOTICE_COPY = {
  journey_guide: {
    title: "Before you use the AI Journey Guide",
    intro:
      "The Journey Guide uses artificial intelligence to answer your questions. What you type is sent to our AI service provider to write a reply.",
    instead: "You don't need any personal details to get a helpful answer.",
    button: "Continue to the Journey Guide",
  },
  default: {
    title: "Before you use the AI tools",
    intro:
      "SA CoParents AI tools use artificial intelligence to help you write messages, reflect and answer questions. What you type is sent to our AI service provider to write a draft or reply.",
    instead: "You can add personal details yourself after the draft is written, right before you send it.",
    button: "Continue",
  },
};

export function AiNoticeModal({ feature, onContinue, onClose, busy, error }) {
  const copy = NOTICE_COPY[feature] || NOTICE_COPY.default;
  const agreeRef = useRef(null);
  const [agree, setAgree] = useState(false);
  const footer = (
    <>
      <label className="sa-ai-modal__check">
        <input type="checkbox" ref={agreeRef} data-testid="ai-notice-agree" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
        I understand and will not enter personal or sensitive information into the AI tool.
      </label>
      {error && (
        <p className="sa-ai-modal__error" role="alert" data-testid="ai-notice-error">
          {error}
        </p>
      )}
      <button type="button" className="sa-ai-btn" data-testid="ai-notice-continue" disabled={!agree || busy} onClick={onContinue}>
        {copy.button}
      </button>
    </>
  );
  return (
    <TrapModal testid="ai-notice-modal" title={copy.title} initialRef={agreeRef} onEscape={onClose} footer={footer}>
      <p data-testid="ai-notice-intro">{copy.intro}</p>
      <p><strong>Please do not enter:</strong></p>
      <ul>
        <li>Your child&apos;s or your own full name, birth date, or Social Security number</li>
        <li>Student ID, Medicaid, insurance, or case numbers</li>
        <li>Home address, phone number, or email</li>
        <li>Specific diagnoses, medications, or therapy and psychological details</li>
      </ul>
      <p>
        <strong>Instead,</strong> use general wording like &quot;my child,&quot; &quot;their school,&quot; or &quot;a health condition.&quot; {copy.instead}
      </p>
      <p className="sa-ai-modal__fine">
        See our{" "}
        <a href="/privacy-notice#ai" target="_blank" rel="noopener" data-testid="ai-notice-privacy-link">
          Privacy Notice
        </a>
        .
      </p>
    </TrapModal>
  );
}

export function AiConfirmModal({ labels, onEdit, onSendAnyway }) {
  const editRef = useRef(null);
  return (
    <TrapModal testid="ai-confirm-modal" title="Your message may contain personal information" initialRef={editRef} onEscape={onEdit}>
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
