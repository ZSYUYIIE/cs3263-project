import json

import pytest

from m1_data.catalog import Catalog
from solver.run import run, run_text
from solver.spec import validate

COMPLETED = ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"]


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


def q1_spec(**changes):
    spec = {"query": "eligible", "target": "CS3263", "current_sem": 3, "completed": list(COMPLETED)}
    spec.update(changes)
    return spec


def q2_spec(**changes):
    spec = {
        "query": "plan",
        "current_sem": 3,
        "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522"],
        "must_take": ["ST2334", "CS2109S", "CS3263"],
    }
    spec.update(changes)
    return spec


def test_valid_q1_spec_has_no_errors(cat):
    errors, problems, warnings, cleaned, _ = validate(q1_spec(), cat)
    assert errors == [] and problems == [] and warnings == []
    assert cleaned["target"] == "CS3263"


def test_codes_are_upper_cased(cat):
    errors, _, _, cleaned, _ = validate(q1_spec(target="cs3263", completed=["cs1101s"]), cat)
    assert errors == []
    assert cleaned["target"] == "CS3263" and cleaned["completed"] == ["CS1101S"]


def test_missing_fields_are_listed_not_errors(cat):
    errors, _, _, cleaned, missing = validate({"query": "eligible"}, cat)
    assert errors == []
    assert missing == ["completed", "target"]
    assert "target" not in cleaned and "completed" not in cleaned


def test_bad_query_and_unknown_field_are_errors(cat):
    errors, _, _, _, _ = validate(q1_spec(query="both", colour="red"), cat)
    assert any("query must be one of" in e for e in errors)
    assert any("unknown field 'colour'" in e for e in errors)


def test_wrong_question_fields_are_ignored_with_a_warning(cat):
    errors, _, warnings, cleaned, _ = validate(q1_spec(objective="none", must_take=["CS3230"]), cat)
    assert errors == []
    assert any("'objective' belongs to query 'plan'" in w for w in warnings)
    assert any("'must_take' belongs to query 'plan'" in w for w in warnings)
    assert "objective" not in cleaned and "must_take" not in cleaned
    errors, _, warnings, cleaned, _ = validate(q2_spec(target="CS3263"), cat)
    assert errors == []
    assert any("'target' belongs to query 'eligible'" in w for w in warnings)
    assert "target" not in cleaned


def test_wrong_question_fields_are_not_validated(cat):
    errors, _, warnings, _, _ = validate(q1_spec(objective="fastest"), cat)
    assert errors == [] and len(warnings) == 1


def test_plan_requires_current_sem_but_eligible_does_not(cat):
    spec = q2_spec()
    del spec["current_sem"]
    errors, _, _, _, missing = validate(spec, cat)
    assert errors == [] and missing == ["current_sem"]
    spec = q1_spec()
    del spec["current_sem"]
    errors, _, _, cleaned, missing = validate(spec, cat)
    assert errors == [] and missing == [] and "current_sem" not in cleaned


def test_plan_requires_must_take(cat):
    spec = q2_spec()
    del spec["must_take"]
    errors, _, _, _, missing = validate(spec, cat)
    assert errors == [] and missing == ["must_take"]


def test_plan_defaults_are_filled(cat):
    errors, _, _, cleaned, _ = validate(q2_spec(), cat)
    assert errors == []
    assert cleaned["mc_max"] == 20
    assert cleaned["objective"] == "none"
    assert cleaned["sem_caps"] == {} and cleaned["rules"] == []
    assert cleaned["balance_load"] is False and cleaned["light_sems"] == []
    assert "atap_sems" not in cleaned and "mc_min" not in cleaned


