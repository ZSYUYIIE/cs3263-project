# Solver guide (M2)

This guide describes what the solver accepts, what it returns, and exactly what its answers mean. It is written for
M3 (instance generator, pipelines A0/A/B/C, evaluation harness and the independent checker) and for any AI assistant
helping M3. Every JSON example below was produced by running the solver, not typed by hand.

The companion file [`docs/TRANSLATION_GUIDE.md`](TRANSLATION_GUIDE.md) covers pipeline B's natural-language to JSON
translation. Course facts (prerequisites, preclusions, offering terms) are in `data/processed/AY2026-2027/catalog.json`
and are described in [`docs/DATA_SCHEMA.md`](DATA_SCHEMA.md).

Terms used in this guide:

- **Spec**: the JSON object the solver reads.
- **MC**: modular credits. Most courses in the data are 4 MC.
- **Term**: Semester 1 or Semester 2 of an academic year. Our semester numbers 1 to 8 map to terms by parity: odd is
  term 1, even is term 2.
- **ATAP**: the Advanced Technology Attachment Programme, an internship semester planned as the course `CP3880` (12 MC).
- **CSP**: constraint satisfaction problem, a set of variables, the values each can take, and constraints between them.
- **CP-SAT**: the constraint solver from Google OR-Tools that `solver/model.py` uses.
- **Added course**: a course the student did not list that a planned course needs as a prerequisite or corequisite.
- **Hard rule / preference**: a hard rule must hold or there is no plan; a preference is only counted.

Contents:

1. How to call the solver
2. Input fields (the spec)
3. Output responses
4. The hard rules, exactly as enforced
5. Preferences, exactly as scored
6. Optimality
7. Infeasible requests and the response each one gets
8. `explain.py` and Responsible AI
9. The four backtracking variants
10. Analysis directions the solver makes possible
11. Known limitations

## 1. How to call the solver

Requirements: Python 3.10+, the `ortools` package (CP-SAT), and the repo root as the working directory.

```bash
python -m pip install -r requirements-dev.txt
python -m solver.run spec.json
```

From Python:

```python
import json
from solver.run import run, run_text

answer = run(spec_dict)
answer = run_text(llm_output_string)
```

| Call | Input | Use it for |
|---|---|---|
| `run(spec)` | a Python `dict` | a spec you already have as an object (gold specs, generated instances) |
| `run_text(text)` | the raw string the LLM returned | pipeline B: text that is not valid JSON becomes `INVALID_SPEC` instead of raising an error |
| `solve_with_stats(spec, variant=..., time_limit=...)` | a `dict` | the own backtracking solver, which also returns search counters (section 9) |

Points that matter for the harness:

- **No catalog import is needed.** `run(spec)` and `run_text(text)` load the data themselves. This matters because code
  under `eval/` must not import `m1_data.catalog` or `m1_data.resolve` (AGENTS.md rule 4). Calling `solver.run` from
  the pipeline B code is fine; the independent checker must not call the solver.
- **The solver never raises on a bad spec.** Wrong types, unknown fields and malformed JSON all come back as an answer
  with `"status": "INVALID_SPEC"`.
- **The answer is a plain, JSON-serialisable `dict`.** The input spec is never modified.
- **Answers are deterministic.** CP-SAT runs with one worker and a fixed seed, so the same spec gives the same answer on
  every run. Several different plans can tie for optimal; the solver always returns the same one of them.
- **Time limits.** CP-SAT stops each solve after 60 seconds, and the conflict search of `explain.py` after 20 seconds per check (see section 11 for what a time-out looks like).

A minimal pipeline B loop:

```python
from solver.run import run_text

def pipeline_b(request_text, llm):
    spec_text = llm(request_text)
    return run_text(spec_text)
```

## 2. Input fields (the spec)

A spec is one JSON object. Each natural-language request asks exactly one of two questions, and the `query` field says
which:

- `"eligible"` is question 1 (Q1): can the student take one course now?
- `"plan"` is question 2 (Q2): plan the remaining semesters.

### 2.1 Fields by question

| Field | Q1 (`eligible`) | Q2 (`plan`) | Type | Default if left out |
|---|---|---|---|---|
| `query` | required | required | `"eligible"` or `"plan"` | none |
| `completed` | **mandatory** | **mandatory** | list of course codes (`[]` = none completed) | none, so the answer is `MISSING_INFO` |
| `current_sem` | optional | **mandatory** | integer 1 to 8 | Q1: answered for either term; Q2: `MISSING_INFO` |
| `target` | **mandatory** | not allowed | one course code | none, so `MISSING_INFO` |
| `must_take` | not allowed | **mandatory** | list of course codes (`[]` = none) | none, so `MISSING_INFO` |
| `programme` | optional | optional | string | not checked |
| `unsupported` | optional | optional | list of strings | `[]` |
| `mc_max` | not allowed | optional | positive integer | 20 |
| `mc_min` | not allowed | optional | integer, 0 up to `mc_max` | no minimum |
| `sem_caps` | not allowed | optional | object, semester number as a **string** key, non-negative integer value | none |
| `atap_sems` | not allowed | optional | non-empty list of semesters | no ATAP |
| `rules` | not allowed | optional | list of rule objects (section 2.3) | `[]` |
| `objective` | not allowed | optional | `"earliest_graduation"`, `"min_total_mc"` or `"none"` | `"none"` |
| `light_sems` | not allowed | optional | list of semesters, may include `"last"` | `[]` |
| `balance_load` | not allowed | optional | `true` or `false` | `false` |
| `early` | not allowed | optional | list of course codes | `[]` |
| `late` | not allowed | optional | list of course codes | `[]` |

