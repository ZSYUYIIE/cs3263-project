import itertools
import json

import pytest

from m1_data.catalog import Catalog, satisfied
from solver.run import run

BASE_DONE = ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522"]
MUST = ["ST2334", "CS2109S", "CS3263", "CS4248", "CS3230", "CS2100", "CS2106"]


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


def spec(**changes):
    base = {
        "query": "plan",
        "current_sem": 3,
        "completed": list(BASE_DONE),
        "must_take": list(MUST),
        "mc_max": 8,
        "sem_caps": {"6": 0},
    }
    base.update(changes)
    return base


def term(semester):
    return 1 if semester % 2 == 1 else 2


def semester_of(answer):
    return {code: int(s) for s, courses in answer["plan"].items() for code in courses}


def cap_of(request, semester):
    return request.get("sem_caps", {}).get(str(semester), request.get("mc_max", 20))


def hard_rule_violations(request, assign, cat):
    done = set(request["completed"])
    problems = []
    load, other = {}, {}
    for code, s in assign.items():
        record = cat[code]
        load[s] = load.get(s, 0) + int(record["mc"])
        if code != "CP3880":
            other[s] = other.get(s, 0) + int(record["mc"])
        if term(s) not in record["offered"]:
            problems.append(f"{code} not offered in semester {s}")
        before = done | {c for c, t in assign.items() if t < s}
        same = before | {c for c, t in assign.items() if t == s}
        if not satisfied(record["prereq"]["logic"], before):
            problems.append(f"{code} prerequisite unmet in semester {s}")
        if record["coreq"]["logic"] is not None and not satisfied(record["coreq"]["logic"], same):
            problems.append(f"{code} corequisite unmet in semester {s}")
        if cat.blocked_by(code, done):
            problems.append(f"{code} blocked by completed course")
        for other_code in record["preclusion"]["mutually_exclusive_with"]:
            if other_code in assign and other_code != code:
                problems.append(f"{code} excludes {other_code}")
    for s in set(load):
        cap = cap_of(request, s)
        if "CP3880" in assign and assign["CP3880"] == s:
            if other.get(s, 0) > min(8, cap):
                problems.append(f"semester {s} other load {other.get(s, 0)} over ATAP cap")
        elif load[s] > cap:
            problems.append(f"semester {s} load {load[s]} over cap {cap}")
        if "mc_min" in request and load[s] < request["mc_min"]:
            problems.append(f"semester {s} load {load[s]} under mc_min")
    for code in request["must_take"]:
        if code not in done and code not in assign:
            problems.append(f"{code} missing")
    for rule in request.get("rules", []):
        if rule["strength"] != "must":
            continue
        if rule["type"] == "before" and not assign[rule["a"]] < assign[rule["b"]]:
            problems.append(f"must before {rule}")
        if rule["type"] == "in_sem" and assign[rule["course"]] != rule["sem"]:
            problems.append(f"must in_sem {rule}")
        if rule["type"] == "apart" and assign[rule["a"]] == assign[rule["b"]]:
            problems.append(f"must apart {rule}")
        if rule["type"] == "same_sem" and assign[rule["a"]] != assign[rule["b"]]:
            problems.append(f"must same_sem {rule}")
    return problems


PLAN_CACHE = {}


def all_valid_plans(request, cat):
    must_rules = [r for r in request.get("rules", []) if r["strength"] == "must"]
    key = json.dumps([request["current_sem"], request["completed"], request["must_take"],
                      request.get("mc_max"), request.get("mc_min"), request.get("sem_caps"), must_rules],
                     sort_keys=True)
    if key not in PLAN_CACHE:
        PLAN_CACHE[key] = enumerate_valid_plans(request, cat)
    return PLAN_CACHE[key]


def enumerate_valid_plans(request, cat):
    courses = [c for c in request["must_take"] if c not in request["completed"]]
    sems = [s for s in range(request["current_sem"], 9) if cap_of(request, s) > 0]
    plans = []
    for combo in itertools.product(sems, repeat=len(courses)):
        assign = dict(zip(courses, combo))
        loads = {}
        for code, s in assign.items():
            loads[s] = loads.get(s, 0) + int(cat[code]["mc"])
        if any(v > cap_of(request, s) for s, v in loads.items()):
            continue
        if not hard_rule_violations(request, assign, cat):
            plans.append(assign)
    return plans


def loads_of(assign, cat):
    loads = {}
    for code, s in assign.items():
        loads[s] = loads.get(s, 0) + int(cat[code]["mc"])
    return loads