def test_full_plan_spec_is_accepted(cat):
    spec = q2_spec(
        mc_max=8,
        mc_min=0,
        sem_caps={"6": 0},
        atap_sems=[5, 6],
        rules=[
            {"type": "before", "a": "ST2334", "b": "CS3263", "strength": "must"},
            {"type": "in_sem", "course": "CS3263", "sem": 5, "strength": "prefer"},
            {"type": "apart", "a": "CS2109S", "b": "CS3263", "strength": "prefer"},
            {"type": "same_sem", "a": "ST2334", "b": "CS2109S", "strength": "prefer"},
        ],
        objective="earliest_graduation",
        light_sems=["last", 8],
        balance_load=True,
        early=["CS2109S"],
        late=["CS3263"],
        unsupported=["no 8am classes"],
    )
    errors, problems, warnings, cleaned, _ = validate(spec, cat)
    assert errors == [] and problems == [] and warnings == []
    assert cleaned["sem_caps"] == {6: 0}
    assert cleaned["atap_sems"] == [5, 6]
    assert cleaned["mc_min"] == 0


@pytest.mark.parametrize("changes, text", [
    ({"objective": "fastest"}, "objective must be one of"),
    ({"mc_max": 0}, "mc_max must be a positive integer"),
    ({"mc_min": 30}, "mc_min cannot be larger than mc_max"),
    ({"sem_caps": {"six": 0}}, "is not a semester number"),
    ({"sem_caps": {"6": -1}}, "non-negative integer"),
    ({"atap_sems": []}, "non-empty list"),
    ({"atap_sems": [2]}, "before current_sem"),
    ({"light_sems": ["first"]}, "light_sems entry"),
    ({"balance_load": "yes"}, "balance_load must be true or false"),
    ({"early": "CS2109S"}, "early must be a list"),
    ({"current_sem": "three"}, "current_sem must be an integer"),
    ({"rules": [{"type": "after", "a": "CS2100", "b": "CS2106", "strength": "must"}]}, "rules[0].type"),
    ({"rules": [{"type": "before", "a": "CS2100", "b": "CS2106", "strength": "maybe"}]}, "rules[0].strength"),
    ({"rules": [{"type": "before", "a": "CS2100", "b": "CS2100", "strength": "must"}]}, "different courses"),
    ({"rules": [{"type": "before", "a": "CS2100", "b": "CS2106", "strength": "must", "x": 1}]}, "unknown key 'x'"),
])
def test_structure_errors(cat, changes, text):
    errors, _, _, cleaned, _ = validate(q2_spec(**changes), cat)
    assert cleaned is None
    assert any(text in e for e in errors), errors


@pytest.mark.parametrize("changes", [
    {"current_sem": 10},
    {"sem_caps": {"9": 0}},
    {"atap_sems": [9]},
    {"light_sems": [0]},
    {"rules": [{"type": "in_sem", "course": "CS3263", "sem": 12, "strength": "must"}]},
])
def test_out_of_range_semesters_are_content_problems(cat, changes):
    errors, problems, _, _, _ = validate(q2_spec(**changes), cat)
    assert errors == []
    assert any("outside the modelled semesters 1 to 8" in p for p in problems), problems


def test_unknown_course_is_a_problem_but_unknown_completed_is_ignored(cat):
    errors, problems, _, _, _ = validate(q1_spec(target="ZZ9999"), cat)
    assert errors == []
    assert any("ZZ9999 (in target) is not in the catalogue" in p for p in problems)
    errors, problems, warnings, cleaned, _ = validate(q1_spec(completed=COMPLETED + ["GEA1000"]), cat)
    assert errors == [] and problems == [] and cleaned is not None
    assert any("GEA1000" in w for w in warnings)


def test_q1_not_eligible_missing_prerequisite(cat):
    result = run(q1_spec(), cat)
    assert result["status"] == "NOT_ELIGIBLE"
    assert any("missing prerequisite" in r and "CS2109S" in r for r in result["reasons"])
    assert result["can_still_become_eligible"] is True
    assert "never_eligible_because" not in result


def test_q1_eligible_once_prerequisite_done(cat):
    result = run(q1_spec(completed=COMPLETED + ["CS2109S"]), cat)
    assert result["status"] == "ELIGIBLE" and result["reasons"] == []


def test_q1_cs3244_makes_target_permanently_unreachable(cat):
    completed = ["CS1101S", "CS1231S", "CS2040S", "MA1522", "ST2334", "CS3244"]
    result = run(q1_spec(completed=completed), cat)
    assert result["status"] == "NOT_ELIGIBLE"
    assert result["can_still_become_eligible"] is False
    assert "CS2109S" in result["never_eligible_because"]