"Not allowed" means the field is accepted but ignored, and the answer carries a `warnings` entry such as
`field 'mc_max' belongs to query 'plan', not 'eligible', and was ignored`. The harness can count these warnings as a
sign of poor translation. A field that is not in the table at all is an error (`INVALID_SPEC`).

Missing, `null` and empty values:

- A field that is **absent** or **`null`** counts as "not given". For a mandatory field the answer is `MISSING_INFO`.
- `[]` is a real answer: "the student has completed nothing" or "has no courses left that must be taken". It is never
  `MISSING_INFO`.
- An empty-string `target` counts as not given.
- A field of the wrong type is an error, not "missing" (`INVALID_SPEC`).
- `null` is accepted for any field in the table above. `null` for a field that is not in the table is still an error
  (the field is unknown).

### 2.2 Meaning of the fields

| Field | Meaning |
|---|---|
| `current_sem` | Semesters are numbered 1 to 8 (Y1S1 = 1, Y1S2 = 2, Y2S1 = 3, Y2S2 = 4, ..., Y4S2 = 8). An odd number is Semester 1 of the academic year (term 1) and an even number is Semester 2 (term 2). For Q2 it is the first semester that still has to be planned. For Q1 it is the semester in which the student wants to take the course. |
| `completed` | Courses already passed. A course the student did not list is treated as **not completed**. A code that is not in the catalogue is ignored with a warning. |
| `target` | The course asked about in Q1. |
| `must_take` | Courses the plan has to contain. Graduation in this project means completing every course in this list. Courses already in `completed` are not planned again; the answer adds a note. |
| `programme` | Only used to check scope. The value `BComp CS Hons` (and the spellings in `m1_data/scope.py`, for example `Computer Science`) is accepted; any other value gives `OUT_OF_SCOPE`. |
| `unsupported` | Wishes the schema cannot express, as short strings. They are echoed back as `not_applied` so that nothing is dropped silently. |
| `mc_max` | The most MC allowed in one semester. |
| `mc_min` | The fewest MC allowed in a semester **that has at least one course**. Empty semesters are not affected. ATAP's 12 MC counts towards this total in the semester that holds it. |
| `sem_caps` | Per-semester override of `mc_max`, for example `{"6": 0}`. A cap of `0` blocks the semester completely, so no course (and not ATAP) can be placed in it. Keys must be strings holding a number from 1 to 8. |
| `atap_sems` | Semesters in which ATAP (course code `CP3880`, 12 MC) may be planned. Giving the field asks for ATAP to be planned. See section 4. |
| `rules` | Student wishes about specific courses, each marked `must` (hard) or `prefer` (soft). |
| `objective` | What to optimise first (section 6). |
| `light_sems` | Semesters that should carry less than the average load. `"last"` means the last semester the plan uses. |
| `balance_load` | Make the largest per-semester load as small as possible. |
| `early` / `late` | Courses that should be placed as early (or as late) as possible. |

### 2.3 Rule objects

Every rule has a `type`, a `strength`, and the course fields for that type. No other keys are allowed.

| `type` | Fields | Holds when |
|---|---|---|
| `before` | `a`, `b` | `a` is in a strictly earlier semester than `b` |
| `apart` | `a`, `b` | `a` and `b` are in different semesters |
| `same_sem` | `a`, `b` | `a` and `b` are in the same semester |
| `in_sem` | `course`, `sem` | `course` is in semester `sem` |

`strength` is `"must"` (the plan has to satisfy it, otherwise there is no plan) or `"prefer"` (the plan satisfies it if
that is possible, as described in section 5). For `before`, `apart` and `same_sem`, `a` and `b` must be different
courses.

### 2.4 Cleaning applied before solving

Course codes are stripped of spaces and upper-cased. Duplicate entries in `completed`, `must_take`, `early`, `late`,
`light_sems` and `rules` are removed. This is why two specs that differ only in letter case or duplicates give the same
answer, and why a gold spec and a translated spec should be compared after cleaning, not as raw text.

### 2.5 Every way the input can be wrong

| Situation | Status | Example message |
|---|---|---|
| not a JSON object, not valid JSON, unknown field, wrong type, bad enum value, rule with a missing or extra key, `mc_min` above `mc_max`, `atap_sems` entry before `current_sem` | `INVALID_SPEC` | `unknown field 'foo'`, `current_sem must be an integer, got 'three'` |
| a mandatory field not given | `MISSING_INFO` | `missing: ["completed", "current_sem", "must_take"]` |
| semester outside 1 to 8, a course in `must_take`, `target`, `early`, `late` or a rule that is not in the catalogue, programme not CS Hons | `OUT_OF_SCOPE` | `course CS9999 (in must_take) is not in the catalogue` |

If several apply, the first row that applies wins: `INVALID_SPEC`, then `OUT_OF_SCOPE`, then `MISSING_INFO`. Only
answers that were actually computed (`ELIGIBLE`, `NOT_ELIGIBLE`, `PLAN`, `NO_PLAN`) carry `warnings`.

