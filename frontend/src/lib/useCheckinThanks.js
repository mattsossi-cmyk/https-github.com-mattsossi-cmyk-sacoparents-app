import { useEffect, useState } from "react";

import { api } from "./api";

// Shows the thank-you note once per account: the server marks it seen as soon as it is shown.
export function useCheckinThanks(done) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (!done) return undefined;
    let live = true;
    api
      .get("/family-checkin/thanks")
      .then((r) => {
        if (!live || !r.data?.show) return;
        setShow(true);
        api.post("/family-checkin/thanks/seen").catch(() => {});
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [done]);
  return [show, () => setShow(false)];
}