def test_q1_already_completed_has_no_reachability_field(cat):
    result = run(q1_spec(target="CS2040S", current_sem=5), cat)
    assert result["status"] == "NOT_ELIGIBLE"
    assert result["reasons"] == ["CS2040S already completed"]
    assert "can_still_become_eligible" not in result


def test_q1_course_not_offered_in_that_term(cat):
    result = run(q1_spec(target="CS3230R", current_sem=4), cat)
    assert result["status"] == "NOT_ELIGIBLE"
    assert any("not offered in semester 2" in r for r in result["reasons"])


def test_q1_unavailable_course(cat):
    result = run(q1_spec(target="CS2109HS"), cat)
    assert result["status"] == "NOT_ELIGIBLE"
    assert any(r.startswith("unavailable") for r in result["reasons"])
    assert result["can_still_become_eligible"] is False


def no_semester(**changes):
    spec = q1_spec(completed=COMPLETED + ["CS2109S"], **changes)
    del spec["current_sem"]
    return spec


def test_q1_without_semester_course_offered_in_both_terms(cat):
    result = run(no_semester(), cat)
    assert result["status"] == "ELIGIBLE" and result["reasons"] == []
    assert result["offered_in"] == [1, 2]
    assert "semester" not in result
    assert "does not matter" in result["notes"][0]


def test_q1_without_semester_course_offered_in_one_term_only(cat):
    result = run(no_semester(target="CS3233"), cat)
    assert result["status"] == "ELIGIBLE"
    assert result["offered_in"] == [2]
    assert "Semester 2 only" in result["notes"][0]


def test_q1_without_semester_course_never_offered_in_a_semester(cat):
    never = next(code for code, c in cat.courses.items()
                 if c["available"] and c["exists_in_ay"] and c["prereq"]["logic"] is None
                 and not [t for t in c["offered"] if t in (1, 2)])
    result = run(no_semester(target=never), cat)
    assert result["status"] == "NOT_ELIGIBLE"
    assert result["reasons"] == ["not offered in Semester 1 or Semester 2"]


def test_q1_without_semester_still_reports_missing_prerequisite(cat):
    spec = q1_spec()
    del spec["current_sem"]
    result = run(spec, cat)
    assert result["status"] == "NOT_ELIGIBLE"
    assert any("missing prerequisite" in r for r in result["reasons"])
    assert result["can_still_become_eligible"] is True
    assert "notes" not in result


def test_q1_reports_unsupported_requests(cat):
    result = run(q1_spec(completed=COMPLETED + ["CS2109S"], unsupported=["S/U on CS3263"]), cat)
    assert result["status"] == "ELIGIBLE"
    assert result["not_applied"] == ["S/U on CS3263"]


def test_q1_wrong_question_field_still_gets_an_answer_with_warning(cat):
    result = run(q1_spec(completed=COMPLETED + ["CS2109S"], objective="none"), cat)
    assert result["status"] == "ELIGIBLE"
    assert any("'objective'" in w for w in result["warnings"])


def test_programme_in_scope(cat):
    assert run(q1_spec(programme="BComp CS Hons"), cat)["status"] in ("ELIGIBLE", "NOT_ELIGIBLE")
    assert run(q1_spec(), cat)["status"] in ("ELIGIBLE", "NOT_ELIGIBLE")


def test_other_programme_is_out_of_scope(cat):
    out = run(q1_spec(programme="Business Analytics"), cat)
    assert out["status"] == "OUT_OF_SCOPE"
    assert any("Business Analytics" in r for r in out["reasons"])


def test_unknown_course_is_out_of_scope(cat):
    out = run(q1_spec(target="CS9999"), cat)
    assert out["status"] == "OUT_OF_SCOPE"
    assert out["reasons"] == ["course CS9999 (in target) is not in the catalogue"]
    assert "CS9999" in out["message"]


def test_semester_outside_range_is_out_of_scope(cat):
    out = run(q1_spec(current_sem=10), cat)
    assert out["status"] == "OUT_OF_SCOPE"
    assert "outside the modelled semesters 1 to 8" in out["reasons"][0]


