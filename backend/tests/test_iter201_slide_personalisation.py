"""Iter 201 — Personalised slide order pure-function contract.

Locks the JavaScript helper in `personaliseSlides.js` via node exec —
no jsdom / jest dependency needed. Read as a Python test but the
assertions run in node (which is already available in the pod's
frontend toolchain).

We keep this test in the backend pytest suite so it runs alongside
the other iter-locked tests and gates the CI regression sweep.
"""
from __future__ import annotations

import json
import os
import subprocess


HELPER = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..",
        "frontend", "src", "lib", "personaliseSlides.js",
    )
)

BASE = [
    {"key": "situation"},
    {"key": "child-needs"},
    {"key": "relationship"},
    {"key": "communication"},
    {"key": "foundation"},
]


def _run(situation=None, courtOrdered=False):
    """Import the helper via node's dynamic `import()`, call it with
    the given inputs, print JSON to stdout, parse in Python."""
    src = f"""
(async () => {{
  const m = await import('{HELPER}');
  const out = m.personaliseSlides({json.dumps(BASE)}, {{
    situation: {json.dumps(situation)},
    courtOrdered: {json.dumps(courtOrdered)},
  }});
  process.stdout.write(JSON.stringify(out.map(s => s.key)));
}})();
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", src],
        capture_output=True, text=True, check=True,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend")),
    )
    return json.loads(result.stdout)


def test_default_order_when_no_situation_or_case():
    order = _run(situation=None, courtOrdered=False)
    assert order == ["situation", "child-needs", "relationship",
                     "communication", "foundation"]


def test_court_ordered_rotates_foundation_to_front():
    order = _run(situation=None, courtOrdered=True)
    assert order[0] == "foundation"
    # Iter202 · court-ordered now HIDES the "situation" (Assess your
    # family situation) frame. All other slides still present.
    assert set(order) == {"foundation", "child-needs",
                          "relationship", "communication"}
    # The relative order of the non-rotated slides is preserved.
    assert order == ["foundation", "child-needs",
                     "relationship", "communication"]


def test_court_ordered_wins_over_situation():
    """Court-ordered flag beats situation-based ordering — a parent
    linked to a case always starts with Foundation Statement."""
    order = _run(situation="special-needs", courtOrdered=True)
    assert order[0] == "foundation"


def test_special_needs_situation_starts_with_child_needs():
    order = _run(situation="special-needs", courtOrdered=False)
    assert order[0] == "child-needs"
    assert set(order) == {s["key"] for s in BASE}


def test_mediation_situation_starts_with_communication():
    order = _run(situation="mediation", courtOrdered=False)
    assert order[0] == "communication"


def test_safety_and_high_conflict_use_default_order():
    for sit in ("safety", "high-conflict", "cooperate", "difficult",
                "not-a-real-situation"):
        order = _run(situation=sit, courtOrdered=False)
        assert order[0] == "situation", (
            f"expected 'situation' first for {sit}, got {order[0]}"
        )


def test_rotate_is_idempotent_when_target_already_first():
    """A parent whose personalised target happens to be at index 0
    already must not get a reshuffled list."""
    # child-needs is index 1 → rotates to 0.
    order = _run(situation="special-needs", courtOrdered=False)
    assert order == ["child-needs", "situation", "relationship",
                     "communication", "foundation"]


# ---------------------------------------------------------------------------
# Iter202 · Hide rules.
# ---------------------------------------------------------------------------

def test_safety_situation_hides_joint_oriented_slides():
    """Safety-situation parents should never see the joint-oriented
    "Strengthen communication" or "Foundation Statement" slides."""
    order = _run(situation="safety", courtOrdered=False)
    assert "communication" not in order
    assert "foundation" not in order
    # The exploratory frames remain — parent still sees situation,
    # child-needs, and relationship.
    assert order == ["situation", "child-needs", "relationship"]


def test_court_ordered_hides_family_situation_frame():
    """Court-referred parents skipped the "how are you arriving"
    question by definition — hide the Assess family situation frame."""
    order = _run(situation=None, courtOrdered=True)
    assert "situation" not in order
    # Foundation still gets rotated to the front.
    assert order[0] == "foundation"
    assert set(order) == {"foundation", "child-needs", "relationship", "communication"}


def test_safety_plus_court_ordered_hides_all_three_and_skips_rotation():
    """Edge case: both hide rules fire. Foundation was the rotation
    target for court-ordered but is now hidden by safety — the
    filtered list should render in its natural order with no
    rotation applied."""
    order = _run(situation="safety", courtOrdered=True)
    # situation (court-ordered rule) + communication + foundation
    # (safety rule) are all hidden. Only child-needs + relationship
    # survive.
    assert order == ["child-needs", "relationship"]


def test_hidden_slide_keys_helper_matches_expected_rules():
    """Locking the hiddenSlideKeys helper explicitly so a future
    change here doesn't silently reshape the hide rules."""
    src = f"""
(async () => {{
  const m = await import('{HELPER}');
  const cases = [
    {{ situation: null,          courtOrdered: false }},
    {{ situation: 'safety',      courtOrdered: false }},
    {{ situation: null,          courtOrdered: true  }},
    {{ situation: 'safety',      courtOrdered: true  }},
    {{ situation: 'mediation',   courtOrdered: false }},
    {{ situation: 'special-needs', courtOrdered: false }},
  ];
  const out = cases.map(c => Array.from(m.hiddenSlideKeys(c)).sort());
  process.stdout.write(JSON.stringify(out));
}})();
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", src],
        capture_output=True, text=True, check=True,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend")),
    )
    got = json.loads(result.stdout)
    assert got == [
        [],                                       # neutral
        ["communication", "foundation"],          # safety only
        ["situation"],                            # court only
        ["communication", "foundation", "situation"],  # both
        [],                                       # mediation
        [],                                       # special-needs
    ]


def test_non_safety_non_court_never_hides_slides():
    """Every other situation must return the full 5-slide list —
    hides are surgical, only applied in the two documented cases."""
    for sit in ("mediation", "special-needs", "high-conflict",
                "cooperate", "difficult", "not-a-real-situation"):
        order = _run(situation=sit, courtOrdered=False)
        assert len(order) == 5, (
            f"expected 5 slides for situation={sit}, got {order}"
        )
