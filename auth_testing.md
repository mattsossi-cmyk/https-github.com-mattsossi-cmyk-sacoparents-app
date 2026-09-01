# Auth Testing Playbook

## Step 1: MongoDB Verification
```
mongosh
use test_database
db.users.find({role: "admin"}).pretty()
db.users.findOne({role: "admin"}, {password_hash: 1})
```
Verify: bcrypt hash starts with `$2b$`, indexes exist on users.email (unique) and login_attempts.identifier. Expired password-reset codes are validated and deleted by the reset endpoint itself (no TTL index).

## Step 2: API Testing
```
curl -c cookies.txt -X POST http://localhost:8001/api/auth/login -H "Content-Type: application/json" -d '{"email":"mattsossi@bsossi.com","password":"CoParents2026!"}'
cat cookies.txt
curl -b cookies.txt http://localhost:8001/api/auth/me
```
Login should return the user object and set `access_token` + `refresh_token` cookies. The `/me` call should return the same user using those cookies.

## Step 3: Refresh flow
```
curl -b cookies.txt -c cookies.txt -X POST http://localhost:8001/api/auth/refresh
curl -b cookies.txt http://localhost:8001/api/auth/me
```

## Step 4: Register a new user
```
curl -c cookies2.txt -X POST http://localhost:8001/api/auth/register -H "Content-Type: application/json" -d '{"name":"Test Parent","email":"parent@test.com","password":"testpass123","role":"parent"}'
```

## Step 5: Password reset flow
```
curl -X POST http://localhost:8001/api/auth/forgot-password -H "Content-Type: application/json" -d '{"email":"mattsossi@bsossi.com"}'
```
Always returns 200 (no account enumeration). A 6-digit code is emailed via the managed
Resend proxy and stored as a SHA-256 hash in `password_resets` (10-min TTL index).
See /app/memory/test_credentials.md for how to set a known code hash for testing.
```
curl -X POST http://localhost:8001/api/auth/reset-password -H "Content-Type: application/json" -d '{"email":"mattsossi@bsossi.com","code":"123456","new_password":"newpass123"}'
```
Wrong/expired code returns 400. Successful reset updates the bcrypt hash, deletes the
code (single-use), and clears login lockouts for that email.
