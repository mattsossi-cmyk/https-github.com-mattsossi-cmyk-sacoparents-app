import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Send,
  Sparkles,
  Loader2,
  Plus,
  Trash2,
  MessageSquare,
  ShieldAlert,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";

import AppShell from "../components/AppShell";
import DemoModeBanner from "../components/DemoModeBanner";
import CoachModelPickerChip, {
  useCoachModelPreference,
} from "../components/coach/CoachModelPickerChip";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

/**
 * Coach — Interactive AI Coach Chat.
 *
 * A safe, warm, BIFF-first chat surface a parent can open in the moments
 * that matter (right after a hard exchange, before a hard reply, when
 * they feel stuck). Multi-turn — sessions are persisted to Mongo so a
 * parent can pick a conversation back up later.
 *
 * URL shapes:
 *   /coach                  — landing / new-session state
 *   /coach/:sessionId       — active conversation
 */

function useStarters() {
  const [starters, setStarters] = useState([]);
  useEffect(() => {
    let cancelled = false;
    api
      .get("/coach/starters")
      .then((r) => {
        if (!cancelled) setStarters(r.data?.starters || []);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);
  return starters;
}

function useSessions() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    try {
      const r = await api.get("/coach/sessions");
      setSessions(r.data?.sessions || []);
    } catch (e) {
      logError("coach.sessions", e);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    reload();
  }, [reload]);
  return { sessions, loading, reload };
}

function SafetyBanner() {
  return (
    <div
      className="rounded-2xl bg-[#FEF1EC] border border-[#F5C9B4] p-4 flex items-start gap-3"
      data-testid="coach-safety-banner"
    >
      <ShieldAlert size={18} className="text-[#C2481F] mt-0.5 shrink-0" />
      <div className="text-sm text-[#3A1A0F] leading-relaxed">
        The coach can&apos;t help with immediate safety concerns. If you or
        your child are in danger, please contact the{" "}
        <a
          href="tel:18007997233"
          className="font-semibold underline"
          data-testid="coach-safety-hotline"
        >
          National DV Hotline (1-800-799-7233)
        </a>{" "}
        or dial 911. In-app,{" "}
        <Link
          to="/safety-assessment"
          className="font-semibold underline"
          data-testid="coach-safety-assessment-link"
        >
          take the Safety Screen
        </Link>{" "}
        for a personalised pathway.
      </div>
    </div>
  );
}

const MARKDOWN_COMPONENTS = {
  p: (props) => <p className="mb-2 last:mb-0" {...props} />,
  ul: (props) => <ul className="list-disc pl-5 mb-2 space-y-1" {...props} />,
  ol: (props) => <ol className="list-decimal pl-5 mb-2 space-y-1" {...props} />,
  strong: (props) => <strong className="text-[#3D1A78]" {...props} />,
  em: (props) => <em className="italic" {...props} />,
  a: (props) => (
    <a
      className="text-[#3D1A78] underline"
      target="_blank"
      rel="noreferrer"
      {...props}
    />
  ),
};

function Bubble({ role, content, safety_flag }) {
  const isUser = role === "user";
  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
      data-testid={`coach-bubble-${role}`}
    >
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 leading-relaxed text-sm ${
          isUser
            ? "bg-[#3D1A78] text-white rounded-br-sm"
            : "bg-white text-[#1A1330] border border-[#E5E0EE] rounded-bl-sm"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <div className="coach-markdown prose prose-sm max-w-none">
            <ReactMarkdown components={MARKDOWN_COMPONENTS}>
              {content}
            </ReactMarkdown>
          </div>
        )}
        {safety_flag && (
          <div className="mt-2 flex items-center gap-1.5 text-xs text-[#C2481F] font-semibold">
            <ShieldAlert size={12} /> Safety-aware response
          </div>
        )}
      </div>
    </div>
  );
}

