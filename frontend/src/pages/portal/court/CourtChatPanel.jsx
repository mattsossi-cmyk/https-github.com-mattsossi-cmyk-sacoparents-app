import React, { useEffect, useRef, useState } from "react";

import { CourtDialog } from "./CourtDialog";
import { CourtDraftPanel } from "./CourtDraftPanel";
import { AI_GRADIENT } from "./CourtHeader";

const GREETING =
  "Hello! I am your Emergent AI Assistant. I can help with neutral language drafting, your court-ordered steps, or creating your Foundation Statement. I share general guidance, not legal advice.";
const PROMPTS = [
  ["fa-pen-nib", "Foundation Statement", "Draft a child-focused Foundation Statement."],
  ["fa-comments", "Neutral Reframing", "Help me reframe my communication concerns neutrally."],
  ["fa-list-check", "What's next?", "What should I do next on my court path?"],
];

const DRAFT_MIN_WORDS = 40;
const draftBtn = "text-[11px] font-bold px-2.5 py-1 rounded-full bg-white border border-[#e7dbf8] hover:border-[#7b2cbf] text-[#3b1566] transition-colors";

function Msg({ m, i, onDraft }) {
  const mine = m.role === "user";
  const long = !mine && m.text.split(/\s+/).length >= DRAFT_MIN_WORDS;
  return (
    <div className={`max-w-[82%] ${mine ? "self-end" : "self-start"}`}>
      <p
        data-testid={mine ? "court-chat-msg-user" : "court-chat-msg-guide"}
        className={`px-4 py-3 rounded-[14px] text-[0.92rem] leading-relaxed whitespace-pre-wrap break-words ${
          mine ? "bg-[#3b1566] text-white" : "bg-[#f2ebfc] text-[#3b1566] border border-[#e7dbf8]"
        }`}
      >
        {m.text}
      </p>
      {long && (
        <div className="flex flex-wrap gap-1.5 mt-1.5">
          <button type="button" data-testid={`court-chat-send-step4-${i}`} onClick={() => onDraft({ text: m.text, mode: "statement" })} className={draftBtn}>
            <i className="fa-solid fa-file-import mr-1"></i>Send to Step 4
          </button>
          <button type="button" data-testid={`court-chat-split-step4-${i}`} onClick={() => onDraft({ text: m.text, mode: "split" })} className={draftBtn}>
            <i className="fa-solid fa-table-cells-large mr-1"></i>Split into Step 4 boxes
          </button>
        </div>
      )}
    </div>
  );
}

function ChatHeader({ chat, onClose }) {
  return (
    <div className="text-white px-5 sm:px-6 py-4 flex justify-between items-center gap-2" style={{ background: AI_GRADIENT }}>
      <div className="font-bold flex items-center gap-2">
        <i className="fa-solid fa-robot"></i> Emergent Co-Parenting AI
      </div>
      <div className="flex items-center gap-1.5">
        {chat.messages.length > 0 && (
          <button type="button" data-testid="court-chat-new" onClick={chat.reset} className="text-[11px] font-bold px-3 py-1.5 rounded-full bg-white/15 hover:bg-white/25 transition-colors">
            <i className="fa-solid fa-plus mr-1"></i>Start new chat
          </button>
        )}
        <button type="button" data-testid="court-chat-close" aria-label="Close chat" onClick={onClose} className="w-8 h-8 rounded-full hover:bg-white/15 transition-colors">
          <i className="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>
    </div>
  );
}