def preference_count(request, assign, tied, cat):
    count = 0
    done = set(request["completed"])
    cur = request["current_sem"]
    loads = loads_of(assign, cat)
    last = max(assign.values())
    window = 8 - cur + 1 if request.get("objective", "none") == "none" else last - cur + 1
    total = sum(loads.values())
    for rule in request.get("rules", []):
        if rule["strength"] != "prefer":
            continue
        if rule["type"] == "before":
            count += assign[rule["a"]] < assign[rule["b"]]
        elif rule["type"] == "in_sem":
            count += assign[rule["course"]] == rule["sem"]
        elif rule["type"] == "apart":
            count += assign[rule["a"]] != assign[rule["b"]]
        else:
            count += assign[rule["a"]] == assign[rule["b"]]
    for entry in request.get("light_sems", []):
        semester = last if entry == "last" else entry
        if semester < cur:
            continue
        count += loads.get(semester, 0) * window < total
    if request.get("balance_load"):
        best = min(max(loads_of(a, cat).values()) for a in tied)
        count += max(loads.values()) == best
    for code in request.get("early", []):
        count += assign[code] == min(a[code] for a in tied)
    for code in request.get("late", []):
        count += assign[code] == max(a[code] for a in tied)
    return count


def optimum(request, cat):
    plans = all_valid_plans(request, cat)
    objective = request.get("objective", "none")
    if objective == "earliest_graduation":
        best = min(max(a.values()) for a in plans)
        tied = [a for a in plans if max(a.values()) == best]
    else:
        tied = plans
    best_count = max(preference_count(request, a, tied, cat) for a in tied)
    return tied, best_count


def test_feasible_example_is_valid_and_optimal(cat):
    request = spec(
        rules=[{"type": "before", "a": "CS2100", "b": "CS2106", "strength": "must"},
               {"type": "in_sem", "course": "CS3230", "sem": 5, "strength": "prefer"}],
        objective="earliest_graduation", light_sems=["last"], early=["CS2109S"],
    )
    out = run(request, cat)
    assert out["status"] == "PLAN"
    assign = semester_of(out)
    assert hard_rule_violations(request, assign, cat) == []
    tied, best = optimum(request, cat)
    assert out["last_semester"] == max(tied[0].values()) == 7
    assert len(out["preferences_met"]) == best == 3
    assert out["preferences_not_met"] == []
    assert out["mc_per_semester"]["7"] == 4 and out["plan"]["6"] == []


def test_infeasible_preclusion_gives_reachability_reason(cat):
    request = {"query": "plan", "current_sem": 3, "must_take": ["CS3263"],
               "completed": ["CS1101S", "CS1231S", "CS2040S", "MA1522", "ST2334", "CS3244"]}
    out = run(request, cat)
    assert out["status"] == "NO_PLAN"
    assert "CS2109S is ruled out by completed CS3244" in out["reasons"][0]


def test_capacity_reason(cat):
    out = run(spec(mc_max=4), cat)
    assert out["status"] == "NO_PLAN"
    assert "need 28 MC" in out["reasons"][0] and "at most 20 MC" in out["reasons"][0]


def test_conflicting_must_rules(cat):
    rules = [{"type": "before", "a": "CS2100", "b": "CS2106", "strength": "must"},
             {"type": "before", "a": "CS2106", "b": "CS2100", "strength": "must"}]
    assert run(spec(rules=rules), cat)["status"] == "NO_PLAN"


@pytest.mark.parametrize("rule", [
    {"type": "before", "a": "CS3230", "b": "CS3263", "strength": "must"},
    {"type": "in_sem", "course": "CS4248", "sem": 4, "strength": "must"},
    {"type": "apart", "a": "ST2334", "b": "CS2109S", "strength": "must"},
    {"type": "same_sem", "a": "ST2334", "b": "CS2109S", "strength": "must"},
])
def test_must_rules_hold_and_match_brute_force(cat, rule):
    request = spec(rules=[rule], objective="earliest_graduation")
    out = run(request, cat)
    assert out["status"] == "PLAN"
    assert hard_rule_violations(request, semester_of(out), cat) == []
    tied, _ = optimum(request, cat)
    assert out["last_semester"] == max(tied[0].values())


def test_solver_may_use_an_alternative_prerequisite(cat):
    rules = [{"type": "before", "a": "CS2106", "b": "CS2100", "strength": "must"}]
    request = spec(rules=rules, objective="earliest_graduation")
    out = run(request, cat)
    assert out["status"] == "PLAN"
    assert out["added_prerequisites"]
    assert hard_rule_violations(request, semester_of(out), cat) == []
    assert out["plan"] and semester_of(out)["CS2106"] < semester_of(out)["CS2100"]


