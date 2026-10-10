import React, { useEffect, useState } from "react";
import { toast } from "sonner";

import CONTENT from "./childNeedsContent.json";
import { ChildNeedsForm } from "./childNeeds/ChildNeedsForm";
import { NeedsProgress } from "./childNeeds/NeedsProgress";
import { NEEDS_PAGE_ART } from "./childNeeds/needsPageArt";
import { SendToProvider } from "./childNeeds/SendToProvider";
import { useProviderShares } from "./childNeeds/useProviderShares";
import { useGuideChat } from "./guide/useGuideChat";
import { JourneyPage } from "./selfJourney/JourneyPage";
import { NEEDS_ART } from "./selfJourney/selfJourneyArt";

const ORDER = NEEDS_ART.items.map((i) => i.key);
const CATS = Object.fromEntries(CONTENT.categories.map((c) => [c.key, c]));
const GREETING = "Hi, I'm your Child Needs Guide. Ask me how to describe your child's school, health or emotional needs so both homes can support them.";
const STARTERS = {
  educational: [
    "How do I describe my child's learning strengths?",
    "What should I share about an IEP or 504 plan?",
    "How can both homes handle homework the same way?",
    "How do we split school communication fairly?",
  ],
  medical: [
    "What health details are most useful to include?",
    "How do we keep medication schedules the same in both homes?",
    "How should we handle doctor appointments and updates?",
    "What should I leave off this form for privacy?",
  ],
  psychological: [
    "How do I describe my child's emotional needs without blaming?",
    "What triggers or routines are worth noting?",
    "How can both homes support therapy goals?",
    "How do I talk about stress or big changes calmly?",
  ],
};

function PortalBar() {
  return (
    <div data-testid="child-needs-portal-bar" className="rounded-xl bg-[#4A154B] text-white px-4 py-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5 shadow-md">
      <div className="flex items-center gap-3 min-w-0">
        <span className="w-9 h-9 shrink-0 rounded-lg bg-white text-[#4A154B] font-extrabold flex items-center justify-center text-sm">SA</span>
        <span className="font-semibold tracking-wide text-[14px] sm:text-[15px] leading-tight">{CONTENT.portal_title}</span>
      </div>
      <span className="text-[11px] opacity-85 whitespace-nowrap">
        <i className="fa-solid fa-lock mr-1"></i>
        {CONTENT.portal_badge}
      </span>
    </div>
  );
}

