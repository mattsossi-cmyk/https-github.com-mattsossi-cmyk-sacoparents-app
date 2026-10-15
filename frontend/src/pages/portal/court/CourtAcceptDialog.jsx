import React from "react";

import { CaseVisibilityNotice } from "../../../components/privacy/CaseVisibilityNotice";
import { CourtDialog } from "./CourtDialog";

const input =
  "w-full px-3 py-[11px] border border-[#ccc] rounded-lg text-[0.92rem] focus:outline-none focus:ring-2 focus:ring-[#7b2cbf] focus:border-transparent";

function Field({ id, label, ...props }) {
  return (
    <div className="mb-3.5">
      <label htmlFor={id} className="block text-[0.85rem] font-semibold mb-1.5 text-[#202124]">
        {label}
      </label>
      <input id={id} data-testid={id} type="text" autoComplete="off" className={input} {...props} />
    </div>
  );
}

export function CourtAcceptDialog({ open, onClose, cc, mediator, courtKey, onConfirm }) {
  const tone = cc.status?.tone === "error" ? "text-rose-600" : "text-emerald-700";
  return (
    <CourtDialog
      open={open}
      onClose={onClose}
      testid="court-accept-dialog"
      title="Accept Your Court-Ordered Invite"
      desc="Provide your court case details to open your secure individual workspace. Use the code from your court order, mediator, or attorney."
    >
      {cc.verified && (
        <p data-testid="court-accept-verified" className="mb-4 text-xs font-bold text-emerald-800 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">
          <i className="fa-solid fa-circle-check mr-1.5"></i>
          Case {courtKey} verified{mediator ? ` · Professional: ${mediator}` : ""}
        </p>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onConfirm();
        }}
      >
        <Field id="court-code-input" label="Court Reference Number" placeholder="e.g., SA-2026-CV-8821" maxLength={80} value={cc.code} onChange={(e) => cc.setCode(e.target.value)} />
        <Field id="court-legal-name-input" label="Your Full Legal Name" placeholder="Enter your full name" maxLength={120} value={cc.name} onChange={(e) => cc.setName(e.target.value)} />
        {cc.status && (
          <p data-testid="court-code-status" role="status" className={`-mt-1 mb-3 text-xs font-semibold ${tone}`}>
            {cc.status.text}
          </p>
        )}
        <CaseVisibilityNotice testid="court-accept-visibility" className="mb-3.5" />
        <button
          type="submit"
          data-testid="court-accept-confirm"
          disabled={!!cc.busy}
          className="w-full bg-[#2fa144] hover:bg-[#268537] disabled:opacity-70 text-white font-bold text-base py-3 px-5 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          {cc.busy === "accept" && <i className="fa-solid fa-spinner fa-spin"></i>}
          {cc.verified ? "Save & Continue" : "Confirm & Proceed to Workspace"}
        </button>
      </form>
    </CourtDialog>
  );
}
