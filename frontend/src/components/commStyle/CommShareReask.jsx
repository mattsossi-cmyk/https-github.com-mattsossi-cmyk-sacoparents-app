import React, { useEffect, useState } from "react";

import { getCommShareStatus } from "../../lib/commShare";
import { CommShareCard } from "./CommShareCard";

// Asks again when a parent's earlier "yes" was given under older sharing wording; until then nothing is shared.
export function CommShareReask() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    getCommShareStatus().then((s) => setOpen(Boolean(s?.reask)), () => {});
  }, []);
  if (!open) return null;
  return <CommShareCard open reask onDone={() => setOpen(false)} />;
}
