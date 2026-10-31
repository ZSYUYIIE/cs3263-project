# Translation guide: natural-language request to solver spec (pipeline B)

Pipeline B asks an LLM to turn a student's request into a JSON **spec**, and the solver then answers the spec. The
solver can only be as right as the spec is. This guide tells the LLM exactly how to write the spec, and tells M3 how
to use the guide, how to test it and how to score it.

Everything the solver does with a spec is described in [`docs/SOLVER_GUIDE.md`](SOLVER_GUIDE.md). Every JSON example
and every solver reply below was produced by running the solver.

Terms used in this guide:

- **Spec**: the JSON object the solver reads.
- **MC**: modular credits. Most courses in the data are 4 MC.
- **ATAP**: the Advanced Technology Attachment Programme, an internship semester planned as the course `CP3880` (12 MC).
- **Q1 / Q2**: the two questions, `eligible` (can I take this course) and `plan` (plan my remaining semesters).
- **Gold spec**: the correct spec for an instance, the one the instance was generated from.

Contents:

1. How M3 uses this guide
2. The prompt to give the LLM (copy it as it is)
3. Field-by-field reference
4. Conversion rules: student wording to fields
5. Worked examples
6. Common mistakes and what the solver does with them
7. Scoring a translation

## 1. How M3 uses this guide

- Copy the prompt in section 2 as the instruction of pipeline B. Put the student's request after it. The LLM sees no
  course data: prerequisites, offerings and exclusions are applied inside the solver, and AGENTS.md rule 5 forbids
  putting answers or reasoning in the prompt.
- The LLM must return **only** the JSON object. The harness passes the returned string to `run_text(text)`. Text that
  is not valid JSON, including JSON wrapped in a markdown fence, gives `INVALID_SPEC`:
  `{"status": "INVALID_SPEC", "errors": ["not valid JSON: Expecting value: line 1 column 1 (char 0)"]}`. Decide once, and write it in the report, whether the harness strips fences before calling the
  solver. If it does, count a fenced answer as a formatting error in the translation metrics.
- Each prompt asks exactly one question: `eligible` (Q1) or `plan` (Q2). The `query` value has to match it.
- The gold spec for every generated instance is the spec the instance was generated from. Compare a translated spec with
  the gold spec after cleaning (upper-case codes, duplicates removed), and also compare the two solver answers.
- A good translation is one where the solver answer under the translated spec equals the answer under the gold spec.

## 2. The prompt to give the LLM

Copy everything inside the block, then add the student's request. The examples inside it are verified: the solver
accepts each JSON and answers it as described in section 5.

