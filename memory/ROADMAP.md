# SA CoParents — Roadmap

## P0
- Self Journey guide: user to review in preview / live.
- Journey photos: user to attach the five photos (self, safety, coparent, parallel, needs) as one .zip to
  replace the stand-ins in `frontend/public/images/journey/` ("next" no longer used).

## P0 (pending publish)

- Co-Parenting report: 3 lines suggest joint actions (school events together, joint parent-teacher meeting, joint
  parent-training session); ask founder whether to swap them for separate-meeting versions when the parent picked concern.
- Existing Self-Assessment retake EMAILS (self_assessment_reminders.py, sa-reassess-reminder cron) still send; ask founder
  whether to switch them to in-app only like check-ins.

## P1
- Align outbound import (`push_to_align`): OFF until the exact import URL + key are provided (secure secret card).
- Align to confirm the `cr_*` field meanings, header name and how to remove data after a "no"
  (draft reply: `align_reply_2026-10-21.md`).
- "Who has looked at my information": now only in the AppFooter on in-app pages (home footer was removed by the user).
- Optional: after accepting the AI notice, send the first question automatically (today the parent taps again;
  app-wide AiNoticeProvider behaviour, left as is).

## P2
- Professional / Align "Suggested for your family" mark on the parenting-path cards (both cards still shown).
- "Done" tick on the Start with Safety step when Align confirms the check-in.
- Note on the Court Ordered screen about the safety check-in email.

- Optional: "include my check-ins" choice for the PDF (off today). AI-notice modal copy still says "AI Communication Builder" (app-wide, versioned).
- SelfJourney.jsx is ~1000 lines; split step pages into files when next touched.
