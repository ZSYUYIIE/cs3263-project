import json
import random

import pytest

from m1_data.catalog import Catalog
from solver.backtrack import VARIANTS, solve_with_stats
from solver.run import run
from test_q2 import (ATAP_DONE, BASE_DONE, MUST, POOL, hard_rule_violations, pool_spec,
                     random_request, semester_of, spec)

NAMES = list(VARIANTS)


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


def agree(request, cat, variant, limit=60):
    expected = run(request, cat)
    got, stats = solve_with_stats(request, cat, variant=variant, time_limit=limit)
    assert not stats["timed_out"], (variant, request)
    assert got["status"] == expected["status"], (variant, request, got, expected)
    if expected["status"] == "PLAN":
        assert got["last_semester"] == expected["last_semester"], (variant, request)
        assert len(got["preferences_met"]) == len(expected["preferences_met"]), (variant, request)
        assert sorted(got["preferences_met"] + got["preferences_not_met"]) == \
            sorted(expected["preferences_met"] + expected["preferences_not_met"])
        assert hard_rule_violations(request, semester_of(got), cat) == []
        assert got.get("added_prerequisites") == expected.get("added_prerequisites")
    return got, stats


@pytest.mark.parametrize("variant", NAMES)
@pytest.mark.parametrize("seed", range(60))
def test_random_pool_requests_agree_with_cp_sat(cat, variant, seed):
    agree(random_request(random.Random(seed)), cat, variant)


@pytest.mark.parametrize("variant", NAMES)
def test_variants_do_not_change_the_answer_quality_on_the_feasible_example(cat, variant):
    request = spec(
        rules=[{"type": "before", "a": "CS2100", "b": "CS2106", "strength": "must"},
               {"type": "in_sem", "course": "CS3230", "sem": 5, "strength": "prefer"}],
        objective="earliest_graduation", light_sems=["last"], early=["CS2109S"],
    )
    got, _ = agree(request, cat, variant)
    assert got["last_semester"] == 7 and len(got["preferences_met"]) == 3


@pytest.mark.parametrize("variant", NAMES)
def test_no_plan_example_agrees(cat, variant):
    request = spec(
        objective="earliest_graduation", light_sems=["last"], early=["CS2109S"],
        rules=[{"type": "in_sem", "course": "CS4248", "sem": 4, "strength": "must"},
               {"type": "in_sem", "course": "CS3263", "sem": 4, "strength": "must"},
               {"type": "in_sem", "course": "CS2100", "sem": 3, "strength": "must"},
               {"type": "before", "a": "CS2100", "b": "CS2106", "strength": "must"}],
    )
    got, _ = agree(request, cat, variant)
    assert got["status"] == "NO_PLAN" and got["reasons"]


@pytest.mark.parametrize("variant", NAMES)
@pytest.mark.parametrize("seed", range(10))
def test_infeasible_pool_requests_agree(cat, variant, seed):
    rng = random.Random(1000 + seed)
    request = random_request(rng)
    request["mc_max"] = 4
    request["sem_caps"] = {str(rng.randint(request["current_sem"], 8)): 0}
    request["must_take"] = rng.sample(POOL, 4)
    request.pop("rules", None)
    request.pop("early", None)
    request.pop("late", None)
    agree(request, cat, variant)


EXTRAS_CASES = [
    spec(objective="earliest_graduation"),
    spec(objective="min_total_mc", light_sems=["last"]),
    spec(objective="none", balance_load=True, early=["CS2109S"]),
    spec(objective="earliest_graduation", must_take=["CS3263", "CS2106"], mc_max=12),
    spec(objective="min_total_mc", must_take=["CS4248", "CS3230"], mc_max=8,
         rules=[{"type": "before", "a": "CS3230", "b": "CS4248", "strength": "prefer"}]),
]


@pytest.mark.parametrize("index", range(len(EXTRAS_CASES)))
def test_mac_agrees_when_prerequisites_must_be_added(cat, index):
    agree(EXTRAS_CASES[index], cat, "mac", limit=120)


