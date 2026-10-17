/**
 * GmailMiniInbox — dashboard card that surfaces the 5 most recent
 * inbox messages so a parent doesn't have to leave the app to read a
 * co-parent's reply.
 *
 * States rendered from a single component:
 *   - Loading (initial fetch of /api/gmail/status)
 *   - Disconnected → "Connect Gmail" CTA linking to the full page.
 *   - Empty inbox → "Nothing new" message.
 *   - Connected + messages → 5-row list; tap a row to expand the body
 *     inline; tap Reply to open the shared GmailComposer with a
 *     Coach-drafted reply already pre-selectable.
 *   - Errors are toasted; the card stays usable.
 *
 * All backend calls use the shared `api` client. Tokens are stored
 * server-side, Fernet-encrypted — the frontend never sees them.
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Inbox, Loader2, Mail, RefreshCw, Reply, ExternalLink, ChevronRight, ChevronDown,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";
import GmailComposer from "./gmail/GmailComposer";

const REFRESH_MS = 30_000;
const MAX_MESSAGES = 5;
const SNIPPET_MAX = 110;

/** Pull just the "Alice <alice@x>" display name portion; fall back to the address. */
function extractSender(from) {
  if (!from) return "Unknown";
  const m = /^\s*"?([^"<]+?)"?\s*</.exec(from);
  return (m ? m[1] : from).trim();
}

