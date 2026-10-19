# Step 4 — old vs new (preview only, 2026-10-19)

## 1. Professional Access Notice
| Place | Old | New |
|---|---|---|
| Case-invitation page (`JoinInvitation.jsx`) | Box "What this professional will see": "Once you accept, they can see whether each step they asked for is done, in progress or not started, with the dates. They don't see your answers. Shared co-parenting results reach them only after both parents finish. Your Self-Assessment answers are never shared." | Full notice "Who can see your information" (Align v2026-10-19.1 wording, verbatim) + link "Read the full privacy notification" → /privacy-notice (new tab) |
| Court-code accept dialog (`CourtAcceptDialog.jsx`) | Same old box | Same full notice |
| "You control this report" step (`PreShareConsentDialog.jsx`) | No such box (headline + six bullets + checkbox) | Full notice added above the checkbox; dialog body now scrolls (max 60vh) |
| Dashboard (`/dashboard`, top of the Journey screen) | (nothing — the old Safety Gate notices were removed in step 2) | Short card "Who can see your information" + link "Who can see my information"; X hides it per account (survives reload) |
| Footer (in-app footer and portal footer) | "Privacy Notice" only | + "Who can see my information" → new page /who-can-see-my-information (full notice; Align "Who has looked at my information" button only when Align's address is set) |
| `CaseVisibilityNotice.jsx` | Component | Deleted (no other users) |

## 2. Privacy Notice page (/privacy-notice), section 2
- Old: "**Who can see your information.** Your co-parent never sees your individual screening answers. A professional linked to your case (for example a mediator or attorney) may see information you add to a shared case. Assigned professionals may see individual screening answers, as described in the Privacy Notification you accepted at sign-in. We share nothing else without your permission."
- New: "**Who can see your information.**" followed by the full version, verbatim, as page text (no box).
- "the professional linked to your case" is gone (it was only in the replaced paragraph). "your professional" remains twice, inside the full version itself, kept word-for-word to match Align.
- `PRIVACY_NOTICE_VERSION`: "2026-10-16-v2" → "2026-10-19-v3"; `PRIVACY_NOTICE_TEXT_SHA256` updated. Effect: every parent is asked to re-accept the Privacy Notice at next sign-in (preview now; live only after a publish).
- Sections shown (preview AND live, live checked read-only): 1, 2, 7, 12 only. Sections 3–6 and 8–11 do not exist in the code.

## 3. Scoring — full Safety Assessment
| Line | Old (earlier today, never live) | New |
|---|---|---|
| Meaning of "I'd rather not answer" | Counted like "Unsure" | A skip: never counts toward a concern |
| Extension sections (pattern / trauma / child) | Mapped to "Unsure" (counted as answered) | Ignored like an unanswered item (mapping removed) |
| Floor | none | Skip on any of these → result at least Level 2 (Amber, "Structured Written Communication Only"); never lowers a Level 1 |
| Floor list — immediate danger | — | s1_q1 threats to hurt/kill; s1_q11 violence increasing; s1_q12 gun/weapon threat; s1_q15 suicide threat / "if I can't have you"; s1_q20 firearm access; s1_q25 threat to kill; s1_q26 threat to kill self |
| Floor list — physical harm | — | s1_q2 physically hurt/blocked/choked; s1_q13 choke/strangle; s1_q19 strangled more than once |
| Floor list — sexual harm | — | s1_q14 forced sexual activity; s1_q21 coerced sexual activity |
| Floor list — harm to children | — | ce_q1 child hit/threatened/harmed; ce_q8 child described being frightened/hurt/unsafe |
| Result fields | declined_count, section_1_declined_count | + skip_floor_ids |
| Results page note | "…These don't raise or lower your result." | "You chose Prefer not to answer for N question(s). That's okay." + either "Skipped questions don't raise your result." or "Because a question about immediate danger, physical or sexual harm, or harm to your children was skipped, your result is set to at least Level 2." + Get help link if a Section 1 item was skipped (kept) |
| PDF | "PREFER NOT TO ANSWER" | unchanged (kept) |
| Quick 3-question Safety Screen | Skip opens the gentle support card (same as "Not sure") | unchanged |

Existing results affected: none. 0 of 1,367 preview results contain a skip (the option only existed in preview since earlier today; never live). Results are scored once when saved and are never recalculated.

## 4. Self Journey "Safety Screen" link
- Old: nothing under the Family check-in card.
- New: small "Safety Screen" button (or "Safety Screen · retake" once done) that opens the quick Safety Screen.

## Round 2 (same day) — true-sentences-only notice, plain skips, neutral link
- Full notice: now only "Your co-parent never sees your answers. Nothing you write in the safety questions is ever shown to them." / "Texas law requires anyone who suspects child abuse or neglect to report it." / "Every question can be skipped, and you can stop at any time." / link "Read the full privacy notice" (was "...notification").
- Dashboard card: now only "Your co-parent never sees your safety answers." (+ link).
- Privacy Notice section 2: the same three true sentences as one paragraph. Version 2026-10-19-v4.
- Removed as untrue for this app: professionals-can-see list (5 bullets), administrators sentence, views-recorded sentence, court-documents sentence, "the professional who reads them must report it", "your professional will be asked to check in", and the short card's 3 matching sentences.
- Self Journey link: "Safety Screen" -> "Quick check-in" ("· retake"), shield icon -> clipboard-check, rose -> neutral purple.
- Full assessment: Amber floor removed (a skip never changes the level). PDF/AI label "Prefer not to answer" -> "Skipped". Results note -> "You skipped N question(s). That's okay. Skipped questions don't change your result." (+ Get help link if Section 1 skipped).
- Quick check: a skip no longer flags. Saved ack gets `skipped: N`; Complete Coparenting Report line "Cleared - no risk flag." -> "Completed - no risk flag. Skipped: N question(s)." when N > 0.
- Footer: global "Who can see my information" line on every page without its own footer link (lib/footerLink.jsx).
