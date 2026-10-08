import React, { useEffect, useRef, useState } from "react";

const SUGGESTIONS = ["What is parallel parenting?", "How do I keep exchanges calm?", "What if the other parent ignores the plan?"];

function Bubble({ m }) {
  const mine = m.role === "user";
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <p
        data-testid={mine ? "pp-chat-msg-user" : "pp-chat-msg-guide"}
        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words ${
          mine ? "bg-[#4a2574] text-white rounded-br-md" : "bg-white border border-purple-100 text-slate-800 rounded-bl-md shadow-sm"
        }`}
      >
        {m.text}
      </p>
    </div>
  );
}

export function PpChat({ chat }) {
  const [text, setText] = useState("");
  const listRef = useRef(null);
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [chat.messages.length, chat.busy]);

  const submit = async (value) => {
    const t = (value ?? text).trim();
    if (!t || chat.busy) return;
    setText("");
    if (!(await chat.send(t))) setText(t);
  };

  return (
    <section data-testid="pp-chat" className="bg-white rounded-2xl border border-purple-100 shadow-lg flex flex-col overflow-hidden">
      <header className="px-4 py-3 bg-[#2d1548] text-white flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center">
            <i className="fa-solid fa-comments"></i>
          </span>
          <div>
            <h4 className="text-sm font-bold leading-tight">Parallel Parenting Guide</h4>
            <p className="text-[10px] text-purple-200">Powered by Emergent AI · private to you</p>
          </div>
        </div>
        {chat.messages.length > 0 && (
          <button type="button" data-testid="pp-chat-new" onClick={chat.reset} className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-white/15 hover:bg-white/25 transition-colors">
            New chat
          </button>
        )}
      </header>
      <div ref={listRef} data-testid="pp-chat-messages" className="pp-scroll flex-1 overflow-y-auto p-4 space-y-3 min-h-[220px] max-h-[380px] bg-[#f8f6fc]">
        {chat.messages.length === 0 && (
          <div data-testid="pp-chat-empty" className="space-y-3">
            <p className="text-sm text-slate-700 bg-white border border-purple-100 rounded-2xl rounded-bl-md px-3.5 py-2.5 shadow-sm">
              Hi, I'm your Guide. Ask me anything about parallel parenting or the choices on this page.
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={s}
                  type="button"
                  data-testid={`pp-chat-suggestion-${i}`}
                  onClick={() => submit(s)}
                  className="text-[11px] font-semibold text-[#4a2574] bg-white border border-purple-200 hover:bg-purple-50 rounded-full px-3 py-1.5 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {chat.messages.map((m, i) => (
          <Bubble key={i} m={m} />
        ))}
        {chat.busy && (
          <div data-testid="pp-chat-typing" className="flex gap-1 px-3 py-2">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce"></span>
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:120ms]"></span>
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:240ms]"></span>
          </div>
        )}
      </div>
      {chat.error && <p data-testid="pp-chat-error" className="px-4 pt-2 text-[11px] text-rose-700">{chat.error}</p>}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="p-3 border-t border-purple-100 flex gap-2"
      >
        <input
          data-testid="pp-chat-input"
          value={text}
          maxLength={1000}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask your Guide…"
          aria-label="Message your Parallel Parenting Guide"
          className="flex-1 min-w-0 rounded-xl border border-purple-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#8251b8]"
        />
        <button
          type="submit"
          data-testid="pp-chat-send"
          disabled={chat.busy || !text.trim()}
          aria-label="Send"
          className="shrink-0 w-11 rounded-xl bg-[#4a2574] hover:bg-[#2d1548] disabled:opacity-50 text-white transition-colors"
        >
          <i className="fa-solid fa-paper-plane"></i>
        </button>
      </form>
      <p className="px-4 pb-3 text-[10px] text-slate-400">General guidance, not legal advice. In danger? Call 911.</p>
    </section>
  );
}
