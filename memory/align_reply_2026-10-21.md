# Reply to Align (2026-10-20.1), 2026-10-21. Test data only

## 1. How data reaches Align
- SA CoParents does not post to Align today. Align reads each linked parent from
  `GET /api/integrations/export-assessments?email=<parent email>` with the `X-Integration-Key` header.
- New, switched off until Align sends its import address and key: after a parent says yes (and each time they re-save
  Communication Style while sharing), the app POSTs to Align's import address with the header `X-Integration-Key: <key Align gives us>`.
  Please confirm that header name.

## 2. Sample POST body to /api/integrations/import (test data)
```json
{
  "case_id": "SA-SAMPLE1",
  "email": "sample.parent@example.com",
  "cr_conflict": "Pause, then reply briefly and factually.",
  "cr_direct": "Defending instead of listening.",
  "cr_channel": "Hi, can we swap Saturday pickup to 10am? Thanks.",
  "cr_child": "Send articles, screenshots, and context.",
  "completed_at": "2026-10-21T15:19:32.500497+00:00"
}
```
`case_id` and `email` are for matching the parent only (case_id is null if the parent has no SA case yet).

The same five fields are now also inside `communication_readiness` in the export Align already reads, next to the
original `answers` list and `answered_at`.

## 3. Field mapping: please confirm
| Align field | Our question | Answer format |
|---|---|---|
| cr_conflict | "When my co-parent texts me about a conflict, my first instinct is to…" | one of 6 plain-language sentences |
| cr_child | "When disagreements arise about our child, I most often…" | one of 6 plain-language sentences |
| cr_direct | "If I had to be honest, the pattern I'd most like to change is…" | one of 6 plain-language sentences |
| cr_channel | "A recent message I sent" (free text the parent pasted, optional) | free text or null |
| completed_at | date the parent last saved these answers | ISO 8601 UTC |

cr_direct and cr_channel are our closest guess. Please tell us what each cr_ field means if this is wrong.
Nothing else we rely on goes to /import. Situation Snapshot and Special Needs are only in the export Align reads.

Open question: when a parent switches sharing off, the export stops including the answers right away. For the import,
should we send a removal (for example the same body with all cr_ fields null)?

## 4. Footer link
"Who has looked at my information" is now in the in-app footer and the home-screen footer for parents linked to Align:
`https://sacoparentsalign.com/who-can-see?case=<SA case code>`, or `https://sacoparentsalign.com/who-can-see` when linked
without a case. Hidden for parents who aren't linked.

## 5. Parent-facing wording
Updated to match Align: the answers are "seen only by your assigned professionals and, when needed, SA CoParents
administrators". This applies to the share question, the Account switch, the "What professionals can see" page and the
Privacy Notice (now v9, which everyone re-accepts). Parents who said yes before this change are asked again, and
nothing is shared until they answer.