## 3. Output responses

Every answer is a JSON object with a `status`. The statuses are:

| Status | Query | Meaning |
|---|---|---|
| `ELIGIBLE` | Q1 | the student can take the course in the stated semester |
| `NOT_ELIGIBLE` | Q1 | the student cannot, with the reasons |
| `PLAN` | Q2 | a plan that satisfies every hard rule |
| `NO_PLAN` | Q2 | no plan satisfies every hard rule, with the reasons |
| `MISSING_INFO` | both | a mandatory field was not given |
| `INVALID_SPEC` | both | the spec itself is malformed |
| `OUT_OF_SCOPE` | both | the student or a course is outside what the data covers |
| `TIMED_OUT` | Q2, own backtracking solver only | the search hit its time limit before it finished |

### 3.1 Q1 answers

`ELIGIBLE` and `NOT_ELIGIBLE` carry `target`, `semester` (when `current_sem` was given) and `reasons` (a list; empty
when eligible).

A not-eligible answer for a course the student is missing a prerequisite for:

```json
{
  "query": "eligible",
  "target": "CS3263",
  "current_sem": 3,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"]
}
```

```json
{
  "status": "NOT_ELIGIBLE",
  "target": "CS3263",
  "semester": 3,
  "reasons": ["missing prerequisite: CS2109S or CS2109HS"],
  "can_still_become_eligible": true
}
```

When the student can still become eligible, `can_still_become_eligible` is `true`. When completed courses rule the
course out for good, it is `false` and `never_eligible_because` says why:

```json
{
  "query": "eligible",
  "target": "CS3263",
  "current_sem": 3,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334", "CS3244"]
}
```

```json
{
  "status": "NOT_ELIGIBLE",
  "target": "CS3263",
  "semester": 3,
  "reasons": ["missing prerequisite: CS2109S or CS2109HS"],
  "can_still_become_eligible": false,
  "never_eligible_because": "CS3263: every option fails: CS2109S is ruled out by completed CS3244 | CS2109HS unavailable (not open to PROGRAMS 0300CSHON)"
}
```

An eligible answer:

```json
{
  "status": "ELIGIBLE",
  "target": "CS2109S",
  "semester": 3,
  "reasons": []
}
```

If `current_sem` is left out, the answer holds for either term and says so (`offered_in` and `notes`):

```json
{
  "query": "eligible",
  "target": "CS2109S",
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"]
}
```

```json
{
  "status": "ELIGIBLE",
  "target": "CS2109S",
  "reasons": [],
  "offered_in": [1, 2],
  "notes": ["no semester given; the course is offered in both Semester 1 and Semester 2, so the term does not matter"]
}
```

A target the student has already completed is `NOT_ELIGIBLE` with the reason `CS2040S already completed` and no
`can_still_become_eligible`:

```json
{
  "status": "NOT_ELIGIBLE",
  "target": "CS2040S",
  "semester": 3,
  "reasons": ["CS2040S already completed"]
}
```

Wishes the schema cannot express are echoed back as `not_applied`:

```json
{
  "query": "eligible",
  "target": "CS2109S",
  "current_sem": 3,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"],
  "unsupported": ["I might fail CS2040S"]
}
```

```json
{
  "status": "ELIGIBLE",
  "target": "CS2109S",
  "semester": 3,
  "reasons": [],
  "not_applied": ["I might fail CS2040S"]
}
```

A field that belongs to the other question is ignored and reported in `warnings`:

```json
{
  "query": "eligible",
  "target": "CS2109S",
  "current_sem": 3,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"],
  "mc_max": 12
}
```

```json
{
  "status": "ELIGIBLE",
  "target": "CS2109S",
  "semester": 3,
  "reasons": [],
  "warnings": ["field 'mc_max' belongs to query 'plan', not 'eligible', and was ignored"]
}
```

### 3.2 Q2 answers

A `PLAN` answer has these fields:

| Field | Meaning |
|---|---|
| `objective` | the objective that was optimised |
| `last_semester` | the last semester that holds a course (`null` when there is nothing to plan) |
| `plan` | semester number (string) to the sorted list of course codes; every semester from `current_sem` to `last_semester` appears, empty ones as `[]` |
| `mc_per_semester` | semester number to total MC, for the same semesters (ATAP's 12 MC is included) |
| `preferences_met` | the labels of the preferences the plan satisfies |
| `preferences_not_met` | the labels of the preferences it does not satisfy |
| `added_prerequisites` | only present when the plan contains courses the student did not list but that a planned course needs |
| `notes` | only present for remarks, such as a `must_take` course that is already completed |
| `not_applied` | only present when `unsupported` was given |
| `warnings` | only present when a field of the other question was given |

The main example:

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522"],
  "must_take": ["ST2334", "CS2109S", "CS3263", "CS4248", "CS3230", "CS2100", "CS2106"],
  "mc_max": 8,
  "sem_caps": {"6": 0},
  "objective": "earliest_graduation",
  "light_sems": ["last"],
  "early": ["CS2109S"],
  "rules": [
    {"type": "before", "a": "CS2100", "b": "CS2106", "strength": "must"},
    {"type": "in_sem", "course": "CS3230", "sem": 5, "strength": "prefer"}
  ]
}
```

```json
{
  "status": "PLAN",
  "objective": "earliest_graduation",
  "last_semester": 7,
  "plan": {
    "3": ["CS2100", "CS2109S"],
    "4": ["CS2106", "ST2334"],
    "5": ["CS3230", "CS3263"],
    "6": [],
    "7": ["CS4248"]
  },
  "mc_per_semester": {"3": 8, "4": 8, "5": 8, "6": 0, "7": 4},
  "preferences_met": ["CS3230 in semester 5", "last semester lighter than average", "CS2109S as early as possible"],
  "preferences_not_met": []
}
```

A plan that needs a course the student did not list (CS3263 needs CS2109S, which is not in `completed`):

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"],
  "must_take": ["CS3263"]
}
```

