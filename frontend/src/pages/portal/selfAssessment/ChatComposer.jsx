import React, { useEffect, useState } from "react";

const backBtn =
  "text-[0.6875rem] font-semibold text-slate-500 hover:text-purple-800 transition-colors disabled:opacity-40";

export function BackLink({ onBack }) {
  if (!onBack) return null;
  return (
    <button type="button" data-testid="sa-back-question" onClick={onBack} className={backBtn}>
      <i className="fa-solid fa-rotate-left mr-1"></i>Change my last answer
    </button>
  );
}

export function TextReply({ testidPrefix, initial = "", placeholder, sendLabel, skipLabel, onSend, onSkip, onBack, busy }) {
  const [text, setText] = useState(initial);
  useEffect(() => setText(initial), [initial]);
  return (
    <div className="space-y-2">
      <textarea
        data-testid={`${testidPrefix}-input`}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={placeholder}
        rows={3}
        maxLength={2000}
        className="w-full px-3 py-2 border border-purple-200 rounded-xl text-sm text-slate-900 focus:outline-none focus:border-purple-600 focus:ring-2 focus:ring-purple-100 resize-none"
      />
      <div className="flex items-center gap-2 flex-wrap">
        <BackLink onBack={onBack} />
        <button
          type="button"
          data-testid={`${testidPrefix}-skip`}
          onClick={onSkip}
          disabled={busy}
          className="ml-auto px-3 py-2 rounded-full text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors disabled:opacity-50"
        >
          {skipLabel}
        </button>
        <button
          type="button"
          data-testid={`${testidPrefix}-send`}
          onClick={() => onSend(text.trim())}
          disabled={busy || !text.trim()}
          className="px-4 py-2 rounded-full bg-[#4c2889] hover:bg-[#371a68] text-white text-xs font-bold transition-colors disabled:opacity-50"
        >
          {busy ? <i className="fa-solid fa-spinner fa-spin"></i> : sendLabel}
        </button>
      </div>
    </div>
  );
}
