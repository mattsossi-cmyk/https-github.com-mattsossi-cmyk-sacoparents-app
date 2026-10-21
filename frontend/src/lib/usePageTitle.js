import { useEffect } from "react";

export const NEUTRAL_TITLE = "SA CoParents";

export function usePageTitle(title = NEUTRAL_TITLE) {
  useEffect(() => {
    const prev = document.title;
    document.title = title;
    return () => { document.title = prev; };
  }, [title]);
}
