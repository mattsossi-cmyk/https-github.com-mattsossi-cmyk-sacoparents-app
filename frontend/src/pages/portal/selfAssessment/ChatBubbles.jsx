import React from "react";

const enter = "animate-in fade-in slide-in-from-bottom-2 duration-300";

export function GuideAvatar() {
  return (
    <div className="shrink-0 w-8 h-8 rounded-full bg-[#4c2889] text-white flex items-center justify-center shadow-sm">
      <i className="fa-solid fa-seedling text-[0.8125rem]"></i>
    </div>
  );
}

export function CoachBubble({ children, testid, showAvatar = true }) {
  return (
    <div data-testid={testid} className={`flex items-end gap-2 max-w-[88%] ${enter}`}>
      {showAvatar ? <GuideAvatar /> : <div className="w-8 shrink-0" />}
      <div className="bg-white border border-purple-100 rounded-2xl rounded-bl-md px-3.5 py-2.5 text-[13.5px] leading-relaxed text-slate-800 shadow-sm whitespace-pre-line">
        {children}
      </div>
    </div>
  );
}

export function ParentBubble({ children, testid, muted = false }) {
  return (
    <div data-testid={testid} className={`flex justify-end ${enter}`}>
      <div
        className={`max-w-[80%] rounded-2xl rounded-br-md px-3.5 py-2 text-[13.5px] leading-relaxed whitespace-pre-line ${
          muted ? "bg-slate-100 text-slate-500 italic" : "bg-[#4c2889] text-white shadow-sm"
        }`}
      >
        {children}
      </div>
    </div>
  );
}

export function TypingBubble() {
  return (
    <div data-testid="sa-chat-typing" className={`flex items-end gap-2 ${enter}`}>
      <GuideAvatar />
      <div className="bg-white border border-purple-100 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm flex gap-1">
        {[0, 150, 300].map((d) => (
          <span
            key={d}
            className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce"
            style={{ animationDelay: `${d}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

export function SectionDivider({ number, title, testid }) {
  return (
    <div data-testid={testid} className={`flex items-center gap-2 py-1 ${enter}`}>
      <div className="flex-1 h-px bg-purple-200" />
      <div className="shrink-0 px-3 py-1 rounded-full bg-purple-100 text-purple-900 text-[0.6875rem] font-bold tracking-wide">
        {number}. {title}
      </div>
      <div className="flex-1 h-px bg-purple-200" />
    </div>
  );
}
