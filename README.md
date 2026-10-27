# CS3263 Project: LLM vs Solver for NUS Degree Plans

We compare a frontier LLM answering NUS degree-planning requests directly against the
same LLM translating each request into a spec for a constraint solver (CP-SAT). We also
measure where each approach breaks, including when no valid plan exists.
Scope: BComp (CS) Hons, NUSMods AY2026/27 data.

| Role | Owns | Lives in |
|---|---|---|
| **M1** (leader) | Data pipeline: prerequisite and exclusion parsing, coordination | `m1_data/`, `data/` (**done, see below**) |
| M2 | CP-SAT model, own CSP solver | `solver/` (to add) |
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

## Repository layout

```
m1_data/            data pipeline package (fetch, rules, resolve, build, check, catalog)
data/config/        scope.json, student_context.json
data/raw/           NUSMods responses, kept so results are reproducible (data drifts year to year)
data/processed/     generated outputs (do not edit)
data/manual/        overrides.json, SPOT_CHECK.md
docs/               DATA_SCHEMA.md, diagrams/ (hand-laid overviews)
tests/              pytest
AGENTS.md           orientation for AI coding agents working in this repo
```
