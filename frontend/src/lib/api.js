import axios from "axios";

const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  withCredentials: true,
  timeout: 45000,
});

export function formatApiError(e) {
  const detail = e?.response?.data?.detail;
  if (detail == null) {
    if (!e?.response && (e?.code === "ERR_NETWORK" || e?.code === "ECONNABORTED" || /network error|timeout/i.test(e?.message || ""))) {
      return "We couldn't reach the server (connection dropped or timed out). Please check your connection and try again.";
    }
    return e?.message || "Something went wrong. Please try again.";
  }
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((x) => (x && typeof x.msg === "string" ? x.msg : JSON.stringify(x))).join(" ");
  }
  if (typeof detail === "object" && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export default api;
