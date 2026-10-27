"""Tests for the M1 data pipeline. Run: python -m pytest -q

The first group only needs the code; the second needs a built catalogue
(`python -m m1_data build`) and pins the facts written in the project doc.
"""
import pytest

from m1_data.resolve import Resolver, render, simplify
from m1_data.rules import has_mixed_and_or, parse_rule

CTX = {"program_type": "Undergraduate Degree", "programs": ["0300CSHON"], "second_major": [],
       "minor": [], "special_programme": [], "cohort": 2024,
       "subjects_held": ["06", "EP"], "subject_level": "H2", "unknown_policy": "assume_true"}
KNOWN = {"CS2040", "CS2040S", "CS2040C", "CS1010", "CS1010S", "MA1301"}


def req(rule, code="X"):
    return Resolver(CTX, KNOWN, code).requirement(parse_rule(rule))


# --- parser ---------------------------------------------------------------
def test_parse_basic_and_or_counts():
    t = parse_rule("PROGRAM_TYPES IF_IN Undergraduate Degree THEN COURSES (1) A1000:D, B1000:D AND COURSES (2) C1000:D, D1000:D, E1000:D")
    assert t["op"] == "if" and t["cond"]["values"] == ["Undergraduate Degree"]
    a, b = t["then"]["args"]
    assert a["n"] == 1 and [i["code"] for i in a["items"]] == ["A1000", "B1000"]
    assert b["n"] == 2 and len(b["items"]) == 3


def test_parse_condition_before_then():
    t = parse_rule("(PROGRAM_TYPES IF_IN Graduate Degree Coursework OR PROGRAM_TYPES IF_IN Undergraduate Degree) THEN COURSES (1) EE3204:D")
    assert t["op"] == "if" and t["cond"]["op"] == "or"


def test_parse_groups_patterns_and_specials():
    t = parse_rule('PROGRAM_TYPES IF_IN Undergraduate Degree THEN (COURSES (1) CS2040%:D AND PROGRAMS MUST_BE_IN (1) 0300CSHON, 0300AIHON AND SPECIAL MUST_BE_IN "ACAD_LEVEL=2-3-4" AND UNITS (80) AND GPA (3.2))')
    ops = [a["op"] for a in t["then"]["args"]]
    assert ops == ["courses", "group", "special", "units", "gpa"]
    assert t["then"]["args"][0]["items"][0] == {"code": "CS2040", "pattern": True, "min_grade": "D"}


def test_mixed_and_or_detected():
    assert has_mixed_and_or("COURSES (1) A1000 AND COURSES (1) B1000 OR COURSES (1) C1000")
    assert not has_mixed_and_or("COURSES (1) A1000 AND (COURSES (1) B1000 OR COURSES (1) C1000)")
    assert not has_mixed_and_or("COURSES A1000 AND (COURSES (1) B1000 OR (COURSES C1000 AND COURSES D1000))")


# --- resolution -----------------------------------------------------------
def test_no_count_means_any_of():
    t = req("PROGRAM_TYPES IF_IN Undergraduate Degree THEN COURSES CS2106:D, CG2271:D")
    assert t["op"] == "or"


def test_subject_alternative_uses_context():
    # Student holds 06 (H2 maths): the MA1301 alternative disappears.
    assert req("PROGRAM_TYPES IF_IN Undergraduate Degree THEN (SUBJECTS (1) 06:E OR COURSES (1) MA1301:D)") is True
    # Student does not hold 11 (biology): the course is required.
    t = req("PROGRAM_TYPES IF_IN Undergraduate Degree THEN (SUBJECTS (1) 11:E OR COURSES LSM1301:D)")
    assert render(t) == "LSM1301"


def test_programme_gate_makes_impossible():
    assert req("PROGRAM_TYPES IF_IN Undergraduate Degree THEN PROGRAMS MUST_BE_IN (1) 1006DSAHON") is False


def test_pattern_expansion_excludes_self():
    t = req("COURSES (1) CS2040%:D", code="CS2040S")
    assert "CS2040S" not in render(t) and "CS2040C" in render(t)


def test_preclusion_programme_and_courses():
    r = Resolver(CTX, KNOWN, "CS2109HS")
    blocked, reasons = r.preclusion(parse_rule(
        "PROGRAM_TYPES IF_IN Undergraduate Degree THEN (COURSES (1) CS3244:D, CS2109S:D) AND (PROGRAMS MUST_NOT_BE_IN 0300CSHON)"))
    assert render(blocked) == "CS3244 or CS2109S"
    assert reasons == ["not open to PROGRAMS 0300CSHON"]


def test_simplify_n_of():
    c = lambda x: {"op": "course", "code": x, "min_grade": "D"}
    assert simplify({"op": "n_of", "n": 1, "args": [c("A"), c("B")]})["op"] == "or"
    assert simplify({"op": "n_of", "n": 2, "args": [c("A"), c("B")]})["op"] == "and"
    assert simplify({"op": "n_of", "n": 3, "args": [c("A"), c("B")]}) is False
    assert simplify({"op": "and", "args": [True, c("A")]}) == c("A")


# --- facts from the project doc (needs a built catalogue) -----------------
@pytest.fixture(scope="module")
def cat():
    from m1_data.catalog import Catalog
    try:
        return Catalog.load()
    except FileNotFoundError:
        pytest.skip("run `python -m m1_data build` first")


def test_doc_cs3263(cat):
    c = cat["CS3263"]
    assert c["prereq"]["text"].startswith("(CS2109S or CS2109HS) and (CS2040")
    assert c["preclusion"]["courses"] == ["CS3243"]
    assert c["offered"] == [1, 2] and c["mc"] == 4


def test_doc_cs2109hs_closed_to_cs_hons(cat):
    assert not cat["CS2109HS"]["available"]


def test_doc_example_took_cs3244_wants_cs3263(cat):
    done = {"CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334", "CS3244"}
    ok, why = cat.reachable("CS3263", done)
    assert not ok and "CS3244" in why
    ok, _ = cat.can_take("CS2109S", done)
    assert not ok


def test_doc_t1_sample(cat):
    done = {"CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"}
    ok, why = cat.can_take("CS3263", done)
    assert not ok and "CS2109S or CS2109HS" in why[0]
