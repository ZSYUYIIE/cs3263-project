# Guide for AI agents

You are working in the CS3263 project repo (LLM vs constraint solver for NUS degree
planning). Read `README.md` for the project and `docs/DATA_SCHEMA.md` for the data contract.
This file covers what you need to avoid mistakes.

## Ground rules

1. **Course facts come from the data, never from memory.** Prerequisites and preclusions change
   every year. Your training data is likely an older AY. Look the course up in
   `data/processed/AY2026-2027/catalog.json` (or `COURSES.md`) and cite the AY.
2. **Do not edit `data/processed/`, `data/raw/` or `docs/diagrams/`.** They are generated. To change an output,
   fix the parser in `m1_data/` or add an entry with a `reason` to `data/manual/overrides.json`,
   then run `python -m m1_data build`.
3. **After any change to `m1_data/`, run `python -m m1_data build` and `python -m pytest -q`.**
   Both must pass. `build` already runs the invariant checks.
4. **Keep the evaluation checker independent.** Code under `eval/` must not import
   `m1_data.catalog` or `m1_data.resolve`. It implements the rules from `docs/DATA_SCHEMA.md`
   itself, so a bug in one side shows up as a disagreement.
5. **Never put the answer in the prompt.** Pipeline A gives the LLM course records, chosen by the
   rule written in the report. Don't add fields like `available` or `reachable` that do the
   reasoning for the model unless that is the condition being tested.

## Finding things fast

| Need | Where |
|---|---|
| One course, readable | `grep -n -A 12 "^### CS3263" data/processed/AY2026-2027/COURSES.md` |
| One course, structured | `catalog.json → courses → "CS3263"` or `Catalog.load()["CS3263"]` |
| Is X allowed now? (T1) | `Catalog.can_take(code, completed, semester)` |
| Is X ruled out forever? | `Catalog.reachable(code, completed)` |
| Courses that need X | `courses[X]["unlocks"]` |
| All relations as a table | `edges.csv` |
| Traverse the graph (and/or kept) | `graph.json` (nodes `course` / `all` / `any` / `n_of`; edges `prereq` / `arg` / `excludes`) |
| Show a person a course | `data/processed/AY2026-2027/diagrams/<CODE>.html` |
| Why a rule was read a certain way | `courses[X]["assumptions"]`, `["warnings"]`, and `docs/DATA_SCHEMA.md#interpretation-decisions` |
| Raw NUSMods text | `courses[X]["prereq"]["source_text"]`, `["source"]["prerequisiteRule"]` |

## Logic tree semantics, in one breath

Nodes are `course` (completed), `and`, `or`, and `n_of` (≥ n args). `prereq.logic = null`
means no requirement, and `false` means never satisfiable. `preclusion.blocked_if` is the
condition under which the student may NOT take the course. `mutually_exclusive_with` is
the symmetric "never both" list to use in a planner. Stub records (`details: "stub"`) can
satisfy a tree when they appear in a transcript, but can't be planned.

## Things that look like bugs but are intended

- `CS2109HS`, `CS2040HS` and `CS2030HS` are `available: false`, because they are closed to BComp CS Hons.
- `MA1521` and similar have no prerequisite. The "A-level H2 Maths or MA1301" alternative is
  resolved by the student context, which holds H2 Maths.
- `CS2309` follows NUSMods' bracket reading, not normal precedence (see its `warnings`).
- 95 codes have `exists_in_ay: false`. They are old courses that are still named in preclusions.