def test_reasons_are_combined(cat):
    out = run(q1_spec(target="CS9999", programme="Business Analytics"), cat)
    assert out["status"] == "OUT_OF_SCOPE" and len(out["reasons"]) == 2


def test_structure_error_gives_invalid_spec(cat):
    result = run({"completed": []}, cat)
    assert result["status"] == "INVALID_SPEC" and result["errors"]
    result = run(q1_spec(colour="red"), cat)
    assert result["status"] == "INVALID_SPEC"


def test_invalid_spec_wins_over_out_of_scope(cat):
    result = run(q1_spec(colour="red", target="CS9999"), cat)
    assert result["status"] == "INVALID_SPEC"


def test_malformed_json_is_invalid_spec(cat):
    for text in ('{"query": "eligible"', "just words", "[1, 2]", "42"):
        result = run_text(text, cat)
        assert result["status"] == "INVALID_SPEC", text


def test_run_text_accepts_valid_json(cat):
    result = run_text(json.dumps(q1_spec()), cat)
    assert result["status"] == "NOT_ELIGIBLE"


def test_plan_query_returns_a_plan(cat):
    result = run(q2_spec(), cat)
    assert result["status"] == "PLAN"
    assert sorted(c for courses in result["plan"].values() for c in courses)[:3] == ["CS2109S", "CS3263", "ST2334"]


def without(spec, *keys):
    return {k: v for k, v in spec.items() if k not in keys}


def test_q1_missing_target_gives_missing_info(cat):
    result = run(without(q1_spec(), "target"), cat)
    assert result["status"] == "MISSING_INFO"
    assert result["missing"] == ["target"]
    assert "course you want to check" in result["message"]


def test_q1_missing_completed_gives_missing_info(cat):
    result = run(without(q1_spec(), "completed"), cat)
    assert result["status"] == "MISSING_INFO" and result["missing"] == ["completed"]


def test_q1_both_missing_are_listed_together(cat):
    result = run({"query": "eligible", "current_sem": 3}, cat)
    assert result["status"] == "MISSING_INFO" and result["missing"] == ["completed", "target"]


@pytest.mark.parametrize("target", ["", "   ", None])
def test_q1_empty_or_null_target_counts_as_missing(cat, target):
    result = run(q1_spec(target=target), cat)
    assert result["status"] == "MISSING_INFO" and result["missing"] == ["target"]


def test_q1_target_of_wrong_type_is_invalid_spec(cat):
    result = run(q1_spec(target=123), cat)
    assert result["status"] == "INVALID_SPEC"


def test_q1_missing_field_with_unknown_field_is_invalid_spec(cat):
    result = run(without(q1_spec(colour="red"), "target"), cat)
    assert result["status"] == "INVALID_SPEC"


def test_q1_missing_field_with_other_programme_is_out_of_scope(cat):
    result = run(without(q1_spec(programme="Business Analytics"), "target"), cat)
    assert result["status"] == "OUT_OF_SCOPE"


def test_q1_missing_current_sem_is_still_answered(cat):
    result = run(without(q1_spec(), "current_sem"), cat)
    assert result["status"] in ("ELIGIBLE", "NOT_ELIGIBLE")


def test_q1_null_current_sem_is_treated_as_not_given(cat):
    result = run(q1_spec(current_sem=None), cat)
    assert result["status"] in ("ELIGIBLE", "NOT_ELIGIBLE")


def test_q2_missing_fields_are_listed_in_fixed_order(cat):
    result = run({"query": "plan"}, cat)
    assert result["status"] == "MISSING_INFO"
    assert result["missing"] == ["completed", "current_sem", "must_take"]


def test_q2_missing_current_sem_gives_missing_info(cat):
    result = run(without(q2_spec(), "current_sem"), cat)
    assert result["status"] == "MISSING_INFO" and result["missing"] == ["current_sem"]
    assert "semester" in result["message"]


def test_q2_missing_must_take_gives_missing_info(cat):
    result = run(without(q2_spec(), "must_take"), cat)
    assert result["status"] == "MISSING_INFO" and result["missing"] == ["must_take"]