/** Loose "3 min ago"-style formatter tolerant of the varied Date header shapes Gmail returns. */
function relativeTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const seconds = Math.round((Date.now() - d.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString();
}

function truncate(s, n) {
  if (!s) return "";
  return s.length <= n ? s : `${s.slice(0, n - 1).trimEnd()}…`;
}

function ConnectPrompt() {
  return (
    <div
      className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 shadow-sm"
      data-testid="gmail-mini-connect"
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-10 h-10 rounded-full bg-[#F5F1FB] text-[#3D1A78] flex items-center justify-center">
          <Mail size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Mini Inbox
          </div>
          <div className="font-serif text-lg text-[#1A1330] mt-0.5">
            Read your co-parent&apos;s replies without leaving the app
          </div>
          <p className="mt-1 text-xs text-[#4B4567]">
            Connect your Gmail once and the last five messages will
            appear right here. Drafts are still assisted by the
            co-parenting coach. Your tokens stay server-side, encrypted.
          </p>
          <Link
            to="/gmail"
            className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#3D1A78] text-white text-xs font-semibold hover:bg-[#4E2792]"
            data-testid="gmail-mini-connect-cta"
          >
            <Mail size={12} /> Connect Gmail
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function GmailMiniInbox() {
  const [status, setStatus] = useState(null);   // {connected, google_email}
  const [messages, setMessages] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [expandedBody, setExpandedBody] = useState(null); // {id, subject, from, body}
  const [expandLoading, setExpandLoading] = useState(false);
  const [replyTarget, setReplyTarget] = useState(null);   // full message dict

  const loadInbox = useCallback(async () => {
    setRefreshing(true);
    try {
      // Fetch messages + inbox-wide unread count in parallel. The
      // count endpoint is O(1) (INBOX label) so it doesn't slow
      // the panel down.
      const [msgs, unread] = await Promise.all([
        api.get("/gmail/messages", { params: { max_results: MAX_MESSAGES } }),
        api.get("/gmail/unread-count").catch(() => ({ data: null })),
      ]);
      setMessages(Array.isArray(msgs.data?.messages) ? msgs.data.messages : []);
      setUnreadCount(Number(unread?.data?.unread_messages) || 0);
    } catch (err) {
      // Token expired or gmail scope revoked — surface once, then let
      // the user retry via the refresh button.
      logError("mini inbox load failed:", err);
      if (err?.response?.status === 401) {
        setStatus({ connected: false });
      } else {
        toast.error(err?.response?.data?.detail || "Couldn't read your inbox right now.");
      }
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.get("/gmail/status");
        if (cancelled) return;
        setStatus(data || null);
        if (data?.connected) {
          await loadInbox();
        }
      } catch (err) {
        logError("mini inbox status failed:", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [loadInbox]);

  useEffect(() => {
    if (!status?.connected) return undefined;
    const t = setInterval(loadInbox, REFRESH_MS);
    return () => clearInterval(t);
  }, [status?.connected, loadInbox]);

  const expandMessage = async (msg) => {
    if (expandedId === msg.id) {
      setExpandedId(null);
      setExpandedBody(null);
      return;
    }
    setExpandedId(msg.id);
    setExpandedBody(null);
    setExpandLoading(true);
    try {
      const { data } = await api.get(`/gmail/messages/${msg.id}`);
      setExpandedBody(data || null);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't open that message.");
      setExpandedId(null);
    } finally {
      setExpandLoading(false);
    }
  };

  const openReply = (full) => {
    // Convert Gmail's plain-text body → quoted reply body so the
    // co-parent conversation stays threaded even for parents who
    // don't have their client set up to auto-quote.
    const quoted = (full.body || "")
      .split("\n")
      .slice(0, 30) // keep it short — full history is on gmail if needed
      .map((line) => `> ${line}`)
      .join("\n");
    const subject = full.subject?.startsWith("Re: ") ? full.subject : `Re: ${full.subject || ""}`;
    setReplyTarget({
      ...full,
      _prefill: {
        to: full.from || "",
        subject,
        body: `\n\n---\nOn ${full.date || "a previous message"}, ${full.from || ""} wrote:\n${quoted}`,
      },
    });
  };

  if (loading) {
    return (
      <div
        className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 shadow-sm flex items-center gap-2 text-sm text-[#4B4567]"
        data-testid="gmail-mini-loading"
      >
        <Loader2 size={14} className="animate-spin" /> Checking your Gmail…
      </div>
    );
  }

  if (!status?.connected) {
    return <ConnectPrompt />;
  }

  return (
    <div
      className="rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-6 shadow-sm"
      data-testid="gmail-mini-inbox"
    >
      <div className="flex items-start justify-between flex-wrap gap-2">
        <div className="min-w-0">
          <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78]">
            Mini Inbox
          </div>
          <div className="font-serif text-lg text-[#1A1330] mt-0.5 flex items-center gap-2 flex-wrap">
            <Inbox size={16} className="text-[#3D1A78]" />
            Recent messages
            {unreadCount > 0 && (
              <span
                className="inline-flex items-center justify-center min-w-[20px] h-[20px] px-1.5 rounded-full bg-[#C13030] text-white text-[0.625rem] font-bold tabular-nums"
                title={`${unreadCount} unread message${unreadCount === 1 ? "" : "s"} in your inbox`}
                aria-label={`${unreadCount} unread`}
                data-testid="gmail-mini-unread-badge"
              >
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
            {status?.google_email && (
              <span className="text-[0.625rem] font-normal text-[#6A5799] font-sans truncate max-w-[180px] sm:max-w-none">
                {status.google_email}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={loadInbox}
            disabled={refreshing}
            className="inline-flex items-center gap-1 text-xs text-[#3D1A78] hover:underline px-2 py-1 disabled:opacity-60"
            data-testid="gmail-mini-refresh"
            title="Refresh"
          >
            {refreshing ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
            Refresh
          </button>
          <Link
            to="/gmail"
            className="inline-flex items-center gap-1 text-xs text-[#3D1A78] hover:underline px-2 py-1"
            data-testid="gmail-mini-open-full"
          >
            Open full Gmail <ExternalLink size={11} />
          </Link>
        </div>
      </div>

      {messages.length === 0 ? (
        <div
          className="mt-4 rounded-2xl border border-dashed border-[#E5E0EE] bg-[#FCFBFE] p-4 text-sm text-[#4B4567]"
          data-testid="gmail-mini-empty"
        >
          Nothing new in your inbox. Enjoy the quiet.
        </div>
      ) : (
        <ul className="mt-4 divide-y divide-[#F1EEF7]" data-testid="gmail-mini-list">
          {messages.map((m) => {
            const isOpen = expandedId === m.id;
            const sender = extractSender(m.from);
            const when = relativeTime(m.date);
            return (
              <li key={m.id} data-testid={`gmail-mini-item-${m.id}`}>
                <button
                  type="button"
                  onClick={() => expandMessage(m)}
                  className="w-full text-left py-3 flex items-start gap-3 hover:bg-[#FAF8FD] rounded-lg px-2 -mx-2"
                  data-testid={`gmail-mini-row-${m.id}`}
                >
                  <div className="shrink-0 mt-0.5 text-[#3D1A78]">
                    {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <span
                        className={`text-sm truncate ${m.unread ? "font-bold text-[#1A1330]" : "font-semibold text-[#1A1330]"}`}
                      >
                        {sender}
                      </span>
                      <span className="text-[0.625rem] text-[#6A5799] shrink-0">{when}</span>
                    </div>
                    <div className="text-xs text-[#1A1330] truncate mt-0.5">
                      {m.subject || <span className="italic text-[#6A5799]">(no subject)</span>}
                    </div>
                    <div className="text-[0.6875rem] text-[#4B4567] mt-0.5">
                      {truncate(m.snippet, SNIPPET_MAX)}
                    </div>
                  </div>
                </button>
                {isOpen && (
                  <div
                    className="ml-6 mb-3 rounded-2xl border border-[#E5E0EE] bg-[#FCFBFE] p-4"
                    data-testid={`gmail-mini-body-${m.id}`}
                  >
                    {expandLoading || !expandedBody ? (
                      <div className="text-xs text-[#4B4567] inline-flex items-center gap-1.5">
                        <Loader2 size={12} className="animate-spin" /> Opening…
                      </div>
                    ) : (
                      <>
                        <div className="text-xs text-[#6A5799]">
                          From <span className="text-[#1A1330]">{expandedBody.from}</span>
                        </div>
                        <pre className="mt-2 whitespace-pre-wrap break-words text-xs text-[#1A1330] font-sans max-h-64 overflow-y-auto">
                          {expandedBody.body || expandedBody.snippet || ""}
                        </pre>
                        <div className="mt-3 flex items-center gap-2 justify-end">
                          <button
                            type="button"
                            onClick={() => openReply(expandedBody)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#3D1A78] text-white text-xs font-semibold hover:bg-[#4E2792]"
                            data-testid={`gmail-mini-reply-${m.id}`}
                          >
                            <Reply size={12} /> Reply
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {replyTarget && (
        <GmailComposer
          prefill={replyTarget._prefill}
          sourceMessage={replyTarget}
          onClose={() => setReplyTarget(null)}
          onSent={loadInbox}
        />
      )}
    </div>
  );
}
