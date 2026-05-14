/* BiometricGate
   On native (iOS/Android via Capacitor): when the user is authenticated AND
   the app comes to the foreground, require Face ID / Touch ID before showing
   protected content. On the web, this component is a transparent passthrough.

   The gate is unlocked once per app-foreground session, not per route. */
import React, { useCallback, useEffect, useState } from "react";
import { isNative, isBiometricAvailable, requireBiometric } from "../lib/native";
import { useAuth } from "../context/AuthContext";
import { ShieldCheck, Lock } from "lucide-react";

export default function BiometricGate({ children }) {
  const { user } = useAuth();
  const [available, setAvailable] = useState(false);
  const [locked, setLocked] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");

  // Web: instantly pass-through. Native: probe biometric capability.
  useEffect(() => {
    if (!isNative()) {
      setLocked(false);
      return;
    }
    isBiometricAvailable().then((ok) => {
      setAvailable(ok);
      if (!ok) setLocked(false); // no biometric on device → don't trap user
    });
  }, []);

  // Re-lock when app returns to foreground.
  useEffect(() => {
    if (!isNative()) return undefined;
    let listener;
    (async () => {
      try {
        const { App } = await import("@capacitor/app");
        listener = await App.addListener("appStateChange", ({ isActive }) => {
          if (isActive && user) setLocked(true);
        });
      } catch {
        /* ignore */
      }
    })();
    return () => {
      try {
        listener?.remove?.();
      } catch {
        /* ignore */
      }
    };
  }, [user]);

  const unlock = useCallback(async () => {
    setChecking(true);
    setError("");
    const ok = await requireBiometric("Unlock your SA Coparents prep");
    setChecking(false);
    if (ok) setLocked(false);
    else setError("Authentication failed. Please try again.");
  }, []);

  // Auto-prompt once when locked + user authenticated.
  useEffect(() => {
    if (locked && available && user && !checking) {
      unlock();
    }
  }, [locked, available, user, checking, unlock]);

  // Pass through when: web, no user, no biometric available, or unlocked.
  if (!locked || !user || !available) return children;

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#FDFAF3] p-6">
      <div className="card-soft p-8 text-center max-w-sm w-full">
        <div className="w-14 h-14 rounded-full bg-[#849D8E]/15 text-[#5C7A6A] grid place-items-center mx-auto mb-5">
          <Lock size={22} />
        </div>
        <div className="eyebrow mb-2">Locked</div>
        <h2 className="font-serif text-2xl text-[#2A3631] mb-3">
          Welcome back, {user.name?.split(" ")[0] || "friend"}
        </h2>
        <p className="text-sm text-[#5C6B64] mb-6">
          For your privacy, please use Face ID or Touch ID to unlock your prep.
        </p>
        <button
          onClick={unlock}
          disabled={checking}
          className="btn-sage inline-flex items-center gap-2"
          data-testid="biometric-unlock-button"
        >
          <ShieldCheck size={16} />
          {checking ? "Checking…" : "Unlock"}
        </button>
        {error && (
          <p className="text-xs text-[#C28771] mt-4" data-testid="biometric-error">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
