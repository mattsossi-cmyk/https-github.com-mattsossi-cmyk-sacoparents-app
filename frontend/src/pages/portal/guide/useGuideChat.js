import { useEffect, useRef, useState } from "react";

import { api } from "../../../lib/api";

// Multi-turn Guide chat: one ongoing server-stored session per parent. `extra` is sent with every message.
export function useGuideChat(path, extra) {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const extraRef = useRef(extra);
  extraRef.current = extra;

  useEffect(() => {
    api
      .get(path)
      .then(({ data }) => {
        setSessionId(data.session_id);
        setMessages(data.messages || []);
      })
      .catch(() => {});
  }, [path]);

  const send = async (message) => {
    setMessages((m) => [...m, { role: "user", text: message }]);
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post(path, { message, session_id: sessionId, ...extraRef.current });
      setSessionId(data.session_id);
      setMessages((m) => [...m, { role: "guide", text: data.reply }]);
      return true;
    } catch (e) {
      const d = e?.response?.data?.detail;
      setMessages((m) => m.slice(0, -1));
      setError(typeof d === "string" ? d : "Your Guide couldn't reply right now. Please try again.");
      return false;
    } finally {
      setBusy(false);
    }
  };

  // Starts a fresh saved session so a reload shows the new chat, not the old one.
  const reset = () => {
    setSessionId(null);
    setMessages([]);
    setError("");
    api
      .post(`${path}/new`)
      .then(({ data }) => setSessionId(data.session_id))
      .catch(() => {});
  };

  return { messages, busy, error, send, reset };
}
