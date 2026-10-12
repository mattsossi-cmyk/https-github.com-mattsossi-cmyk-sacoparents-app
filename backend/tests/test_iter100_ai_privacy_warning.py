"""AI Privacy Warning (owner text 2026-10-12): exact strings, rendered above every AI input, never dismissable, no policy link."""
import re

SRC = "/app/frontend/src"
W = open(f"{SRC}/components/AiPrivacyWarning.jsx", encoding="utf-8").read()

EXACT = [
    "SA CoParents Communication Builder — Privacy Warning",
    'heading: "Privacy Warning"',
    "SA CoParents is committed to protecting your personal information and your child's privacy.",
    "When using an AI-assisted communication tool, information you enter may be processed by external technology providers and could be disclosed to third parties depending on the platform's privacy practices and safeguards.",
    "Please speak in general terms. Do not provide names or identifying details; upload assessments or reports; disclose sensitive medical, mental health, psychological or educational information; or enter confidential legal communications or details concerning family violence or personal safety.",
    "You can improve communication without sharing private family details.",
    "SA CoParents — Start with Safety. Protect Your Privacy. Focus on Your Child.",
]

PLACEMENTS = {
    "components/AlignAssistant.jsx": ("ai-privacy-warning-assistant", "<form onSubmit"),            # Gemini chat input
    "components/LensAiTools.jsx": ("ai-privacy-warning-research", "value={q} onChange"),           # Perplexity research question
    "pages/LegalLensReport.jsx": ("ai-privacy-warning-lens", "<NeutralityCheck id={id} rep={rep} />"),  # report fields → AI draft / Jev / Claude
    "pages/FoundationEditor.jsx": ("ai-privacy-warning-foundation", "<Textarea"),                   # concerns → Jev blame-check
}


def test_exact_text_and_single_editable_source():
    for s in EXACT:
        assert s in W, s
    assert "AI_PRIVACY_ONE_LINER" in W and 'export const AI_PRIVACY_WARNING' in W
    low = W.lower()
    assert "href=" not in low and "/privacy" not in low and "fonts.googleapis" not in low and "cdn" not in low
    assert "font-jakarta" in W and "#3D1A78" in W and "localStorage" not in W and "dismiss" not in low


def test_warning_renders_above_each_ai_input():
    for f, (tid, anchor) in PLACEMENTS.items():
        src = open(f"{SRC}/{f}", encoding="utf-8").read()
        assert "AiPrivacyWarning" in src, f
        i, j = src.index(f'testId="{tid}"'), src.index(anchor)
        assert i < j, f"{f}: warning must appear ABOVE the input ({tid})"


def test_every_ai_calling_component_has_warning():
    ai_calls = re.compile(r"/assistant/|/research/ask|/professional-report/ai-draft|neutrality-check|child-focus-suggest|parallel-summary-draft|blame-check")
    import os
    missing = []
    for root, _d, files in os.walk(SRC):
        for f in files:
            if not f.endswith(".jsx"):
                continue
            p = os.path.join(root, f)
            s = open(p, encoding="utf-8").read()
            if ai_calls.search(s) and "AiPrivacyWarning" not in s and f not in ("AiDraftComparison.jsx", "PipelineStepper.jsx"):  # PipelineStepper only reads /assistant/case-brief (no user text)
                missing.append(f)
    assert missing == [], missing
