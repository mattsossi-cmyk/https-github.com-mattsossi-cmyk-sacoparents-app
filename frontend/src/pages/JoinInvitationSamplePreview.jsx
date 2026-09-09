/**
 * `/join/sample-preview` — public, no-auth preview of the invited
 * parent experience. Renders the same layout as JoinInvitation.jsx
 * with a stub professional and first-name so a professional-lead
 * visitor can see exactly what an invited parent sees BEFORE we
 * ever mint a real invitation.
 *
 * Not linked from anywhere except the collapsed Path B card on
 * Landing. No backend endpoint — the "preview" data is a hard-coded
 * stub. A dismissible banner at the top makes clear this is fake.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight, Info, Sparkles, ShieldCheck, X,
} from "lucide-react";

import AppShell from "../components/AppShell";

const STUB = {
  case_id: "SA-SAMPLE1",
  assessment_type: "co-parenting",
  professional_name: "Adele van Wyk (sample)",
  invited_first_name: "Alex",
  token_expires_at: null,
};

export default function JoinInvitationSamplePreview() {
  const [bannerDismissed, setBannerDismissed] = useState(false);

  return (
    <AppShell>
      <div
        className="max-w-2xl mx-auto px-4 sm:px-6 py-10"
        data-testid="join-sample-preview"
      >
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="join-sample-back"
        >
          ← Back to Landing
        </Link>

        {!bannerDismissed && (
          <div
            className="mb-6 rounded-2xl border border-[#F0D9A1] bg-[#FFF6E5] px-4 py-3 flex items-start gap-2.5"
            role="note"
            data-testid="join-sample-banner"
          >
            <Info size={16} className="text-[#8A5B00] flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-[#5C3D00]">
                You&rsquo;re viewing a sample preview
              </div>
              <p className="text-[12px] text-[#7A5300] mt-0.5 leading-relaxed">
                This case is fictional. No real invitation exists. Use
                this to see what an invited parent will see when they
                open the email link from a professional.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setBannerDismissed(true)}
              aria-label="Dismiss sample banner"
              className="text-[#8A5B00] hover:text-[#5C3D00] p-1 flex-shrink-0"
              data-testid="join-sample-banner-dismiss"
            >
              <X size={14} />
            </button>
          </div>
        )}

        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
          <ShieldCheck size={12} /> Invitation preview
        </div>
        <p
          className="text-[#3D1A78] font-serif text-lg sm:text-xl mt-2 mb-1"
          data-testid="join-sample-personal-hello"
        >
          Hi, {STUB.invited_first_name},
        </p>
        <h1
          className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-2"
          data-testid="join-sample-title"
        >
          You&rsquo;ve been invited to a Joint Alignment Report.
        </h1>
        <p
          className="text-[#4B4567] mt-3 leading-relaxed"
          data-testid="join-sample-body"
        >
          <strong>{STUB.professional_name}</strong> has invited you to
          complete a private SA CoParents reflection to help prepare for
          a child-focused conversation. Your responses are completed
          independently. Your individual responses are not automatically
          shared with the other parent.
        </p>

        <div className="mt-6 rounded-2xl border border-[#D6CFE8] bg-[#F5F1FB] p-4 text-[12.5px] text-[#3D1A78] leading-relaxed">
          <div className="font-semibold mb-1">What your professional receives</div>
          Only the completed Joint Alignment Report — never your raw
          answers, journal entries, or AI-coach conversations. You
          record a separate consent when you&rsquo;re ready to release.
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            disabled
            className="inline-flex items-center gap-2 rounded-full bg-[#C9C0DC] text-white px-5 py-2.5 text-sm font-semibold cursor-not-allowed"
            data-testid="join-sample-begin-disabled"
            title="Sample preview — no real invitation to accept"
          >
            <Sparkles size={16} />
            Begin my reflection
            <ArrowRight size={14} />
          </button>
        </div>
        <p className="text-[11px] text-[#857E9C] mt-2">
          Buttons are disabled on this sample. Ask your professional to
          send a real invitation email to see the working version.
        </p>
      </div>
    </AppShell>
  );
}
