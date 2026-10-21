import { api } from "./api";

// Parent's yes/no on sharing their 4 Communication Style answers with SACOparentsAlign.
const PATH = "/integrations/align-share/communication-readiness";

export const COMM_SHARE_WHO =
  "They're seen only by your assigned professionals and, when needed, SA CoParents administrators. They never go to your co-parent, the court, or any report.";
export const COMM_SHARE_QUESTION = `Share these 4 answers with SACOparentsAlign? ${COMM_SHARE_WHO}`;
export const COMM_SHARE_REASK =
  "We've updated who can see these answers, so we're asking again. Until you choose, nothing is shared.";

export const getCommShare = () => api.get(PATH).then((r) => r.data?.choice ?? null);
export const getCommShareStatus = () => api.get(PATH).then((r) => r.data);
export const setCommShare = (share) => api.put(PATH, { share }).then((r) => r.data?.choice ?? null);
export const clearCommShare = () => api.delete(PATH);