def test_semester_caps_block_the_exchange_semester(cat):
    out = run(spec(objective="earliest_graduation"), cat)
    assert out["plan"]["6"] == []
    assert all(int(s) != 6 or not c for s, c in out["plan"].items())


def test_mc_min_applies_to_used_semesters(cat):
    request = spec(must_take=MUST[:6], mc_min=8, objective="earliest_graduation")
    out = run(request, cat)
    assert out["status"] == "PLAN"
    assert all(v == 0 or v >= 8 for v in out["mc_per_semester"].values())
    assert hard_rule_violations(request, semester_of(out), cat) == []


def test_mc_min_is_never_met_by_inventing_courses(cat):
    out = run(spec(mc_min=8, objective="earliest_graduation"), cat)
    assert out["status"] == "NO_PLAN"


def test_prerequisite_is_added_before_the_course_that_needs_it(cat):
    request = {"query": "plan", "current_sem": 3, "must_take": ["CS3263"],
               "completed": ["CS1101S", "CS1231S", "CS2040S", "MA1522", "MA1521", "ST2334"],
               "objective": "earliest_graduation"}
    out = run(request, cat)
    assert out["status"] == "PLAN"
    assign = semester_of(out)
    assert "CS2109S" in out["added_prerequisites"]
    assert assign["CS2109S"] < assign["CS3263"]
    assert out["last_semester"] == 4


def test_course_already_completed_is_noted(cat):
    out = run(spec(must_take=MUST + ["CS2040S"]), cat)
    assert out["status"] == "PLAN"
    assert "CS2040S is already completed" in out["notes"]


def test_nothing_left_to_plan(cat):
    request = {"query": "plan", "current_sem": 3, "must_take": ["CS2040S"], "completed": ["CS2040S"]}
    out = run(request, cat)
    assert out["status"] == "PLAN" and out["plan"] == {} and out["last_semester"] is None


@pytest.mark.parametrize("extra", [
    {"balance_load": True},
    {"late": ["CS2109S"]},
    {"early": ["CS3263"]},
    {"light_sems": [4]},
    {"light_sems": ["last", 5]},
    {"rules": [{"type": "apart", "a": "CS3263", "b": "CS4248", "strength": "prefer"},
               {"type": "same_sem", "a": "ST2334", "b": "CS2109S", "strength": "prefer"},
               {"type": "before", "a": "CS3230", "b": "CS2100", "strength": "prefer"}]},
])
def test_preference_count_matches_brute_force(cat, extra):
    for objective in ("earliest_graduation", "none"):
        request = spec(objective=objective, **extra)
        out = run(request, cat)
        assert out["status"] == "PLAN"
        assign = semester_of(out)
        assert hard_rule_violations(request, assign, cat) == []
        tied, best = optimum(request, cat)
        if objective == "earliest_graduation":
            assert out["last_semester"] == max(tied[0].values())
        assert len(out["preferences_met"]) == best, (objective, out)


def test_min_total_mc_counts_chosen_prerequisites(cat):
    request = {"query": "plan", "current_sem": 3, "must_take": ["CS3263"],
               "completed": ["CS1101S", "CS1231S", "CS2040S", "MA1522", "MA1521", "ST2334"],
               "objective": "min_total_mc"}
    out = run(request, cat)
    assert out["status"] == "PLAN"
    assert sum(out["mc_per_semester"].values()) == 8


def test_atap_is_added_and_respects_its_rules(cat):
    request = {"query": "plan", "current_sem": 3, "must_take": ["CS3263", "CS3230"],
               "completed": BASE_DONE + ["CS2109S"], "atap_sems": [5, 6],
               "objective": "earliest_graduation"}
    out = run(request, cat)
    assert out["status"] == "PLAN"
    assign = semester_of(out)
    assert assign["CP3880"] in (5, 6)
    assert assign["CP3880"] < out["last_semester"]
    assert hard_rule_violations(request, assign, cat) == []
    assert out["added_prerequisites"]


def test_atap_not_added_when_not_requested(cat):
    out = run(spec(objective="earliest_graduation"), cat)
    assert "CP3880" not in semester_of(out)


def test_atap_in_a_single_semester_is_followed(cat):
    request = {"query": "plan", "current_sem": 3, "must_take": ["CS3263"],
               "completed": BASE_DONE + ["CS2109S", "CS2101", "CS2103T"], "atap_sems": [4]}
    out = run(request, cat)
    assert out["status"] == "PLAN"
    assert semester_of(out)["CP3880"] == 4