// Floating Emergent AI button + remembered multi-turn chat (saved to the parent's account).
export function CourtChatPanel({ chat, open, onOpenChange, draft, fb, onOpenStep4 }) {
  const [text, setText] = useState("");
  const [toStep4, setToStep4] = useState(null);
  const listRef = useRef(null);
  useEffect(() => {
    if (open && draft) setText(draft);
  }, [open, draft]);
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [chat.messages.length, chat.busy, open]);

  const submit = async (value) => {
    const t = (value ?? text).trim();
    if (!t || chat.busy) return;
    setText("");
    if (!(await chat.send(t))) setText(t);
  };

  return (
    <>
      <button
        type="button"
        data-testid="court-ai-fab"
        onClick={() => onOpenChange(true)}
        className="court-fab fixed bottom-5 right-4 sm:bottom-[25px] sm:right-[25px] z-[55] text-white px-5 sm:px-[22px] py-3.5 rounded-full font-bold text-[0.95rem] flex items-center gap-2.5 shadow-[0_8px_24px_rgba(123,44,191,0.4)]"
        style={{ background: AI_GRADIENT }}
      >
        <i className="fa-solid fa-wand-magic-sparkles"></i> Emergent AI Assistant
      </button>
      <CourtDialog open={open} onClose={() => onOpenChange(false)} testid="court-chat" title="Emergent Co-Parenting AI" desc="Your saved chat with Emergent AI" wide bare>
        <div className="relative flex flex-col h-[80vh] max-h-[700px]">
          {toStep4 && (
            <CourtDraftPanel
              key={toStep4.text + toStep4.mode}
              draft={toStep4}
              fb={fb}
              onClose={() => setToStep4(null)}
              onOpenStep4={() => {
                setToStep4(null);
                onOpenChange(false);
                onOpenStep4();
              }}
            />
          )}
          <ChatHeader chat={chat} onClose={() => onOpenChange(false)} />
          <div ref={listRef} data-testid="court-chat-messages" className="pp-scroll flex-1 overflow-y-auto p-5 flex flex-col gap-[15px] bg-[#faf8fd]">
            <p data-testid="court-chat-greeting" className="max-w-[82%] self-start px-4 py-3 rounded-[14px] text-[0.92rem] bg-[#f2ebfc] text-[#3b1566] border border-[#e7dbf8]">
              {GREETING}
            </p>
            {chat.messages.map((m, i) => (
              <Msg key={i} m={m} i={i} onDraft={setToStep4} />
            ))}
            {chat.busy && (
              <p data-testid="court-chat-typing" className="self-start px-4 py-3 rounded-[14px] text-[0.92rem] bg-[#f2ebfc] text-[#3b1566] border border-[#e7dbf8]">
                <i className="fa-solid fa-spinner fa-spin mr-2"></i>Emergent AI is thinking...
              </p>
            )}
          </div>
          {chat.error && <p data-testid="court-chat-error" className="px-5 pt-2 text-xs text-rose-700 bg-white">{chat.error}</p>}
          <div className="px-[18px] py-2.5 bg-white border-t border-[#eee] flex gap-2 overflow-x-auto whitespace-nowrap">
            {PROMPTS.map(([icon, label, prompt], i) => (
              <button
                key={label}
                type="button"
                data-testid={`court-chat-prompt-${i}`}
                disabled={chat.busy}
                onClick={() => submit(prompt)}
                className="shrink-0 bg-[#f2ebfc] hover:bg-[#e7dbf8] disabled:opacity-60 text-[#3b1566] border border-[#e7dbf8] px-3.5 py-1.5 rounded-2xl text-[0.8rem] font-semibold transition-colors"
              >
                <i className={`fa-solid ${icon} mr-1.5`}></i>
                {label}
              </button>
            ))}
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
            className="p-[15px] bg-white border-t border-[#eee] flex gap-2.5"
          >
            <input
              data-testid="court-chat-input"
              value={text}
              maxLength={1000}
              onChange={(e) => setText(e.target.value)}
              placeholder="Ask Emergent AI for assistance..."
              aria-label="Message Emergent AI"
              className="flex-1 min-w-0 px-4 py-3 border border-[#ccc] rounded-full text-[0.95rem] focus:outline-none focus:ring-2 focus:ring-[#7b2cbf] focus:border-transparent"
            />
            <button
              type="submit"
              data-testid="court-chat-send"
              disabled={chat.busy || !text.trim()}
              aria-label="Send"
              className="shrink-0 w-11 h-11 rounded-full bg-[#7b2cbf] hover:bg-[#5c2c8e] disabled:opacity-50 text-white transition-colors"
            >
              <i className="fa-solid fa-paper-plane"></i>
            </button>
          </form>
          <p className="px-5 pb-3 bg-white text-[10px] text-slate-400">Saved to your account · General guidance, not legal advice · In danger? Call 911.</p>
        </div>
      </CourtDialog>
    </>
  );
}
