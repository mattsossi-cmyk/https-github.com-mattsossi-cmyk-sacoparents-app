import { useEffect, useRef } from "react";
import { LogOut, ShieldAlert } from "lucide-react";

const EXIT_URL = "https://www.weather.com";
const KEYS = ["screening", "safety", "align-safety"];

export function quickExit() {
  try {
    [sessionStorage, localStorage].forEach((s) => Object.keys(s).forEach((k) => { if (KEYS.some((p) => k.toLowerCase().includes(p))) s.removeItem(k); }));
    sessionStorage.setItem("align-quick-exit", "1");
  } catch { /* storage unavailable */ }
  try {
    // End the session on the server (all devices) so a copied cookie no longer works; keepalive lets it finish after navigation.
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/logout?everywhere=true`, { method: "POST", credentials: "include", keepalive: true }).catch(() => {});
  } catch { /* ignore */ }
  window.location.replace(EXIT_URL);
}

export function QuickExitBar({ notice, variant = "purple", label }) {
  const presses = useRef(0);
  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== "Escape") return;
      presses.current += 1;
      if (presses.current >= 2) quickExit();
      setTimeout(() => { presses.current = 0; }, 1500);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return (
    <div className={`sticky top-0 z-50 border-b font-jakarta text-white ${variant === "red" ? "border-red-800 bg-red-700" : "border-[#3D1A78]/20 bg-[#3D1A78]"}`} data-testid="quick-exit-bar" role="region" aria-label="Quick exit">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-2 sm:px-6">
        <div className="min-w-0">
          {label && <p className="text-xs font-bold uppercase tracking-widest" data-testid="quick-exit-label">{label}</p>}
          <p className="flex items-center gap-2 text-xs text-white/90" data-testid="safe-device-notice"><ShieldAlert className="h-4 w-4 shrink-0" aria-hidden="true" />{notice || "Use a device your co-parent cannot see. Quick Exit (or Escape twice) leaves this page immediately."}</p>
        </div>
        <button type="button" onClick={quickExit} className={`inline-flex shrink-0 items-center gap-1.5 rounded-full bg-white px-4 py-1.5 text-xs font-bold shadow hover:bg-white/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white ${variant === "red" ? "text-red-700" : "text-[#3D1A78]"}`} data-testid="quick-exit-btn" aria-label="Quick Exit — leave this page immediately"><LogOut className="h-3.5 w-3.5" aria-hidden="true" /> Quick Exit</button>
      </div>
    </div>
  );
}