def test_atap_other_courses_capped_at_eight_mc(cat):
    request = {"query": "plan", "current_sem": 3,
               "must_take": ["CS3263", "CS3230", "CS4248", "CS2100"],
               "completed": BASE_DONE + ["CS2109S", "CS2101", "CS2103T"], "atap_sems": [3],
               "objective": "earliest_graduation"}
    out = run(request, cat)
    assert out["status"] == "PLAN"
    assert out["mc_per_semester"]["3"] <= 12 + 8


def test_output_is_deterministic(cat):
    request = spec(objective="earliest_graduation", balance_load=True, light_sems=["last"])
    assert run(request, cat) == run(request, cat)


def test_unsupported_wishes_are_reported(cat):
    out = run(spec(unsupported=["no 8am classes"]), cat)
    assert out["not_applied"] == ["no 8am classes"]
    request = {"query": "plan", "current_sem": 3, "must_take": ["CS3263"],
               "completed": ["CS1101S", "CS1231S", "CS2040S", "MA1522", "ST2334", "CS3244"],
               "unsupported": ["no 8am classes"]}
    assert run(request, cat)["not_applied"] == ["no 8am classes"]


import random

POOL = ["CS2100", "CS2104", "CS2105", "CS2107", "CS2108", "CS2109S", "CS3230", "CS3231", "CS3233", "CS3234", "ST2334"]
ATAP_DONE = BASE_DONE + ["CS2101", "CS2103T"]


def pool_spec(courses, **changes):
    base = {"query": "plan", "current_sem": 3, "completed": list(BASE_DONE),
            "must_take": list(courses), "mc_max": 8}
    base.update(changes)
    return base


def expected_best_plans(request, cat):
    tied, best = optimum(request, cat)
    return [a for a in tied if preference_count(request, a, tied, cat) == best], tied, best


def test_pool_courses_need_no_extra_prerequisites(cat):
    for code in POOL:
        assert satisfied(cat[code]["prereq"]["logic"], set(BASE_DONE)), code
        assert cat[code]["coreq"]["logic"] is None, code


def test_objective_outranks_preferences(cat):
    rule = {"type": "in_sem", "course": "CS4248", "sem": 8, "strength": "prefer"}
    earliest = run(spec(objective="earliest_graduation", rules=[rule]), cat)
    assert earliest["last_semester"] == 7
    assert earliest["preferences_not_met"] == ["CS4248 in semester 8"]
    free = run(spec(objective="none", rules=[rule]), cat)
    assert semester_of(free)["CS4248"] == 8
    assert free["preferences_met"] == ["CS4248 in semester 8"]


def test_two_preferences_that_cannot_both_hold_give_one_met(cat):
    rules = [{"type": "in_sem", "course": "CS3230", "sem": 4, "strength": "prefer"},
             {"type": "in_sem", "course": "CS3230", "sem": 5, "strength": "prefer"}]
    out = run(spec(rules=rules), cat)
    assert len(out["preferences_met"]) == 1 and len(out["preferences_not_met"]) == 1


def test_must_rule_beats_a_conflicting_preference(cat):
    rules = [{"type": "in_sem", "course": "CS3230", "sem": 5, "strength": "must"},
             {"type": "in_sem", "course": "CS3230", "sem": 4, "strength": "prefer"}]
    out = run(spec(rules=rules), cat)
    assert semester_of(out)["CS3230"] == 5
    assert out["preferences_not_met"] == ["CS3230 in semester 4"]


def test_min_total_mc_with_a_fixed_list_lets_preferences_decide(cat):
    request = spec(objective="min_total_mc",
                   rules=[{"type": "before", "a": "CS3263", "b": "CS3230", "strength": "prefer"}])
    out = run(request, cat)
    assert out["status"] == "PLAN"
    _, _, best = expected_best_plans(request, cat)
    assert len(out["preferences_met"]) == best == 1
    assert sum(out["mc_per_semester"].values()) == 28


def test_light_semester_bonus_picks_the_lowest_load(cat):
    request = spec(objective="earliest_graduation", light_sems=[4])
    out = run(request, cat)
    best_plans, _, _ = expected_best_plans(request, cat)
    expected = min(loads_of(a, cat).get(4, 0) for a in best_plans)
    assert out["mc_per_semester"].get("4", 0) == expected


@pytest.mark.parametrize("objective", ["earliest_graduation", "none", "min_total_mc"])
def test_balance_load_reaches_the_smallest_possible_peak(cat, objective):
    request = spec(objective=objective, balance_load=True)
    out = run(request, cat)
    tied, _ = optimum(request, cat)
    assert max(out["mc_per_semester"].values()) == min(max(loads_of(a, cat).values()) for a in tied)
    assert out["preferences_met"] == ["largest semester load is as small as possible"]


