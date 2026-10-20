import { api } from "./api";

// Parent's yes/no on sharing their 4 Communication Style answers with their assigned professional on Align.
const PATH = "/integrations/align-share/communication-readiness";

export const COMM_SHARE_QUESTION =
  "Share these 4 answers privately with your assigned professional on Align? They never go to your co-parent, the court, or any report.";

export const getCommShare = () => api.get(PATH).then((r) => r.data?.choice ?? null);
export const setCommShare = (share) => api.put(PATH, { share }).then((r) => r.data?.choice ?? null);
