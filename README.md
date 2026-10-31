# CS3263 Project: LLM vs Solver for NUS Degree Plans

We compare a frontier LLM answering NUS degree-planning requests directly against the
same LLM translating each request into a spec for a constraint solver (CP-SAT). We also
measure where each approach breaks, including when no valid plan exists.
Scope: BComp (CS) Hons, NUSMods AY2026/27 data.

| Role | Owns | Lives in |
|---|---|---|
| **M1** (leader) | Data pipeline: prerequisite and exclusion parsing, coordination | `m1_data/`, `data/` (**done, see below**) |
| M2 | CP-SAT model, own CSP solver | `solver/`, `experiments/` (**done, see below**) |
| M3 | Instance generator and perturbations, pipelines A0/A/B/C, evaluation harness | `instances/`, `pipelines/`, `eval/` (to add) |

Key dates: data parsed and spot-checked by **Thu 29 Oct**, feasible T2 results by
**Wed 4 Nov** (fallback point), report and presentation **Fri 13 Nov**.

## Data pipeline (M1)

The NUSMods API gives prerequisites as rule strings with programme, cohort and A-level
conditions mixed in. Preclusions come as free text plus a rule string. The pipeline turns
both into **course-only logic trees** for a BComp CS Hons student, writes them as JSON for
code and Markdown for people, and checks the result.

```
NUSMods API ──fetch──▶ data/raw/AY2026-2027/modules/*.json      (verbatim, minus timetables)
                │
              build      parse rule strings ─▶ resolve for student_context ─▶ simplify
                │        cross-check against NUSMods' own prereqTree
                ▼
data/processed/AY2026-2027/
    catalog.json        ◀── load this (one record per course)
    COURSES.md          ◀── read this (one block per course)
    diagrams/index.html ◀── look at this (one dependency diagram per course)
    graph.json  course_graph.graphml  edges.csv  PARSE_REPORT.md  rules_literal.json
```

### Use the data

The processed data is committed, so you don't need to run anything to use it.

```python
from m1_data.catalog import Catalog
cat = Catalog.load()

cat["CS3263"]["prereq"]["text"]
# '(CS2109S or CS2109HS) and (CS2040 or CS2040S or ...) and (MA2001 or MA1522 or ...) and (...)'

cat.can_take("CS3263", {"CS2040S", "MA1521", "MA1522", "ST2334"})
# (False, ['missing prerequisite: CS2109S or CS2109HS'])

cat.reachable("CS3263", {"CS3244", "CS2040S", "MA1521", "MA1522", "ST2334"})
# (False, 'CS3263: every option fails: CS2109S is ruled out by completed CS3244 |
#          CS2109HS unavailable (not open to PROGRAMS 0300CSHON)')
```

Without Python, open `data/processed/AY2026-2027/COURSES.md` and search for `### CS3263`.

### See it as a graph

- **Open `data/processed/AY2026-2027/diagrams/index.html` in a browser.** It has one dependency diagram
  per course: what it needs, what needs it, and what it excludes. Click through course to course.
- **Overviews for the report:** [`docs/diagrams/cs-core-chain.html`](docs/diagrams/cs-core-chain.html)
  (year 1 → CS3263) and [`docs/diagrams/exclusion-trap.html`](docs/diagrams/exclusion-trap.html)
  (why completing CS3244 makes CS3263 impossible).
- **For code:** `graph.json` is a node-link graph that keeps the and/or structure.
  `course_graph.graphml` opens in yEd, Gephi or Cytoscape.

The diagrams follow the diagram-design skill (dependency-graph type, default skin) and pass its
`self_check.py` and `verify-geometry.py`.

**Scope:** BComp (CS) Hons, single major, AY2026/27. Requests about DDPs, second majors,
minors or other programmes are answered `OUT_OF_SCOPE` with a reason (`m1_data/scope.py`).

**Field reference and every interpretation decision: [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md).**

### Rebuild the data

Python 3.10+ and the standard library only. Run from the repo root:

```bash
python -m m1_data fetch    # download from NUSMods (internet; about 1 min)
python -m m1_data build    # parse + write data/processed + run checks
python -m m1_data check    # checks only
python -m pytest -q        # tests (pip install pytest)
```

