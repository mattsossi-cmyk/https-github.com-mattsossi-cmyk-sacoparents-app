import React from "react";

const H2 = "font-serif text-2xl sm:text-3xl text-[#1A1330] mb-3";

// The exact Privacy Notice text. Changing anything here requires bumping
// PRIVACY_NOTICE_VERSION and PRIVACY_NOTICE_TEXT_SHA256 in backend/privacy_consent.py.
export function PrivacyNoticeContent() {
  return (
    <div data-testid="privacy-notice-content" className="space-y-10">
      <section id="promise" data-testid="privacy-notice-promise" className="scroll-mt-6">
        <h2 className={H2}>1. Our promise</h2>
        <p>
          We treat information about your family as confidential. We never sell your information or your child&apos;s information. We use it only to run
          the app and the services you ask for. We share it only as described in this notice or with your permission.
        </p>
      </section>

      <section id="collect" data-testid="privacy-notice-collect" className="scroll-mt-6 space-y-4">
        <h2 className={H2}>2. Information we collect</h2>
        <p>
          <strong>About you (parent or guardian):</strong> name, email, phone, username, password (stored encrypted), home city or ZIP, your relationship
          to each child, and messages you send.
        </p>
        <div>
          <p>
            <strong>About your child, as you choose to enter it:</strong>
          </p>
          <ul className="list-disc pl-6 mt-2 space-y-2">
            <li>
              <strong>Educational:</strong> school, grade, report cards, IEP or 504 plans, ARD meeting notes, teacher communications, attendance and
              discipline records.
            </li>
            <li>
              <strong>Medical:</strong> diagnoses, medications, allergies, doctor and therapy notes, immunization records.
            </li>
            <li>
              <strong>Psychological and behavioral:</strong> evaluations, counseling or therapy information, behavior plans, developmental assessments.
            </li>
          </ul>
        </div>
        <p>
          <strong>Technical data:</strong> device type, browser, IP address, log-in times and app usage, collected to keep the app secure and working. We
          do not use analytics or advertising trackers.
        </p>
        <p>We call the medical, psychological and special-education information above Sensitive Family Information.</p>
        <div data-testid="privacy-notice-who-can-see" className="space-y-2">
          <p>
            <strong>Who can see your information.</strong> Your co-parent never sees your answers. Nothing you write in the safety check-in is ever shown
            to them.
          </p>
          <p>The professionals assigned to your case can see:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Your individual answers, including anything you write in your own words</li>
            <li>Which questions you skipped (they see that you skipped, not why)</li>
            <li>The safe ways to contact you, if you choose to share them</li>
            <li>A concern level based on your answers, which helps your professional decide what support to offer</li>
            <li>Whether you have started, finished, or declined this step</li>
          </ul>
          <p>A small number of SA CoParents administrators can also open your answers, only to check that the service is working safely.</p>
          <p>
            Your answers are kept on a protected screen. Each time anyone opens it, that is recorded, and you can see who looked and when under &ldquo;Who
            has looked at my information.&rdquo;
          </p>
          <p>
            Court documents and reports show only whether this step was completed, not started, or declined. They never show your answers, what you
            wrote, or your concern level.
          </p>
          <p>
            If your answers suggest a child has been abused or neglected, the professional who reads them must report it. Texas law requires anyone who
            suspects child abuse or neglect to report it.
          </p>
          <p>
            Every question can be skipped, and you can stop at any time. If you skip a question about immediate danger, physical or sexual harm, or harm
            to your children, your professional will be asked to check in with you.
          </p>
        </div>
      </section>

      <section id="ai" data-testid="privacy-notice-ai" className="scroll-mt-6 space-y-4">
        <h2 className={H2}>7. AI Communication Builder</h2>
        <p>
          The AI Communication Builder helps you draft messages, for example to your child&apos;s school. When you use it, the text you type is sent to
          our AI service providers, OpenAI and Anthropic (Claude), to generate a draft.
        </p>
        <p>A warning appears above every AI input.</p>
        <p>
          Please do not enter personal or sensitive information, such as names, birth dates, Social Security or ID numbers, contact details, or medical or
          psychological details. Use general wording and add specifics after the draft is written.
        </p>
        <p>AI drafts can contain mistakes. Review every draft before you send it.</p>
      </section>

      <section id="contact" data-testid="privacy-notice-contact" className="scroll-mt-6 space-y-4">
        <h2 className={H2}>12. Questions or complaints</h2>
        <p>
          Contact our Privacy Officer, Matt Sossi, at{" "}
          <a href="mailto:mattsossi@bsossi.com" data-testid="privacy-notice-email" className="text-[#3D1A78] font-semibold underline underline-offset-2">
            mattsossi@bsossi.com
          </a>
          . You may also file a complaint with the Texas Attorney General&apos;s Consumer Protection Division. We will never retaliate against you for
          making a complaint.
        </p>
      </section>
    </div>
  );
}
