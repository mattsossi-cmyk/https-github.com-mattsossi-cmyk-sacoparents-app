import { useEffect } from "react";
import { useLocation } from "react-router-dom";

// Scroll to the element named in the URL hash (e.g. /privacy#your-rights) after the page renders.
export function useHashScroll() {
  const { hash } = useLocation();
  useEffect(() => {
    if (!hash) return undefined;
    const t = setTimeout(() => document.getElementById(decodeURIComponent(hash.slice(1)))?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
    return () => clearTimeout(t);
  }, [hash]);
}
