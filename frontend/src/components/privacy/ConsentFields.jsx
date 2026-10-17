import React from "react";
import { Link } from "react-router-dom";

export const emptyConsent = { ack_privacy_notice: false, consent_sensitive_info: false };
export const consentReady = (c) => c.ack_privacy_notice === true && c.consent_sensitive_info === true;

function Box({ testid, checked, onChange, children }) {
  return (
    <label className="flex items-start gap-3 cursor-pointer select-none">
      <input
        type="checkbox"
        data-testid={testid}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 w-5 h-5 shrink-0 accent-[#3D1A78] cursor-pointer"
      />
      <span className="text-sm text-[#1A1330] leading-relaxed">{children}</span>
    </label>
  );
}

// The two required consent boxes, with the first-visit pop-up's two lines above them. Unchecked by default.
export function ConsentFields({ tp, value, onChange }) {
  const set = (key) => (v) => onChange({ ...value, [key]: v });
  return (
    <div data-testid={`${tp}-consent`} className="space-y-3 rounded-2xl border border-[#E5E0EE] bg-[#F8F7FC] p-4">
      <p className="text-[0.8125rem] text-[#1A1330] leading-relaxed">
        SA CoParents provides educational conflict-management and mediation-preparation tools. It does not provide legal advice, therapy, or create an
        attorney-client relationship.
      </p>
      <p className="text-[0.75rem] text-[#4B4567] leading-relaxed">
        Full details are in our{" "}
        <Link to="/terms" target="_blank" rel="noopener noreferrer" data-testid={`${tp}-consent-terms-link`} className="text-[#3D1A78] underline">
          Terms of Use
        </Link>
        .
      </p>
      <Box testid={`${tp}-consent-ack`} checked={value.ack_privacy_notice} onChange={set("ack_privacy_notice")}>
        I have read and understand the{" "}
        <Link
          to="/privacy-notice"
          target="_blank"
          rel="noopener noreferrer"
          data-testid={`${tp}-consent-privacy-link`}
          className="text-[#3D1A78] font-semibold underline"
          onClick={(e) => e.stopPropagation()}
        >
          Privacy Notice
        </Link>
        .
      </Box>
      <Box testid={`${tp}-consent-sensitive`} checked={value.consent_sensitive_info} onChange={set("consent_sensitive_info")}>
        I consent to SA CoParents storing the sensitive family information I choose to enter, such as medical, psychological and special-education
        information about my child, as described in the Privacy Notice.
      </Box>
    </div>
  );
}