def test_q2_empty_completed_and_must_take_lists_are_not_missing(cat):
    result = run(q2_spec(completed=[], must_take=[]), cat)
    assert result["status"] == "PLAN"


def test_q2_missing_current_sem_with_semester_out_of_range_elsewhere_is_out_of_scope(cat):
    result = run(without(q2_spec(sem_caps={"9": 0}), "current_sem"), cat)
    assert result["status"] == "OUT_OF_SCOPE"


def test_q2_missing_current_sem_with_atap_is_missing_info(cat):
    result = run(without(q2_spec(atap_sems=[7]), "current_sem"), cat)
    assert result["status"] == "MISSING_INFO"


OPTIONAL_Q2_FIELDS = ["objective", "mc_min", "mc_max", "sem_caps", "atap_sems", "rules",
                      "light_sems", "balance_load", "early", "late", "programme", "unsupported"]


@pytest.mark.parametrize("field", OPTIONAL_Q2_FIELDS)
def test_null_optional_field_is_treated_as_not_given(cat, field):
    with_null = run(q2_spec(**{field: None}), cat)
    assert with_null == run(q2_spec(), cat)


def test_null_unknown_field_is_still_an_error(cat):
    result = run(q2_spec(colour=None), cat)
    assert result["status"] == "INVALID_SPEC"
    assert any("unknown field 'colour'" in e for e in result["errors"])


def test_null_query_is_invalid_spec(cat):
    result = run(q1_spec(query=None), cat)
    assert result["status"] == "INVALID_SPEC"


def test_duplicate_entries_are_removed(cat):
    errors, _, _, cleaned, _ = validate(
        q2_spec(
            must_take=["ST2334", "st2334", "CS2109S"],
            light_sems=[4, 4, "last", "last"],
            early=["CS2109S", "CS2109S"],
            late=["ST2334", "st2334"],
            rules=[
                {"type": "before", "a": "ST2334", "b": "CS2109S", "strength": "prefer"},
                {"type": "before", "a": "st2334", "b": "cs2109s", "strength": "prefer"},
            ],
            completed=["CS1101S", "cs1101s"],
        ),
        cat,
    )
    assert errors == []
    assert cleaned["must_take"] == ["ST2334", "CS2109S"]
    assert cleaned["light_sems"] == [4, "last"]
    assert cleaned["early"] == ["CS2109S"] and cleaned["late"] == ["ST2334"]
    assert len(cleaned["rules"]) == 1
    assert cleaned["completed"] == ["CS1101S"]


@pytest.mark.parametrize("changes, text", [
    ({"current_sem": True}, "current_sem must be an integer"),
    ({"current_sem": 3.5}, "current_sem must be an integer"),
    ({"completed": "CS1101S"}, "completed must be a list of course codes"),
    ({"completed": [""]}, "completed must be a list of course codes"),
    ({"completed": [101]}, "completed must be a list of course codes"),
    ({"must_take": "CS3263"}, "must_take must be a list of course codes"),
    ({"must_take": [""]}, "must_take must be a list of course codes"),
    ({"mc_max": True}, "mc_max must be a positive integer"),
    ({"mc_max": "20"}, "mc_max must be a positive integer"),
    ({"mc_max": -4}, "mc_max must be a positive integer"),
    ({"mc_min": True}, "mc_min must be a non-negative integer"),
    ({"mc_min": -1}, "mc_min must be a non-negative integer"),
    ({"sem_caps": []}, "sem_caps must be an object"),
    ({"sem_caps": {"6": 1.5}}, "sem_caps value for semester 6"),
    ({"sem_caps": {"6": True}}, "sem_caps value for semester 6"),
    ({"atap_sems": 5}, "atap_sems must be a non-empty list"),
    ({"atap_sems": ["5"]}, "atap_sems entry must be an integer"),
    ({"rules": {}}, "rules must be a list"),
    ({"rules": ["x"]}, "rules[0] must be an object"),
    ({"rules": [{}]}, "rules[0].type must be one of"),
    ({"rules": [{"type": "in_sem", "sem": 4, "strength": "must"}]}, "rules[0].course must be a course code"),
    ({"rules": [{"type": "in_sem", "course": "CS3263", "strength": "must"}]}, "rules[0].sem must be an integer"),
    ({"rules": [{"type": "in_sem", "course": "CS3263", "sem": 4, "strength": "must", "a": "X"}]}, "unknown key 'a'"),
    ({"rules": [{"type": "before", "a": "CS2100", "strength": "must"}]}, "rules[0].b must be a course code"),
    ({"light_sems": "last"}, "light_sems must be a list"),
    ({"light_sems": [True]}, "light_sems entry must be an integer"),
    ({"early": [1]}, "early must be a list of course codes"),
    ({"late": "CS3263"}, "late must be a list of course codes"),
    ({"objective": 5}, "objective must be one of"),
    ({"balance_load": 1}, "balance_load must be true or false"),
    ({"unsupported": "no mornings"}, "unsupported must be a list of strings"),
    ({"unsupported": [1]}, "unsupported must be a list of strings"),
    ({"programme": 5}, "programme must be a string"),
    ({"query": ["plan"]}, "query must be one of"),
])
def test_more_structure_errors_give_invalid_spec(cat, changes, text):
    result = run(q2_spec(**changes), cat)
    assert result["status"] == "INVALID_SPEC"
    assert any(text in e for e in result["errors"]), result["errors"]


