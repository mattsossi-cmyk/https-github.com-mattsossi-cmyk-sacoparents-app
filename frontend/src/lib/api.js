import axios from "axios";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Auth is handled exclusively via httpOnly cookies (`auth_token` for JWT
// users, `session_token` for Emergent Google users). withCredentials ensures
// these cookies are sent on every API request.
export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});

// Global handler for guest-gating: any 402 from the backend means
// "Save your work to unlock this feature". Show a single toast with a CTA
// pointing to /claim. The component-level catch can still render its own UI;
// this is just to make sure the user always sees the call-to-action.
let lastUpsellAt = 0;
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error?.response?.status === 402) {
      const now = Date.now();
      if (now - lastUpsellAt > 4000) {
        lastUpsellAt = now;
        toast.error(
          error.response.data?.detail ||
            "Save your work to unlock this feature.",
          {
            action: {
              label: "Save my work",
              onClick: () => {
                window.location.href = "/claim";
              },
            },
            duration: 8000,
          }
        );
      }
    }
    return Promise.reject(error);
  }
);
