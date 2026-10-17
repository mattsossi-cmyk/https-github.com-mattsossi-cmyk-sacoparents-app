# Auth testing playbook (Emergent Google sign-in, this app)

This app uses its own JWT cookies (`access_token` / `refresh_token`, set by `auth.set_auth_cookies`). Google sign-in does NOT create a separate
`user_sessions` store: `POST /api/auth/google/session {session_id}` exchanges the Emergent session id for the user's email, finds an EXISTING
user with role `professional` or `admin`, and sets the same cookies password login sets. No account is ever created by Google sign-in.

## Backend
- `GET  /api/auth/google/config` → `{"enabled": true, "roles": ["professional","admin"]}`
- `POST /api/auth/google/session` body `{"session_id": "..."}`
  - 200 + cookies + public user → existing professional/admin
  - 403 → no account for that email, or a parent / judge account, or unapproved professional
  - 401 → Emergent could not verify the session id
  - 502 → Emergent session-data endpoint unreachable

## Frontend
- `/auth` (login mode, non-parent) shows `data-testid="google-signin-btn"` → redirects to `https://auth.emergentagent.com/?redirect=<origin>/dashboard`.
- Return URL `/dashboard#session_id=...` is caught synchronously in `AppRoutes` (`useLocation().hash`) → `AuthCallback` posts to the backend, calls `refresh()`, navigates to `/dashboard`.
- `AuthProvider` skips `/auth/me` when the hash contains `session_id=`.

## Test without a real Google account
The Emergent session-data call cannot be faked end-to-end from here. Test the gate logic with a monkeypatched `httpx` response
(see `backend/tests/test_iter115_google_models_disclosure.py`), and test password login unchanged. Real Google round-trip: owner signs in with
`mattsossi@bsossi.com` (admin) on the preview URL.

## Test identities
- Admin/owner: mattsossi@bsossi.com (role admin) — Google sign-in allowed.
- Parents: never allowed via Google (403).