def test_several_structure_errors_are_all_reported(cat):
    result = run(q2_spec(mc_max=0, objective="fastest", colour="red"), cat)
    assert result["status"] == "INVALID_SPEC" and len(result["errors"]) == 3


@pytest.mark.parametrize("text", ['{"query": "plan", "completed": [], "must_take": [], "current_sem": null}',
                                  'null', 'true', '"plan"', '', '{', '{"query": "plan"} extra'])
def test_run_text_never_raises(cat, text):
    result = run_text(text, cat)
    assert result["status"] in ("INVALID_SPEC", "MISSING_INFO")


def test_q2_wrong_question_field_is_ignored_with_warning(cat):
    result = run(q2_spec(target="CS3263"), cat)
    assert result["status"] == "PLAN"
    assert any("'target' belongs to query 'eligible'" in w for w in result["warnings"])


def test_q2_unknown_completed_course_is_ignored_with_warning(cat):
    result = run(q2_spec(completed=q2_spec()["completed"] + ["GEA1000"]), cat)
    assert result["status"] == "PLAN"
    assert any("GEA1000" in w for w in result["warnings"])


def test_warnings_only_appear_on_answers(cat):
    assert "warnings" not in run(without(q1_spec(objective="none"), "target"), cat)
    assert "warnings" not in run(q1_spec(objective="none", programme="Law"), cat)
    assert "warnings" not in run(q1_spec(objective="none", colour="red"), cat)
    assert run(q1_spec(objective="none"), cat)["warnings"]


@pytest.mark.parametrize("spec_maker", [q1_spec, q2_spec])
def test_status_priority_invalid_then_out_of_scope_then_missing(cat, spec_maker):
    base = spec_maker()
    key = "target" if base["query"] == "eligible" else "must_take"
    assert run(without(spec_maker(colour="x", programme="Law"), key), cat)["status"] == "INVALID_SPEC"
    assert run(without(spec_maker(programme="Law"), key), cat)["status"] == "OUT_OF_SCOPE"
    assert run(without(spec_maker(), key), cat)["status"] == "MISSING_INFO"
    assert run(spec_maker(programme="Law"), cat)["status"] == "OUT_OF_SCOPE"


@pytest.mark.parametrize("programme", [None, "BComp CS Hons", "bcomp (cs) hons", "Computer Science", "CS"])
def test_cs_programme_is_in_scope(cat, programme):
    assert run(q1_spec(programme=programme), cat)["status"] in ("ELIGIBLE", "NOT_ELIGIBLE")


@pytest.mark.parametrize("programme", ["Business Analytics", "BBA with CS minor", "Information Systems",
                                       "double degree CS and Math", "CS second major"])
def test_other_programme_text_is_out_of_scope(cat, programme):
    result = run(q2_spec(programme=programme), cat)
    assert result["status"] == "OUT_OF_SCOPE" and result["reasons"]


