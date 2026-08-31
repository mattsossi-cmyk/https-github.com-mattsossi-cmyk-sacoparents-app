# Auth Testing Playbook

## Step 1: MongoDB Verification
```
mongosh
use test_database
db.users.find({role: "admin"}).pretty()
db.users.findOne({role: "admin"}, {password_hash: 1})
```
Verify: bcrypt hash starts with `$2b$`, unique index on users.email, index on login_attempts.identifier.

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
