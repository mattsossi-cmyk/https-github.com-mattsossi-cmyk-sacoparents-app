"""AI privacy notice: one acknowledgment per user covers every AI feature. No auth imports (used by auth.py)."""

# Change this whenever the AI notice changes; everyone is asked again (server checks it on every AI call).
AI_NOTICE_VERSION = "2026-10-16"

AI_FEATURES = (
    "communication_builder", "biff", "guide_chat", "summary",
    "self_assessment", "child_needs_help", "comm_style", "guided_journey",
)

# The only category labels the browser check can report; anything else is rejected, so no typed text can be logged.
AI_NOTICE_LABELS = (
    "Social Security number",
    "Date of birth or specific date",
    "Phone number",
    "Email address",
    "Street address",
    "ID, Medicaid, insurance or case number",
    "Medical or psychological details",
)


def has_ai_notice(doc: dict) -> bool:
    return doc.get("ai_notice_version") == AI_NOTICE_VERSION and bool(doc.get("ai_notice_ack_at"))
