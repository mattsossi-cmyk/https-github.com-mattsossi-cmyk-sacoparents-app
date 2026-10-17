import { useEffect, useRef } from "react";

const FOCUSABLE = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

// Dialog keyboard behaviour: focus moves in, Tab stays inside, Escape closes, focus returns to the opener.
export function useDialogFocus(open, ref, onClose) {
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const box = ref.current;
    if (!open || !box) return undefined;
    const opener = document.activeElement;
    // Another dialog on top (e.g. the AI notice) owns the keyboard while it has focus.
    const owns = () => box.contains(document.activeElement) || document.activeElement === document.body;
    box.focus({ preventScroll: true });
    const onKey = (e) => {
      if (!owns()) return;
      if (e.key === "Escape") {
        e.stopPropagation();
        closeRef.current();
        return;
      }
      if (e.key !== "Tab") return;
      const items = [...box.querySelectorAll(FOCUSABLE)].filter((el) => el.offsetParent !== null);
      if (!items.length) return e.preventDefault();
      const first = items[0];
      const last = items[items.length - 1];
      const at = document.activeElement;
      if (e.shiftKey && (at === first || at === box)) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && at === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (opener?.focus && document.contains(opener)) opener.focus({ preventScroll: true });
    };
  }, [open, ref]);
}
