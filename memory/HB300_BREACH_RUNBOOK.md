# HB 300 Breach Response Runbook

> **Purpose.** Give the SA CoParents privacy officer a single,
> pre-approved sequence to follow the moment a suspected PHI breach
> is discovered. Texas HB 300 (Tex. Health & Safety Code Ch. 181)
> layers on top of HIPAA §§164.400–414; the timers below are the
> shorter of the two statutes wherever they diverge.

## 0. Definitions

- **PHI**: Any health-adjacent field the platform holds — safety
  assessments, SNC2 assessments, joint reports, joint agreements,
  trauma-lens findings, coach conversations, mediator emails.
- **Breach**: Unauthorised acquisition, access, use, or disclosure
  of PHI that compromises its security or privacy. Includes
  accidental exposure via logs, misconfigured storage, stolen
  credentials, and vendor incidents.
- **Discovery**: The date the breach is *known or should have been
  known* by any workforce member (agent, contractor, owner).

## 1. First 60 minutes (Contain)

1. Freeze the affected endpoint or credential — rotate keys, revoke
   sessions, disable the offending share.
2. Snapshot the current state of `phi_access_log` for the affected
   users. Do **not** modify or delete rows.
3. Preserve stdout, supervisor, and Mongo logs for the incident
   window. Copy to `/app/memory/incidents/<yyyy-mm-dd>/`.
4. Start the timeline document: `incidents/<yyyy-mm-dd>/timeline.md`.

## 2. First 24 hours (Assess)

- Count affected users. Bucket by state — the AG threshold applies
  to Texas residents only.
- Draft the breach report via `POST /api/admin/breach-report`. The
  endpoint stores a copy in `hb300_breach_reports` and emails
  `OPERATOR_EMAIL`.
- Determine the PHI categories exposed (safety assessment,
  agreement, etc.) — this drives the notification content.
- Engage legal counsel. Do **not** send any user or regulator
  notification without counsel sign-off.

## 3. Timers (HB 300 vs HIPAA)

| Notice                       | Threshold                                    | Deadline from *discovery*           |
| ---------------------------- | -------------------------------------------- | ----------------------------------- |
| Individual (affected user)   | Any                                          | 60 days                             |
| Texas Attorney General       | ≥ 250 Texas residents affected               | Without unreasonable delay, ≤ 60 days |
| US HHS / OCR                 | ≥ 500 individuals (any state)                | 60 days                             |
| US HHS / OCR                 | < 500 individuals                            | Annual log (by 60 days after year-end) |
| Media (Texas)                | ≥ 500 residents of one Texas region          | 60 days                             |

## 4. Notification content — mandatory elements

- What happened (plain English).
- What PHI was involved.
- Steps the user should take to protect themselves.
- Steps SA CoParents has taken to investigate and mitigate.
- Contact details: phone, email, postal address of the Privacy Officer.
- Whether credit monitoring is being offered.

## 5. Texas AG notice (≥ 250 TX residents)

Filed at: <https://www.texasattorneygeneral.gov/consumer-protection>.
Required fields (per Tex. Bus. & Com. Code §521.053, as amended):
- Detailed description of the breach.
- Number of Texas residents affected.
- Measures taken pre- and post-breach.
- Whether law enforcement is engaged.
- Contact for follow-up.

## 6. Post-incident (Learn)

- Complete post-mortem within 14 days of containment.
- Update this runbook if any timer or endpoint changed.
- Retain the incident folder for **six years** per HIPAA
  §164.316(b)(2)(i). Never delete audit rows.
- Refresh workforce training if the root cause was human error.

## 7. Contacts

- Privacy Officer: Matt Sossi — `mattsossi@bsossi.com` · 210-224-1667
- Texas AG Consumer Protection Division — 1-800-621-0508
- HHS OCR Southwest Region — 1-800-368-1019

_Last reviewed: 2026-02-21._
