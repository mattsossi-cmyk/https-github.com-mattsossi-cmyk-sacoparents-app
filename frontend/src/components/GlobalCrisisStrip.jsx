import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { SafetyCrisisStrip } from "../pages/portal/SafetyCrisisStrip";

// The parent portal (home, Self Journey, Journey page) places its own bar above its bottom tabs.
const PORTAL_PATHS = ["/", "/dashboard", "/journey"];

// Red "In danger?" bar on every signed-in screen.
export default function GlobalCrisisStrip() {
  const { user } = useAuth();
  const { pathname } = useLocation();
  // The Journey library and the reading Self Journey have their own help bar, so it isn't doubled there.
  const readingPage =
    pathname.startsWith("/journey-library") || (pathname.startsWith("/self-journey") && !pathname.startsWith("/self-journey/guided"));
  const show = Boolean(user) && !PORTAL_PATHS.includes(pathname.replace(/\/+$/, "") || "/") && !readingPage;
  useEffect(() => {
    if (!show) return undefined;
    document.body.classList.add("has-crisis-strip");
    return () => document.body.classList.remove("has-crisis-strip");
  }, [show]);
  return show ? <SafetyCrisisStrip bottom="bottom-0" /> : null;
}
