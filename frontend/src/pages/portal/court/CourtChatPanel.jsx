import React, { useEffect, useRef, useState } from "react";

import { CourtDialog } from "./CourtDialog";
import { AI_GRADIENT } from "./CourtHeader";

const GREETING =
  "Hello! I am your Emergent AI Assistant. I can help with neutral language drafting, your court-ordered steps, or creating your Foundation Statement. I share general guidance, not legal advice.";
const PROMPTS = [
  ["fa-pen-nib", "Foundation Statement", "Draft a child-focused Foundation Statement."],
  ["fa-comments", "Neutral Reframing", "Help me reframe my communication concerns neutrally."],
  ["fa-list-check", "What's next?", "What should I do next on my court path?"],
];

function Msg({ m }) {
  const mine = m.role === "user";
  return (
    <p
      data-testid={mine ? "court-chat-msg-user" : "court-chat-msg-guide"}
      className={`max-w-[82%] px-4 py-3 rounded-[14px] text-[0.92rem] leading-relaxed whitespace-pre-wrap break-words ${
        mine ? "self-end bg-[#3b1566] text-white" : "self-start bg-[#f2ebfc] text-[#3b1566] border border-[#e7dbf8]"
      }`}
    >
      {m.text}
    </p>
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
export function CourtChatPanel({ chat, open, onOpenChange, draft }) {
  const [text, setText] = useState("");
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
        <div className="flex flex-col h-[80vh] max-h-[700px]">
          <ChatHeader chat={chat} onClose={() => onOpenChange(false)} />
          <div ref={listRef} data-testid="court-chat-messages" className="pp-scroll flex-1 overflow-y-auto p-5 flex flex-col gap-[15px] bg-[#faf8fd]">
            <p data-testid="court-chat-greeting" className="max-w-[82%] self-start px-4 py-3 rounded-[14px] text-[0.92rem] bg-[#f2ebfc] text-[#3b1566] border border-[#e7dbf8]">
              {GREETING}
            </p>
            {chat.messages.map((m, i) => (
              <Msg key={i} m={m} />
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