def test_early_and_late_on_the_same_course_are_scored_separately(cat):
    request = pool_spec(["CS3230", "CS3231"], objective="none", early=["CS3230"], late=["CS3230"])
    out = run(request, cat)
    assert sorted(out["preferences_met"] + out["preferences_not_met"]) == [
        "CS3230 as early as possible", "CS3230 as late as possible"]
    assert len(out["preferences_met"]) == 1


def test_preferences_on_courses_outside_the_plan_are_not_met_and_add_nothing(cat):
    request = pool_spec(["CS3230"], rules=[{"type": "in_sem", "course": "CS2100", "sem": 4, "strength": "prefer"}],
                        early=["CS2100"])
    out = run(request, cat)
    assert sorted(semester_of(out)) == ["CS3230"]
    assert "added_prerequisites" not in out
    assert sorted(out["preferences_not_met"]) == ["CS2100 as early as possible", "CS2100 in semester 4"]
    assert out["preferences_met"] == []


@pytest.mark.parametrize("objective", ["earliest_graduation", "none"])
@pytest.mark.parametrize("light", [[3], [4], ["last"]])
def test_light_preference_never_pulls_in_unneeded_courses(cat, objective, light):
    request = {"query": "plan", "current_sem": 3, "completed": list(BASE_DONE), "must_take": ["CS3263"],
               "mc_max": 20, "objective": objective}
    plain = run(request, cat)
    with_light = run({**request, "light_sems": light}, cat)
    assert len(with_light["added_prerequisites"]) == len(plain["added_prerequisites"]) == 2
    assert sum(with_light["mc_per_semester"].values()) == sum(plain["mc_per_semester"].values()) == 12


@pytest.mark.parametrize("objective", ["earliest_graduation", "none", "min_total_mc"])
def test_light_preferences_on_an_empty_plan_are_not_met(cat, objective):
    request = {"query": "plan", "current_sem": 3, "completed": ["CS2040S"], "must_take": ["CS2040S"],
               "objective": objective, "light_sems": [4, "last"]}
    out = run(request, cat)
    assert out["plan"] == {} and out["preferences_met"] == []
    assert len(out["preferences_not_met"]) == 2


def test_atap_in_must_take_without_atap_sems_is_planned(cat):
    request = {"query": "plan", "current_sem": 3, "completed": list(ATAP_DONE),
               "must_take": ["CP3880", "CS3230"], "mc_max": 20, "objective": "earliest_graduation"}
    out = run(request, cat)
    assert out["status"] == "PLAN"
    assign = semester_of(out)
    assert hard_rule_violations(request, assign, cat) == []
    assert assign["CP3880"] < out["last_semester"]


def test_atap_in_a_must_rule_without_atap_sems_is_planned(cat):
    request = {"query": "plan", "current_sem": 3, "completed": list(ATAP_DONE), "must_take": ["CS3230"],
               "mc_max": 20, "rules": [{"type": "before", "a": "CP3880", "b": "CS3230", "strength": "must"}]}
    out = run(request, cat)
    assert out["status"] == "PLAN"
    assign = semester_of(out)
    assert assign["CP3880"] < assign["CS3230"]
    assert hard_rule_violations(request, assign, cat) == []


def test_atap_alone_cannot_be_the_graduating_semester(cat):
    request = {"query": "plan", "current_sem": 3, "completed": list(ATAP_DONE), "must_take": [],
               "atap_sems": [3, 4, 5]}
    assert run(request, cat)["status"] == "NO_PLAN"


def test_atap_with_a_single_other_course_leaves_atap_before_it(cat):
    request = {"query": "plan", "current_sem": 3, "completed": list(ATAP_DONE), "must_take": ["CS3230"],
               "atap_sems": [3, 4, 5], "objective": "earliest_graduation"}
    out = run(request, cat)
    assign = semester_of(out)
    assert assign["CP3880"] == 3 and assign["CS3230"] == 4 and out["last_semester"] == 4


@pytest.mark.parametrize("rule, text", [
    ({"type": "in_sem", "course": "CS2040S", "sem": 4, "strength": "must"}, "already completed"),
    ({"type": "before", "a": "CS3230", "b": "CS2040S", "strength": "must"}, "already completed"),
    ({"type": "same_sem", "a": "CS2040S", "b": "CS3230", "strength": "must"}, "already completed"),
    ({"type": "in_sem", "course": "CS3230", "sem": 2, "strength": "must"}, "cannot be placed in semester 2"),
    ({"type": "in_sem", "course": "CS3230", "sem": 6, "strength": "must"}, "cannot be placed in semester 6"),
])
def test_must_rules_that_cannot_hold_give_no_plan_with_a_reason(cat, rule, text):
    out = run(pool_spec(["CS3230"], sem_caps={"6": 0}, rules=[rule]), cat)
    assert out["status"] == "NO_PLAN"
    assert any(text in r for r in out["reasons"]), out["reasons"]


