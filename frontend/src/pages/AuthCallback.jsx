import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const hash = window.location.hash || "";
    const params = new URLSearchParams(hash.startsWith("#") ? hash.slice(1) : hash);
    const sessionId = params.get("session_id");

    if (!sessionId) {
      navigate("/login", { replace: true });
      return;
    }

    (async () => {
      try {
        await api.post(
          "/auth/google/session",
          {},
          { headers: { "X-Session-ID": sessionId } }
        );
        await checkAuth();
        navigate("/dashboard", { replace: true });
      } catch (err) {
        console.error("Google session exchange failed:", err);
        navigate("/login", { replace: true });
      }
    })();
  }, [navigate, checkAuth]);

  return (
    <div className="min-h-screen gentle-bg grid place-items-center">
      <div className="text-center">
        <div className="text-xs uppercase tracking-[0.25em] text-[#8A9A92] mb-3">
          Securing your session
        </div>
        <div className="font-serif text-2xl text-[#2A3631]">One moment…</div>
      </div>
    </div>
  );
}
