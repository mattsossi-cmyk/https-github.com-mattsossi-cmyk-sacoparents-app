import { useEffect, useState } from "react";

import { api } from "./api";

// Gentle in-card reminder while the check-in is not finished; closing it hides it for a week (server-side, per account).
export function useCheckinReminder(open) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (!open) {
      setShow(false);
      return undefined;
    }
    let live = true;
    api
      .get("/family-checkin/reminder")
      .then((r) => live && setShow(!!r.data?.show))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [open]);
  const close = () => {
    setShow(false);
    api.post("/family-checkin/reminder/dismiss").catch(() => {});
  };
  return [show, close];
}