```json
{
  "status": "PLAN",
  "objective": "none",
  "last_semester": 4,
  "plan": {"3": ["CS2109S"], "4": ["CS3263"]},
  "mc_per_semester": {"3": 4, "4": 4},
  "preferences_met": [],
  "preferences_not_met": [],
  "added_prerequisites": ["CS2109S"]
}
```

When every `must_take` course is already completed, the plan is empty:

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"],
  "must_take": ["CS2040S"]
}
```

```json
{
  "status": "PLAN",
  "objective": "none",
  "last_semester": null,
  "plan": {},
  "mc_per_semester": {},
  "preferences_met": [],
  "preferences_not_met": [],
  "notes": ["CS2040S is already completed"]
}
```

A request with ATAP in semester 6 and no other course beside it (the cap of 1 MC in semester 6 leaves room for no
course, because every course in this list is 4 MC, while ATAP's own 12 MC is not counted against the cap):

```json
{
  "query": "plan",
  "current_sem": 5,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "CS2100", "MA1521", "MA1522", "ST2334", "CS2109S", "CS2103T", "CS2101"],
  "must_take": ["CS4248", "CS3219", "CS4218", "CS4243", "CS3263", "CS3230", "CS2106"],
  "mc_max": 12,
  "sem_caps": {"6": 1},
  "atap_sems": [6],
  "objective": "none",
  "early": ["CS3230", "CS4243"],
  "late": ["CS2106"]
}
```

```json
{
  "status": "PLAN",
  "objective": "none",
  "last_semester": 8,
  "plan": {
    "5": ["CS3219", "CS3230", "CS4243"],
    "6": ["CP3880"],
    "7": ["CS3263", "CS4248"],
    "8": ["CS2106", "CS4218"]
  },
  "mc_per_semester": {"5": 12, "6": 12, "7": 8, "8": 8},
  "preferences_met": ["CS3230 as early as possible", "CS4243 as early as possible", "CS2106 as late as possible"],
  "preferences_not_met": []
}
```

The preference labels are fixed strings:

| Source | Label |
|---|---|
| `before` rule | `{a} before {b}` |
| `apart` rule | `{a} and {b} in different semesters` |
| `same_sem` rule | `{a} and {b} in the same semester` |
| `in_sem` rule | `{course} in semester {sem}` |
| `light_sems` entry | `semester {n} lighter than average` or `last semester lighter than average` |
| `balance_load` | `largest semester load is as small as possible` |
| `early` | `{code} as early as possible` |
| `late` | `{code} as late as possible` |

A `NO_PLAN` answer carries `reasons`, a list of strings (section 7 shows the kinds). `not_applied` is added when
`unsupported` was given.

### 3.3 Answers that are not about the plan

`MISSING_INFO` lists which mandatory fields were not given, in the fixed order `completed`, `current_sem`, `target`,
`must_take`, and a ready-to-send question:

```json
{
  "query": "plan"
}
```

```json
{
  "status": "MISSING_INFO",
  "missing": ["completed", "current_sem", "must_take"],
  "message": "This cannot be answered yet. Please give: the courses you have already completed (say so if there are none); the semester you are in now (1 to 8); the courses you still have to take."
}
```

`INVALID_SPEC` lists every error found:

```json
{
  "query": "plan",
  "current_sem": "three",
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"],
  "must_take": [],
  "foo": 1
}
```

```json
{
  "status": "INVALID_SPEC",
  "errors": ["unknown field 'foo'", "current_sem must be an integer, got 'three'"]
}
```

Text that is not JSON gives the same status (this is the `run_text` path):

```json
{
  "status": "INVALID_SPEC",
  "errors": ["not valid JSON: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"]
}
```

`OUT_OF_SCOPE` carries `reasons` and a `message` meant to be shown to the student. The message names the academic year
of the data and sends the student to their faculty or advisor:

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"],
  "must_take": ["CS3263"],
  "programme": "Information Systems"
}
```

```json
{
  "status": "OUT_OF_SCOPE",
  "reasons": ["programme 'Information Systems' is not BComp (CS) Hons"],
  "message": "I can only plan for BComp (CS) Hons single-major students under AY2026/2027 rules, and this request is outside that (programme 'Information Systems' is not BComp (CS) Hons). Course rules differ by programme and aren't in my data for your case, so please check with your faculty or academic advisor."
}
```

A course that is not in the catalogue is also out of scope:

```json
{
  "status": "OUT_OF_SCOPE",
  "reasons": ["course CS9999 (in must_take) is not in the catalogue"],
  "message": "I can only plan for BComp (CS) Hons single-major students under AY2026/2027 rules, and this request is outside that (course CS9999 (in must_take) is not in the catalogue). Course rules differ by programme and aren't in my data for your case, so please check with your faculty or academic advisor."
}
```

## 4. The hard rules, exactly as enforced

A plan is valid when it satisfies every rule below. These are the rules an independent checker has to implement, from
`docs/DATA_SCHEMA.md` and `catalog.json`, so that a disagreement between the checker and the solver points at a bug on
one side.

1. **Which semesters.** Courses are placed in semesters `current_sem` to 8. Each course appears at most once. Every
   `must_take` course that is not already completed appears.
2. **Plannable courses.** A planned course must exist in AY2026/27 and be available to a BComp CS Hons student
   (`exists_in_ay` and `available` in the catalogue). A course blocked by a completed course (its preclusion is already
   satisfied) cannot be planned.
3. **Offering.** A course placed in semester `s` must be offered in term 1 if `s` is odd and in term 2 if `s` is even,
   according to its `offered` list.
4. **Prerequisites.** The prerequisite tree must be satisfied by the completed courses plus the courses planned in
   **strictly earlier** semesters.
5. **Corequisites.** The corequisite tree must be satisfied by the completed courses plus the courses planned in the
   **same or an earlier** semester.
6. **Exclusions.** Two planned courses that exclude each other (`mutually_exclusive_with`, from the preclusion data)
   cannot both appear.
7. **MC caps.** In each semester the total MC is at most `mc_max`, or the `sem_caps` value for that semester if there is
   one. A cap of `0` blocks the semester.
8. **Minimum MC.** If `mc_min` is given, every semester that has at least one course totals at least `mc_min` MC.
9. **Must rules.** Every rule with `"strength": "must"` holds. A `must` rule about an already completed course can
   never be satisfied by placing it, so it gives `NO_PLAN` with a reason (for example `CS2040S is already completed, so
   it cannot be placed in semester 5`).
10. **Added courses.** A course that is not in `must_take` may be planned only because a planned course needs it, as
    part of its prerequisites (placed strictly before that course) or corequisites (same or earlier semester). Courses
    are never added to fill a semester, to reach `mc_min`, or to make a light semester lighter.
11. **ATAP.** ATAP is planned only when `atap_sems` is given (or `CP3880` is in `must_take` or in a `must` rule). It
    is placed in one of the `atap_sems`, at most once, **never in the last semester used** (some course has to come in a
    later semester), and the other courses in that semester total at most `min(8, the semester's cap)` MC. ATAP's own 12
    MC does not count against `mc_max` or `sem_caps`.

Two consequences worth knowing:

- Several different plans can be valid and optimal at the same time. Compare plans by the measures in section 6, not by
  equality with the solver's plan.
- A course the student lists in `completed` can still satisfy the prerequisite of a planned course, and can also block a
  course through an exclusion.

## 5. Preferences, exactly as scored

Preferences never override a hard rule. They are counted: the solver maximises the **number of preferences met**, among
the plans that are already best on the objective and use the fewest added courses (section 6).

| Preference | Counts as met when |
|---|---|
| `prefer` rule `before` | `a` is planned in a strictly earlier semester than `b` |
| `prefer` rule `apart` | `a` and `b` are planned in different semesters |
| `prefer` rule `same_sem` | `a` and `b` are planned in the same semester |
| `prefer` rule `in_sem` | the course is planned in that semester |
| `light_sems` entry (a semester or `"last"`) | the non-ATAP MC of that semester is **strictly below** the average per-semester non-ATAP MC over a window. The window runs from `current_sem` to the last semester used; with objective `none` it runs from `current_sem` to semester 8. An empty plan never meets it. Entries before `current_sem` are ignored. |
| `balance_load` | the largest non-ATAP semester load of the plan equals the smallest largest-load reachable by any plan that ties on the objective and the number of added courses |
| `early` course | the course sits in the earliest semester reachable by any plan that ties on the objective and the number of added courses |
| `late` course | the course sits in the latest such semester |

Special cases:

- A preference that names a course that is not in the plan counts as **not met**.
- A preference that involves an already completed course follows fixed rules: `before` is met when `a` is completed and
  not met when only `b` is; `apart` is met when either course is completed; `same_sem` is met when both are completed and
  not met when only one is; `in_sem` on a completed course is not met; `early` and `late` on a completed course are met.
- `early` and `late` on the same course are scored separately: they are two preferences, and the label of each says
  which one it is.

After the count, two tie-breaks pick one plan among equals. They are **not** part of the graded optimum:

- lower MC in the `light_sems` semesters;
- the earliest last semester (only when the objective is not `earliest_graduation`).

## 6. Optimality

**Valid.** A plan is valid when it satisfies every hard rule in section 4.

**Optimal.** Among all valid plans for an instance, a plan is optimal when it is best on the following measures,
compared in this order:

1. **The objective.**
   - `earliest_graduation`: the smallest last semester, that is, the highest semester number that holds a course.
   - `min_total_mc`: the smallest total MC of all planned courses, added courses and ATAP included.
   - `none`: no ranking at this step.
2. **Fewest added courses**: planned courses that are neither in `must_take` nor already completed.
3. **Most preferences met** (section 5).

The light-semester bonus and the earliest last semester are tie-breaks and are not graded.