@pytest.mark.parametrize("rule", [
    {"type": "before", "a": "CS2040S", "b": "CS3230", "strength": "must"},
    {"type": "apart", "a": "CS2040S", "b": "CS3230", "strength": "must"},
    {"type": "same_sem", "a": "CS2040S", "b": "CS1231S", "strength": "must"},
])
def test_must_rules_already_satisfied_by_completed_courses_are_accepted(cat, rule):
    assert run(pool_spec(["CS3230"], rules=[rule]), cat)["status"] == "PLAN"


@pytest.mark.parametrize("rule, met", [
    ({"type": "before", "a": "CS2040S", "b": "CS3230", "strength": "prefer"}, True),
    ({"type": "before", "a": "CS3230", "b": "CS2040S", "strength": "prefer"}, False),
    ({"type": "apart", "a": "CS2040S", "b": "CS3230", "strength": "prefer"}, True),
    ({"type": "same_sem", "a": "CS2040S", "b": "CS3230", "strength": "prefer"}, False),
    ({"type": "same_sem", "a": "CS2040S", "b": "CS1231S", "strength": "prefer"}, True),
    ({"type": "in_sem", "course": "CS2040S", "sem": 4, "strength": "prefer"}, False),
    ({"type": "in_sem", "course": "CS3230", "sem": 2, "strength": "prefer"}, False),
])
def test_preferences_involving_completed_courses(cat, rule, met):
    out = run(pool_spec(["CS3230"], rules=[rule]), cat)
    assert out["status"] == "PLAN"
    assert (len(out["preferences_met"]) == 1) is met
    assert len(out["preferences_met"]) + len(out["preferences_not_met"]) == 1


def test_a_must_rule_pulls_its_course_into_the_plan(cat):
    request = pool_spec(["CS3230"], rules=[{"type": "in_sem", "course": "CS2105", "sem": 5, "strength": "must"}])
    out = run(request, cat)
    assert semester_of(out)["CS2105"] == 5
    assert "CS2105" not in out.get("added_prerequisites", [])


def test_terms_follow_semester_parity(cat):
    request = pool_spec(["CS3231", "CS3234", "CS3233", "CS2104"], objective="earliest_graduation", mc_max=16)
    out = run(request, cat)
    assign = semester_of(out)
    assert assign["CS3231"] % 2 == 1 and assign["CS2104"] % 2 == 1
    assert assign["CS3234"] % 2 == 0 and assign["CS3233"] % 2 == 0
    assert hard_rule_violations(request, assign, cat) == []


def test_course_offered_only_in_semester_one_cannot_be_planned_in_semester_eight(cat):
    out = run(pool_spec(["CS3231"], current_sem=8), cat)
    assert out["status"] == "NO_PLAN"
    assert "CS3231 cannot be placed in any remaining semester" in out["reasons"][0]
    assert run(pool_spec(["CS3234"], current_sem=8), cat)["status"] == "PLAN"


def test_planning_from_the_last_semester_only(cat):
    out = run(pool_spec(["CS3234", "CS2100"], current_sem=8), cat)
    assert out["status"] == "PLAN" and out["plan"] == {"8": ["CS2100", "CS3234"]}
    assert out["mc_per_semester"] == {"8": 8} and out["last_semester"] == 8
    capped = run(pool_spec(["CS3234", "CS2100"], current_sem=8, mc_max=4), cat)
    assert capped["status"] == "NO_PLAN" and "need 8 MC" in capped["reasons"][0]


def test_planning_from_the_first_semester(cat):
    request = pool_spec(["CS2100", "CS3230"], current_sem=1, objective="earliest_graduation")
    out = run(request, cat)
    assert out["last_semester"] == 1 and sorted(out["plan"]["1"]) == ["CS2100", "CS3230"]


def test_semester_cap_can_be_higher_than_mc_max(cat):
    request = pool_spec(["CS3230", "CS2105", "CS2100"], mc_max=4, sem_caps={"4": 12},
                        objective="earliest_graduation")
    out = run(request, cat)
    assert out["last_semester"] == 4 and out["mc_per_semester"]["4"] == 12
    assert hard_rule_violations(request, semester_of(out), cat) == []


def test_caps_of_past_semesters_are_ignored(cat):
    out = run(pool_spec(["CS3230"], current_sem=5, sem_caps={"2": 0, "3": 0}), cat)
    assert out["status"] == "PLAN" and list(out["plan"]) == ["5"]


