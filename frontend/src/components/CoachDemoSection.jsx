/**
 * CoachDemoSection — live Landing-page preview of the SA CoParents
 * AI Communication Coach.
 *
 * Iter205. Powered by POST /api/coach/demo/reply — real Claude output,
 * no auth, aggressively rate-limited server-side (10 messages/IP/hour,
 * 6 turns max per transcript, 600-char cap). The exact same
 * generate_coach_reply() function that powers the signed-in Coach at
 * /coach also powers this preview, so what visitors see is what they
 * get once they register.
 *
 * UX contract:
 *   1. Empty state — headline + a strip of 4 curated starter prompts.
 *   2. Click a starter → it becomes the first user bubble, then the
 *      assistant bubble streams in (well, appears after ~4-8s).
 *   3. After the first exchange, a text input appears so the visitor
 *      can push the conversation one or two more turns.
 *   4. When the transcript hits the demo's turn cap (server-side 6
 *      total turns) OR a safety_flag comes back, the composer is
 *      replaced with the sign-up CTA + safety copy.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import {
  Sparkles, ArrowRight, Loader2, ShieldAlert, MessageSquare,
  Lock, RefreshCw,
} from "lucide-react";

import { api } from "../lib/api";
import { logError } from "../lib/logger";

// Client-side ceiling matches server (6 total turns = 3 back-and-forths).
const MAX_TURNS = 6;
const MAX_USER_MESSAGE_LEN = 600;


export default function CoachDemoSection() {
  const [starters, setStarters] = useState([]);
  const [transcript, setTranscript] = useState([]); // [{role, content, followups?}]
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [composer, setComposer] = useState("");
  const [safetyFlagged, setSafetyFlagged] = useState(false);
  const [capReached, setCapReached] = useState(false);
  const scrollerRef = useRef(null);

  useEffect(() => {
    let alive = true;
    api.get("/coach/demo/starters")
      .then((r) => { if (alive) setStarters(r?.data?.starters || []); })
      .catch((e) => logError("coach demo starters", e));
    return () => { alive = false; };
  }, []);

  // Auto-scroll the transcript viewport as new turns land.
  useEffect(() => {
    if (scrollerRef.current) {
      scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
    }
  }, [transcript, pending]);

  const send = async (message) => {
    const clean = String(message || "").trim();
    if (!clean || pending || capReached) return;
    if (clean.length > MAX_USER_MESSAGE_LEN) {
      setError(`Please keep the message under ${MAX_USER_MESSAGE_LEN} characters for the demo.`);
      return;
    }
    setError("");
    const nextTranscript = [...transcript, { role: "user", content: clean }];
    setTranscript(nextTranscript);
    setComposer("");
    setPending(true);
    try {
      const { data } = await api.post("/coach/demo/reply", {
        user_message: clean,
        history: transcript.map((t) => ({ role: t.role, content: t.content })),
      });
      const assistant = {
        role: "assistant",
        content: data?.reply || "…",
        followups: Array.isArray(data?.suggested_followups) ? data.suggested_followups : [],
        safety_flag: !!data?.safety_flag,
      };
      const finalTranscript = [...nextTranscript, assistant];
      setTranscript(finalTranscript);
      if (assistant.safety_flag) setSafetyFlagged(true);
      if (finalTranscript.length >= MAX_TURNS) setCapReached(true);
    } catch (err) {
      logError("coach demo reply", err);
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 409) setCapReached(true);
      setError(
        detail ||
          (status === 429
            ? "The demo is busy — please try again shortly."
            : "The Coach couldn't respond right now."),
      );
      // Roll back the user bubble so re-submit doesn't double-post it.
      setTranscript(transcript);
    } finally {
      setPending(false);
    }
  };

  const startWith = (prompt) => send(prompt);

  const reset = () => {
    setTranscript([]);
    setSafetyFlagged(false);
    setCapReached(false);
    setError("");
    setComposer("");
  };

  const isEmpty = transcript.length === 0;
  const remaining = useMemo(() => MAX_USER_MESSAGE_LEN - composer.length, [composer]);

  /**
   * Called by the "Try the Coach now" CTA in the section header.
   * Scrolls the composer into view (matters most on mobile where the
   * chat panel sits well below the fold) and focuses whichever
   * textarea is currently rendered — the empty-state one before the
   * first exchange, the follow-up composer afterwards.
   */
  const focusFirstInput = () => {
    // Defer to next tick so the scroll can start before focus fires;
    // otherwise mobile Safari steals focus back to the button.
    setTimeout(() => {
      const target =
        document.querySelector('[data-testid="coach-demo-empty-input"]') ||
        document.querySelector('[data-testid="coach-demo-input"]');
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "center" });
        try { target.focus({ preventScroll: true }); } catch { /* noop */ }
      }
    }, 40);
  };

  return (
    <section
      data-testid="coach-demo-section"
      id="coach-demo-section"
      className="relative py-16 sm:py-24"
      style={{
        background:
          "linear-gradient(180deg, #FBFAFF 0%, #F2ECFF 60%, #E9F6F6 100%)",
      }}
    >
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[#3D1A78]/25 to-transparent" />
      <div className="max-w-6xl mx-auto px-5 sm:px-8">
        {/* Header */}
        <div className="text-center max-w-2xl mx-auto mb-10 sm:mb-14">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/70 backdrop-blur px-3 py-1 text-[11px] font-semibold tracking-[0.14em] uppercase text-[#3D1A78] shadow-sm">
            <Sparkles size={12} /> Live sample · no signup needed
          </div>
          <h2 className="mt-4 font-serif text-4xl sm:text-5xl leading-[1.05] tracking-tight text-[#1A1330]">
            Try the Communication Coach
          </h2>
          <p className="mt-4 text-base sm:text-lg text-[#4B4567] leading-relaxed">
            A private, BIFF-first co-parenting assistant that helps you
            pause, get grounded, and draft a message you won't regret.
            Pick a real scenario below — the Coach responds live.
          </p>
          {/* Primary CTA — jumps the visitor straight to the composer
              on mobile (where the panel sits well below the fold) and
              auto-focuses the textarea so the first keystroke lands
              exactly where it should. */}
          <div className="mt-8 flex justify-center">
            <button
              type="button"
              onClick={focusFirstInput}
              data-testid="coach-demo-try-cta"
              className="inline-flex items-center justify-center gap-2.5 rounded-full bg-[#3D1A78] hover:bg-[#4B2094] text-white text-base sm:text-lg font-semibold px-9 sm:px-11 py-4 sm:py-4.5 shadow-[0_14px_36px_-14px_rgba(61,26,120,0.7)] hover:shadow-[0_18px_44px_-16px_rgba(61,26,120,0.85)] hover:-translate-y-0.5 transition-all"
            >
              <Sparkles size={18} /> Try the Coach now
            </button>
          </div>
        </div>

        {/* Panel */}
        <div className="rounded-3xl bg-white/85 backdrop-blur border border-[#E5E0EE] shadow-[0_24px_60px_-30px_rgba(61,26,120,0.35)] overflow-hidden">
          {/* Panel header (status pill) */}
          <div className="flex items-center justify-between px-5 sm:px-7 py-4 border-b border-[#EFEBF7] bg-white/50">
            <div className="flex items-center gap-2 text-[13px] font-semibold text-[#3D1A78]">
              <MessageSquare size={14} /> AI Communication Coach
            </div>
            <div className="flex items-center gap-3 text-[11px] text-[#857E9C]">
              <span className="inline-flex items-center gap-1">
                <Lock size={11} /> Nothing here is saved
              </span>
              {!isEmpty && (
                <button
                  type="button"
                  onClick={reset}
                  data-testid="coach-demo-reset-btn"
                  className="inline-flex items-center gap-1 rounded-full border border-[#E5E0EE] px-2.5 py-1 hover:bg-[#F8F5FF] transition"
                >
                  <RefreshCw size={10} /> Start over
                </button>
              )}
            </div>
          </div>

          {/* Body */}
          <div className="grid md:grid-cols-[220px_1fr] min-h-[420px]">
            {/* Starter rail (desktop) */}
            <div className="hidden md:flex flex-col gap-2 p-5 border-r border-[#EFEBF7] bg-gradient-to-b from-white to-[#FBFAFF]">
              <div className="text-[10px] font-bold tracking-[0.16em] uppercase text-[#857E9C] mb-1">
                Try one
              </div>
              {starters.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  disabled={pending || capReached}
                  onClick={() => startWith(s.prompt)}
                  data-testid={`coach-demo-starter-${s.id}`}
                  className="text-left text-[12.5px] leading-snug text-[#3D1A78] bg-white rounded-xl border border-[#E5E0EE] px-3 py-2.5 hover:bg-[#F5F0FF] hover:border-[#C7B4EF] transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {s.label}
                </button>
              ))}
            </div>

            {/* Chat viewport */}
            <div
              ref={scrollerRef}
              className="p-5 sm:p-7 max-h-[560px] overflow-y-auto flex flex-col gap-4"
              data-testid="coach-demo-transcript"
            >
              {isEmpty && (
                <div className="flex-1 flex items-center justify-center text-center py-8">
                  <div className="max-w-md w-full">
                    <div className="text-[14.5px] font-semibold text-[#1A1330] mb-2">
                      Pick a scenario or write your own
                    </div>
                    <p className="text-[13px] text-[#4B4567] leading-relaxed">
                      Tap a starter on the left (or scroll down on mobile) —
                      or describe your own situation below in your own words.
                      The Coach will help you pause, get grounded, and draft
                      the actual reply.
                    </p>

                    {/* Custom-prompt slot — first message the visitor writes */}
                    <form
                      onSubmit={(e) => { e.preventDefault(); send(composer); }}
                      className="mt-5 text-left"
                      data-testid="coach-demo-empty-composer"
                    >
                      <label className="text-[10px] font-bold tracking-[0.16em] uppercase text-[#857E9C]">
                        Or in your own words
                      </label>
                      <div className="mt-2 relative">
                        <textarea
                          rows={3}
                          value={composer}
                          onChange={(e) => setComposer(e.target.value.slice(0, MAX_USER_MESSAGE_LEN))}
                          placeholder="e.g. My co-parent keeps changing plans last-minute and my daughter is left waiting…"
                          disabled={pending}
                          data-testid="coach-demo-empty-input"
                          className="w-full resize-none rounded-2xl border border-[#E5E0EE] bg-white px-4 py-3 text-[13.5px] text-[#1A1330] placeholder:text-[#857E9C]/70 focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
                        />
                        <div className="absolute bottom-1.5 right-3 text-[10px] text-[#857E9C]">
                          {remaining} chars left
                        </div>
                      </div>
                      <button
                        type="submit"
                        disabled={pending || !composer.trim()}
                        data-testid="coach-demo-empty-send-btn"
                        className="mt-3 w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white text-[13px] font-semibold px-4 py-2.5 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:hover:translate-y-0"
                      >
                        {pending
                          ? <Loader2 size={14} className="animate-spin" />
                          : <ArrowRight size={14} />}
                        Ask the Coach
                      </button>
                    </form>

                    {/* Mobile starter list */}
                    <div className="md:hidden mt-6">
                      <div className="text-[10px] font-bold tracking-[0.16em] uppercase text-[#857E9C] mb-2">
                        Or try one
                      </div>
                      <div className="flex flex-col gap-2">
                        {starters.map((s) => (
                          <button
                            key={s.id}
                            type="button"
                            disabled={pending}
                            onClick={() => startWith(s.prompt)}
                            data-testid={`coach-demo-starter-mobile-${s.id}`}
                            className="text-left text-[12.5px] leading-snug text-[#3D1A78] bg-white rounded-xl border border-[#E5E0EE] px-3 py-2.5"
                          >
                            {s.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {transcript.map((turn, i) => (
                <ChatBubble key={i} turn={turn} onFollowup={send} pending={pending} />
              ))}

              {pending && (
                <div className="self-start flex items-center gap-2 text-[12.5px] text-[#857E9C] italic px-2">
                  <Loader2 size={13} className="animate-spin" />
                  Coach is thinking…
                </div>
              )}

              {safetyFlagged && (
                <div className="mt-2 rounded-2xl bg-[#FFF4EE] border border-[#F1B08E] p-4 text-[13px] text-[#7C3A1A] leading-relaxed">
                  <div className="flex items-center gap-2 font-semibold mb-1">
                    <ShieldAlert size={14} /> Safety signal detected
                  </div>
                  What you described sounds serious. If you're in immediate
                  danger, call your local emergency number. In the app we
                  route these conversations through our{" "}
                  <Link to="/safety" className="underline underline-offset-2">
                    Safety Pathway
                  </Link>{" "}
                  first, not the Coach.
                </div>
              )}

              {error && (
                <div className="mt-2 rounded-2xl bg-[#FEF1F1] border border-[#F1B0B0] p-3 text-[12.5px] text-[#7C1A1A]">
                  {error}
                </div>
              )}
            </div>
          </div>

          {/* Composer / CTA footer */}
          <div className="border-t border-[#EFEBF7] bg-[#FBFAFF]/70 px-5 sm:px-7 py-4">
            {capReached ? (
              <SignUpCta reason="cap" />
            ) : safetyFlagged ? (
              <SignUpCta reason="safety" />
            ) : isEmpty ? (
              <div className="text-center text-[12px] text-[#857E9C]">
                Every reply is generated live by the same Coach signed-in
                parents use — nothing here is retained.
              </div>
            ) : (
              <form
                onSubmit={(e) => { e.preventDefault(); send(composer); }}
                className="flex items-end gap-2"
                data-testid="coach-demo-composer"
              >
                <div className="flex-1 relative">
                  <textarea
                    rows={2}
                    value={composer}
                    onChange={(e) => setComposer(e.target.value.slice(0, MAX_USER_MESSAGE_LEN))}
                    placeholder="Ask a follow-up (e.g. 'make it firmer' or 'add a rescheduling line')…"
                    disabled={pending}
                    data-testid="coach-demo-input"
                    className="w-full resize-none rounded-2xl border border-[#E5E0EE] bg-white px-4 py-3 text-[13.5px] text-[#1A1330] placeholder:text-[#857E9C]/70 focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
                  />
                  <div className="absolute bottom-1.5 right-3 text-[10px] text-[#857E9C]">
                    {remaining} chars left
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={pending || !composer.trim()}
                  data-testid="coach-demo-send-btn"
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white text-[13px] font-semibold px-4 py-3 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:hover:translate-y-0"
                >
                  {pending
                    ? <Loader2 size={14} className="animate-spin" />
                    : <ArrowRight size={14} />}
                  Send
                </button>
              </form>
            )}
          </div>
        </div>

        {/* Sub-line beneath the panel */}
        <div className="mt-6 text-center text-[12px] text-[#857E9C] leading-relaxed max-w-xl mx-auto">
          Same Coach model, safety guardrails, and BIFF-first tone as the
          signed-in experience. This demo is capped at {MAX_TURNS / 2} exchanges;
          create a free account to keep going and save your conversations.
        </div>

        {/* Before / After social-proof strip */}
        <BeforeAfterStrip />
      </div>
    </section>
  );
}


/**
 * BeforeAfterStrip — three anonymized "message → Coach reframe" cards
 * that live under the demo panel to socially prove the tone shift the
 * Coach reliably produces. These are illustrative examples (not
 * verbatim user reviews), so we frame them honestly as
 * "Real-world reframes" rather than as testimonials.
 *
 * Each card intentionally leads with the raw, activated draft so a
 * visitor scanning the strip feels the contrast in one glance:
 * blaming, reactive, second-person → brief, informative, friendly,
 * firm, child-centered.
 */
const BEFORE_AFTER_EXAMPLES = [
  {
    scenario: "Late pickup, third week in a row",
    before:
      "Are you serious right now?? You're 40 mins late AGAIN. She's the one sitting at school wondering if you forgot her. Grow up.",
    after:
      "Just checking in — Ava has been waiting at pickup past 4:30 the last three Fridays. Could we lock in a 4:00 handoff going forward so she isn't left wondering? Happy to swap contacts with the after-care lead if that helps on your side.",
  },
  {
    scenario: "New partner introduced without a heads-up",
    before:
      "So I heard from Leo that Jenna was there this weekend. Really? You couldn't even give me a heads-up before introducing our kid to your new girlfriend?",
    after:
      "Leo mentioned meeting Jenna this weekend and I want to make sure we're on the same page. Could we agree that new adults in either home get a quick heads-up before they meet the kids? Not a veto — just a heads-up so they aren't caught off guard.",
  },
  {
    scenario: "Last-minute weekend cancel",
    before:
      "Cancelling an hour before pickup? Nice. She was already packed. This is exactly the kind of stuff that makes her not trust you.",
    after:
      "Thanks for letting me know. Ava was already packed for this weekend, so this landed hard for her. Going forward, could you give me 24 hrs notice if a weekend needs to shift? I'll break the news to her tonight and we can talk about a make-up weekend when you're able.",
  },
];


function BeforeAfterStrip() {
  return (
    <div className="mt-14 sm:mt-20" data-testid="coach-demo-before-after-strip">
      <div className="text-center max-w-xl mx-auto mb-8">
        <div className="inline-flex items-center gap-2 rounded-full bg-white/70 backdrop-blur px-3 py-1 text-[11px] font-semibold tracking-[0.14em] uppercase text-[#3D1A78] shadow-sm">
          Real-world reframes
        </div>
        <h3 className="mt-3 font-serif text-2xl sm:text-3xl leading-tight text-[#1A1330]">
          See the tone shift
        </h3>
        <p className="mt-2 text-[13px] sm:text-[14px] text-[#4B4567] leading-relaxed">
          Three anonymized situations we hear a lot — the raw draft on the
          left, the Coach-refined version on the right.
        </p>
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        {BEFORE_AFTER_EXAMPLES.map((ex, i) => (
          <article
            key={i}
            data-testid={`coach-demo-before-after-card-${i}`}
            className="rounded-3xl bg-white/85 backdrop-blur border border-[#E5E0EE] shadow-[0_18px_44px_-28px_rgba(61,26,120,0.35)] overflow-hidden flex flex-col"
          >
            <div className="px-5 pt-5 pb-3 border-b border-[#EFEBF7] bg-gradient-to-b from-white to-[#FBFAFF]">
              <div className="text-[10px] font-bold tracking-[0.16em] uppercase text-[#857E9C]">
                Scenario
              </div>
              <div className="mt-1 text-[13px] font-semibold text-[#1A1330] leading-snug">
                {ex.scenario}
              </div>
            </div>

            <div className="p-5 flex flex-col gap-4 flex-1">
              {/* Before */}
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#C2554A]" />
                  <span className="text-[10px] font-bold tracking-[0.14em] uppercase text-[#C2554A]">
                    Draft (activated)
                  </span>
                </div>
                <div className="rounded-2xl bg-[#FDF2F0] border border-[#F4CFC7] text-[12.5px] leading-relaxed text-[#5A2318] px-3.5 py-2.5">
                  {ex.before}
                </div>
              </div>
              {/* After */}
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#2DB5B5]" />
                  <span className="text-[10px] font-bold tracking-[0.14em] uppercase text-[#2DB5B5]">
                    Coach-refined
                  </span>
                </div>
                <div className="rounded-2xl bg-[#EDF9F9] border border-[#B6E4E4] text-[12.5px] leading-relaxed text-[#1A5555] px-3.5 py-2.5">
                  {ex.after}
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>
      <p className="mt-6 text-center text-[11px] text-[#857E9C] italic max-w-xl mx-auto">
        Illustrative examples · names changed · no real messages included.
      </p>
    </div>
  );
}


function ChatBubble({ turn, onFollowup, pending }) {
  if (turn.role === "user") {
    return (
      <div className="self-end max-w-[78%]" data-testid="coach-demo-bubble-user">
        <div className="rounded-3xl rounded-br-md bg-gradient-to-br from-[#3D1A78] to-[#2A0F5A] text-white text-[13.5px] leading-relaxed px-4 py-3 shadow-sm">
          {turn.content}
        </div>
      </div>
    );
  }
  return (
    <div className="self-start max-w-[86%] w-full" data-testid="coach-demo-bubble-assistant">
      <div className="rounded-3xl rounded-bl-md bg-white border border-[#E5E0EE] text-[#1A1330] text-[13.5px] leading-relaxed px-4 py-3 shadow-sm">
        <div className="coach-demo-markdown">
          <ReactMarkdown
            components={{
              p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
              strong: ({ node, ...props }) => <strong className="font-semibold text-[#3D1A78]" {...props} />,
              ul: ({ node, ...props }) => <ul className="list-disc pl-5 my-2 space-y-1" {...props} />,
              ol: ({ node, ...props }) => <ol className="list-decimal pl-5 my-2 space-y-1" {...props} />,
              li: ({ node, ...props }) => <li className="leading-relaxed" {...props} />,
              a: ({ node, ...props }) => <a className="underline underline-offset-2 text-[#3D1A78]" {...props} />,
              code: ({ node, ...props }) => <code className="bg-[#F5F0FF] rounded px-1 py-0.5 text-[12.5px]" {...props} />,
            }}
          >
            {turn.content}
          </ReactMarkdown>
        </div>
      </div>
      {Array.isArray(turn.followups) && turn.followups.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {turn.followups.slice(0, 3).map((f, i) => (
            <button
              key={i}
              type="button"
              disabled={pending}
              onClick={() => onFollowup(f)}
              data-testid={`coach-demo-followup-${i}`}
              className="text-[11.5px] font-medium text-[#3D1A78] bg-[#F5F0FF] border border-[#E0D3FF] rounded-full px-3 py-1.5 hover:bg-[#EBE1FF] transition disabled:opacity-50"
            >
              {f}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}


function SignUpCta({ reason }) {
  const copy = reason === "safety"
    ? "This looks like a moment for extra care — create a free account to route through our safety-first pathway."
    : "You've reached the demo's cap — create a free account to keep chatting and save your conversation.";
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
      <div className="flex-1 text-[13px] text-[#1A1330] leading-relaxed">
        {copy}
      </div>
      <Link
        to="/register"
        data-testid="coach-demo-signup-cta"
        className="inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white text-[13px] font-semibold px-4 py-2.5 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all"
      >
        Create a free account <ArrowRight size={13} />
      </Link>
    </div>
  );
}
