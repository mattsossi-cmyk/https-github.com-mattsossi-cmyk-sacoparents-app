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
    # Every other slide is still present.
    assert set(order) == {s["key"] for s in BASE}
    # The relative order of the non-rotated slides is preserved.
    assert order == ["foundation", "situation", "child-needs",
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