The solver reaches this optimum with a staged search: it solves for the objective and fixes that value, then fixes the
number of added courses, then fixes the preference count. This is why a plan that is faster to graduate is never traded
for more preferences.

**Scoring an LLM plan against the optimum.** For one feasible instance, let the solver's answer give the reference
objective value, the minimum number of added courses and the maximum preference count. A pipeline's plan then falls into
exactly one of these classes, checked in this order:

| Class | Condition |
|---|---|
| invalid | it breaks at least one hard rule (the checker lists which) |
| valid, objective gap | valid, but worse than the optimum on the objective; the gap is the difference in last semester or in total MC |
| valid, extra courses | valid and objective-optimal, but with more added courses than the minimum |
| valid, preference gap | valid, objective-optimal and minimal in added courses, but with fewer preferences met than the maximum |
| optimal | none of the above |

For an infeasible instance the answer is correct when it says that no plan exists. A plan given for an infeasible
instance is an *invented plan*; the statement that no plan exists for a feasible instance is an *over-refusal*. The
solver's `status` is the ground truth for both.

**Agreement between solvers.** CP-SAT and each of the four backtracking variants must agree on `status`,
`last_semester` and the number of preferences met on every instance both finish. The plans themselves can differ when
several tie. Disagreement is a bug, never a result.

## 7. Infeasible requests and the response each one gets

The plan builds infeasible instances from five kinds of perturbation. This is what the solver answers for each kind,
and what the reason looks like. Use it to label instances and to score explanation correctness.

