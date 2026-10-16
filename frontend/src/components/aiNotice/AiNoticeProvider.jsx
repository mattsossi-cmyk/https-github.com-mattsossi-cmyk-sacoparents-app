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
  const [needConsent, setNeedConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [ackError, setAckError] = useState("");
  const [confirm, setConfirm] = useState(null);
  const returnRef = useRef(null);
  const skipFocusRef = useRef(false);
  const afterConsentRef = useRef(false);
  const scrollRef = useRef(0);
  const userRef = useRef(user);
  userRef.current = user;
  // AI stays locked until "Before you continue" is accepted too.
  const acked = !!user && !!user.consent_current && (user.ai_notice_current || justAcked);

  useEffect(() => setJustAcked(false), [user?.user_id]);

  // "Before you continue" comes first; once it's accepted, the AI pop-up opens by itself (same scroll spot).
  const askConsent = useCallback(() => {
    afterConsentRef.current = true;
    scrollRef.current = window.scrollY;
    setNeedConsent(true);
  }, []);

  const showNotice = useCallback(() => {
    if (userRef.current && !userRef.current.consent_current) {
      askConsent();
      return;
    }
    setAckError("");
    setNoticeOpen(true);
  }, [askConsent]);

  useEffect(() => {
    if (!user) {
      afterConsentRef.current = false;
      setNeedConsent(false);
      return;
    }
    if (!afterConsentRef.current || !user.consent_current) return;
    afterConsentRef.current = false;
    setNeedConsent(false);
    requestAnimationFrame(() => window.scrollTo(0, scrollRef.current));
    if (!user.ai_notice_current) showNotice();
  }, [user, showNotice]);

  // A version change while the page is open: the server refuses (428), so ask again.
  useEffect(() => {
    const id = api.interceptors.response.use(null, (err) => {
      if (err?.response?.status === 428) {
        setJustAcked(false);
        checkAuth().catch(() => {});
        showNotice();
      }
      return Promise.reject(err);
    });
    return () => api.interceptors.response.eject(id);
  }, [checkAuth, showNotice]);

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
        if (afterConsentRef.current) return;
        askConsent();
        startGuest().catch(() => {
          afterConsentRef.current = false;
          setNeedConsent(false);
        });
        return;
      }
      returnRef.current = el || document.activeElement;
      showNotice();
    },
    [user, startGuest, showNotice, askConsent]
  );

  const ack = async () => {
    setBusy(true);
    setAckError("");
    try {
      await api.post("/ai-notice/ack");
      setJustAcked(true);
      setNoticeOpen(false);
      checkAuth().catch(() => {});
      setTimeout(restoreFocus, 0);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setAckError(typeof detail === "string" ? detail : "Couldn't save that. Please try again.");
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
    () => ({ acked, needConsent, openNotice, confirmSend, shouldSkipFocus: () => skipFocusRef.current }),
    [acked, needConsent, openNotice, confirmSend]
  );
  return (
    <AiNoticeContext.Provider value={value}>
      {children}
      {noticeOpen && (
        <AiNoticeModal
          busy={busy}
          error={ackError}
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