```text
You convert a student's request into one JSON object for a degree-planning solver. The solver knows all course data;
you do not. Never answer the student's question yourself.

OUTPUT FORMAT
- Output exactly one JSON object and nothing else: no text before or after, no markdown fences, no comments.
- Use only the fields listed below. Never add any other field.
- Leave a field out when the request does not tell you its value. Never write null, "" or [] as a placeholder.
  Write [] only when the student says there are none (for example "I have not completed any module").
- Write semesters and MC as JSON integers, and true/false as JSON booleans.
- Write course codes in capitals without spaces (CS2040S, not "cs 2040s").

STEP 1: CHOOSE THE QUESTION
- "query": "eligible" when the student asks whether they can take one course.
- "query": "plan" when the student asks you to plan their remaining semesters.

FIELDS FOR BOTH QUESTIONS
- "completed": list of the courses the student says they have finished. Courses they do not mention are not completed.
- "current_sem": integer 1 to 8. Semester number = (year - 1) x 2 + semester, so Y1S1 = 1, Y1S2 = 2, Y2S1 = 3, Y2S2 = 4,
  Y3S1 = 5, Y3S2 = 6, Y4S1 = 7, Y4S2 = 8. "Semester 5" means 5.
  For "plan": the semester the student says they are in now, which is where planning starts.
  For "eligible": the semester in which the student wants to take the course ("next semester" is the current
  semester plus 1). Leave it out if the request does not allow you to work it out.
- "programme": only when the student states their programme in words. Write exactly "BComp CS Hons" when the student
  says they are a Computer Science / BComp (CS) Honours student. If the student names a different programme, or a second
  major, minor or double degree, copy the student's own words (for example "Business Analytics", or "BComp CS Hons with
  second major in Mathematics"). Never work out the programme from the course codes: a student who has completed CS
  modules is not necessarily a Computer Science student. Leave it out if the student does not state it.
- "unsupported": list of short strings, one per wish that no field below can express. Never drop such a wish silently.
  Examples: "no 8am classes", "might fail CS3263", "wants a waiver for CS2030S", "S/U option".

FIELDS FOR "eligible" ONLY
- "target": the one course the student asks about.

FIELDS FOR "plan" ONLY
- "must_take": list of the courses the student says they must or want to take.
- "mc_max": most MC in one semester. If the student gives modules instead, use 4 MC per module (3 modules = 12).
- "mc_min": fewest MC in any semester that has courses ("at least N MC per semester").
- "sem_caps": object from semester number written as a string to its own MC limit, for a semester with a different
  limit. A semester with no courses (exchange, NOC, leave of absence) is {"6": 0}.
- "atap_sems": list of semesters, only when the student says they will do ATAP. If the student gives the ATAP semester,
  list just that semester. If they give none, list every semester from current_sem to 8. Do not put ATAP in
  "must_take". If the student wants no other module in the ATAP semester, also set "sem_caps" for that semester to 1
  (not 0, which would block ATAP itself).
- "objective": "earliest_graduation" when the student wants to graduate as early as possible or take the fewest
  semesters; "min_total_mc" when they want the fewest total credits; leave it out otherwise.
- "light_sems": list of semesters that should be lighter, for example [6]. A light final semester is ["last"].
- "balance_load": true when the student wants the workload spread evenly or the heaviest semester kept small.
- "early": courses the student wants as early as possible. "late": courses they want as late as possible.
- "rules": list of rule objects, one per wish about where specific courses go:
    {"type": "before", "a": X, "b": Y, "strength": S}      X must be in an earlier semester than Y
    {"type": "apart", "a": X, "b": Y, "strength": S}       X and Y in different semesters
    {"type": "same_sem", "a": X, "b": Y, "strength": S}    X and Y in the same semester
    {"type": "in_sem", "course": X, "sem": N, "strength": S}   X in semester N
  Each rule has exactly these keys. "strength" is "must" when the student says must, have to, need to, definitely,
  only, or required. It is "prefer" when the student says prefer, would like, ideally, if possible, hope, or when
  you are unsure.

IF INFORMATION IS MISSING
Leave the field out. Do not guess and do not ask the student a question. The solver replies by asking for it.

EXAMPLES
Request: I have finished CS1101S, CS1231S, CS2030S, CS2040S, MA1521, MA1522 and ST2334. Can I take CS3263 in Y2S1?
JSON: {"query": "eligible", "target": "CS3263", "current_sem": 3, "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"]}

Request: Can I take CS3263 next semester?
JSON: {"query": "eligible", "target": "CS3263"}

Request: I have not completed any module yet and I am in Y1S1. Plan my semesters so that I take CS1101S and CS1231S.
JSON: {"query": "plan", "current_sem": 1, "completed": [], "must_take": ["CS1101S", "CS1231S"]}

Request: I am in Y2S1. I have completed CS1101S, CS1231S, CS2030S, CS2040S, MA1521 and MA1522. I still have to take ST2334, CS2109S, CS3263, CS4248, CS3230, CS2100 and CS2106. I can take at most 8 MC per semester, and semester 6 is my exchange semester. I want to graduate as early as possible, with a light last semester. I would like to take CS2109S as early as possible. CS2100 must come before CS2106. If possible, I would like CS3230 in semester 5.
JSON: {"query": "plan", "current_sem": 3, "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522"], "must_take": ["ST2334", "CS2109S", "CS3263", "CS4248", "CS3230", "CS2100", "CS2106"], "mc_max": 8, "sem_caps": {"6": 0}, "objective": "earliest_graduation", "light_sems": ["last"], "early": ["CS2109S"], "rules": [{"type": "before", "a": "CS2100", "b": "CS2106", "strength": "must"}, {"type": "in_sem", "course": "CS3230", "sem": 5, "strength": "prefer"}]}

Request: I am in semester 5 now. I have completed CS1101S, CS1231S, CS2030S, CS2040S, CS2100, MA1521, MA1522, ST2334, CS2109S, CS2103T and CS2101. I want to take CS4248, CS3219, CS4218, CS4243, CS3263, CS3230 and CS2106, at most 3 modules per semester. Semester 6 is my ATAP semester and I do not want any other module in it. I prefer CS3230 and CS4243 early, and CS2106 late.
JSON: {"query": "plan", "current_sem": 5, "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "CS2100", "MA1521", "MA1522", "ST2334", "CS2109S", "CS2103T", "CS2101"], "must_take": ["CS4248", "CS3219", "CS4218", "CS4243", "CS3263", "CS3230", "CS2106"], "mc_max": 12, "sem_caps": {"6": 1}, "atap_sems": [6], "early": ["CS3230", "CS4243"], "late": ["CS2106"]}

Request: I am in semester 4 with CS1101S, CS1231S, CS2030S, CS2040S, MA1521, MA1522, ST2334 and CS2109S completed. I still need CS3263. I do not want any 8am classes, and I might fail CS3263, so keep that in mind.
JSON: {"query": "plan", "current_sem": 4, "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334", "CS2109S"], "must_take": ["CS3263"], "unsupported": ["no 8am classes", "might fail CS3263"]}
```

