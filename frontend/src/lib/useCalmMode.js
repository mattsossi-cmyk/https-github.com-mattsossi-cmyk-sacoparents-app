import { useEffect, useState } from "react";

import { useAuth } from "../context/AuthContext";

const query = () => window.matchMedia?.("(prefers-reduced-motion: reduce)");

// Calm Mode: the parent's Account switch, or on by itself when the device asks to reduce motion.
export function useCalmMode() {
  const { user } = useAuth();
  const [phone, setPhone] = useState(() => Boolean(query()?.matches));
  useEffect(() => {
    const q = query();
    if (!q?.addEventListener) return undefined;
    const onChange = (e) => setPhone(e.matches);
    q.addEventListener("change", onChange);
    return () => q.removeEventListener("change", onChange);
  }, []);
  return { calm: phone || user?.calm_mode === true, phone };
}
