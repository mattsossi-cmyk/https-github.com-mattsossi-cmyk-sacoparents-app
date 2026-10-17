import { useEffect, useRef } from "react";

const FOCUSABLE = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

// The opening view can be hidden before our effect runs, so remember the last focused element.
let lastFocused = null;
document.addEventListener("focusin", (e) => { lastFocused = e.target; }, true);

// Dialog keyboard behaviour: focus moves in, Tab stays inside, Escape closes, focus returns to the opener.
export function useDialogFocus(open, ref, onClose) {
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const box = ref.current;
    if (!open || !box) return undefined;
    const outside = (el) => el && el !== document.body && !box.contains(el) && el;
    // Kept on the dialog node so a re-run of this effect (React StrictMode) keeps the real opener.
    const opener = box.dialogOpener || outside(document.activeElement) || outside(lastFocused) || null;
    box.dialogOpener = opener;
    const openerId = opener?.dataset?.testid;
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
      const items = [...box.querySelectorAll(FOCUSABLE)].filter((el) => el.getClientRects().length > 0);
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
      // The opener may be re-rendered or still hidden for a moment, so retry briefly.
      const restore = (tries) => {
        if (document.activeElement?.closest?.('[role="dialog"]')) return;
        const el = opener && document.contains(opener) ? opener : openerId && document.querySelector(`[data-testid="${CSS.escape(openerId)}"]`);
        if (el?.getClientRects().length) el.focus({ preventScroll: true });
        if (document.activeElement !== el && tries > 0) setTimeout(() => restore(tries - 1), 60);
      };
      restore(8);
    };
  }, [open, ref]);
}