## 3. Field-by-field reference

| Field | Question | Required? | Type | Source in the request | Left out when |
|---|---|---|---|---|---|
| `query` | both | always | `"eligible"` / `"plan"` | what the student asks | never |
| `completed` | both | yes (else `MISSING_INFO`) | list of codes | "I have finished ..." | the student does not say what they completed |
| `current_sem` | both | Q2: yes, Q1: no | integer 1 to 8 | "I am in Y2S1", "semester 5" | not stated and not derivable |
| `target` | Q1 | yes | one code | "Can I take X" | never for Q1 |
| `must_take` | Q2 | yes | list of codes | "I need to take ..." | the student does not say which courses |
| `programme` | both | no | string | "I am a ... student" | the student does not state a programme in words (course codes do not count) |
| `unsupported` | both | no | list of strings | any wish no field can hold | there is no such wish |
| `mc_max` | Q2 | no | integer | "at most N MC / modules per semester" | no limit stated (the solver uses 20) |
| `mc_min` | Q2 | no | integer | "at least N MC each semester" | not stated |
| `sem_caps` | Q2 | no | object (string key to integer) | exchange, NOC, a lighter semester | not stated |
| `atap_sems` | Q2 | no | list of integers | "ATAP in semester 6" | ATAP not mentioned |
| `objective` | Q2 | no | enum | "graduate as early as possible" | no such wish |
| `light_sems` | Q2 | no | list of integers or `"last"` | "light last semester" | no such wish |
| `balance_load` | Q2 | no | boolean | "spread evenly" | no such wish |
| `early`, `late` | Q2 | no | list of codes | "X as early as possible" | no such wish |
| `rules` | Q2 | no | list of rule objects | "X before Y", "Z in semester 5" | no such wish |

A field that belongs to the other question is ignored with a warning, and an unknown field is an error. The solver's
`MISSING_INFO` answer is the intended way to find out what the student still has to say; a spec that leaves out a field
the student did not state is correct, and a spec that invents a value is wrong.

## 4. Conversion rules: student wording to fields

| The student says | Write |
|---|---|
| "Y2S2", "year 2 semester 2", "sem 4" | `"current_sem": 4` (semester = (year - 1) x 2 + semester) |
| "I am in Y2S1. Can I take X next semester?" | Q1, `"current_sem": 4` |
| "I am in semester 5 now" (planning) | `"current_sem": 5` |
| "I have not completed anything" | `"completed": []` |
| (nothing about completed courses) | leave `completed` out |
| "at most 3 modules per semester" | `"mc_max": 12` (4 MC per module) |
| "at most 20 MC per semester" | `"mc_max": 20` |
| "at least 8 MC in every semester I study" | `"mc_min": 8` |
| "semester 6 is my exchange semester", "NOC in semester 6" | `"sem_caps": {"6": 0}` |
| "at most 8 MC in semester 7" | `"sem_caps": {"7": 8}` |
| "I will do ATAP in semester 6" | `"atap_sems": [6]` |
| "I will do ATAP in semester 6 and take no other module then" | `"atap_sems": [6], "sem_caps": {"6": 1}` |
| "I will do ATAP, not sure when" (current_sem 5) | `"atap_sems": [5, 6, 7, 8]` |
| "graduate as early as possible", "fewest semesters" | `"objective": "earliest_graduation"` |
| "fewest total credits" | `"objective": "min_total_mc"` |
| "a light last semester" | `"light_sems": ["last"]` |
| "semester 6 should be light" | `"light_sems": [6]` |
| "spread the workload evenly" | `"balance_load": true` |
| "I want X as early as possible" | `"early": ["X"]` |
| "I want X as late as possible" | `"late": ["X"]` |
| "X must be before Y" | rule `before`, `a` = X, `b` = Y, `strength` = `"must"` |
| "I would rather take X after Y" | rule `before`, `a` = Y, `b` = X, `strength` = `"prefer"` |
| "X and Y must not be in the same semester" | rule `apart`, `"must"` |
| "I would like X and Y together" | rule `same_sem`, `"prefer"` |
| "X has to be in semester 5" | rule `in_sem`, `"sem": 5`, `"must"` |
| "if possible, X in semester 5" | rule `in_sem`, `"sem": 5`, `"prefer"` |
| "I am a Business Analytics student" | `"programme": "Business Analytics"` |
| "I am a CS student" / "BComp (CS) Hons" | `"programme": "BComp CS Hons"` |
| "no 8am classes", "I might fail X", "waive X" | an entry in `"unsupported"` |

