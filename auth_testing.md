# Auth Testing Playbook (Emergent Google Auth)
- Cookie name: `session_token` (httpOnly, secure, samesite=none, path=/)
- Backend resolves user via cookie OR Bearer token
- For testing protected endpoints, you can create a synthetic session:

```
mongosh "$MONGO_URL" --eval '
use("test_database");
var userId = "user_test" + Date.now();
var sessionToken = "test_sess_" + Date.now();
db.users.insertOne({user_id: userId, email: "test.google@example.com", name: "Test G", auth_method:"google", picture: null, hashed_password: null, children: [], custody_situation: "", mediation_date: null, created_at: new Date().toISOString()});
db.user_sessions.insertOne({user_id: userId, session_token: sessionToken, expires_at: new Date(Date.now()+7*24*60*60*1000).toISOString(), created_at: new Date().toISOString()});
print("session: " + sessionToken);
print("user_id: " + userId);
'
```

Then call `/api/auth/me` with `Authorization: Bearer <session>` or with `Cookie: session_token=<session>`.
