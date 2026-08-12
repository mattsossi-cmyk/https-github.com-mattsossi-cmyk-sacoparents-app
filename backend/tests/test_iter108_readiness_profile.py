"""Iter 108 — Mediation-readiness profile-first output.

Locks the contract that ``compute_readiness()`` now:

    * Leads with a per-domain descriptive **profile** (level +
      headline + narrative + strengths + growth areas + specific
      preparation recommendations), not the overall number.
    * Attaches ``readiness_disclaimer`` warning that the score
      reflects **completeness of preparation, not emotional
      readiness** — and that a coercive pattern makes ordinary
      mediation unsafe regardless of score.
    * Emits ``caveats`` when the profile could mislead — e.g.
      "polished communication + high conflict load" (which is
      the exact failure mode the user flagged), or safety concerns
      present in the underlying safety_assessment.
    * Preserves legacy fields (``overall``, ``label``,
      ``dimensions``) unchanged for backwards compatibility.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/app/backend")

from readiness_scoring import compute_readiness  # noqa: E402


def _prep_baseline() -> dict:
    """A middle-of-the-road prep dict — every source has *some* content
    so no domain returns the neutral placeholder."""
    return {
        "comm_style": {
            "scores": {"tone": 3.0, "listening": 3.0, "escalation": 3.0, "boundaries": 3.0, "repair": 3.0},
        },
        "child_goals": {
            "emotional_wellbeing": "steady bedtime routine",
            "stability": "same school",
            "relationships": "keep grandparent time",
            "development": "swimming lessons",
        },
        "priority": [
            {"category": "compromise"},
            {"category": "compromise"},
            {"category": "compromise"},
        ],
        "issues": {"schedule": "school pickups", "communication": ""},
        "readiness": {
            "scores": {
                "cooperation": 3.0,
                "hope_for_agreement": 3.0,
                "trust_in_process": 3.0,
                "patience": 3.0,
                "emotional_preparation": 3.0,
            }
        },
        "safety_assessment": {},
    }


def test_profile_is_returned_alongside_legacy_fields():
    r = compute_readiness(_prep_baseline())
    # Legacy contract preserved.
    assert "overall" in r and "label" in r and "dimensions" in r
    # New profile-first fields present.
    assert "profile" in r
    assert set(r["profile"].keys()) == {"communication", "trust", "child_alignment", "conflict"}
    assert "readiness_disclaimer" in r
    assert "secondary_score" in r
    assert r["secondary_score"]["overall"] == r["overall"]
    # Every domain has the profile-first shape.
    for k, p in r["profile"].items():
        assert p.get("level") in ("emerging", "developing", "solid")
        assert p.get("headline")
        assert p.get("narrative")
        assert isinstance(p.get("preparation_recommendations"), list)
        assert len(p["preparation_recommendations"]) >= 1
        assert isinstance(p.get("strengths"), list)
        assert isinstance(p.get("growth_areas"), list)
        assert isinstance(p.get("secondary_score"), (int, float))


def test_disclaimer_names_completeness_vs_readiness_distinction():
    r = compute_readiness(_prep_baseline())
    disc = r["readiness_disclaimer"].lower()
    # The whole point of this iteration — the disclaimer must name the
    # distinction between COMPLETENESS and READINESS.
    assert "completeness" in disc
    assert "emotional readiness" in disc or "not a measure of emotional" in disc or "readiness" in disc
    # And it must warn about coercive patterns making mediation unsafe.
    assert "coercive" in disc or "safety" in disc


def test_high_scores_still_produce_caveat_when_safety_concerns_present():
    """The exact failure mode the user flagged — polished answers, high
    score, but a coercive relationship in the background. The caveat
    must fire."""
    prep = _prep_baseline()
    # Push every self-rating to the top so the score comes out strong.
    prep["comm_style"]["scores"] = {k: 5.0 for k in prep["comm_style"]["scores"]}
    prep["readiness"]["scores"] = {k: 5.0 for k in prep["readiness"]["scores"]}
    # Safety concerns present.
    prep["safety_assessment"] = {"high_risk": True}
    r = compute_readiness(prep)
    # The score can still be reported (backwards compat), but the caveat
    # must warn about coercive patterns making mediation unsafe.
    joined = " ".join(r["caveats"]).lower()
    assert "coercive" in joined
    assert "finding 3" in joined or "family-violence practitioner" in joined
    # And the disclaimer at the top level also carries the warning.
    assert "coercive" in r["readiness_disclaimer"].lower()


def test_polished_communication_plus_high_conflict_load_triggers_caveat():
    """Direct capture of the user's stated concern: 'a parent who writes
    detailed polished answers may score highly while still lacking
    emotional regulation'."""
    prep = _prep_baseline()
    # Polished communication.
    prep["comm_style"]["scores"] = {k: 5.0 for k in prep["comm_style"]["scores"]}
    # Very high conflict load: lots of issue categories + urgent priorities
    # + low emotional prep.
    prep["issues"] = {k: "yes there is a lot going on here" for k in ("schedule", "communication", "finances", "safety", "other")}
    prep["priority"] = [{"category": "urgent"} for _ in range(5)]
    prep["readiness"]["scores"]["emotional_preparation"] = 1.0
    r = compute_readiness(prep)
    joined = " ".join(r["caveats"]).lower()
    assert "polished" in joined or "communication score is strong" in joined
    assert "conflict" in joined


def test_low_score_produces_emerging_profile_with_scaffolding_recommendations():
    prep = _prep_baseline()
    # Everything low so all domains are emerging.
    prep["comm_style"]["scores"] = {k: 1.0 for k in prep["comm_style"]["scores"]}
    prep["readiness"]["scores"] = {k: 1.0 for k in prep["readiness"]["scores"]}
    prep["child_goals"] = {}
    prep["priority"] = []
    prep["issues"] = {k: "concern" for k in ("schedule", "communication", "finances", "safety", "other")}
    r = compute_readiness(prep)
    # At least one domain should be at "emerging" level.
    levels = {k: v["level"] for k, v in r["profile"].items()}
    assert "emerging" in set(levels.values())
    # And the recommendations must include real preparation scaffolding,
    # not just "try harder".
    all_recs = []
    for p in r["profile"].values():
        all_recs.extend(p["preparation_recommendations"])
    joined = " ".join(all_recs).lower()
    assert any(word in joined for word in ("coach", "support person", "written", "review", "practitioner"))


def test_profile_recommendations_reference_trauma_informed_lens_for_trust_emerging():
    """When trust is emerging (safety concerns present), the
    preparation recommendations should route the parent to the
    Trauma-Informed Safety and Functioning Lens — not straight into
    joint mediation."""
    prep = _prep_baseline()
    prep["safety_assessment"] = {"high_risk": True}
    prep["readiness"]["scores"] = {k: 1.0 for k in prep["readiness"]["scores"]}
    r = compute_readiness(prep)
    trust = r["profile"]["trust"]
    joined = " ".join(trust["preparation_recommendations"]).lower()
    assert "trauma-informed" in joined or "finding 3" in joined