Notes on the conversions:

- **A strong word makes a rule hard.** "Must", "have to", "need to" and "definitely" give `"strength": "must"`: the
  solver then answers `NO_PLAN` if the rule cannot hold. Everything softer is `"prefer"`.
- **`early` and `late` are always soft.** They cannot be made hard. If the student insists ("X has to be early"), use
  `early` and, if a particular semester is meant, an `in_sem` rule.
- **`[]` and "left out" mean different things.** `"completed": []` tells the solver the student has completed nothing,
  and it plans every prerequisite from scratch. Writing `[]` when the student simply did not say gives a confident,
  wrong plan with no error, because the solver cannot tell the two cases apart. When the student does not say, leave the
  field out and the solver asks.
- **Modules to MC.** Most courses in the data are 4 MC, so "3 modules" is written as 12 MC. This is an approximation; use
  the same rule for the gold specs so both sides agree.
- **Courses outside `must_take`.** A course that appears only in `early`, `late` or a `prefer` rule, and not in
  `must_take`, is not planned because of it: a preference about a course that is not in the plan counts as not met.
  A `must` rule does bring its courses into the plan.
- **ATAP.** Write `atap_sems` only when the student says ATAP. Never write the course code `CP3880` yourself.
- **Programme is never inferred.** A request that lists CS courses but does not say "I am a CS student" gets no
  `programme` field. Writing `"BComp CS Hons"` there is an invented field: the solver accepts it, so a student from
  another programme who has taken CS modules would pass the scope check without ever having said they are in Computer
  Science.
- **Programme wording.** Copy the student's words when the programme is not Computer Science Hons, and also when the
  student names a second major, a minor or a double degree. The solver answers `OUT_OF_SCOPE` for any value other than
  the Computer Science Hons spellings. Never put a second major or minor in a field of its own: unknown fields are an
  error.

## 5. Worked examples

Each example shows a request, the spec an LLM following the prompt should return, and what the solver replies to that
spec.

### 5.1 Q1: can I take a course

> I have finished CS1101S, CS1231S, CS2030S, CS2040S, MA1521, MA1522 and ST2334. Can I take CS3263 in Y2S1?

```json
{
  "query": "eligible",
  "target": "CS3263",
  "current_sem": 3,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"]
}
```

Solver reply to this spec: `NOT_ELIGIBLE`

> I am in Y2S1 and have done CS1101S, CS1231S, CS2030S and CS2040S. Can I take CS3230 next semester?

```json
{
  "query": "eligible",
  "target": "CS3230",
  "current_sem": 4,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S"]
}
```

Solver reply to this spec: `ELIGIBLE`

> I have completed CS1101S, CS1231S, CS2030S, CS2040S, MA1521, MA1522 and ST2334. Am I allowed to take CS2109S?

```json
{
  "query": "eligible",
  "target": "CS2109S",
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"]
}
```

Solver reply to this spec: `ELIGIBLE`

The next one leaves out `completed` and `current_sem`, because the student stated neither. The solver replies by asking
for `completed`; `current_sem` is optional for Q1, so it does not ask for it.

> Can I take CS3263 next semester?

```json
{
  "query": "eligible",
  "target": "CS3263"
}
```

Solver reply to this spec: `MISSING_INFO` (missing: completed)

