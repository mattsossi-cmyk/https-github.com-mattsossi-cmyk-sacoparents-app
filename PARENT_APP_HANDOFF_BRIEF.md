# Copy-paste brief for the sacoparentsapp.online project

Align (sacoparentsalign.com) now sends every parent invitation to:

    https://sacoparentsapp.online/?invite=<token>

Implement the following in the SA CoParents App:

1. On app load, read `invite` from the query string. If present, call
   `GET https://sacoparentsalign.com/api/joint/invitations/lookup/<token>`
   (public, no auth). It returns the case subject, child first name, the inviting
   professional's name, the invited parent's email, and expiry.
2. Show an "You've been invited by <professional>" screen. Require the parent to
   sign in / register with the SAME email the invitation was sent to; reject a mismatch.
3. Capture explicit authorization (checkbox + timestamp) that results may be shared
   with the inviting professional only.
4. Run the parent's private assessment for the invited subject(s). Never show the
   other parent's answers.
5. On completion, POST the signed payload to Align as described in
   `SACOPARENTSAPP_ONLINE_INTEGRATION_SPEC.md` (section "Joint Alignment Case
   integration"): include the invitation token / Align case ID, parent email,
   answers, authorization record, and an HMAC-SHA256 signature using the shared
   `INTEGRATION_SHARED_SECRET`. Align marks that parent side complete; when both
   sides are in, the case becomes READY_FOR_ALIGNMENT.
6. Show the parent a "Sent to your professional" confirmation; do not show any
   comparison or the other parent's status.

Environment needed in the App project: `ALIGN_API_URL=https://sacoparentsalign.com`,
`INTEGRATION_SHARED_SECRET` (same value as Align production).