def test_every_remaining_semester_blocked_gives_a_capacity_reason(cat):
    caps = {str(s): 0 for s in range(3, 9)}
    out = run(pool_spec(["CS3230"], sem_caps=caps), cat)
    assert out["status"] == "NO_PLAN" and "cannot be placed in any remaining semester" in out["reasons"][0]


def test_mc_min_that_no_course_combination_can_reach_gives_no_plan(cat):
    assert run(pool_spec(["CS3230"], mc_min=8), cat)["status"] == "NO_PLAN"


def test_mc_min_still_allows_empty_semesters(cat):
    out = run(pool_spec(["CS3230", "CS2105"], mc_min=8, sem_caps={"4": 0}, objective="earliest_graduation"), cat)
    assert out["status"] == "PLAN"
    assert all(v == 0 or v >= 8 for v in out["mc_per_semester"].values())


@pytest.mark.parametrize("objective", ["none", "min_total_mc"])
def test_without_a_ranking_objective_the_plan_still_ends_as_early_as_possible(cat, objective):
    request = spec(objective=objective)
    out = run(request, cat)
    plans = all_valid_plans(request, cat)
    assert out["last_semester"] == min(max(a.values()) for a in plans)


@pytest.mark.parametrize("request_maker", [
    lambda: spec(objective="earliest_graduation", light_sems=["last", 4], balance_load=True),
    lambda: spec(objective="none", early=["CS3263"], late=["CS2100"]),
    lambda: spec(objective="min_total_mc", rules=[{"type": "apart", "a": "CS3230", "b": "CS3263", "strength": "prefer"}]),
    lambda: pool_spec(["CS3230", "CS3234"], current_sem=4, objective="earliest_graduation"),
])
def test_answer_invariants(cat, request_maker):
    request = request_maker()
    out = run(request, cat)
    assert out["status"] == "PLAN"
    keys = [int(k) for k in out["plan"]]
    assert keys == list(range(request["current_sem"], out["last_semester"] + 1))
    assert out["plan"][str(out["last_semester"])]
    assert set(out["mc_per_semester"]) == set(out["plan"])
    for s, courses in out["plan"].items():
        assert out["mc_per_semester"][s] == sum(int(cat[c]["mc"]) for c in courses)
        assert courses == sorted(courses)
    placed = [c for courses in out["plan"].values() for c in courses]
    assert len(placed) == len(set(placed))
    assert set(request["must_take"]) - set(request["completed"]) <= set(placed)
    assert set(out["preferences_met"]).isdisjoint(out["preferences_not_met"])
    assert out["objective"] == request.get("objective", "none")
    assert hard_rule_violations(request, semester_of(out), cat) == []


def test_no_plan_answer_has_only_the_documented_fields(cat):
    out = run(spec(mc_max=4), cat)
    assert set(out) == {"status", "reasons"}
    out = run(spec(mc_max=4, unsupported=["no 8am"]), cat)
    assert set(out) == {"status", "reasons", "not_applied"}


def test_plan_answer_has_the_documented_fields(cat):
    out = run(spec(objective="earliest_graduation"), cat)
    assert set(out) == {"status", "objective", "last_semester", "plan", "mc_per_semester",
                        "preferences_met", "preferences_not_met"}


def random_request(rng):
    cur = rng.choice([2, 3, 4, 5])
    courses = rng.sample(POOL, rng.choice([2, 3, 4]))
    request = {"query": "plan", "current_sem": cur, "completed": list(BASE_DONE),
               "must_take": courses, "mc_max": rng.choice([4, 8, 12])}
    if rng.random() < 0.4:
        request["sem_caps"] = {str(rng.randint(cur, 8)): rng.choice([0, 4, 12])}
    if rng.random() < 0.3:
        request["mc_min"] = rng.choice([m for m in (4, 8) if m <= request["mc_max"]])
    rules = []
    for _ in range(rng.randint(0, 3)):
        kind = rng.choice(["before", "apart", "same_sem", "in_sem"])
        strength = rng.choice(["must", "prefer", "prefer"])
        if kind == "in_sem":
            rule = {"type": kind, "course": rng.choice(courses), "sem": rng.randint(cur, 8), "strength": strength}
        else:
            a, b = rng.sample(courses, 2)
            rule = {"type": kind, "a": a, "b": b, "strength": strength}
        if rule not in rules:
            rules.append(rule)
    if rules:
        request["rules"] = rules
    request["objective"] = rng.choice(["earliest_graduation", "none", "min_total_mc"])
    light = rng.sample(["last"] + list(range(cur, 9)), rng.randint(0, 2))
    if light:
        request["light_sems"] = light
    if rng.random() < 0.5:
        request["balance_load"] = True
    for key in ("early", "late"):
        picked = rng.sample(courses, rng.randint(0, 2))
        if picked:
            request[key] = picked
    return request