### 5.2 Q2: plan my semesters

The main example, with caps, an objective, preferences and rules together:

> I am in Y2S1. I have completed CS1101S, CS1231S, CS2030S, CS2040S, MA1521 and MA1522. I still have to take ST2334, CS2109S, CS3263, CS4248, CS3230, CS2100 and CS2106. I can take at most 8 MC per semester, and semester 6 is my exchange semester. I want to graduate as early as possible, with a light last semester. I would like to take CS2109S as early as possible. CS2100 must come before CS2106. If possible, I would like CS3230 in semester 5.

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

Solver reply to this spec: `PLAN`

ATAP, with a limit in modules and no other module in the ATAP semester:

> I am in semester 5 now. I have completed CS1101S, CS1231S, CS2030S, CS2040S, CS2100, MA1521, MA1522, ST2334, CS2109S, CS2103T and CS2101. I want to take CS4248, CS3219, CS4218, CS4243, CS3263, CS3230 and CS2106, at most 3 modules per semester. Semester 6 is my ATAP semester and I do not want any other module in it. I prefer CS3230 and CS4243 early, and CS2106 late.

```json
{
  "query": "plan",
  "current_sem": 5,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "CS2100", "MA1521", "MA1522", "ST2334", "CS2109S", "CS2103T", "CS2101"],
  "must_take": ["CS4248", "CS3219", "CS4218", "CS4243", "CS3263", "CS3230", "CS2106"],
  "mc_max": 12,
  "sem_caps": {"6": 1},
  "atap_sems": [6],
  "early": ["CS3230", "CS4243"],
  "late": ["CS2106"]
}
```

Solver reply to this spec: `PLAN`

ATAP with no semester decided:

> I am in semester 5 and have completed CS1101S, CS1231S, CS2030S, CS2040S, CS2100, MA1521, MA1522, ST2334, CS2109S, CS2103T and CS2101. I plan to do ATAP at some point, but I have not decided when. I still have to take CS3263 and CS4248.

```json
{
  "query": "plan",
  "current_sem": 5,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "CS2100", "MA1521", "MA1522", "ST2334", "CS2109S", "CS2103T", "CS2101"],
  "must_take": ["CS3263", "CS4248"],
  "atap_sems": [5, 6, 7, 8]
}
```

Solver reply to this spec: `PLAN`

Minimum credits, a hard in-semester rule and a minimum load:

> I am in semester 3 and have completed CS1101S, CS1231S, CS2030S, CS2040S, MA1521, MA1522 and ST2334. I must take CS3230 and CS2100. I want the fewest total MC. CS3230 has to be in semester 5, and I want at least 8 MC in every semester I take courses.

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334"],
  "must_take": ["CS3230", "CS2100"],
  "objective": "min_total_mc",
  "mc_min": 8,
  "rules": [
    {"type": "in_sem", "course": "CS3230", "sem": 5, "strength": "must"}
  ]
}
```

Solver reply to this spec: `PLAN`

A balanced workload and a soft "apart" rule, with a limit given in modules:

> I am in Y2S2. Completed: CS1101S, CS1231S, CS2030S, CS2040S, MA1521, MA1522, ST2334 and CS2109S. I need CS3263, CS3230 and CS4248 and I want my workload spread evenly. I would rather not take CS3230 and CS4248 in the same semester. I can take at most 4 modules a semester.

```json
{
  "query": "plan",
  "current_sem": 4,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334", "CS2109S"],
  "must_take": ["CS3263", "CS3230", "CS4248"],
  "mc_max": 16,
  "balance_load": true,
  "rules": [
    {"type": "apart", "a": "CS3230", "b": "CS4248", "strength": "prefer"}
  ]
}
```

Solver reply to this spec: `PLAN`

### 5.3 Missing information

The student gives only the courses to take. The spec leaves out `completed` and `current_sem`, and the solver asks for
both:

> Please plan my remaining semesters. I need to take CS3263 and CS4248.

```json
{
  "query": "plan",
  "must_take": ["CS3263", "CS4248"]
}
```

Solver reply to this spec: `MISSING_INFO` (missing: completed, current_sem)

The student says they have completed nothing. This is a real answer and `[]` is correct:

> I have not completed any module yet and I am in Y1S1. Plan my semesters so that I take CS1101S and CS1231S.

```json
{
  "query": "plan",
  "current_sem": 1,
  "completed": [],
  "must_take": ["CS1101S", "CS1231S"]
}
```

Solver reply to this spec: `PLAN`

### 5.4 Wishes the schema cannot express

Both wishes go into `unsupported`. The solver still plans, and returns them as `not_applied` so that the harness can
see they were not applied:

> I am in semester 4 with CS1101S, CS1231S, CS2030S, CS2040S, MA1521, MA1522, ST2334 and CS2109S completed. I still need CS3263. I do not want any 8am classes, and I might fail CS3263, so keep that in mind.

```json
{
  "query": "plan",
  "current_sem": 4,
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334", "CS2109S"],
  "must_take": ["CS3263"],
  "unsupported": ["no 8am classes", "might fail CS3263"]
}
```

Solver reply to this spec: `PLAN`

### 5.5 Out of scope

A different programme, and a second major, are both written as the student's own words in `programme`:

> I am a Business Analytics student in Y2S1. I have completed CS1101S, CS1231S, CS2030S, CS2040S, MA1521 and MA1522, and I need CS3230. Plan my semesters.

```json
{
  "query": "plan",
  "current_sem": 3,
  "programme": "Business Analytics",
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522"],
  "must_take": ["CS3230"]
}
```

Solver reply to this spec: `OUT_OF_SCOPE`

> I am a BComp Computer Science Honours student with a second major in Mathematics, in Y2S1, and have completed CS1101S, CS1231S, CS2030S, CS2040S, MA1521 and MA1522. I need CS3230.

```json
{
  "query": "plan",
  "current_sem": 3,
  "programme": "BComp CS Hons with second major in Mathematics",
  "completed": ["CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522"],
  "must_take": ["CS3230"]
}
```

Solver reply to this spec: `OUT_OF_SCOPE`

## 6. Common mistakes and what the solver does with them

| Mistake | What happens |
|---|---|
| text around the JSON, or a markdown fence | `INVALID_SPEC`: not valid JSON |
| an empty `target`, or a mandatory field left out | `MISSING_INFO` for that field |
| `[]` for `completed` when the student did not say | no error; the plan is wrong because the solver thinks nothing is completed |
| a number written as a string | `INVALID_SPEC` |
| an invented field | `INVALID_SPEC` |
| an invented key inside a rule | `INVALID_SPEC` |
| a rule type or strength that does not exist | `INVALID_SPEC` |
| a boolean written as text | `INVALID_SPEC` |
| a plan-only field in a Q1 spec | the field is ignored and the answer carries a warning |
| `sem_caps` of 0 for the ATAP semester | `NO_PLAN`: ATAP cannot be placed in a blocked semester |

Each of these, with the solver's reply:

**Fenced JSON.** The reply to a spec wrapped in a markdown fence: `{"status": "INVALID_SPEC", "errors": ["not valid JSON: Expecting value: line 1 column 1 (char 0)"]}`

**A mandatory string left empty:**

```json
{
  "query": "eligible",
  "target": "",
  "completed": []
}
```

Solver reply (shortened):

```json
{
  "status": "MISSING_INFO",
  "missing": ["target"]
}
```

**A number written as a string:**

```json
{
  "query": "plan",
  "current_sem": "3",
  "completed": [],
  "must_take": []
}
```

Solver reply (shortened):

```json
{
  "status": "INVALID_SPEC",
  "errors": ["current_sem must be an integer, got '3'"]
}
```

**An invented field (a second major written as a field of its own):**

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": [],
  "must_take": [],
  "second_major": "Mathematics"
}
```

Solver reply (shortened):

```json
{
  "status": "INVALID_SPEC",
  "errors": ["unknown field 'second_major'"]
}
```

**An invented key inside a rule:**

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": [],
  "must_take": ["CS3230"],
  "rules": [
    {"type": "in_sem", "course": "CS3230", "sem": 5, "strength": "prefer", "reason": "friends"}
  ]
}
```

Solver reply (shortened):

```json
{
  "status": "INVALID_SPEC",
  "errors": ["rules[0] has unknown key 'reason'"]
}
```

**A rule type that does not exist:**

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": [],
  "must_take": ["CS3230", "CS2100"],
  "rules": [
    {"type": "after", "a": "CS3230", "b": "CS2100", "strength": "prefer"}
  ]
}
```

Solver reply (shortened):