Change which courses are fetched in `data/config/scope.json`, and the student that
conditions are resolved for in `data/config/student_context.json`. Hand fixes go in
`data/manual/overrides.json`, and every fix needs a reason.

### Status

| | |
|---|---|
| Courses with full data | 306 (all CS 1000–4999 + prerequisite closure + referenced) |
| Rule strings parsed | 918 / 918, 0 errors |
| Cross-check with NUSMods prereqTree | 198 match, 31 differ (all explained in `PARSE_REPORT.md`) |
| Invariant checks | pass |
| Hand spot-check | **to do:** `data/manual/SPOT_CHECK.md` (before generating instances) |

## Solver (M2)

The solver answers two kinds of request, each given as a JSON **spec**:

- **Q1** (`"query": "eligible"`): can the student take one course now, and if not, why not.
- **Q2** (`"query": "plan"`): plan the remaining semesters (1 to 8) so that every course in
  `must_take` is completed, and optimise the stated objective and preferences.

It needs Python 3.10+ and the `ortools` package (CP-SAT). Run from the repo root:

```bash
python -m pip install -r requirements-dev.txt    # pytest and ortools
python -m solver.run spec.json                   # answer one spec as JSON
python -m pytest -q                              # all tests
```

```python
import json
from m1_data.catalog import Catalog
from solver.run import run

answer = run(json.load(open("spec.json")), Catalog.load())
```

Solver reference (inputs, outputs, rules, optimality, variants): [`docs/SOLVER_GUIDE.md`](docs/SOLVER_GUIDE.md)
Pipeline B translation guide and prompt: [`docs/TRANSLATION_GUIDE.md`](docs/TRANSLATION_GUIDE.md)

### Spec fields

| Field | Used by | Meaning |
|---|---|---|
| `query` | both | `"eligible"` or `"plan"` |
| `current_sem` | both | first semester still to plan (odd semester = Sem 1, even = Sem 2); optional in Q1 |
| `completed` | both | courses already passed (`[]` if none) |
| `programme` | both | copied from the student; checked by `m1_data/scope.py` |
| `unsupported` | both | wishes the solver cannot model; echoed back as `not_applied` |
| `target` | Q1 | the course asked about |
| `must_take` | Q2 | courses the plan must contain (`[]` if none) |
| `mc_max`, `mc_min` | Q2 | MC limit per semester (default 20); minimum MC in every semester that has courses |
| `sem_caps` | Q2 | per-semester limit overriding `mc_max`; `0` blocks the semester |
| `atap_sems` | Q2 | semesters where ATAP (`CP3880`, 12 MC) may be planned; giving the field asks for ATAP |
| `rules` | Q2 | list of `{"type": before / in_sem / apart / same_sem, "strength": must / prefer, ...}` |
| `objective` | Q2 | `earliest_graduation`, `min_total_mc` or `none` |
| `light_sems`, `balance_load`, `early`, `late` | Q2 | preferences: lighter semesters (`"last"` or a number), smallest peak load, earlier or later courses |

A field the student did not state is left out of the spec. `null`, `""` and `[]` are never used as placeholders;
`[]` is written only when the student says there are none. Field values of the wrong type or unknown fields give
`INVALID_SPEC`.

### Answer statuses

| Query | Statuses |
|---|---|
| Q1 | `ELIGIBLE`, `NOT_ELIGIBLE`, `MISSING_INFO`, `INVALID_SPEC`, `OUT_OF_SCOPE` |
| Q2 | `PLAN`, `NO_PLAN`, `MISSING_INFO`, `INVALID_SPEC`, `OUT_OF_SCOPE` |

The check order is `INVALID_SPEC`, then `OUT_OF_SCOPE`, then `MISSING_INFO`. `MISSING_INFO` lists the mandatory
fields that were not given (Q1: `completed`, `target`; Q2: `completed`, `current_sem`, `must_take`).
`NO_PLAN` carries a `reasons` list; when the rules conflict, `solver/explain.py` names a minimal set of
conflicting rules.

### Rules the model enforces

- Prerequisites in a strictly earlier semester, corequisites in the same or an earlier one.
- A course only in semesters of a term it is offered in; preclusions and mutual exclusions respected.
- MC per semester at most `mc_max` (or the `sem_caps` value); `mc_min` for semesters that have courses.
- A course the student did not list is added only when a planned course in a later semester needs it
  (reported as `added_prerequisites`).