def test_atap_request_agrees(cat):
    request = {"query": "plan", "current_sem": 5, "completed": list(ATAP_DONE),
               "must_take": ["CS2106", "CS3230", "ST2334"], "mc_max": 12,
               "atap_sems": [5, 6], "objective": "earliest_graduation"}
    got, _ = agree(request, cat, "mac", limit=120)
    assert any("CP3880" in courses for courses in got["plan"].values())


def test_light_and_balance_preferences_agree_with_extra_variants(cat):
    for variant in ("fc", "mac"):
        request = pool_spec(POOL[:4], objective="none", light_sems=["last", 6],
                            balance_load=True, late=["CS2109S"], mc_max=12)
        agree(request, cat, variant)


@pytest.mark.parametrize("variant", NAMES)
def test_status_paths_match_run(cat, variant):
    cases = [
        {"query": "plan", "completed": []},
        {"query": "plan", "current_sem": "three", "completed": [], "must_take": []},
        {"query": "plan", "current_sem": 3, "completed": list(BASE_DONE), "must_take": ["CS9999"]},
        {"query": "plan", "current_sem": 3, "completed": list(BASE_DONE), "must_take": ["CS2100"],
         "mc_max": 8, "sem_caps": {"3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0}},
    ]
    for request in cases:
        expected = run(request, cat)
        got, stats = solve_with_stats(request, cat, variant=variant, time_limit=30)
        assert got["status"] == expected["status"]
        assert got.get("errors") == expected.get("errors")
        assert got.get("missing") == expected.get("missing")
        assert stats["timed_out"] is False


@pytest.mark.parametrize("variant", NAMES)
def test_q1_passes_through_with_zero_counters(cat, variant):
    request = {"query": "eligible", "completed": list(BASE_DONE), "target": "CS3263", "current_sem": 3}
    expected = run(request, cat)
    got, stats = solve_with_stats(request, cat, variant=variant)
    assert got == expected
    assert stats["nodes"] == stats["backtracks"] == stats["checks"] == 0
    assert stats["timed_out"] is False and stats["seconds"] >= 0


def test_stats_have_the_agreed_fields_and_are_counted(cat):
    request = pool_spec(POOL[:4], objective="earliest_graduation")
    _, stats = solve_with_stats(request, cat, variant="plain")
    assert set(stats) == {"nodes", "backtracks", "checks", "seconds", "timed_out"}
    assert stats["nodes"] > 0 and stats["checks"] > 0 and stats["seconds"] > 0
    assert 0 <= stats["backtracks"] <= stats["nodes"]


def test_forward_checking_and_mac_search_no_more_nodes_than_plain(cat):
    request = pool_spec(POOL[:5], objective="earliest_graduation", mc_max=8)
    nodes = {v: solve_with_stats(request, cat, variant=v)[1]["nodes"] for v in NAMES}
    assert nodes["fc"] <= nodes["plain"]
    assert nodes["mac"] <= nodes["fc"] * 2


def test_tiny_time_limit_gives_timed_out(cat):
    request = pool_spec(POOL[:6], objective="earliest_graduation", balance_load=True, mc_max=8)
    got, stats = solve_with_stats(request, cat, variant="plain", time_limit=0.0001)
    assert got["status"] == "TIMED_OUT" and got["reasons"]
    assert stats["timed_out"] is True


def test_unknown_variant_is_rejected(cat):
    with pytest.raises(ValueError):
        solve_with_stats(pool_spec(POOL[:2]), cat, variant="ac3")


@pytest.mark.parametrize("variant", NAMES)
def test_answers_are_deterministic_and_json_serialisable(cat, variant):
    request = pool_spec(POOL[:4], objective="earliest_graduation", light_sems=["last"], balance_load=True)
    first, _ = solve_with_stats(request, cat, variant=variant)
    second, _ = solve_with_stats(request, cat, variant=variant)
    assert first == second
    json.dumps(first)


def test_input_is_not_mutated(cat):
    request = pool_spec(POOL[:4], objective="none", light_sems=["last"], early=["CS2109S"])
    before = json.dumps(request, sort_keys=True)
    solve_with_stats(request, cat, variant="mac")
    assert json.dumps(request, sort_keys=True) == before


def test_must_course_list_matches_run_for_the_full_example(cat):
    request = spec(must_take=MUST, objective="earliest_graduation")
    agree(request, cat, "mac", limit=120)
