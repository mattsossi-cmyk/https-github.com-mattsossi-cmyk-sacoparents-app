import { useEffect, useRef } from "react";
import { LogOut, ShieldAlert } from "lucide-react";

const EXIT_URL = "https://www.weather.com";
const KEYS = ["screening", "safety", "align-safety"];

export function quickExit() {
  try {
    [sessionStorage, localStorage].forEach((s) => Object.keys(s).forEach((k) => { if (KEYS.some((p) => k.toLowerCase().includes(p))) s.removeItem(k); }));
    sessionStorage.setItem("align-quick-exit", "1");
  } catch { /* storage unavailable */ }
  window.location.replace(EXIT_URL);
}

export function QuickExitBar({ notice }) {
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
    <div className="sticky top-0 z-50 border-b border-[#3D1A78]/20 bg-[#3D1A78] text-white" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }} data-testid="quick-exit-bar">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-2 sm:px-6">
        <p className="flex items-center gap-2 text-xs text-white/90" data-testid="safe-device-notice"><ShieldAlert className="h-4 w-4 shrink-0" />{notice || "Use a device your co-parent cannot see. Quick Exit (or Escape twice) leaves this page immediately."}</p>
        <button type="button" onClick={quickExit} className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-white px-4 py-1.5 text-xs font-bold text-[#3D1A78] shadow hover:bg-white/90" data-testid="quick-exit-btn"><LogOut className="h-3.5 w-3.5" /> Quick Exit</button>
      </div>
    </div>
  );
}
