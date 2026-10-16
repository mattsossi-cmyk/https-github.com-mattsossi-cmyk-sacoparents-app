import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import "./aiNotice.css";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../lib/api";
import { scanText } from "../../lib/aiNoticeChecks";
import { AiConfirmModal, AiNoticeModal } from "./AiNoticeModals";

const AiNoticeContext = createContext(null);
export const useAiNotice = () => useContext(AiNoticeContext);

// One acknowledgment (stored on the server per user) covers every AI feature; one pop-up and one version.
export function AiNoticeProvider({ children }) {
  const { user, checkAuth, startGuest } = useAuth();
  const [justAcked, setJustAcked] = useState(false);
  const [noticeOpen, setNoticeOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(null);
  const returnRef = useRef(null);
  const skipFocusRef = useRef(false);
  const afterGuestRef = useRef(false);
  const acked = !!user && (user.ai_notice_current || justAcked);

  useEffect(() => setJustAcked(false), [user?.user_id]);

  // A signed-out visitor who tapped an AI box: once the demo session has passed the consent screen, show the AI pop-up.
  useEffect(() => {
    if (!afterGuestRef.current || !user?.consent_current) return;
    afterGuestRef.current = false;
    if (!user.ai_notice_current) setNoticeOpen(true);
  }, [user]);

  // A version change while the page is open: the server refuses (428), so ask again.
  useEffect(() => {
    const id = api.interceptors.response.use(null, (err) => {
      if (err?.response?.status === 428) {
        setJustAcked(false);
        checkAuth().catch(() => {});
        setNoticeOpen(true);
      }
      return Promise.reject(err);
    });
    return () => api.interceptors.response.eject(id);
  }, [checkAuth]);

  const restoreFocus = useCallback(() => {
    const el = returnRef.current;
    if (!el?.focus) return;
    skipFocusRef.current = true;
    el.focus();
    skipFocusRef.current = false;
  }, []);

  const openNotice = useCallback(
    (el) => {
      if (!user) {
        // Signed-out visitors get a demo session first; the consent screen then appears before the AI pop-up.
        if (afterGuestRef.current) return;
        afterGuestRef.current = true;
        startGuest().catch(() => {
          afterGuestRef.current = false;
        });
        return;
      }
      returnRef.current = el || document.activeElement;
      setNoticeOpen(true);
    },
    [user, startGuest]
  );

  const ack = async () => {
    setBusy(true);
    try {
      await api.post("/ai-notice/ack");
      setJustAcked(true);
      setNoticeOpen(false);
      checkAuth().catch(() => {});
      setTimeout(restoreFocus, 0);
    } finally {
      setBusy(false);
    }
  };

  const confirmSend = useCallback(
    async (feature, text) => {
      if (!acked) {
        openNotice();
        return false;
      }
      const labels = scanText(text || "");
      if (!labels.length) return true;
      returnRef.current = document.activeElement;
      const go = await new Promise((resolve) => setConfirm({ labels, resolve }));
      setConfirm(null);
      if (!go) {
        setTimeout(restoreFocus, 0);
        return false;
      }
      // Only the feature and category labels are recorded, never the text.
      await api.post("/ai-notice/send-anyway", { feature, labels }).catch(() => {});
      return true;
    },
    [acked, openNotice, restoreFocus]
  );

  const value = useMemo(
    () => ({ acked, openNotice, confirmSend, shouldSkipFocus: () => skipFocusRef.current }),
    [acked, openNotice, confirmSend]
  );
  return (
    <AiNoticeContext.Provider value={value}>
      {children}
      {noticeOpen && (
        <AiNoticeModal
          busy={busy}
          onContinue={ack}
          onClose={() => {
            setNoticeOpen(false);
            setTimeout(restoreFocus, 0);
          }}
        />
      )}
      {confirm && <AiConfirmModal labels={confirm.labels} onEdit={() => confirm.resolve(false)} onSendAnyway={() => confirm.resolve(true)} />}
    </AiNoticeContext.Provider>
  );
}
