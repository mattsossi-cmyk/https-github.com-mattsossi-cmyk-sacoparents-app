import { useEffect } from "react";
import { useLocation } from "react-router-dom";

// Safety-sensitive pages: kept out of search results and never pass their address on to sites a parent opens from them.
const SENSITIVE = ["/self-journey", "/start-with-safety", "/safety-first", "/journey-library"];

const isSensitive = (pathname) => SENSITIVE.some((p) => pathname === p || pathname.startsWith(`${p}/`));

function setMeta(name, content) {
  let el = document.head.querySelector(`meta[name="${name}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute("name", name);
    document.head.appendChild(el);
  }
  const before = el.getAttribute("content");
  el.setAttribute("content", content);
  return () => (before === null ? el.remove() : el.setAttribute("content", before));
}

export default function PrivacyGuard() {
  const { pathname } = useLocation();
  const sensitive = isSensitive(pathname);
  useEffect(() => {
    if (!sensitive) return undefined;
    const undo = [setMeta("robots", "noindex, nofollow"), setMeta("referrer", "no-referrer")];
    document.documentElement.dataset.privacyGuard = "on";
    return () => {
      undo.forEach((u) => u());
      delete document.documentElement.dataset.privacyGuard;
    };
  }, [sensitive]);
  return null;
}