| Perturbation | Example | Where the reason comes from |
|---|---|---|
| Preclusion conflict | took CS3244, wants CS3263 | the data: a course that completed courses rule out for good |
| Prerequisite chain too long for the semesters left | CS3263 asked in semester 8 with CS2109S not completed | the conflict explanation |
| MC capacity | required MC exceed the room left | a capacity message with the two numbers |
| Offering parity | a Sem 1-only course with only Sem 2 left | the data: the course cannot go in any remaining semester |
| Conflicting rules | three `must` rules putting three courses in semester 4 under an 8 MC cap | the conflict explanation |
| Hidden conflict (rules and prerequisites together) | a `must` rule placing a course in a semester earlier than its prerequisites allow (example in section 8.1) | the conflict explanation |

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334", "CS3244"],
  "must_take": ["CS3263"]
}
```

```json
{
  "status": "NO_PLAN",
  "reasons": ["CS3263: every option fails: CS2109S is ruled out by completed CS3244 | CS2109HS unavailable (not open to PROGRAMS 0300CSHON)"]
}
```

```json
{
  "query": "plan",
  "current_sem": 8,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"],
  "must_take": ["CS3263"]
}
```

```json
{
  "status": "NO_PLAN",
  "reasons": ["these cannot all hold together with the courses you must take: the prerequisites of CS3263"]
}
```

```json
{
  "query": "plan",
  "current_sem": 7,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334", "CS2109S"],
  "mc_max": 4,
  "must_take": ["CS3263", "CS4248", "CS3230"]
}
```

```json
{
  "status": "NO_PLAN",
  "reasons": ["the required courses need 12 MC but the remaining semesters [7, 8] allow at most 8 MC"]
}
```

```json
{
  "query": "plan",
  "current_sem": 8,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334", "CS2109S"],
  "must_take": ["CS3231"]
}
```

```json
{
  "status": "NO_PLAN",
  "reasons": ["CS3231 cannot be placed in any remaining semester (offered in terms [1]; semesters left [8])"]
}
```

```json
{
  "query": "plan",
  "current_sem": 4,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334", "CS2109S"],
  "mc_max": 8,
  "must_take": ["CS3263", "CS4248", "CS3230"],
  "rules": [
    {"type": "in_sem", "course": "CS3263", "sem": 4, "strength": "must"},
    {"type": "in_sem", "course": "CS4248", "sem": 4, "strength": "must"},
    {"type": "in_sem", "course": "CS3230", "sem": 4, "strength": "must"}
  ]
}
```

```json
{
  "status": "NO_PLAN",
  "reasons": ["these cannot all hold together with the courses you must take: your rule: CS3263 in semester 4; your rule: CS4248 in semester 4; your rule: CS3230 in semester 4; the MC limits (at most 8 MC per semester)"]
}
```

Other reasons the solver can give:

```json
{
  "status": "NO_PLAN",
  "reasons": ["these cannot all hold together with the courses you must take: your rule: CS3263 before CS4248; your rule: CS4248 before CS3263"]
}
```

```json
{
  "status": "NO_PLAN",
  "reasons": ["CS3263 cannot be placed in any remaining semester (offered in terms [1, 2]; semesters left [])"]
}
```

```json
{
  "status": "NO_PLAN",
  "reasons": ["CS3231 cannot be placed in semester 6"]
}
```

The reasons come in three forms. The reasons from the data and the capacity message are exact. The conflict explanation
is described in section 8.

## 8. `explain.py` and Responsible AI

### 8.1 What `explain.py` does

When a `NO_PLAN` has no simpler cause, `solver/explain.py` finds a **minimal conflicting set** of rules: a set of rule
groups that cannot all hold together, where removing any one group makes the rest satisfiable. Each rule group is
switched by an assumption literal inside a copy of the CP-SAT model; CP-SAT reports which assumptions it needs to prove
infeasibility, and `explain.py` then removes groups one at a time until none can be removed.

The groups it can name:

| Text in the reason | Group |
|---|---|
| `your rule: ...` | one of the student's rules |
| `the prerequisites of CODE` | the prerequisite tree of that course |
| `the MC limits (...)` | `mc_max` and `sem_caps` |
| `your minimum of N MC in every semester that has courses` | `mc_min` |
| `the semesters in which the courses are offered` | offering terms |
| `the course exclusions (courses that cannot be taken together)` | preclusions |
| `the ATAP rules (allowed semesters, not the last semester, at most 8 MC beside it)` | ATAP |

The full reason reads: `these cannot all hold together with the courses you must take: <list>`. Items that are not part
of the conflict, such as an unrelated rule or a preference, do not appear.

```json
{
  "query": "plan",
  "current_sem": 5,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "CS2100", "MA1521", "MA1522", "ST2334", "CS2109S", "CS2103T", "CS2101"],
  "must_take": ["CS4248", "CS3219", "CS4218", "CS4243", "CS3263", "CS3230", "CS2106"],
  "mc_max": 12,
  "sem_caps": {"6": 1},
  "atap_sems": [6],
  "objective": "earliest_graduation",
  "early": ["CS3230"],
  "rules": [
    {"type": "in_sem", "course": "CS3219", "sem": 5, "strength": "must"},
    {"type": "in_sem", "course": "CS4218", "sem": 5, "strength": "must"},
    {"type": "in_sem", "course": "CS2106", "sem": 8, "strength": "prefer"}
  ]
}
```

```json
{
  "status": "NO_PLAN",
  "reasons": ["these cannot all hold together with the courses you must take: your rule: CS4218 in semester 5; the prerequisites of CS4218"]
}
```

CS4218 needs CS3213 or CS3219 completed in an earlier semester; neither is completed, and the student is already at
semester 5. The `CS3219 in semester 5` rule and the `CS2106` preference are not part of the conflict and are left out.

### 8.2 What the explanation is, and is not

- It is **one** minimal conflict. A request can contain several independent conflicts; the solver returns one of them.
  After the student fixes it, re-running can show another. Explanation scoring should accept any correct minimal
  conflict, not compare against a single expected one.
- It is **minimal** (nothing can be dropped) and **sound** (the named items really cannot hold together). Both are
  covered by tests.
- It describes the student's **stated** rules together with the data. It is not a statement of university policy.

### 8.3 Links to the Responsible AI section of the report

| Risk in the plan | What the solver does |
|---|---|
| Confidently wrong plans | A plan is only returned after every hard rule is satisfied by construction, and an impossible request returns `NO_PLAN` with the conflicting items instead of an invented plan. The explanation lets the student check the claim against their own rules. |
| Over-refusal | `NO_PLAN` is returned only when the solver has proved there is no plan. One exception is listed in section 11: a CP-SAT time-out. The tight-feasible instance set measures how often the pipelines over-refuse. |
| Silent assumptions | Added courses (`added_prerequisites`), skipped requests (`not_applied`), ignored fields (`warnings`) and remarks (`notes`) are all reported, so nothing the solver decided on its own, and nothing it dropped, is hidden. The out-of-schema set measures whether the LLM flags or drops such wishes. |
| Stale knowledge | Every course fact comes from the AY2026/27 data. `OUT_OF_SCOPE` messages name the academic year. A `PLAN` or `NO_PLAN` answer does not repeat it, so the answer shown to a student should add the data year. |
| Waivers and over-reliance | The wording "these cannot all hold together" is about the stated rules and the data. A student can still appeal; the answer shown to a student should say that an advisor decides. `OUT_OF_SCOPE` already does. |
| Privacy | The solver reads only the spec. Instances are synthetic. |
| Bias | The solver only plans for the list in `must_take`; unusual degree paths are covered only if the list says so. |

## 9. The four backtracking variants

`solver/backtrack.py` is our own CSP solver, written independently of the CP-SAT model (it does not import
`model.py` or `objectives.py`). It solves Q2 only; a Q1 spec is passed straight to the Q1 code with all counters at zero.
It exists for the solver ablation (plain backtracking vs MRV vs forward checking vs MAC) and for cross-checking CP-SAT.

The variants are **cumulative**. Each one includes the techniques of the one before it:

| Variant | Definition |
|---|---|
| `plain` | static variable order; each value is checked only against the variables already assigned |
| `mrv` | `plain` plus MRV (minimum remaining values): the next variable is the one with the fewest legal values given the current assignment, counted on demand |
| `fc` | `mrv` plus forward checking: after each assignment, the values of unassigned variables that conflict with the assigned ones are deleted |
| `mac` | `mrv` plus forward checking plus domain propagation: after each assignment the pruning is repeated, using the reduced domains, until no domain changes; an empty domain means backtrack |

So `mac` includes `fc`, and `fc` includes `mrv`. Slides 36 to 38 of the CSP lecture define forward checking and MAC;
`mac` reaches the same fixpoint as AC-3 but rescans every variable instead of keeping a queue of arcs, and the MC caps
are checked only against assigned courses.

How the search is organised:

- A variable is a candidate course. A course the student must take takes a value in its allowed semesters. A course
  that could be added also has the value 0 (not planned). Values are tried in ascending semester order, 0 first.
- The search is **branch-and-bound** over the same stages as CP-SAT (objective, added courses, preferences, tie-breaks),
  so it proves the optimum instead of stopping at the first solution.
- Every complete plan gets a full validity check, so pruning only changes speed, never the answer.

How to call it:

```python
from solver.backtrack import VARIANTS, solve_with_stats

