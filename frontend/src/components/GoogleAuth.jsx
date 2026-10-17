import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export const startGoogleSignIn = () => {
  const redirectUrl = window.location.origin + "/dashboard";
  window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
};

export const AuthCallback = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const done = useRef(false);
  useEffect(() => {
    if (done.current) return;
    done.current = true;
    const sid = new URLSearchParams(location.hash.replace(/^#/, "")).get("session_id");
    window.history.replaceState(null, "", location.pathname);
    api.post("/auth/google/session", { session_id: sid })
      .then(async () => { await refresh(); navigate("/dashboard", { replace: true }); })
      .catch((e) => { toast.error(formatApiError(e)); navigate("/auth", { replace: true }); });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return <div className="min-h-screen bg-background" data-testid="google-auth-callback" />;
};