function Suggestions({ items, onPick }) {
  if (!items || items.length === 0) return null;
  return (
    <div
      className="flex flex-wrap gap-2 mb-4 ml-1"
      data-testid="coach-followups"
    >
      {items.map((s, i) => (
        <button
          key={`${i}-${s}`}
          type="button"
          onClick={() => onPick(s)}
          className="text-xs px-3 py-1.5 rounded-full border border-[#E5E0EE] bg-white text-[#3D1A78] hover:bg-[#F5F2FA] transition-colors"
          data-testid={`coach-followup-${i}`}
        >
          {s}
        </button>
      ))}
    </div>
  );
}

function ChatComposer({ onSend, disabled }) {
  const [value, setValue] = useState("");
  const inputRef = useRef(null);
  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className="sticky bottom-0 bg-gradient-to-t from-white via-white to-transparent pt-4 pb-2"
      data-testid="coach-composer"
    >
      <div className="flex items-end gap-2 bg-white border border-[#E5E0EE] rounded-3xl px-4 py-2 shadow-sm focus-within:border-[#3D1A78]">
        <textarea
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Tell your coach what's happening…"
          rows={1}
          maxLength={4000}
          className="flex-1 resize-none outline-none text-sm text-[#1A1330] bg-transparent py-2 max-h-40"
          data-testid="coach-input"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="shrink-0 w-10 h-10 rounded-full bg-[#3D1A78] text-white grid place-items-center disabled:opacity-40 hover:bg-[#2D0F63] transition-colors"
          aria-label="Send message"
          data-testid="coach-send-btn"
        >
          {disabled ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Send size={16} />
          )}
        </button>
      </div>
      <p className="text-[11px] text-[#857E9C] mt-2 text-center">
        Not legal, medical, or therapy advice. In an emergency call 911 or
        1-800-799-7233.
      </p>
    </form>
  );
}

function EmptyState({ starters, onPick, onStartBlank, busy }) {
  return (
    <div className="space-y-6" data-testid="coach-empty-state">
      <div>
        <div className="eyebrow text-[#3D1A78] flex items-center gap-1.5">
          <Sparkles size={12} /> AI Coach · BIFF-first
        </div>
        <h2 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-2">
          What&apos;s on your mind?
        </h2>
        <p className="text-[#4B4567] mt-2 max-w-2xl">
          A warm, non-judgemental coach for the moments that matter — right
          after a hard exchange, before a reply you might regret, or when
          you just need to think out loud about your child.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {starters.map((s) => (
          <button
            key={s.id}
            type="button"
            disabled={busy}
            onClick={() => onPick(s.prompt)}
            className="text-left rounded-2xl border border-[#E5E0EE] bg-white p-4 hover:border-[#3D1A78] hover:bg-[#F5F2FA] transition-colors disabled:opacity-50"
            data-testid={`coach-starter-${s.id}`}
          >
            <div className="text-sm font-semibold text-[#1A1330]">
              {s.label}
            </div>
            <div className="text-xs text-[#4B4567] mt-1 line-clamp-2">
              {s.prompt}
            </div>
          </button>
        ))}
      </div>

      <div className="pt-2">
        <button
          type="button"
          onClick={onStartBlank}
          disabled={busy}
          className="inline-flex items-center gap-2 text-sm text-[#3D1A78] hover:underline font-medium"
          data-testid="coach-start-blank-btn"
        >
          <Plus size={14} /> Start with a blank conversation
        </button>
      </div>
    </div>
  );
}

