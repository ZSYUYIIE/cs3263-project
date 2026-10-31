import json
import random

import pytest

from m1_data.catalog import Catalog
from solver.explain import conflict_reasons, find_conflict, holds_together
from solver.run import run
from solver.spec import validate
from test_q2 import ATAP_DONE, BASE_DONE, pool_spec, random_request, spec

PREFIX = "these cannot all hold together with the courses you must take: "


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


def cleaned(request, cat):
    errors, _, _, result, missing = validate(request, cat)
    assert errors == [] and missing == []
    return result


def must(kind, **fields):
    return {"type": kind, "strength": "must", **fields}


NO_PLAN_EXAMPLE = spec(
    objective="earliest_graduation", light_sems=["last"], early=["CS2109S"],
    rules=[must("in_sem", course="CS4248", sem=4), must("in_sem", course="CS3263", sem=4),
           must("in_sem", course="CS2100", sem=3), must("before", a="CS2100", b="CS2106"),
           {"type": "in_sem", "course": "CS3230", "sem": 5, "strength": "prefer"}],
)


def reason_of(request, cat):
    out = run(request, cat)
    assert out["status"] == "NO_PLAN"
    assert len(out["reasons"]) == 1 and out["reasons"][0].startswith(PREFIX)
    return out["reasons"][0][len(PREFIX):]


def test_example_names_the_conflicting_rules(cat):
    text = reason_of(NO_PLAN_EXAMPLE, cat)
    assert "your rule: CS2100 in semester 3" in text
    assert "the MC limits (at most 8 MC per semester; semesters 6 blocked)" in text
    assert ("your rule: CS3263 in semester 4" in text) or ("your rule: CS4248 in semester 4" in text)
    assert "CS3230" not in text and "CS2106" not in text


def test_example_conflict_is_minimal_and_real(cat):
    request = cleaned(NO_PLAN_EXAMPLE, cat)
    core = find_conflict(request, cat)
    assert core and not holds_together(request, cat, core)
    for key in core:
        assert holds_together(request, cat, [k for k in core if k != key]), key


def test_dropping_the_cs2100_rule_makes_the_example_feasible(cat):
    rules = [r for r in NO_PLAN_EXAMPLE["rules"] if not (r["type"] == "in_sem" and r["course"] == "CS2100")]
    assert run({**NO_PLAN_EXAMPLE, "rules": rules}, cat)["status"] == "PLAN"


@pytest.mark.parametrize("request_data, expected, absent", [
    (spec(rules=[must("before", a="CS2100", b="CS2106"), must("before", a="CS2106", b="CS2100")]),
     ["your rule: CS2100 before CS2106", "your rule: CS2106 before CS2100"], ["MC limits"]),
    (spec(rules=[must("same_sem", a="CS3230", b="CS2100"), must("apart", a="CS3230", b="CS2100"),
                 must("in_sem", course="CS3263", sem=5)]),
     ["CS3230 and CS2100 in the same semester", "CS3230 and CS2100 in different semesters"], ["CS3263"]),
    (spec(mc_min=8), ["your minimum of 8 MC in every semester that has courses", "the MC limits"], ["your rule"]),
    (spec(rules=[must("before", a="CS3263", b="CS2109S")]),
     ["your rule: CS3263 before CS2109S", "the prerequisites of CS3263"], ["MC limits"]),
    (pool_spec(["CS2101", "CS2113"]), ["the course exclusions"], ["your rule", "MC limits"]),
    (pool_spec(["CS3231", "CS3233"], rules=[must("same_sem", a="CS3231", b="CS3233")]),
     ["CS3231 and CS3233 in the same semester", "the semesters in which the courses are offered"], ["MC limits"]),
    ({"query": "plan", "current_sem": 3, "completed": list(ATAP_DONE), "must_take": [], "atap_sems": [3, 4, 5]},
     ["the ATAP rules"], ["your rule"]),
])
def test_conflicts_name_exactly_the_expected_groups(cat, request_data, expected, absent):
    text = reason_of(request_data, cat)
    for part in expected:
        assert part in text, (part, text)
    for part in absent:
        assert part not in text, (part, text)


@pytest.mark.parametrize("request_data", [
    spec(rules=[must("before", a="CS2100", b="CS2106"), must("before", a="CS2106", b="CS2100")]),
    spec(mc_min=8),
    spec(rules=[must("before", a="CS3263", b="CS2109S")]),
    pool_spec(["CS2101", "CS2113"]),
    pool_spec(["CS3231", "CS3233"], rules=[must("same_sem", a="CS3231", b="CS3233")]),
])
def test_every_conflict_is_minimal(cat, request_data):
    request = cleaned(request_data, cat)
    core = find_conflict(request, cat)
    assert core and not holds_together(request, cat, core)
    for key in core:
        assert holds_together(request, cat, [k for k in core if k != key]), key


def test_specific_reasons_are_kept(cat):
    capacity = run(spec(mc_max=4), cat)["reasons"][0]
    assert "need 28 MC" in capacity and not capacity.startswith(PREFIX)
    unreachable = run({"query": "plan", "current_sem": 3, "must_take": ["CS3263"],
                       "completed": ["CS1101S", "CS1231S", "CS2040S", "MA1522", "ST2334", "CS3244"]}, cat)
    assert "ruled out by completed CS3244" in unreachable["reasons"][0]
    parity = run(pool_spec(["CS3234"], rules=[must("in_sem", course="CS3234", sem=3)]), cat)
    assert "cannot be placed in semester 3" in parity["reasons"][0]


def test_feasible_requests_are_not_explained(cat):
    request = cleaned(spec(objective="earliest_graduation"), cat)
    assert find_conflict(request, cat) is None
    assert conflict_reasons(request, cat) == []
    assert run(spec(objective="earliest_graduation"), cat)["status"] == "PLAN"


def test_explanation_is_deterministic(cat):
    assert run(NO_PLAN_EXAMPLE, cat) == run(NO_PLAN_EXAMPLE, cat)


def test_unsupported_wishes_are_still_reported_with_a_conflict(cat):
    out = run({**NO_PLAN_EXAMPLE, "unsupported": ["no 8am classes"]}, cat)
    assert out["reasons"][0].startswith(PREFIX) and out["not_applied"] == ["no 8am classes"]


@pytest.mark.parametrize("seed", range(60))
def test_random_infeasible_requests_get_minimal_conflicts(cat, seed):
    request_data = random_request(random.Random(seed))
    out = run(request_data, cat)
    if out["status"] != "NO_PLAN":
        return
    reason = out["reasons"][0]
    if not reason.startswith(PREFIX):
        return
    request = cleaned(request_data, cat)
    core = find_conflict(request, cat)
    assert core and not holds_together(request, cat, core)
    for key in core:
        assert holds_together(request, cat, [k for k in core if k != key]), (request_data, key)