```json
{
  "status": "INVALID_SPEC",
  "errors": ["rules[0].type must be one of ['before', 'in_sem', 'apart', 'same_sem'], got 'after'"]
}
```

**A strength that does not exist:**

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": [],
  "must_take": ["CS3230"],
  "rules": [
    {"type": "in_sem", "course": "CS3230", "sem": 5, "strength": "hard"}
  ]
}
```

Solver reply (shortened):

```json
{
  "status": "INVALID_SPEC",
  "errors": ["rules[0].strength must be one of ['must', 'prefer'], got 'hard'"]
}
```

**An objective that does not exist:**

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": [],
  "must_take": [],
  "objective": "fastest"
}
```

Solver reply (shortened):

```json
{
  "status": "INVALID_SPEC",
  "errors": ["objective must be one of ['earliest_graduation', 'min_total_mc', 'none'], got 'fastest'"]
}
```

**A boolean written as text:**

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": [],
  "must_take": [],
  "balance_load": "yes"
}
```

Solver reply (shortened):

```json
{
  "status": "INVALID_SPEC",
  "errors": ["balance_load must be true or false"]
}
```

**A plan-only field in a Q1 spec (the answer is computed, and the field is reported in `warnings`):**

```json
{
  "query": "eligible",
  "target": "CS3263",
  "completed": [],
  "must_take": ["CS3263"]
}
```

Solver reply (shortened):

```json
{
  "status": "NOT_ELIGIBLE",
  "reasons": ["missing prerequisite: (CS2109S or CS2109HS) and (CS2040 or CS2040S or CS2040C or CS2040DE or CS2040HS) and (MA2001 or MA1522 or MA1513 or..."],
  "warnings": ["field 'must_take' belongs to query 'plan', not 'eligible', and was ignored"]
}
```

**ATAP in a blocked semester:**

```json
{
  "query": "plan",
  "current_sem": 5,
  "completed": [],
  "must_take": ["CS2106"],
  "atap_sems": [6],
  "sem_caps": {"6": 0}
}
```

Solver reply (shortened):

```json
{
  "status": "NO_PLAN",
  "reasons": ["CP3880 cannot be placed in any remaining semester (offered in terms [1, 2, 3, 4]; semesters left [5, 7, 8])"]
}
```

**`[]` for `completed` when the student never said (no error, but the solver plans every prerequisite from scratch, so the
plan is wrong for a student who has completed courses):**

```json
{
  "query": "plan",
  "current_sem": 3,
  "completed": [],
  "must_take": ["CS3263"]
}
```

Solver reply (shortened):

```json
{
  "status": "PLAN",
  "added_prerequisites": ["CS1101S", "CS2040DE", "CS2109S", "MA1521", "MA1522", "MA2116"],
  "last_semester": 6,
  "plan": {
    "3": ["CS1101S"],
    "4": ["CS2040DE", "MA1521"],
    "5": ["CS2109S", "MA1522", "MA2116"],
    "6": ["CS3263"]
  }
}
```

## 7. Scoring a translation

Compare the translated spec with the gold spec, after cleaning both, and compare the two solver answers.

| Check | How |
|---|---|
| Valid JSON | `run_text` does not return `INVALID_SPEC` with `not valid JSON` |
| Valid spec | the status is not `INVALID_SPEC` |
| Right `query` | equals the gold `query` |
| Exact field match | each field equals the gold value, per field |
| Missing-information behaviour | the translated spec leaves out exactly the fields the gold spec leaves out; a false `MISSING_INFO` means the LLM dropped a stated field, and an invented value means it guessed |
| Silent drops | the gold `unsupported` list is not empty and the translated one is |
| Same answer | the solver's status, `last_semester` and number of preferences met under the translated spec equal those under the gold spec |

Failure types worth reporting, which map to the failure taxonomy in the project plan:

1. not valid JSON;
2. `INVALID_SPEC`, by error type (unknown field, wrong type, bad enum, rule shape);
3. `MISSING_INFO` that should not have happened (a stated field was dropped);
4. `[]` or a value invented for a field the student never stated;
5. a wrong value (semester numbering, MC conversion, `must` against `prefer`, a rule with `a` and `b` swapped);
6. a wish dropped instead of listed in `unsupported`;
7. a plan-only field in a Q1 spec, or the reverse (the `warnings` field).

The solver's `warnings`, `not_applied` and `MISSING_INFO` answers exist so that these failures are visible and
countable instead of silent.
