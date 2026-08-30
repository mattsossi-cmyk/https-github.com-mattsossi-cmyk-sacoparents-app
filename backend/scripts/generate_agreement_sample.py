"""Generate a sample Co-Parenting Agreement Draft PDF using realistic
fictional data. Uses the *same* pdf_service.build_agreement_pdf used
by the live app so the sample is representative — not a mockup.
"""
from pathlib import Path

from pdf_service import build_agreement_pdf


SAMPLE_USER_NAME = "Alex Rivera"
SAMPLE_MEDIATION_DATE = "2026-04-15"

SAMPLE_AGREEMENT = {
    "overview": (
        "This draft summarises how I hope our co-parenting partnership will work "
        "for our two children, Maya (8) and Jonas (5). Every clause below is a "
        "starting proposal I want to discuss — not a demand. My focus is on "
        "keeping the children's routines stable and giving both of us the "
        "predictability we need to be present when the kids are with us."
    ),
    "changes_since_last": (
        "Since the last draft I've added a shared communication protocol and "
        "moved the school-transport clause under Household Rules where it "
        "belongs. I also softened the language on holidays after our last "
        "conversation went well."
    ),
    "shared_goals": [
        "Keep both children's school performance and after-school activities uninterrupted.",
        "Speak about each other with respect in front of the kids — no exceptions.",
        "Make big decisions (medical, educational, therapy) together, in writing.",
        "Protect the children's relationships with both extended families.",
        "Revisit this agreement every six months so it can grow with the kids.",
    ],
    "communication": [
        {
            "topic": "Day-to-day logistics",
            "clause": (
                "Route routine coordination (pickups, playdates, homework, sick days) "
                "through OurFamilyWizard messages. Aim for a response inside 24 hours "
                "on weekdays and 48 hours on weekends. Voice calls reserved for anything "
                "time-sensitive."
            ),
        },
        {
            "topic": "Escalation path",
            "clause": (
                "If either of us feels a message is escalating, we agree to pause for "
                "24 hours before replying and reach out to our parenting coordinator "
                "if we cannot land on the same page inside 72 hours."
            ),
        },
        {
            "topic": "The BIFF rule",
            "clause": (
                "Messages stay Brief, Informative, Friendly, and Firm. No debating past "
                "events in text. Save deeper conversations for the biweekly parenting "
                "check-in call on the second Sunday of the month."
            ),
        },
    ],
    "child_needs": [
        {
            "topic": "Maya (8) — school",
            "clause": (
                "Homework starts by 4:30 pm at whichever house she's at. Reading log "
                "goes home in her folder every Friday. Both parents attend school "
                "conferences together whenever possible."
            ),
        },
        {
            "topic": "Jonas (5) — early childhood",
            "clause": (
                "Bedtime routine (bath, story, lights out) held at 7:30 pm at both "
                "houses. Snuggle Bear travels with him between homes. Share any "
                "speech-therapy homework the same day it's assigned."
            ),
        },
        {
            "topic": "Medical + insurance",
            "clause": (
                "Both parents kept on the pediatric emergency contact list. Any "
                "diagnosis, prescription, or specialist referral goes into a shared "
                "medical log inside 48 hours."
            ),
        },
    ],
    "household_rules": [
        {
            "topic": "Screen time",
            "clause": (
                "Weekdays: one hour of screens after homework is complete. Weekends: "
                "two hours before noon, then off. Video calls with the other parent do "
                "not count against the daily limit."
            ),
        },
        {
            "topic": "School transport",
            "clause": (
                "Whichever parent has the children in the morning is responsible for "
                "drop-off. Afternoon pickup follows the parenting schedule. Backup "
                "pickup contact list refreshed at the start of each school year."
            ),
        },
        {
            "topic": "New partners",
            "clause": (
                "New partners are introduced to the children only after a stable "
                "six-month relationship. Both parents give each other at least two "
                "weeks' notice before an introduction happens."
            ),
        },
    ],
    "priority_items": [
        {
            "topic": "Holiday schedule 2026",
            "detail": (
                "Alternate Thanksgiving and Christmas Eve. Spring Break split by "
                "week. Fourth of July with the parent who has scheduled possession "
                "that weekend. Kids' birthdays celebrated with both parents at a "
                "coffee shop or the park — no house handoffs on birthdays."
            ),
            "priority": "high",
        },
        {
            "topic": "Extracurricular budget",
            "detail": (
                "Cap of $1,800/year per child. Anything above that requires written "
                "agreement. Splits 50/50 unless one parent volunteers to cover more."
            ),
            "priority": "medium",
        },
    ],
    "open_for_discussion": [
        "Summer camp choices — I'd like Maya to try the coding camp; happy to hear alternatives.",
        "Whether Jonas is ready for weekday sleepovers at grandparents' this year.",
        "Family therapy — I've been thinking a short-course therapist could help us before big transitions.",
    ],
    "closing_note": (
        "Thank you for reading this all the way through. This is a draft, not a "
        "verdict. I'm writing it with the assumption that we both love our kids "
        "the same way and want the same steady, boring, dependable childhood for "
        "them. Everything above is negotiable except the respect."
    ),
}


def main() -> None:
    pdf_bytes = build_agreement_pdf(
        user_name=SAMPLE_USER_NAME,
        agreement=SAMPLE_AGREEMENT,
        mediation_date=SAMPLE_MEDIATION_DATE,
    )
    out_dir = Path("/app/frontend/public/downloads")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sacoparents-sample-coparenting-agreement.pdf"
    out_path.write_bytes(pdf_bytes)
    print(f"Wrote {out_path} ({len(pdf_bytes):,} bytes)")


if __name__ == "__main__":
    main()