answer, stats = solve_with_stats(spec, variant="mac", time_limit=60)
```

`answer` has the same format as `run()`. `stats` has:

| Counter | Meaning |
|---|---|
| `nodes` | assignment attempts, summed over all search stages |
| `backtracks` | assignments rejected (inconsistent, a domain emptied, or cut by the bound), plus dead ends found by `mrv` |
| `checks` | constraint checks performed |
| `seconds` | wall-clock seconds |
| `timed_out` | `true` when the time limit was reached |

When the time limit is reached the answer is `{"status": "TIMED_OUT", "reasons": [...]}` and `timed_out` is `true`.
Exclude such rows when computing agreement with CP-SAT, and report the number of them. An unknown `variant` raises
`ValueError`.

The counters for the main example are deterministic (`seconds` is not):

| variant | status | last semester | preferences met | nodes | backtracks | checks |
|---|---|---|---|---|---|---|
| plain | PLAN | 7 | 3 | 6477 | 5117 | 11189 |
| mrv | PLAN | 7 | 3 | 733 | 350 | 42039 |
| fc | PLAN | 7 | 3 | 1368 | 731 | 29134 |
| mac | PLAN | 7 | 3 | 1285 | 751 | 35134 |

All four variants reach the same optimum. They differ in how much they search. Node counts alone mislead: `fc` and
`mac` use fewer nodes than `plain` but more checks per node, and on one instance `mrv` can use fewer nodes than `fc`.
Compare nodes, checks and seconds together, and use medians over many instances.

The ablation runner compares CP-SAT with the four variants over a JSON list of `{"id": ..., "spec": {...}}`:

```bash
python -m experiments.run_ablation instances.json --limit 30 --out rows.csv --time-limit 60
```

It writes one CSV row per instance and engine, with the columns `id, engine, status, last_semester, preferences_met,
seconds, nodes, backtracks, checks, timed_out`, and prints for each engine the number of instances finished, the median
seconds, the median nodes and the agreement with CP-SAT over the finished instances.

## 10. Analysis directions the solver makes possible

Beyond the analyses already in the project plan, these are available from the solver's output:

1. **Explanation correctness.** Compare the items named in a `NO_PLAN` reason with the perturbation that was injected.
   The item kinds in section 8.1 map to the perturbation types in section 7. Any correct minimal conflict counts.
2. **Over-refusal against invented plans.** Use the solver's `status` as ground truth for the feasible and infeasible
   confusion matrix, split by tight-feasible and loose-feasible instances.
3. **Translation failure types for pipeline B.** Classify each B failure as: not valid JSON, `INVALID_SPEC` (which error),
   a false `MISSING_INFO` (a field the student stated was left out), a field with the wrong value, a wish that should have
   been in `unsupported` but was dropped, or a field of the other question (`warnings`).
4. **Does a translation error change the answer?** Run the solver on the translated spec and on the gold spec and compare
   the two answers. Many spec differences leave the answer unchanged; this separates harmless from harmful errors.
5. **Optimality classes** from section 6 for pipelines A0, A and C, by objective, and the number of added courses the LLM
   plans compared with `added_prerequisites`.
6. **Preference satisfaction rate** and the share of plans that meet every preference.
7. **Solver ablation** with the counters in section 9: median nodes, checks and seconds per variant, the share of
   instances that hit the time limit, and the agreement rate with CP-SAT (it must be 100% on finished instances).
8. **Nodes against the raw search space.** The raw space is the product, over the candidate courses, of the number of
   values each can take (the semesters left plus one for "not planned"). The runner does not output it; compute it from
   the instance, for example with the number of `must_take` courses and the semesters left, and plot it against `nodes`.
9. **Scaling.** Solver time and nodes against the number of courses, the length of the prerequisite chain and how tight
   the MC caps are.
10. **Cost.** CP-SAT answers in well under a second on the instances tried so far, which makes the LLM call the dominant
    cost and latency of pipeline B.

## 11. Known limitations

- **CP-SAT time-out looks like `NO_PLAN`.** If a stage reaches 60 seconds without an answer, the status is `NO_PLAN`
  and the reason says the solver ran out of time. By status alone this cannot be told apart from true infeasibility;
  check the reason text, and count such answers separately.
- **One minimal conflict.** `explain.py` names one minimal conflict, not all of them (section 8.2).
- **Ties.** Several plans can be equally good; compare by measure, not by plan.
- **Modelled range.** Semesters 1 to 8 only, and only BComp (CS) Hons, single major, AY2026/27.
- **Graduation** means completing every course in `must_take`. Degree requirements are not derived.
- **Not modelled:** S/U, CAP, module bidding, module mapping, timetable clashes, failed courses and waivers. Requests
  about them belong in `unsupported`.
- **The backtracking solver** has a time limit and a `TIMED_OUT` status that CP-SAT does not have. Instances with many
  added courses are the slowest.
