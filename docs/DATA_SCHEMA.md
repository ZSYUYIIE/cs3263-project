# Data schema (M1 → M2, M3)

This is the contract between the data pipeline (M1) and everyone who reads the data:
the CP-SAT model (M2), the instance generator, pipelines and checker (M3), and any LLM
prompt that is given course records. If you need a field that is not here, ask M1 rather
than reading `data/raw/` directly. Raw NUSMods fields change between years. This schema
does not change without a version bump.

- **Schema version:** 1.0 (`catalog.json → schema_version`)
- **Academic year:** AY2026/27, fetched 27 Oct 2026 (`catalog.json → fetched_at`)

## Files

| File | For | What it is |
|---|---|---|
| `data/processed/AY2026-2027/catalog.json` | code | One record per course, keyed by course code. **The file to load.** |
| `data/processed/AY2026-2027/COURSES.md` | people, LLM prompts | The same data as readable blocks. Search for `### CS3263`. |
| `data/processed/AY2026-2027/edges.csv` | spreadsheets, graphs | `course, relation, other, other_in_ay` with relation `needs_prereq` / `needs_coreq` / `precluded_by`. |
| `data/processed/AY2026-2027/PARSE_REPORT.md` | M1, reviewers | Counts, cross-check against NUSMods' own tree, warnings, asymmetric preclusions. |
| `data/processed/AY2026-2027/rules_literal.json` | auditing | The rule strings parsed into trees *before* any assumption was applied. |
| `data/manual/overrides.json` | M1 | Hand fixes, applied last, each with a reason. |
| `data/manual/SPOT_CHECK.md` | everyone | Hand-verification checklist against nusmods.com. |
| `data/config/scope.json` | M1 | Which courses are fetched. |
| `data/config/student_context.json` | M1, M3 | The student that conditions are resolved for (see below). |

Everything under `data/processed/` is generated. Never edit it by hand: change the parser
or `overrides.json` and rebuild.

## A course record

```jsonc
"CS3263": {
  "code": "CS3263",
  "title": "Foundations of Artificial Intelligence",
  "mc": 4,                       // number; null only for stubs
  "offered": [1, 2],             // 1 = Sem 1, 2 = Sem 2, 3 = Special Term I, 4 = Special Term II
  "exists_in_ay": true,          // false = code has no AY2026/27 page (old/renamed course)
  "details": "full",             // "full" = fetched; "stub" = only known by name (see below)
  "scope": "seed",               // seed | prereq_closure | referenced_only
  "available": true,             // can this student put it in a plan this AY?
  "unavailable_reasons": [],     // why not, in words, when available = false
  "prereq": {
    "text":  "(CS2109S or CS2109HS) and (CS2040 or CS2040S or ...) and (...) and (...)",
    "logic": { "op": "and", "args": [ ... ] },   // null = none, false = never satisfiable
    "courses": ["CS2040", "CS2040C", ...],       // every code that appears in logic
    "source_text": "If undertaking an Undergraduate Degree THEN must have completed ..."
  },
  "coreq": { same shape as prereq },            // must be taken in the same or an earlier semester
  "preclusion": {
    "text": "CS3243",
    "blocked_if": {"op": "course", "code": "CS3243", "min_grade": "D"},  // null = never blocked
    "courses": ["CS3243"],                       // every code in blocked_if
    "mutually_exclusive_with": ["CS3243", "CS4263"],   // blocked_if codes + codes that list THIS course
    "source_text": "If undertaking an Undergraduate Degree THEN must not have completed CS3243 ..."
  },
  "unlocks": ["CP4284", "CS4244", ...],          // courses whose prereq.logic mentions this one
  "department": "Computer Science", "faculty": "Computing",
  "assumptions": [...],          // every non-course condition that was folded away, in words
  "warnings": [...],             // things the parser was unsure about: spot-check these
  "overrides": [...],            // reasons for any manual fix applied
  "source": { "url": "https://nusmods.com/courses/CS3263", "prerequisiteRule": "...", ... }
}
```

### Logic trees

`prereq.logic`, `coreq.logic` and `preclusion.blocked_if` all use the same four node types:

| Node | Meaning (given the set of completed courses) |
|---|---|
| `{"op": "course", "code": "CS2040S", "min_grade": "D"}` | CS2040S is completed (at grade ≥ `min_grade`, which is D everywhere in scope). May carry `"via_pattern": "CS2040%"` if it came from a wildcard. |
| `{"op": "and", "args": [...]}` | every arg holds |
| `{"op": "or", "args": [...]}` | at least one arg holds |
| `{"op": "n_of", "n": 2, "args": [...]}` | at least `n` args hold (always `1 < n < len(args)`; other cases are simplified to `or`/`and`) |

Invariants, checked by `python -m m1_data check`:
- Trees are simplified: no booleans inside a tree, no single-argument `and`/`or`, no nested same-op chains.
- Every `code` in any tree has its own record in `courses` (possibly a stub).
- `mutually_exclusive_with` is symmetric.
- No hard prerequisite cycles. Wildcard edges are excluded, because they are big n-of pools.

**Reading `prereq.logic` at the top level:** `null` means there is no prerequisite. `false` means
it can never be met by this student, usually because of a programme gate. In that case
`available` is false. Anything else is a tree.

**Reading `blocked_if`:** the student may not take the course once their completed courses satisfy
this tree. For the planner, treat `mutually_exclusive_with` as "at most one of each pair, across
the transcript and the plan". This covers both directions, including cases where only the
other course lists the preclusion.

### Stubs

