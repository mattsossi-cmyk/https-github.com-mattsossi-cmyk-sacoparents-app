import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Auth is handled exclusively via httpOnly cookies (`auth_token` for JWT
// users, `session_token` for Emergent Google users). withCredentials ensures
// these cookies are sent on every API request.
export const api = axios.create({
  baseURL: API,
  withCredentials: true,
});
