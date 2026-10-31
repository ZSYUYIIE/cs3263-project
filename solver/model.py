from __future__ import annotations

from ortools.sat.python import cp_model

from m1_data.catalog import satisfied

LAST_SEM = 8
ATAP_CODE = "CP3880"
ATAP_OTHER_CAP = 8


def term_of(semester: int) -> int:
    return 1 if semester % 2 == 1 else 2


def unmet_codes(node, done: set, found: set) -> None:
    if node is None or node is True or node is False:
        return
    if satisfied(node, done):
        return
    if node["op"] == "course":
        found.add(node["code"])
        return
    for arg in node["args"]:
        unmet_codes(arg, done, found)


def rule_courses(rule: dict) -> list[str]:
    if rule["type"] == "in_sem":
        return [rule["course"]]
    return [rule["a"], rule["b"]]


class PlanModel:
    def __init__(self, spec: dict, catalog, explain: bool = False):
        self.spec = spec
        self.catalog = catalog
        self.explain = explain
        self.guards: dict[tuple, cp_model.IntVar] = {}
        self.current = spec["current_sem"]
        self.done = set(spec["completed"])
        self.model = cp_model.CpModel()
        self.reasons: list[str] = []
        self.notes: list[str] = []
        self.supports: dict[str, list[tuple[str, bool]]] = {}
        if explain:
            self.sems = list(range(self.current, LAST_SEM + 1))
        else:
            self.sems = [s for s in range(self.current, LAST_SEM + 1) if self.cap(s) > 0]
        self.atap_allowed = set(spec.get("atap_sems", self.sems))
        self.required = self.find_required()
        self.candidates = self.find_candidates()
        self.check_reachable()
        if not self.reasons:
            self.build()

    def check_reachable(self) -> None:
        for code in self.required:
            reachable, why = self.catalog.reachable(code, self.done)
            if not reachable:
                self.reasons.append(why)

    def guard(self, key: tuple):
        if key not in self.guards:
            self.guards[key] = self.model.NewBoolVar(f"group_{len(self.guards)}")
        return self.guards[key]

    def enforce(self, constraint, key: tuple | None = None, extra=()):
        literals = list(extra)
        if self.explain and key is not None:
            literals.append(self.guard(key))
        if literals:
            constraint.OnlyEnforceIf(literals)
        return constraint

    def cap(self, semester: int) -> int:
        return self.spec["sem_caps"].get(semester, self.spec["mc_max"])

    def plannable(self, code: str) -> bool:
        record = self.catalog.courses.get(code)
        return bool(record and record["exists_in_ay"] and record["available"])

    def find_required(self) -> list[str]:
        required: list[str] = []

        def add(code: str) -> None:
            if code in self.done:
                return
            if code not in required:
                required.append(code)

        for code in self.spec["must_take"]:
            if code in self.done:
                self.notes.append(f"{code} is already completed")
            add(code)
        for rule in self.spec["rules"]:
            if rule["strength"] == "must":
                for code in rule_courses(rule):
                    add(code)
        if "atap_sems" in self.spec:
            add(ATAP_CODE)
        return required

    def find_candidates(self) -> list[str]:
        candidates: list[str] = []
        seen: set[str] = set()
        queue = list(self.required)
        while queue:
            code = queue.pop(0)
            if code in seen or code in self.done:
                continue
            seen.add(code)
            if not self.plannable(code) or self.catalog.blocked_by(code, self.done):
                continue
            candidates.append(code)
            record = self.catalog[code]
            for tree, inclusive in ((record["prereq"]["logic"], False), (record["coreq"]["logic"], True)):
                found: set[str] = set()
                unmet_codes(tree, self.done, found)
                for needed in sorted(found):
                    self.supports.setdefault(needed, []).append((code, inclusive))
                    queue.append(needed)
        return candidates

    def build(self) -> None:
        m = self.model
        self.true = m.NewBoolVar("true")
        m.Add(self.true == 1)
        self.false = self.true.Not()
        self.mc = {code: int(self.catalog[code]["mc"]) for code in self.candidates}

        self.var: dict[tuple[str, int], cp_model.IntVar] = {}
        for code in self.candidates:
            offered = self.catalog[code]["offered"]
            for s in self.sems:
                off_term = term_of(s) not in offered
                off_atap = code == ATAP_CODE and s not in self.atap_allowed
                if (off_term or off_atap) and not self.explain:
                    continue
                var = m.NewBoolVar(f"{code}@{s}")
                self.var[(code, s)] = var
                if off_term:
                    self.enforce(m.Add(var == 0), ("offering",))
                if off_atap:
                    self.enforce(m.Add(var == 0), ("atap",))

        self.planned: dict[str, cp_model.IntVar] = {}
        for code in self.candidates:
            slots = [self.var[(code, s)] for s in self.sems if (code, s) in self.var]
            if code in self.required and not slots:
                offered = self.catalog[code]["offered"]
                self.reasons.append(
                    f"{code} cannot be placed in any remaining semester "
                    f"(offered in terms {offered or 'never'}; semesters left {self.sems})"
                )
            flag = m.NewBoolVar(f"plan_{code}")
            m.Add(sum(slots) == flag)
            self.planned[code] = flag
            if code in self.required:
                m.Add(flag == 1)
        if self.reasons:
            return

        self.before_cache: dict[tuple, cp_model.IntVar] = {}
        for (code, s), v in self.var.items():
            record = self.catalog[code]
            prereq, coreq = record["prereq"]["logic"], record["coreq"]["logic"]
            cond = self.prerequisite_condition(code, v, prereq, coreq)
            self.require(prereq, s, cond, False)
            self.require(coreq, s, cond, True)

        self.add_support()
        self.add_exclusions()
        self.add_loads()
        self.add_last()
        self.add_atap()
        self.add_must_rules()

    def prerequisite_condition(self, code: str, v, prereq, coreq):
        trivial = all(tree is None or tree is True for tree in (prereq, coreq))
        if not self.explain or trivial:
            return v
        cond = self.model.NewBoolVar("cond")
        self.model.AddBoolOr([v.Not(), self.guard(("prereq", code)).Not(), cond])
        return cond

    def sem_expr(self, code: str):
        return sum(s * self.var[(code, s)] for s in self.sems if (code, s) in self.var)

    def done_by(self, code: str, semester: int, inclusive: bool):
        if code in self.done:
            return self.true
        if code not in self.planned:
            return self.false
        key = (code, semester, inclusive)
        if key in self.before_cache:
            return self.before_cache[key]
        end = semester + 1 if inclusive else semester
        slots = [self.var[(code, t)] for t in self.sems if t < end and (code, t) in self.var]
        if not slots:
            self.before_cache[key] = self.false
            return self.false
        flag = self.model.NewBoolVar(f"done_{code}_{semester}_{inclusive}")
        self.model.Add(sum(slots) == flag)
        self.before_cache[key] = flag
        return flag

    def require(self, node, semester: int, cond, inclusive: bool) -> None:
        m = self.model
        if node is None or node is True:
            return
        if node is False:
            m.AddBoolOr([cond.Not()])
            return
        op = node["op"]
        if op == "course":
            m.AddImplication(cond, self.done_by(node["code"], semester, inclusive))
        elif op == "and":
            for arg in node["args"]:
                self.require(arg, semester, cond, inclusive)
        else:
            lits = []
            for arg in node["args"]:
                lit = m.NewBoolVar("opt")
                self.require(arg, semester, lit, inclusive)
                lits.append(lit)
            need = 1 if op == "or" else node["n"]
            m.Add(sum(lits) >= need).OnlyEnforceIf(cond)

    def add_support(self) -> None:
        m = self.model
        for (code, s), v in self.var.items():
            if code in self.required:
                continue
            users = []
            for dependent, inclusive in self.supports.get(code, []):
                for t in self.sems:
                    if (dependent, t) in self.var and (t >= s if inclusive else t > s):
                        users.append(self.var[(dependent, t)])
            if users:
                m.AddBoolOr(users).OnlyEnforceIf(v)
            else:
                m.Add(v == 0)

    def add_exclusions(self) -> None:
        pairs: set[frozenset] = set()
        for code in self.candidates:
            record = self.catalog[code]["preclusion"]
            for other in record["mutually_exclusive_with"]:
                if other in self.planned and other != code:
                    pairs.add(frozenset((code, other)))
            for other in record["courses"]:
                if other in self.planned and other != code:
                    blocked_if = record["blocked_if"]
                    if blocked_if is not None and satisfied(blocked_if, {other}):
                        pairs.add(frozenset((code, other)))
        for pair in sorted(tuple(sorted(p)) for p in pairs):
            a, b = pair
            literals = [self.planned[a].Not(), self.planned[b].Not()]
            if self.explain:
                literals.append(self.guard(("preclusion",)).Not())
            self.model.AddBoolOr(literals)

    def add_loads(self) -> None:
        m = self.model
        self.other_var: dict[int, cp_model.IntVar] = {}
        self.load_var: dict[int, cp_model.IntVar] = {}
        mc_min = self.spec.get("mc_min")
        for s in self.sems:
            cap = self.cap(s)
            courses = [c for c in self.candidates if (c, s) in self.var]
            load = sum(self.mc[c] * self.var[(c, s)] for c in courses)
            other = sum(self.mc[c] * self.var[(c, s)] for c in courses if c != ATAP_CODE)
            self.load_var[s] = m.NewIntVar(0, 200, f"load{s}")
            self.other_var[s] = m.NewIntVar(0, 200, f"other{s}")
            m.Add(self.load_var[s] == load)
            m.Add(self.other_var[s] == other)
            atap = self.var.get((ATAP_CODE, s))
            if atap is not None:
                self.enforce(m.Add(self.load_var[s] <= cap), ("caps",), [atap.Not()])
                self.enforce(m.Add(self.other_var[s] <= cap), ("caps",), [atap])
                self.enforce(m.Add(self.other_var[s] <= ATAP_OTHER_CAP), ("atap",), [atap])
            else:
                self.enforce(m.Add(self.load_var[s] <= cap), ("caps",))
            if mc_min is not None and courses:
                used = m.NewBoolVar(f"used{s}")
                for c in courses:
                    m.AddImplication(self.var[(c, s)], used)
                self.enforce(m.Add(self.load_var[s] >= mc_min), ("mc_min",), [used])

    def add_last(self) -> None:
        m = self.model
        self.last = m.NewIntVar(self.current - 1, LAST_SEM, "last")
        for (code, s), v in self.var.items():
            m.Add(self.last >= s).OnlyEnforceIf(v)
        self.is_last: dict[int, cp_model.IntVar] = {}
        for value in range(self.current - 1, LAST_SEM + 1):
            flag = m.NewBoolVar(f"last_is_{value}")
            m.Add(self.last == value).OnlyEnforceIf(flag)
            m.Add(self.last != value).OnlyEnforceIf(flag.Not())
            self.is_last[value] = flag
            if value >= self.current:
                slots = [self.var[(c, value)] for c in self.candidates if (c, value) in self.var]
                if slots:
                    m.AddBoolOr(slots).OnlyEnforceIf(flag)
                else:
                    m.Add(flag == 0)
            else:
                for v in self.var.values():
                    m.AddImplication(flag, v.Not())
        m.AddExactlyOne(list(self.is_last.values()))

    def add_atap(self) -> None:
        if ATAP_CODE not in self.planned:
            return
        for s in self.sems:
            atap = self.var.get((ATAP_CODE, s))
            if atap is None:
                continue
            later = [self.var[(c, t)] for c in self.candidates if c != ATAP_CODE
                     for t in self.sems if t > s and (c, t) in self.var]
            if later:
                self.enforce(self.model.AddBoolOr(later), ("atap",), [atap])
            else:
                self.enforce(self.model.Add(atap == 0), ("atap",))

    def add_must_rules(self) -> None:
        m = self.model
        for index, rule in enumerate(self.spec["rules"]):
            if rule["strength"] != "must":
                continue
            key = ("rule", index)
            kind = rule["type"]
            if kind == "in_sem":
                course, sem = rule["course"], rule["sem"]
                if course in self.done:
                    self.reasons.append(f"{course} is already completed, so it cannot be placed in semester {sem}")
                elif (course, sem) not in self.var:
                    self.reasons.append(f"{course} cannot be placed in semester {sem}")
                else:
                    self.enforce(m.Add(self.var[(course, sem)] == 1), key)
                continue
            a, b = rule["a"], rule["b"]
            if kind == "before":
                if b in self.done and a not in self.done:
                    self.reasons.append(f"{a} cannot be before {b}: {b} is already completed")
                elif a not in self.done and b not in self.done:
                    self.enforce(m.Add(self.sem_expr(a) + 1 <= self.sem_expr(b)), key)
            elif kind == "apart":
                if a not in self.done and b not in self.done:
                    self.enforce(m.Add(self.sem_expr(a) != self.sem_expr(b)), key)
            elif kind == "same_sem":
                if (a in self.done) != (b in self.done):
                    self.reasons.append(f"{a} and {b} cannot be in the same semester: one is already completed")
                elif a not in self.done:
                    self.enforce(m.Add(self.sem_expr(a) == self.sem_expr(b)), key)
