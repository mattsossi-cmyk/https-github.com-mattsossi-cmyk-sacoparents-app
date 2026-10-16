import React from "react";

// The exact Privacy Notice text. Changing anything here requires bumping
// PRIVACY_NOTICE_VERSION and PRIVACY_NOTICE_TEXT_SHA256 in backend/privacy_consent.py.
export function PrivacyNoticeContent() {
  return (
    <div data-testid="privacy-notice-content" className="space-y-10">
      <section id="promise" data-testid="privacy-notice-promise" className="scroll-mt-6">
        <p data-testid="privacy-notice-pending" className="rounded-xl border border-dashed border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          Preview placeholder: the Privacy Notice text has not been added yet.
        </p>
      </section>
      <section id="collect" data-testid="privacy-notice-collect" className="scroll-mt-6" />
      <section id="ai" data-testid="privacy-notice-ai" className="scroll-mt-6" />
      <section id="contact" data-testid="privacy-notice-contact" className="scroll-mt-6" />
    </div>
  );
}
