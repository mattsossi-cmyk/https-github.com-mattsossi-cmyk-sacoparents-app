import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, Inbox, Search, Send, RefreshCw, Unplug, Loader2, Mail, Sparkles } from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import Composer from "../components/gmail/GmailComposer";

/**
 * Gmail integration page.
 *
 * Lets a signed-in user connect their Google account, then browse/search
 * their inbox and compose a new email. Backend routes live under
 * /api/oauth/gmail/* and /api/gmail/*. Tokens are stored server-side,
 * Fernet-encrypted — the frontend never sees them.
 */

function MessageDetail({ msg, onBack, onReply, onDraftReply, drafting }) {
  return (
    <section className="card-soft p-6" data-testid="gmail-message-detail">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
        data-testid="gmail-back-to-list"
      >
        <ArrowLeft size={14} /> Back to inbox
      </button>
      <h3 className="font-serif text-2xl text-[#1A1330]">{msg.subject || "(no subject)"}</h3>
      <div className="text-sm text-[#4B4567] mt-1">
        <span className="font-semibold">From:</span> {msg.from}
      </div>
      <div className="text-xs text-[#6E6787]">{msg.date}</div>
      <div className="mt-4 whitespace-pre-wrap text-sm text-[#1A1330] leading-relaxed border-t border-[#E5E0EE] pt-4">
        {msg.body || msg.snippet || "(empty message)"}
      </div>
      <div className="mt-6 flex flex-wrap gap-2">
        <button
          onClick={onReply}
          className="px-4 py-2 rounded-lg bg-[#3D1A78] text-white text-sm font-medium flex items-center gap-2"
          data-testid="gmail-reply-btn"
        >
          <Send size={14} /> Reply
        </button>
        <button
          onClick={onDraftReply}
          disabled={drafting}
          className="px-4 py-2 rounded-lg border border-[#3D1A78] text-[#3D1A78] text-sm font-medium flex items-center gap-2 hover:bg-[#F5F2FA] disabled:opacity-60"
          data-testid="gmail-draft-coach-btn"
        >
          {drafting ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          {drafting ? "Coach is drafting…" : "Draft a co-parenting reply"}
        </button>
      </div>
    </section>
  );
}

export default function Gmail() {
  const [params, setParams] = useSearchParams();
  const [status, setStatus] = useState({ connected: false });
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [composerOpen, setComposerOpen] = useState(false);
  const [composerPrefill, setComposerPrefill] = useState(null);
  const [composerSource, setComposerSource] = useState(null);
  const [drafting, setDrafting] = useState(false);

  const loadStatus = useCallback(async () => {
    setLoadingStatus(true);
    try {
      const { data } = await api.get("/gmail/status");
      setStatus(data);
    } catch {
      setStatus({ connected: false });
    } finally {
      setLoadingStatus(false);
    }
  }, []);

  const loadMessages = useCallback(async (q = "") => {
    setLoadingMessages(true);
    try {
      const { data } = await api.get("/gmail/messages", { params: q ? { q } : {} });
      setMessages(data.messages || []);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not load inbox.");
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (status.connected) loadMessages();
  }, [status.connected, loadMessages]);

  useEffect(() => {
    const connected = params.get("connected");
    const error = params.get("error");
    if (connected === "true") {
      toast.success("Gmail connected.");
      loadStatus();
      params.delete("connected");
      setParams(params, { replace: true });
    } else if (connected === "false" || error) {
      toast.error(error ? `Gmail connect failed: ${error}` : "Gmail connect failed.");
      params.delete("connected");
      params.delete("error");
      setParams(params, { replace: true });
    }
  }, [params, setParams, loadStatus]);

  const connect = async () => {
    try {
      const { data } = await api.get("/oauth/gmail/login");
      window.location.href = data.auth_url;
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not start Gmail connect.");
    }
  };

  const disconnect = async () => {
    if (!window.confirm("Disconnect Gmail? You'll need to re-authorize to use it again.")) return;
    try {
      await api.post("/gmail/disconnect");
      setStatus({ connected: false });
      setMessages([]);
      setSelected(null);
      toast.success("Gmail disconnected.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to disconnect.");
    }
  };

  const openMessage = async (m) => {
    try {
      const { data } = await api.get(`/gmail/messages/${m.id}`);
      setSelected(data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not load message.");
    }
  };

  const startReply = () => {
    if (!selected) return;
    // Extract email address from "Name <email>" format
    const fromMatch = /<([^>]+)>/.exec(selected.from);
    const toEmail = fromMatch ? fromMatch[1] : selected.from;
    setComposerPrefill({
      to: toEmail,
      subject: selected.subject?.startsWith("Re:") ? selected.subject : `Re: ${selected.subject || ""}`,
      body: `\n\n---\nOn ${selected.date}, ${selected.from} wrote:\n> ${(selected.body || selected.snippet || "").split("\n").join("\n> ")}`,
    });
    setComposerSource(selected);
    setComposerOpen(true);
  };

  const draftReplyWithCoach = async () => {
    if (!selected) return;
    setDrafting(true);
    try {
      const { data } = await api.post("/gmail/draft-reply", {
        original_body: selected.body || selected.snippet || "",
        original_subject: selected.subject || "",
        original_from: selected.from || "",
      });
      if (data.safety_flag) {
        toast.warning("Safety concern detected — see the Safety page before replying directly.");
      } else {
        toast.success("Coach-drafted reply ready — review before sending.");
      }
      const fromMatch = /<([^>]+)>/.exec(selected.from);
      const toEmail = fromMatch ? fromMatch[1] : selected.from;
      setComposerPrefill({
        to: toEmail,
        subject: selected.subject?.startsWith("Re:") ? selected.subject : `Re: ${selected.subject || ""}`,
        body: data.draft || "",
      });
      setComposerSource(selected);
      setComposerOpen(true);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "The coach couldn't draft this one.");
    } finally {
      setDrafting(false);
    }
  };

  const startCompose = () => {
    setComposerPrefill(null);
    setComposerSource(null);
    setComposerOpen(true);
  };

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
        <Link
          to="/my-plan"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="gmail-back-link"
        >
          <ArrowLeft size={14} /> Back to My Plan
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight" data-testid="gmail-title">
              Gmail
            </h1>
            <p className="text-[#4B4567] mt-2 max-w-2xl">
              Read, search, and send co-parenting emails without leaving the app.
              Your messages stay in your Google account — we only see them when
              you view them here.
            </p>
          </div>
          {status.connected && (
            <button
              onClick={disconnect}
              className="inline-flex items-center gap-2 text-sm text-[#4B4567] hover:text-[#8B1A1A] px-3 py-2 rounded-lg border border-[#E5E0EE]"
              data-testid="gmail-disconnect-btn"
            >
              <Unplug size={14} /> Disconnect
            </button>
          )}
        </div>

        {loadingStatus ? (
          <div className="mt-10 text-[#6E6787]" data-testid="gmail-loading">Checking your Gmail connection…</div>
        ) : !status.connected ? (
          <section className="card-soft p-8 mt-8" data-testid="gmail-connect-card">
            <div className="text-center">
              <Mail size={40} className="mx-auto text-[#3D1A78]" />
              <h2 className="font-serif text-2xl text-[#1A1330] mt-4">
                Connect your Google account
              </h2>
              <p className="text-[#4B4567] mt-2 max-w-xl mx-auto">
                Gmail is an <strong>optional advanced tool</strong> — you don&apos;t
                need it to complete an assessment, generate a report, or share
                anything with a mediator. Connect it only if you want to read
                and reply to a co-parent&apos;s messages without leaving the app.
              </p>
            </div>

            {/* Plain-language disclosure of what we read / store / retain.
                Placed BEFORE the connect button so a hesitant parent can
                answer the trust question before they click through to
                Google's consent screen. */}
            <div
              className="mt-6 mx-auto max-w-2xl rounded-2xl border border-[#E5E0EE] bg-[#FCFBFE] p-5 text-left text-sm text-[#1A1330]"
              data-testid="gmail-disclosure"
            >
              <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-2">
                What we read, store, and retain
              </div>
              <ul className="space-y-2.5 text-[0.8125rem] leading-relaxed">
                <li className="flex gap-2">
                  <span className="text-[#3D1A78] font-bold shrink-0">Read:</span>
                  <span>
                    Only messages in your inbox that you actively open, plus the
                    unread-count on the INBOX label. We never search, index, or
                    train on your mail.
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-[#3D1A78] font-bold shrink-0">Store:</span>
                  <span>
                    An encrypted OAuth refresh token — that&apos;s it. Message
                    bodies, subjects, and attachments are streamed to your
                    browser on demand and never written to our database.
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-[#3D1A78] font-bold shrink-0">Retain:</span>
                  <span>
                    Your refresh token stays only until you click{" "}
                    <em>Disconnect</em> on this page (or revoke access in your{" "}
                    <a
                      href="https://myaccount.google.com/permissions"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline text-[#3D1A78] font-semibold"
                    >
                      Google Account
                    </a>
                    ). Deleting your SA CoParents account wipes the token
                    immediately.
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-[#3D1A78] font-bold shrink-0">Send:</span>
                  <span>
                    We only send an email when you explicitly click{" "}
                    <em>Send</em> on a message you&apos;ve reviewed. Nothing
                    is sent automatically or in the background.
                  </span>
                </li>
              </ul>
            </div>

            <div className="text-center">
              <button
                onClick={connect}
                className="mt-6 inline-flex items-center gap-2 px-6 py-3 rounded-full bg-[#3D1A78] text-white font-medium hover:bg-[#2A1256]"
                data-testid="gmail-connect-btn"
              >
                <Mail size={16} /> Connect Gmail
              </button>
              <p className="text-xs text-[#6E6787] mt-4">
                You&apos;ll be redirected to Google to grant permission. You
                can revoke access anytime from this page or from your Google
                Account settings.
              </p>
            </div>
          </section>
        ) : selected ? (
          <div className="mt-8">
            <MessageDetail
              msg={selected}
              onBack={() => setSelected(null)}
              onReply={startReply}
              onDraftReply={draftReplyWithCoach}
              drafting={drafting}
            />
          </div>
        ) : (
          <div className="mt-8">
            <div className="flex flex-wrap items-center gap-3 mb-4">
              <div className="flex items-center gap-2 text-sm text-[#4B4567]" data-testid="gmail-account-line">
                <Inbox size={14} className="text-[#3D1A78]" />
                {status.google_email || "Connected"}
              </div>
              <div className="flex-1" />
              <button
                onClick={() => loadMessages(query)}
                className="inline-flex items-center gap-1.5 text-xs text-[#3D1A78] hover:underline"
                data-testid="gmail-refresh-btn"
              >
                <RefreshCw size={12} /> Refresh
              </button>
              <button
                onClick={startCompose}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#3D1A78] text-white text-sm font-medium hover:bg-[#2A1256]"
                data-testid="gmail-compose-btn"
              >
                <Send size={14} /> Compose
              </button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                loadMessages(query);
              }}
              className="flex gap-2 mb-4"
            >
              <div className="relative flex-1">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6E6787]" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search — e.g. from:coparent@example.com or subject:visitation"
                  className="w-full pl-9 pr-3 py-2 border border-[#E5E0EE] rounded-lg text-sm"
                  data-testid="gmail-search-input"
                />
              </div>
              <button
                type="submit"
                className="px-4 py-2 rounded-lg border border-[#3D1A78] text-[#3D1A78] text-sm font-medium hover:bg-[#F5F2FA]"
                data-testid="gmail-search-btn"
              >
                Search
              </button>
            </form>

            <section className="card-soft divide-y divide-[#E5E0EE]" data-testid="gmail-message-list">
              {loadingMessages ? (
                <div className="p-8 text-center text-[#6E6787] flex items-center justify-center gap-2">
                  <Loader2 size={14} className="animate-spin" /> Loading messages…
                </div>
              ) : messages.length === 0 ? (
                <div className="p-8 text-center text-[#6E6787]">No messages found.</div>
              ) : (
                messages.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => openMessage(m)}
                    className="w-full text-left px-5 py-3 hover:bg-[#F5F2FA] flex items-start gap-3"
                    data-testid={`gmail-msg-${m.id}`}
                  >
                    <span
                      className={`mt-1.5 h-2 w-2 rounded-full ${
                        m.unread ? "bg-[#3D1A78]" : "bg-[#E5E0EE]"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-3">
                        <div className={`text-sm truncate ${m.unread ? "font-semibold text-[#1A1330]" : "text-[#4B4567]"}`}>
                          {m.from || "(unknown sender)"}
                        </div>
                        <div className="text-xs text-[#6E6787] shrink-0">{m.date?.split(" ").slice(0, 4).join(" ")}</div>
                      </div>
                      <div className="text-sm text-[#1A1330] truncate">{m.subject || "(no subject)"}</div>
                      <div className="text-xs text-[#6E6787] truncate">{m.snippet}</div>
                    </div>
                  </button>
                ))
              )}
            </section>
          </div>
        )}
      </div>

      {composerOpen && (
        <Composer
          prefill={composerPrefill}
          sourceMessage={composerSource}
          onClose={() => setComposerOpen(false)}
          onSent={() => loadMessages(query)}
        />
      )}
    </AppShell>
  );
}