Some codes only appear inside other courses' rules. Examples: `CS1010` (an old course still
named in preclusions) and `BT2101` (an alternative prerequisite outside our scope). They get a
record with `details: "stub"`, `available: false`, no prereq and no MC. If one of them is in a
student's *completed* list it still counts for satisfying trees and for exclusions. It just can't
be *planned*.

- `exists_in_ay: false`: no AY2026/27 page (retired or renamed). 95 of these.
- `exists_in_ay: true, details: "stub"`: exists, but outside the fetch scope. Its `offered` comes
  from the module list. To plan it, add it to `seed_codes` in `scope.json` and rebuild.

## Student context

NUSMods rules contain conditions that are not about courses: programme, cohort,
A-level subjects, GPA, units completed, year of study. The pipeline evaluates all of
them for **one configured student** (`data/config/student_context.json`), so that every
tree you receive mentions only courses.

| Field | Default | Effect |
|---|---|---|
| `program_type` | `"Undergraduate Degree"` | Rules gated "If undertaking an Undergraduate Degree THEN …" apply. |
| `programs` | `["0300CSHON"]` | BComp (CS) Hons. Gates such as "must be in 0300CSHON" or "must NOT be in 0300CSHON" are resolved (e.g. CS2109HS → unavailable). |
| `second_major`, `minor`, `special_programme` | `[]` | Same, for those groups. |
| `cohort` | `2024` | Cohort gates such as `S:2017` (2017 onwards) and `E:2016` (up to 2016). |
| `subjects_held` | maths `06/0006/07/0007/21/22`, English proficiency `EP` | Pre-university subject alternatives. With H2 Maths held, "A-level Maths **or** MA1301" needs nothing. Physics (08/64), Biology (11) and Economics (05) are not held, so their course alternatives stay required. Grades are not checked. |
| `subject_level` | `"H2"` | `SPECIAL "SUBJECT_LEVEL=H2"` conditions. |
| `acad_level`, `units_completed`, `gpa` | `null` (unknown) | Resolved by `unknown_policy` (`assume_true`). Each one is logged in `assumptions`. These only appear in out-of-scope courses. |

To produce data for a different student (for example a Data Science student, or a 2020
cohort), copy the file, edit it, and rebuild. The `student_context` used is embedded in
`catalog.json`.

## Interpretation decisions

These are judgement calls the raw data forces. Each one is applied the same way everywhere
and is visible in the output. Raise disagreements with M1.

1. **The rule string is the source of truth, not `prereqTree`.** `prerequisiteRule` carries
   the programme, cohort and subject conditions that `prereqTree` drops. Both are parsed and
   compared (`PARSE_REPORT.md`): 198 match and 31 differ. All 31 differences are explained:
   a dropped A-level alternative, a programme/cohort gate, or the ambiguity in item 3.
2. **A course list with no count means "any one of".** `COURSES CS2106:D, CG2271:D` reads
   "CG2271/CS2106" on NUSMods, and `prereqTree` agrees.
3. **`A AND B OR C` without brackets follows NUSMods' reading.** This affects only CS2309.
   Normal precedence gives `(A and B) or C`, but NUSMods shows `A and (B or C)`. We use what
   students see on nusmods.com and log a warning.
4. **Preclusion clauses are independent blocks.** A preclusion rule lists things the student must not
   have. Any listed course group completed, or any excluded programme matched, blocks the
   course. For rules joined by AND (nearly all of them) this is the literal meaning. For the few
   that join clauses with OR, the literal reading would let excluded students through, so the
   intended reading is used and a warning is logged.
5. **Preclusions are mutual.** If A lists B, then B is also blocked by A, even when B's page
   doesn't say so. Asymmetric pairs are listed in `PARSE_REPORT.md`.
6. **Wildcards** (`CS2040%`, `NM4%`) expand to every matching AY2026/27 code except the
   course itself. Expanded nodes carry `via_pattern`.
7. **Grades are ignored.** Every in-scope threshold is D, and "completed" means passed.
8. **Not offered = not available.** A course with no semester this AY can't be planned. Most of
   these are Yale-NUS (YSC) courses.

## Overrides

`data/manual/overrides.json` takes the form `{"courses": {"CODE": {...}}}`. Allowed keys:
`prereq_logic` (a logic tree, `null` or `false`), `preclusion_courses` (list of codes), `offered`,
`mc`, `available`, `unavailable_reasons`, and the required `reason`. Overrides are applied after
parsing and recorded in the course's `overrides` list.

## Notes for M2 (CP-SAT)

- Plannable set: `exists_in_ay and available` (`Catalog.plannable()`).
- `sem(c) ∈ {k..8, none}`. A course in the transcript is fixed as "done before k".
- `course` leaf for x: `done(x)` (in the transcript) or `sem(x) < sem(c)`.
- `and` / `or` / `n_of` → `AddBoolAnd` / `AddBoolOr` / a sum of literals `≥ n`, with one
  reified literal per tree node.
- `coreq`: same, with `sem(x) ≤ sem(c)`.
- Preclusion: for each pair in `mutually_exclusive_with`, at most one is done or planned.
- Offering parity: semester `s` is Sem 1 when `s` is odd. Use `offered`.

## Notes for M3 (generator, checker)

- `Catalog.can_take(code, completed, semester)` gives T1 ground truth and reasons.
- `Catalog.reachable(code, completed)` tells you whether a course is ruled out forever by
  completed courses, with an explanation, e.g. *"CS3263: every option fails: CS2109S is ruled
  out by completed CS3244 | CS2109HS unavailable (not open to PROGRAMS 0300CSHON)"*. This
  is useful for building perturbation type 5 ("hidden conflict two or more hops away").
- To keep the checker independent (as the doc requires), implement the checks from this
  document rather than importing `m1_data.catalog`.
