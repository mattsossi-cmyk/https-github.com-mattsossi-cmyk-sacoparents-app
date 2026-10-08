import React, { useEffect, useState } from "react";

import { api } from "../../../lib/api";
import CONTENT from "../foundationBuilderContent.json";

const LABELS = Object.fromEntries(CONTENT.fields.map((f) => [f.key, f.label]));
const TITLES = { statement: "Send to Step 4", split: "Split into Step 4 boxes" };

function Preview({ parts }) {
  return (
    <ul data-testid="court-draft-preview" className="space-y-2.5">
      {parts.map(([key, text]) => (
        <li key={key} data-testid={`court-draft-part-${key}`} className="border border-[#e7dbf8] rounded-xl p-3">
          <p className="text-[11px] font-extrabold uppercase tracking-wider text-[#5c2c8e] mb-1">{LABELS[key]}</p>
          <p className="text-sm text-[#202124] whitespace-pre-wrap break-words">{text}</p>
        </li>
      ))}
    </ul>
  );
}

function Saved({ onOpenStep4, onClose }) {
  return (
    <div data-testid="court-draft-saved" className="text-center py-6">
      <i className="fa-solid fa-circle-check text-4xl text-[#2fa144]"></i>
      <p className="mt-3 text-base font-bold text-[#3b1566]">Saved to Step 4</p>
      <p className="text-sm text-[#5f6368] mb-5">Your Foundation Statement is updated. You can edit it anytime.</p>
      <div className="flex flex-col sm:flex-row gap-2 justify-center">
        <button type="button" data-testid="court-draft-open-step4" onClick={onOpenStep4} className="bg-[#2fa144] hover:bg-[#268537] text-white font-bold text-sm px-5 py-2.5 rounded-lg transition-colors">
          Open Step 4 <i className="fa-solid fa-arrow-right ml-1.5"></i>
        </button>
        <button type="button" data-testid="court-draft-back" onClick={onClose} className="bg-[#f2ebfc] hover:bg-[#e7dbf8] text-[#3b1566] font-bold text-sm px-5 py-2.5 rounded-lg transition-colors">
          Back to chat
        </button>
      </div>
    </div>
  );
}

// Overlay inside the chat: preview where an AI draft goes in Step 4, then Replace / Add below.
export function CourtDraftPanel({ draft, fb, onClose, onOpenStep4 }) {
  const [parts, setParts] = useState(draft.mode === "statement" ? { statement: draft.text } : null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    if (draft.mode !== "split") return;
    api
      .post("/court-path/ai/foundation-split", { text: draft.text.slice(0, 3000) })
      .then(({ data }) => setParts(data))
      .catch((e) => {
        const d = e?.response?.data?.detail;
        setError(typeof d === "string" ? d : "We couldn't sort that draft right now. Please try again.");
      });
  }, [draft]);

  const filled = parts ? Object.entries(parts).filter(([, v]) => (v || "").trim()) : [];
  const hasExisting = filled.some(([k]) => (fb.fields[k] || "").trim());
  const apply = (how) => {
    filled.forEach(([k, v]) => {
      const old = (fb.fields[k] || "").trim();
      fb.update(k, (how === "add" && old ? `${old}\n\n${v.trim()}` : v.trim()).slice(0, 3000));
    });
    setSaved(true);
  };
  const btn = "flex-1 font-bold text-sm py-2.5 px-4 rounded-lg transition-colors";

  return (
    <div data-testid="court-draft-panel" className="absolute inset-0 z-10 bg-white flex flex-col">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#eee]">
        <p className="font-bold text-[#3b1566]">{TITLES[draft.mode]}</p>
        <button type="button" data-testid="court-draft-close" aria-label="Close" onClick={onClose} className="w-8 h-8 rounded-full text-[#888] hover:bg-[#f2ebfc] hover:text-[#3b1566]">
          <i className="fa-solid fa-xmark"></i>
        </button>
      </div>
      <div className="pp-scroll flex-1 overflow-y-auto p-5">
        {saved ? (
          <Saved onOpenStep4={onOpenStep4} onClose={onClose} />
        ) : error ? (
          <p data-testid="court-draft-error" className="text-sm text-rose-700">{error}</p>
        ) : !parts ? (
          <p data-testid="court-draft-loading" className="text-sm text-[#5f6368]"><i className="fa-solid fa-spinner fa-spin mr-2"></i>Sorting your draft into the Step 4 boxes…</p>
        ) : (
          <>
            <p className="text-xs text-[#5f6368] mb-3">
              {hasExisting ? "Some of these boxes already have text. Replace it, or add this below what's there." : "This will be added to your Foundation Statement (Step 4)."}
            </p>
            <Preview parts={filled} />
          </>
        )}
      </div>
      {!saved && parts && filled.length > 0 && (
        <div className="p-4 border-t border-[#eee] flex flex-col sm:flex-row gap-2">
          {hasExisting ? (
            <>
              <button type="button" data-testid="court-draft-replace" onClick={() => apply("replace")} className={`${btn} bg-[#f2ebfc] hover:bg-[#e7dbf8] text-[#3b1566]`}>
                Replace
              </button>
              <button type="button" data-testid="court-draft-add-below" onClick={() => apply("add")} className={`${btn} bg-[#2fa144] hover:bg-[#268537] text-white`}>
                Add below
              </button>
            </>
          ) : (
            <button type="button" data-testid="court-draft-add" onClick={() => apply("add")} className={`${btn} bg-[#2fa144] hover:bg-[#268537] text-white`}>
              Add to Step 4
            </button>
          )}
        </div>
      )}
    </div>
  );
}
