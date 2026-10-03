# Two-Site Deployment — SA CoParents

**Set 2026-02-27 (iter249).** Code-side preparation complete.
The remaining steps are infrastructure (DNS, ingress, SSL),
owned by DevOps / the account owner.

NORTH_STAR.md commits SA CoParents to a rigid two-site split:

| Site              | Hostname (prod)          | Purpose                                   |
| ----------------- | ------------------------ | ----------------------------------------- |
| **SA CoParents**  | `sacoparentsapp.online`  | Parent journey (five-step shell only)     |
| **SA CoParents Align** | `sacoparentsalign.online` | Professional surface (`/align` + `/admin`) |

Both hostnames resolve to the **same deployed React bundle** —
splitting them is enforced inside the app by the `DomainGuard`
component, not by shipping two different bundles.

## What's already shipped (iter249)

- `/app/frontend/src/components/DomainGuard.jsx` — a route-level
  wrapper that, when it detects the parent hostname showing an
  Align route (or vice versa), renders a 2.5-second redirect
  card and auto-sends the visitor to the correct hostname with
  the original path preserved.
- Env config in `/app/frontend/.env`:
    * `REACT_APP_PARENT_HOSTNAME=sacoparentsapp.online`
    * `REACT_APP_ALIGN_HOSTNAME=sacoparentsalign.online`
    * `REACT_APP_PARENT_URL=https://sacoparentsapp.online`
    * `REACT_APP_ALIGN_URL=https://sacoparentsalign.online`
  If either hostname env var is missing, `DomainGuard` is a
  **no-op** — preview / local dev work exactly as before.
- Routes wrapped (`/app/frontend/src/App.js`):
    * `/`     → `<DomainGuard side="parent">`
    * `/align` → `<DomainGuard side="align">`
    * `/admin` → `<DomainGuard side="align">`
  (Sub-routes under `/admin/*` can be wrapped incrementally
  when the DNS flip happens.)

## What DevOps still needs to do

### 1. Register / confirm both domains
Both already registered. Verify DNS management access:
- `sacoparentsapp.online`
- `sacoparentsalign.online`

### 2. Add both hostnames to the Kubernetes ingress

Current ingress serves `prepared-parents.preview.emergentagent.com`.
Add both production hostnames to the same ingress so they land
on the same frontend/backend services.

Example (Emergent platform or kubectl-equivalent):

```yaml
# ingress excerpt — add these rules alongside the existing preview host
spec:
  tls:
    - hosts:
        - sacoparentsapp.online
        - sacoparentsalign.online
      secretName: sa-coparents-tls
  rules:
    - host: sacoparentsapp.online
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 3000
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8001
    - host: sacoparentsalign.online
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 3000
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8001
```

Both hostnames MUST route `/api/*` to the same backend —
`DomainGuard` enforces the UI split in the browser; the API
is shared.

### 3. Point A / ALIAS records at the Kubernetes ingress

```
sacoparentsapp.online        A    <ingress-public-ip>
www.sacoparentsapp.online    CNAME sacoparentsapp.online.
sacoparentsalign.online      A    <ingress-public-ip>
www.sacoparentsalign.online  CNAME sacoparentsalign.online.
```

### 4. TLS certificates

If using `cert-manager`:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: sa-coparents-tls
  namespace: default
spec:
  secretName: sa-coparents-tls
  dnsNames:
    - sacoparentsapp.online
    - www.sacoparentsapp.online
    - sacoparentsalign.online
    - www.sacoparentsalign.online
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
```

If using the Emergent platform's managed TLS: add both
hostnames in the deploy UI; the platform issues the certs
automatically.

### 5. Verify the flip in prod

After DNS propagates:

```bash
# Should return the shell (and NOT redirect)
curl -I https://sacoparentsapp.online/

# Should render the DomainGuard redirect card for ~2.5s then
# auto-forward to https://sacoparentsalign.online/align
curl -I https://sacoparentsapp.online/align

# Should render the Align landing (and NOT redirect)
curl -I https://sacoparentsalign.online/align

# Should render the DomainGuard redirect card for ~2.5s then
# auto-forward to https://sacoparentsapp.online/
curl -I https://sacoparentsalign.online/
```

### 6. Update email templates (Resend) — out of scope for iter249

Any production email templates that currently hard-code the
preview URL (`prepared-parents.preview.emergentagent.com`)
should be audited and switched to the hostname that matches
the recipient:

- Parent-facing emails (progress-share, follow-up nudges,
  consent-adoption digest when toggled on) → link to
  `sacoparentsapp.online`.
- Professional-facing emails (mediator weekly digest,
  reviewer notifications) → link to
  `sacoparentsalign.online`.

The backend uses `PUBLIC_BACKEND_URL` for the tracking pixel
and link base. Consider adding two env vars:
`PUBLIC_PARENT_URL` and `PUBLIC_ALIGN_URL`, then selecting at
send time based on recipient role.

## Rollback

- To temporarily disable the guard without a redeploy, remove
  (or blank) `REACT_APP_PARENT_HOSTNAME` / `REACT_APP_ALIGN_HOSTNAME`
  in `/app/frontend/.env` and redeploy. All routes become
  accessible from any hostname.
- To revert the whole split, point both DNS records at the
  same hostname and the guard stays idle (no-op when hostname
  isn't one of the two configured ones).