function SessionList({ sessions, activeId, onOpen, onDelete }) {
  if (!sessions.length) return null;
  return (
    <aside
      className="rounded-3xl border border-[#E5E0EE] bg-white p-4 h-fit lg:sticky lg:top-24"
      data-testid="coach-session-list"
    >
      <div className="flex items-center gap-2 mb-3">
        <MessageSquare size={14} className="text-[#3D1A78]" />
        <h3 className="text-xs uppercase tracking-[0.2em] font-bold text-[#3D1A78]">
          Past conversations
        </h3>
      </div>
      <ul className="space-y-1 max-h-[60vh] overflow-y-auto">
        {sessions.map((s) => {
          const active = s.session_id === activeId;
          return (
            <li key={s.session_id} className="group flex items-center gap-1">
              <button
                type="button"
                onClick={() => onOpen(s.session_id)}
                className={`flex-1 text-left px-3 py-2 rounded-xl text-sm truncate transition-colors ${
                  active
                    ? "bg-[#3D1A78] text-white font-semibold"
                    : "text-[#1A1330] hover:bg-[#F5F2FA]"
                }`}
                data-testid={`coach-session-${s.session_id}`}
                title={s.title}
              >
                {s.title || "Conversation"}
              </button>
              <button
                type="button"
                onClick={() => onDelete(s.session_id)}
                className="opacity-0 group-hover:opacity-100 shrink-0 w-8 h-8 rounded-lg grid place-items-center text-[#857E9C] hover:text-[#C2481F] hover:bg-[#FEF1EC] transition-all"
                aria-label={`Delete conversation "${s.title}"`}
                data-testid={`coach-delete-${s.session_id}`}
              >
                <Trash2 size={13} />
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

export default function Coach() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [session, setSession] = useState(null);
  const [loadingSession, setLoadingSession] = useState(false);
  const [sending, setSending] = useState(false);
  const starters = useStarters();
  const { sessions, reload: reloadSessions } = useSessions();
  const [modelPreference, setModelPreference] = useCoachModelPreference();
  const scrollRef = useRef(null);

  // Load conversation when the URL sessionId changes.
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      setSession(null);
      return;
    }
    let cancelled = false;
    setLoadingSession(true);
    api
      .get(`/coach/sessions/${sessionId}`)
      .then((r) => {
        if (cancelled) return;
        setSession(r.data?.session || null);
        setMessages(r.data?.messages || []);
      })
      .catch(() => {
        if (!cancelled) {
          toast.error("Could not load that conversation.");
          navigate("/coach", { replace: true });
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingSession(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, navigate]);

  // Auto-scroll on new messages.
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending]);

  const createSessionAndSend = useCallback(
    async (prompt) => {
      setSending(true);
      try {
        const r = await api.post("/coach/sessions", {});
        const newId = r.data?.session_id;
        if (!newId) throw new Error("no session id");
        // Optimistically render the user message so navigation feels instant.
        setSession(r.data);
        setMessages([
          {
            message_id: "pending-user",
            role: "user",
            content: prompt,
            created_at: new Date().toISOString(),
          },
        ]);
        navigate(`/coach/${newId}`, { replace: true });
        const sr = await api.post(`/coach/sessions/${newId}/message`, {
          content: prompt,
          ...(modelPreference ? { model: modelPreference } : {}),
        });
        setMessages([sr.data.user_message, sr.data.assistant_message]);
        reloadSessions();
      } catch (e) {
        logError("coach.newSession", e);
        toast.error("Couldn't start the conversation. Please try again.");
      } finally {
        setSending(false);
      }
    },
    [navigate, reloadSessions, modelPreference]
  );

  const sendInSession = useCallback(
    async (content) => {
      if (!sessionId) {
        await createSessionAndSend(content);
        return;
      }
      setSending(true);
      // Optimistic user bubble
      const pending = {
        message_id: `pending-${Date.now()}`,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };
      setMessages((m) => [...m, pending]);
      try {
        const r = await api.post(`/coach/sessions/${sessionId}/message`, {
          content,
          ...(modelPreference ? { model: modelPreference } : {}),
        });
        setMessages((m) =>
          m
            .filter((x) => x.message_id !== pending.message_id)
            .concat([r.data.user_message, r.data.assistant_message])
        );
        reloadSessions();
      } catch (e) {
        setMessages((m) => m.filter((x) => x.message_id !== pending.message_id));
        toast.error("The coach couldn't respond. Please try again.");
      } finally {
        setSending(false);
      }
    },
    [sessionId, createSessionAndSend, reloadSessions, modelPreference]
  );

  const handleDelete = useCallback(
    async (sid) => {
      if (!window.confirm("Delete this conversation? This can't be undone.")) return;
      try {
        await api.delete(`/coach/sessions/${sid}`);
        toast.success("Conversation deleted.");
        reloadSessions();
        if (sid === sessionId) {
          navigate("/coach", { replace: true });
        }
      } catch (e) {
        toast.error("Couldn't delete the conversation.");
      }
    },
    [sessionId, navigate, reloadSessions]
  );

  const lastAssistant = useMemo(
    () =>
      [...messages].reverse().find((m) => m.role === "assistant") || null,
    [messages]
  );

  return (
    <AppShell>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="coach-back-link"
        >
          <ArrowLeft size={14} /> Back to Dashboard
        </Link>

        <div className="mb-6">
          <DemoModeBanner />
        </div>

        <div className="grid lg:grid-cols-[260px_1fr] gap-6">
          <SessionList
            sessions={sessions}
            activeId={sessionId}
            onOpen={(sid) => navigate(`/coach/${sid}`)}
            onDelete={handleDelete}
          />

          <div className="min-w-0">
            {!sessionId ? (
              <>
                <div className="flex justify-end mb-3">
                  <CoachModelPickerChip
                    value={modelPreference}
                    onChange={setModelPreference}
                  />
                </div>
                <EmptyState
                  starters={starters}
                  onPick={createSessionAndSend}
                  onStartBlank={() => navigate("/coach/new")}
                  busy={sending}
                />
              </>
            ) : (
              <>
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <div className="eyebrow text-[#3D1A78] flex items-center gap-1.5">
                      <Sparkles size={12} /> AI Coach
                    </div>
                    <h1
                      className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight mt-1 line-clamp-2"
                      data-testid="coach-session-title"
                    >
                      {session?.title || "New conversation"}
                    </h1>
                  </div>
                  <div className="shrink-0 flex items-center gap-2 flex-wrap justify-end">
                    <CoachModelPickerChip
                      value={modelPreference}
                      onChange={setModelPreference}
                    />
                    <Link
                      to="/coach"
                      className="inline-flex items-center gap-1.5 text-sm px-3 py-2 rounded-full bg-white border border-[#E5E0EE] text-[#3D1A78] hover:bg-[#F5F2FA]"
                      data-testid="coach-new-conversation-btn"
                    >
                      <Plus size={14} /> New
                    </Link>
                  </div>
                </div>

                {session?.safety_flag && <SafetyBanner />}

                {loadingSession ? (
                  <div className="mt-8 text-sm text-[#857E9C] flex items-center gap-2">
                    <Loader2 size={14} className="animate-spin" /> Loading
                    conversation…
                  </div>
                ) : (
                  <div
                    ref={scrollRef}
                    className="mt-4 max-h-[60vh] overflow-y-auto pr-2"
                    data-testid="coach-thread"
                  >
                    {messages.map((m) => (
                      <Bubble
                        key={m.message_id}
                        role={m.role}
                        content={m.content}
                        safety_flag={m.safety_flag}
                      />
                    ))}
                    {sending && (
                      <div className="flex justify-start mb-4" data-testid="coach-typing">
                        <div className="bg-white text-[#857E9C] border border-[#E5E0EE] rounded-2xl rounded-bl-sm px-4 py-3 text-sm flex items-center gap-2">
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#3D1A78] animate-pulse" />
                          <span
                            className="inline-block w-1.5 h-1.5 rounded-full bg-[#3D1A78] animate-pulse"
                            style={{ animationDelay: "150ms" }}
                          />
                          <span
                            className="inline-block w-1.5 h-1.5 rounded-full bg-[#3D1A78] animate-pulse"
                            style={{ animationDelay: "300ms" }}
                          />
                        </div>
                      </div>
                    )}

                    {!sending &&
                      lastAssistant &&
                      Array.isArray(lastAssistant.suggested_followups) && (
                        <Suggestions
                          items={lastAssistant.suggested_followups}
                          onPick={(s) => sendInSession(s)}
                        />
                      )}
                  </div>
                )}

                <ChatComposer onSend={sendInSession} disabled={sending} />
              </>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