def stated_preferences(request):
    return (sum(r["strength"] == "prefer" for r in request.get("rules", []))
            + len(request.get("light_sems", [])) + bool(request.get("balance_load"))
            + len(request.get("early", [])) + len(request.get("late", [])))


@pytest.mark.parametrize("seed", range(60))
def test_random_requests_match_brute_force(cat, seed):
    request = random_request(random.Random(seed))
    out = run(request, cat)
    plans = all_valid_plans(request, cat)
    if not plans:
        assert out["status"] == "NO_PLAN", request
        return
    assert out["status"] == "PLAN", (request, out)
    assign = semester_of(out)
    assert hard_rule_violations(request, assign, cat) == [], request
    tied, best = optimum(request, cat)
    if request["objective"] == "earliest_graduation":
        assert out["last_semester"] == max(tied[0].values()), request
    assert len(out["preferences_met"]) == best, (request, out)
    assert len(out["preferences_met"]) + len(out["preferences_not_met"]) == stated_preferences(request)
    assert "added_prerequisites" not in out


@pytest.mark.parametrize("seed", range(15))
def test_random_atap_requests_are_valid(cat, seed):
    rng = random.Random(1000 + seed)
    cur = rng.choice([2, 3, 4])
    request = {
        "query": "plan", "current_sem": cur, "completed": list(ATAP_DONE),
        "must_take": rng.sample(["CS3230", "CS2105", "CS2100", "CS2107", "CS3234", "CS2104"], rng.choice([1, 2, 3])),
        "atap_sems": sorted(rng.sample(range(cur, 9), rng.choice([1, 2, 3]))),
        "mc_max": rng.choice([8, 12, 20]),
        "objective": rng.choice(["earliest_graduation", "none", "min_total_mc"]),
    }
    out = run(request, cat)
    assert out["status"] in ("PLAN", "NO_PLAN")
    if out["status"] == "PLAN":
        assign = semester_of(out)
        assert hard_rule_violations(request, assign, cat) == []
        assert assign["CP3880"] in request["atap_sems"]
        assert assign["CP3880"] < out["last_semester"]


@pytest.mark.parametrize("seed", range(10))
def test_random_larger_requests_are_valid(cat, seed):
    rng = random.Random(5000 + seed)
    request = {
        "query": "plan", "current_sem": rng.choice([3, 4]), "completed": list(BASE_DONE),
        "must_take": rng.sample(MUST, rng.randint(4, 7)),
        "mc_max": rng.choice([8, 12]),
        "objective": rng.choice(["earliest_graduation", "none", "min_total_mc"]),
        "light_sems": ["last"], "balance_load": rng.random() < 0.5,
    }
    out = run(request, cat)
    assert out["status"] in ("PLAN", "NO_PLAN")
    if out["status"] == "PLAN":
        assert hard_rule_violations(request, semester_of(out), cat) == []


NEEDS_PREREQUISITES = [
    {"query": "plan", "current_sem": 3, "must_take": ["CS3263"], "mc_max": 20,
     "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522"],
     "objective": "earliest_graduation"},
    {"query": "plan", "current_sem": 3, "must_take": ["CS3263", "CS3230"], "mc_max": 8,
     "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522"],
     "objective": "none", "light_sems": [3, "last"], "balance_load": True},
    {"query": "plan", "current_sem": 3, "must_take": ["CS3263"], "mc_max": 12,
     "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522"],
     "objective": "min_total_mc", "early": ["CS3263"]},
    {"query": "plan", "current_sem": 3, "must_take": ["CS3230"], "mc_max": 20, "atap_sems": [3, 4, 5],
     "completed": BASE_DONE + ["CS2109S"], "objective": "earliest_graduation"},
    {"query": "plan", "current_sem": 3, "must_take": ["CS2100"], "mc_max": 12,
     "completed": list(BASE_DONE), "objective": "earliest_graduation",
     "rules": [{"type": "before", "a": "CS2106", "b": "CS2100", "strength": "must"}]},
]


@pytest.mark.parametrize("request_data", NEEDS_PREREQUISITES)
def test_every_added_prerequisite_is_necessary(cat, request_data):
    out = run(request_data, cat)
    assert out["status"] == "PLAN"
    assign = semester_of(out)
    assert hard_rule_violations(request_data, assign, cat) == []
    for code in out.get("added_prerequisites", []):
        without_it = {c: s for c, s in assign.items() if c != code}
        assert hard_rule_violations(request_data, without_it, cat), f"{code} was not needed"
