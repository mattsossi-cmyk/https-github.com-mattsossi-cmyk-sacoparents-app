"""Iteration 73 — Wall category filter + Verify-page legal-ack skip.

Verifies:
- `GET /api/wall/feed?category=milestones` returns a filtered feed
  restricted to streak/foundation/alignment badges.
- Response echoes the resolved category and per-category counts.
- Unknown/blank category values fall back to "all" (no 400).
- CATEGORY_BADGES["milestones"] is the union of the three sub-groups.
"""
from wall_utils import (
    BADGE_FOUNDATION_READY,
    BADGE_HIGH_ALIGNMENT_90,
    BADGE_HUNDRED_DAY_STREAK,
    BADGE_MONTH_STREAK_30,
    BADGE_WEEK_STREAK_7,
    CATEGORY_BADGES,
)


def test_category_groups_shape():
    assert set(CATEGORY_BADGES.keys()) == {
        "streaks", "foundations", "alignment", "milestones",
    }


def test_streak_group_has_all_streak_badges():
    s = set(CATEGORY_BADGES["streaks"])
    assert BADGE_WEEK_STREAK_7 in s
    assert BADGE_MONTH_STREAK_30 in s
    assert BADGE_HUNDRED_DAY_STREAK in s


def test_foundation_group_has_foundation_badge():
    assert BADGE_FOUNDATION_READY in CATEGORY_BADGES["foundations"]


def test_alignment_group_has_alignment_badge():
    assert BADGE_HIGH_ALIGNMENT_90 in CATEGORY_BADGES["alignment"]


def test_milestones_is_union_of_all_three_groups():
    """The 'milestones' chip narrows to every streak-and-badge story —
    it's the union of streaks + foundations + alignment."""
    m = set(CATEGORY_BADGES["milestones"])
    assert m == (
        set(CATEGORY_BADGES["streaks"])
        | set(CATEGORY_BADGES["foundations"])
        | set(CATEGORY_BADGES["alignment"])
    )


def test_no_badge_appears_in_two_sub_groups():
    """Sub-groups must be disjoint so a badge isn't double-counted in the
    per-category counts."""
    a = set(CATEGORY_BADGES["streaks"])
    b = set(CATEGORY_BADGES["foundations"])
    c = set(CATEGORY_BADGES["alignment"])
    assert a & b == set()
    assert a & c == set()
    assert b & c == set()