def test_out_of_scope_message_is_in_m1_format(cat):
    result = run(q1_spec(programme="Law"), cat)
    assert set(result) >= {"status", "reasons", "message"}
    assert "AY2026/2027" in result["message"]


def test_missing_info_has_exactly_the_documented_fields(cat):
    result = run({"query": "plan"}, cat)
    assert set(result) == {"status", "missing", "message"}


def test_q1_answer_fields_by_status(cat):
    eligible = run(q1_spec(completed=COMPLETED + ["CS2109S"]), cat)
    assert eligible["status"] == "ELIGIBLE"
    assert set(eligible) >= {"status", "target", "semester", "reasons"}
    assert "can_still_become_eligible" not in eligible
    not_eligible = run(q1_spec(), cat)
    assert not_eligible["status"] == "NOT_ELIGIBLE"
    assert not_eligible["can_still_become_eligible"] is True
    assert "never_eligible_because" not in not_eligible
    never = run(q1_spec(completed=COMPLETED + ["CS3244"]), cat)
    assert never["can_still_become_eligible"] is False and never["never_eligible_because"]


def test_q1_term_follows_semester_parity(cat):
    only_term_one = q1_spec(target="CS2104", completed=["CS2030S"])
    assert run({**only_term_one, "current_sem": 3}, cat)["status"] == "ELIGIBLE"
    assert run({**only_term_one, "current_sem": 4}, cat)["status"] == "NOT_ELIGIBLE"
    only_term_two = q1_spec(target="CS3234", completed=["CS1231S"])
    assert run({**only_term_two, "current_sem": 4}, cat)["status"] == "ELIGIBLE"
    assert run({**only_term_two, "current_sem": 3}, cat)["status"] == "NOT_ELIGIBLE"


@pytest.mark.parametrize("semester", [1, 2, 7, 8])
def test_q1_accepts_boundary_semesters(cat, semester):
    result = run(q1_spec(current_sem=semester), cat)
    assert result["status"] in ("ELIGIBLE", "NOT_ELIGIBLE") and result["semester"] == semester


@pytest.mark.parametrize("semester", [0, 9, -1, 100])
def test_q1_semester_outside_range_is_out_of_scope(cat, semester):
    assert run(q1_spec(current_sem=semester), cat)["status"] == "OUT_OF_SCOPE"


def test_q1_target_is_trimmed_and_upper_cased(cat):
    assert run(q1_spec(target="  cs3263 "), cat)["target"] == "CS3263"


def test_q1_target_already_completed_is_not_eligible(cat):
    result = run(q1_spec(target="CS2040S"), cat)
    assert result["status"] == "NOT_ELIGIBLE"
    assert any("already completed" in r for r in result["reasons"])
    assert "can_still_become_eligible" not in result


def test_q1_not_applied_is_reported_for_every_answer(cat):
    for completed in (COMPLETED, COMPLETED + ["CS2109S"]):
        result = run(q1_spec(completed=completed, unsupported=["only afternoon lectures"]), cat)
        assert result["not_applied"] == ["only afternoon lectures"]


@pytest.mark.parametrize("make", [
    lambda: q1_spec(),
    lambda: q1_spec(completed=COMPLETED + ["CS2109S"]),
    lambda: q1_spec(current_sem=None),
    lambda: q2_spec(),
    lambda: q2_spec(mc_max=4),
    lambda: {"query": "plan"},
    lambda: q1_spec(programme="Law"),
    lambda: q1_spec(colour="red"),
])
def test_every_status_is_json_serialisable(cat, make):
    result = run(make(), cat)
    assert json.loads(json.dumps(result)) == result


@pytest.mark.parametrize("make", [
    lambda: q1_spec(),
    lambda: q2_spec(objective="earliest_graduation", light_sems=["last"], balance_load=True, early=["CS3263"]),
    lambda: q2_spec(target="CS3263", rules=[{"type": "before", "a": "CS2109S", "b": "CS3263", "strength": "prefer"}]),
])
def test_run_does_not_change_its_input_and_is_repeatable(cat, make):
    import copy
    spec = make()
    before = copy.deepcopy(spec)
    first = run(spec, cat)
    assert spec == before
    assert run(spec, cat) == first