function Tabs({ activeKey, done, drafts, onPick }) {
  return (
    <div role="tablist" className="flex gap-2.5 overflow-x-auto pb-1">
      {ORDER.map((k) => {
        const on = k === activeKey;
        return (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={on}
            data-testid={`child-needs-tab-${k}`}
            onClick={() => onPick(k)}
            className={`shrink-0 rounded-lg border-2 px-4 py-2.5 text-left font-semibold text-[13px] whitespace-nowrap transition-colors ${
              on ? "bg-[#4A154B] border-[#4A154B] text-white" : "bg-white border-[#E2E8F0] text-[#718096] hover:border-[#611663] hover:text-[#4A154B]"
            }`}
          >
            {CATS[k].card_title}
            {done[k] ? (
              <span data-testid={`child-needs-${k}-completed`} className={`block text-[10px] font-bold ${on ? "text-emerald-200" : "text-emerald-700"}`}>
                Completed <i className="fa-solid fa-check text-[9px]"></i>
              </span>
            ) : (
              <span data-testid={`child-needs-${k}-status`} className={`block text-[10px] font-semibold ${on ? "text-purple-200" : "text-slate-400"}`}>
                {drafts[k] ? "Draft saved" : "Not started"}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

const askGuide = () => {
  document.querySelector('[data-testid="cn-chat"]')?.scrollIntoView({ behavior: "smooth", block: "center" });
  setTimeout(() => document.querySelector('[data-testid="cn-chat-input"]')?.focus(), 400);
};

// Picture icon → scroll to its questions and briefly highlight them; "start" → first question.
const jumpToFields = (item) => {
  const els = item.fields.map((id) => document.querySelector(`#cn-work [data-field="${id}"]`)).filter(Boolean);
  const target = els[0] || document.querySelector("#cn-work [data-field]");
  target?.scrollIntoView({ behavior: "smooth", block: item.fields.length ? "center" : "start" });
  els.forEach((el) => {
    el.classList.add("cn-field-flash");
    setTimeout(() => el.classList.remove("cn-field-flash"), 1800);
  });
};

// Your Child's Specific Needs: tabs + picture bubbles switch the form. `needs` is owned by JourneyShell.
export function ChildNeedsView({ onBack, onQuickExit, needs, parentName, initialOpenKey = null, initialJump = null, safetyFlag, userId }) {
  const { state, saveCategory, downloadReport } = needs;
  const sharing = useProviderShares(!!userId);
  const done = Object.fromEntries(ORDER.map((k) => [k, !!state.completed_at?.[k]]));
  const drafts = state.drafts || {};
  const [activeKey, setActiveKey] = useState(initialOpenKey || ORDER.find((k) => !done[k]) || ORDER[0]);
  const category = CATS[activeKey];
  const chat = useGuideChat("/journey-guide/child-needs/chat", { section: category.form_title, safety_flagged: !!safetyFlag });
  const pageArt = NEEDS_PAGE_ART[activeKey];
  const [live, setLive] = useState({});
  const answered = category.fields.filter((f) => String(live[f.id] || "").trim()).length;
  const total = category.fields.length;
  const hero = {
    title: category.card_title,
    subtitle: category.card_desc,
    pill: <><span data-testid="cn-answered-count">{answered}</span> of {total} questions answered</>,
    pct: Math.round((answered / total) * 100),
  };
  const iconDone = Object.fromEntries(pageArt.items.filter((i) => i.fields.length).map((i) => [i.key, i.fields.every((id) => String(live[id] || "").trim())]));
  // Opened from a Court picture icon: jump to that icon's questions once the page is up.
  useEffect(() => {
    const item = initialJump && pageArt.items.find((i) => i.key === initialJump);
    if (!item) return undefined;
    const t = setTimeout(() => jumpToFields(item), 450);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pick = (k) => {
    setActiveKey(k);
    document.getElementById("cn-work")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  const save = async (values, acknowledged, draft) => {
    try {
      const next = await saveCategory(activeKey, values, { draft, acknowledged });
      if (draft) {
        toast.success("Draft saved. It won't be marked complete until you submit.");
        return;
      }
      const ok = await downloadReport(next.answers, parentName);
      if (ok) toast.success("Submitted. Your Child's Specific Needs report is downloading.");
      const upNext = ORDER.find((k) => !next.completed_at?.[k]);
      if (upNext) pick(upNext);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't save right now. Please try again.");
    }
  };

  return (
    <JourneyPage
      tp="cn"
      hero={hero}
      art={pageArt}
      onArt={(key) => jumpToFields(pageArt.items.find((i) => i.key === key))}
      artState={{ done: iconDone, tickClass: "bg-purple-700" }}
      chat={chat}
      chatProps={{ title: "Child Needs Guide", greeting: GREETING, starters: { label: category.card_title, items: STARTERS[activeKey] } }}
      onBack={onBack}
      onQuickExit={onQuickExit}
      footer="Your Child's Specific Needs"
    >
      <div data-testid="door-view-child-needs" className="space-y-5">
        <PortalBar />
        <Tabs activeKey={activeKey} done={done} drafts={drafts} onPick={pick} />
        <section
          id="cn-work"
          data-testid={`child-needs-panel-${activeKey}`}
          className="bg-white rounded-xl border border-[#E2E8F0] shadow-[0_10px_15px_-3px_rgba(0,0,0,0.05)] p-5 sm:p-8 scroll-mt-6"
        >
          <div className="mb-6 pb-4 border-b-2 border-[#F4EEF5] flex items-start justify-between gap-3">
            <div>
              <h2 data-testid="child-needs-form-title" className="text-xl sm:text-2xl font-bold text-[#4A154B]">
                {category.form_title}
              </h2>
              <p className="text-sm text-[#718096] mt-1">{category.card_desc}</p>
            </div>
            <button
              type="button"
              data-testid="child-needs-ask-guide"
              onClick={askGuide}
              className="shrink-0 text-[11px] font-bold text-[#611663] bg-[#F4EEF5] hover:bg-[#E2D6E5] rounded-full px-3 py-1.5 transition-colors"
            >
              <i className="fa-solid fa-comments mr-1"></i>Ask the Guide
            </button>
          </div>
          <ChildNeedsForm
            key={activeKey}
            category={category}
            initial={drafts[activeKey] || state.answers?.[activeKey]}
            ackDate={state.notice_ack_at}
            onSubmit={(v, ack) => save(v, ack, false)}
            onDraft={(v, ack) => save(v, ack, true)}
            onValuesChange={setLive}
            shareSlot={
              userId && done[activeKey] ? (
                <SendToProvider
                  completedAt={state.completed_at}
                  defaultKeys={[activeKey]}
                  onSent={sharing.refresh}
                  testid="child-needs-send-provider"
                  className="px-5 py-2.5 rounded-md bg-white hover:bg-[#F4EEF5] border border-[#4A154B]/40 text-[#4A154B] text-sm font-semibold transition-colors"
                />
              ) : null
            }
          />
        </section>
        <NeedsProgress
          order={ORDER}
          done={done}
          drafts={drafts}
          activeKey={activeKey}
          onPick={pick}
          shares={sharing.shares}
          showSent={!!userId && done[activeKey]}
          onDownload={() => downloadReport(state.answers, parentName)}
        />
      </div>
    </JourneyPage>
  );
}

export default ChildNeedsView;