- ATAP only in `atap_sems`, never the last semester used, and the other courses in that semester total at most
  min(8, the semester cap) MC; ATAP's own 12 MC is not counted against the cap.
- A `must` rule is hard; a `prefer` rule only counts towards the preference tie-break.

### Optimisation order (Q2)

1. Hard rules. No solution gives `NO_PLAN`.
2. The objective (`earliest_graduation` minimises the last semester, `min_total_mc` minimises total MC); fixed.
3. Fewest added courses; fixed.
4. Preferences: the number met among `prefer` rules, `light_sems`, `balance_load`, `early` and `late`; fixed.
5. Lower MC in the light semesters.
6. Earliest last semester (only when the objective is not `earliest_graduation`; a presentation tie-break).

### Files

| File | Role |
|---|---|
| `solver/spec.py` | validates and cleans a spec |
| `solver/run.py` | entry point: `run(spec, catalog)`; shared `prepare()` front half |
| `solver/q1.py` | Q1 eligibility answer |
| `solver/model.py` | CP-SAT model (variables and hard rules) |
| `solver/objectives.py` | Q2 staged optimisation and answer building |
| `solver/explain.py` | minimal conflicting rules for a `NO_PLAN` |
| `solver/backtrack.py` | own backtracking solver with four variants (below); independent of `model.py` and `objectives.py` |
| `experiments/run_ablation.py` | ablation runner (CP-SAT against the four variants) |
| `tests/test_solver.py`, `test_q2.py`, `test_explain.py`, `test_backtrack.py`, `test_ablation.py` | tests |

### Own CSP solver and ablation

`solver/backtrack.py` solves Q2 with its own backtracking search over partial assignments. The four variants are
cumulative:

- **plain**: static variable order; each value is checked only against the variables already assigned.
- **mrv**: plain plus MRV (minimum remaining values): next variable is the one with the fewest legal values
  given the current assignment, counted on demand.
- **fc**: MRV plus forward checking: after each assignment, values of unassigned variables that conflict with
  the assigned ones are deleted.
- **mac**: MRV plus forward checking plus domain propagation: the pruning is repeated, using the reduced domains,
  until no domain changes; an empty domain means backtrack.

Every complete plan gets a full validity check, so pruning only changes speed. The search is branch-and-bound over
the same stages as CP-SAT, so all four variants and CP-SAT reach the same optimum (status, last semester and number
of preferences met); several plans can tie, so the plans themselves may differ.

```python
from solver.backtrack import solve_with_stats
answer, stats = solve_with_stats(spec, variant="mac", time_limit=60)
# stats: nodes, backtracks, checks, seconds, timed_out
```

`nodes` counts assignment attempts over all stages and `backtracks` counts rejected assignments. A run that
reaches the time limit returns status `TIMED_OUT` and `timed_out=True` (CP-SAT has no such status).

Ablation over a JSON list of `{"id": ..., "spec": {...}}`:

```bash
python -m experiments.run_ablation instances.json --limit 30 --out rows.csv --time-limit 60
```

It writes one CSV row per instance and engine (`id, engine, status, last_semester, preferences_met, seconds, nodes,
backtracks, checks, timed_out`) and prints, per engine, instances finished, median seconds, median nodes and
agreement with CP-SAT over the finished instances.

## Repository layout

```
m1_data/            data pipeline package (fetch, rules, resolve, build, check, catalog,
                    graph, diagrams, scope)
solver/             spec, run, q1, model, objectives, explain, backtrack (M2)
experiments/        run_ablation.py (M2)
examples/           example spec JSON files
data/config/        scope.json, student_context.json
data/raw/           NUSMods responses, kept so results are reproducible (data drifts year to year)
data/processed/     generated outputs (do not edit)
data/manual/        overrides.json, SPOT_CHECK.md
docs/               DATA_SCHEMA.md, SOLVER_GUIDE.md, TRANSLATION_GUIDE.md, diagrams/ (hand-laid overviews)
tests/              pytest
AGENTS.md           orientation for AI coding agents working in this repo
```
