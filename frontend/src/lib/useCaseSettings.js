import { useEffect, useState } from "react";

import { useAuth } from "../context/AuthContext";
import { api } from "./api";

// Read on every screen load (never cached), so a change applies the next time a screen opens.
export function useCaseSettings() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!user) return undefined;
    let live = true;
    api
      .get("/case-settings")
      .then((r) => live && setData(r.data))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [user?.user_id]); // eslint-disable-line react-hooks/exhaustive-deps
  return data;
}
