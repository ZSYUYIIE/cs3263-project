from __future__ import annotations

import time

from m1_data.catalog import Catalog, satisfied

from solver import q1
from solver.run import prepare

LAST_SEM = 8
ATAP_CODE = "CP3880"
ATAP_OTHER_CAP = 8

VARIANTS = {
    "plain": {"mrv": False, "forward": False, "mac": False},
    "mrv": {"mrv": True, "forward": False, "mac": False},
    "fc": {"mrv": True, "forward": True, "mac": False},
    "mac": {"mrv": True, "forward": True, "mac": True},
}

GENERIC_REASON = ("no plan satisfies all the rules together (prerequisite order, offering terms, "
                  "MC caps, exclusions and your must-rules conflict)")


class TimeLimit(Exception):
    pass


class Found(Exception):
    pass


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


def tree_leaves(node, found: set) -> None:
    if node is None or node is True or node is False:
        return
    if node["op"] == "course":
        found.add(node["code"])
        return
    for arg in node["args"]:
        tree_leaves(arg, found)


def rule_courses(rule: dict) -> list[str]:
    if rule["type"] == "in_sem":
        return [rule["course"]]
    return [rule["a"], rule["b"]]


class Stage:
    def __init__(self, sense: str, leaf, bound=None, limit=None):
        self.sense = sense
        self.leaf = leaf
        self.bound = bound
        self.limit = limit
        self.best = None
        self.best_assign = None


class Pref:
    def __init__(self, type_: str, label: str, const=None, **data):
        self.kind = type_
        self.label = label
        self.const = const
        self.data = data
        self.target = None


class Search:
    def __init__(self, spec: dict, catalog, variant: str, deadline: float):
        options = VARIANTS[variant]
        self.use_mrv = options["mrv"]
        self.use_forward = options["forward"]
        self.use_mac = options["mac"]
        self.spec = spec
        self.catalog = catalog
        self.deadline = deadline
        self.nodes = 0
        self.backtracks = 0
        self.checks = 0
        self.current = spec["current_sem"]
        self.done = set(spec["completed"])
        self.objective = spec["objective"]
        self.reasons: list[str] = []
        self.notes: list[str] = []
        self.supports: dict[str, list[tuple[str, bool]]] = {}
        self.sems = [s for s in range(self.current, LAST_SEM + 1) if self.cap(s) > 0]
        self.atap_allowed = set(spec.get("atap_sems", self.sems))
        self.required = self.find_required()
        self.candidates = self.find_candidates()
        self.check_reachable()
        if not self.reasons:
            self.build_domains()
        if not self.reasons:
            self.build_rules()
        if not self.reasons:
            self.build_structure()

    def cap(self, semester: int) -> int:
        return self.spec["sem_caps"].get(semester, self.spec["mc_max"])

    def plannable(self, code: str) -> bool:
        record = self.catalog.courses.get(code)
        return bool(record and record["exists_in_ay"] and record["available"])

    def find_required(self) -> list[str]:
        required: list[str] = []

        def add(code: str) -> None:
            if code not in self.done and code not in required:
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

    def check_reachable(self) -> None:
        for code in self.required:
            reachable, why = self.catalog.reachable(code, self.done)
            if not reachable:
                self.reasons.append(why)

    def build_domains(self) -> None:
        self.mc = {code: int(self.catalog[code]["mc"]) for code in self.candidates}
        self.initial: dict[str, tuple] = {}
        for code in self.candidates:
            offered = self.catalog[code]["offered"]
            values = [s for s in self.sems
                      if term_of(s) in offered and not (code == ATAP_CODE and s not in self.atap_allowed)]
            if code in self.required:
                if not values:
                    self.reasons.append(
                        f"{code} cannot be placed in any remaining semester "
                        f"(offered in terms {offered or 'never'}; semesters left {self.sems})"
                    )
                self.initial[code] = tuple(values)
            else:
                self.initial[code] = (0, *values)

    def build_rules(self) -> None:
        self.rules: list[tuple] = []
        for rule in self.spec["rules"]:
            if rule["strength"] != "must":
                continue
            kind = rule["type"]
            if kind == "in_sem":
                course, sem = rule["course"], rule["sem"]
                if course in self.done:
                    self.reasons.append(f"{course} is already completed, so it cannot be placed in semester {sem}")
                elif sem not in self.initial[course]:
                    self.reasons.append(f"{course} cannot be placed in semester {sem}")
                else:
                    self.initial[course] = (sem,)
                continue
            a, b = rule["a"], rule["b"]
            if kind == "before":
                if b in self.done and a not in self.done:
                    self.reasons.append(f"{a} cannot be before {b}: {b} is already completed")
                elif a not in self.done and b not in self.done:
                    self.rules.append((kind, a, b))
            elif kind == "apart":
                if a not in self.done and b not in self.done:
                    self.rules.append((kind, a, b))
            elif kind == "same_sem":
                if (a in self.done) != (b in self.done):
                    self.reasons.append(f"{a} and {b} cannot be in the same semester: one is already completed")
                elif a not in self.done:
                    self.rules.append((kind, a, b))

    def build_structure(self) -> None:
        self.extras = [c for c in self.candidates if c not in self.required]
        self.order = list(self.required) + self.extras
        self.index = {code: i for i, code in enumerate(self.order)}
        self.rules_of: dict[str, list[tuple]] = {}
        for rule in self.rules:
            for code in (rule[1], rule[2]):
                self.rules_of.setdefault(code, []).append(rule)

        pairs: set[frozenset] = set()
        for code in self.candidates:
            record = self.catalog[code]["preclusion"]
            for other in record["mutually_exclusive_with"]:
                if other in self.mc and other != code:
                    pairs.add(frozenset((code, other)))
            for other in record["courses"]:
                if other in self.mc and other != code:
                    blocked_if = record["blocked_if"]
                    if blocked_if is not None and satisfied(blocked_if, {other}):
                        pairs.add(frozenset((code, other)))
        self.excl: dict[str, list[str]] = {}
        for pair in sorted(tuple(sorted(p)) for p in pairs):
            a, b = pair
            self.excl.setdefault(a, []).append(b)
            self.excl.setdefault(b, []).append(a)
        for code in self.excl:
            self.excl[code].sort()

        self.trees = {c: (self.catalog[c]["prereq"]["logic"], self.catalog[c]["coreq"]["logic"])
                      for c in self.candidates}
        self.tree_codes: dict[str, set[str]] = {}
        self.in_trees: dict[str, list[str]] = {}
        for code in self.candidates:
            found: set[str] = set()
            for tree in self.trees[code]:
                tree_leaves(tree, found)
            found = {c for c in found if c in self.mc}
            self.tree_codes[code] = found
            for leaf in sorted(found):
                self.in_trees.setdefault(leaf, []).append(code)
        self.supported_by: dict[str, list[str]] = {}
        for extra in self.extras:
            for dependent, _ in self.supports.get(extra, ()):
                self.supported_by.setdefault(dependent, []).append(extra)

    def tick(self) -> None:
        if time.perf_counter() > self.deadline:
            raise TimeLimit()

    def values(self, code: str, assign: dict, dom: dict, use_dom: bool):
        if code in assign:
            return (assign[code],)
        return dom[code] if use_dom else self.initial[code]

    def node_possible(self, node, s: int, inclusive: bool, assign, dom, use_dom, without) -> bool:
        if node is None or node is True:
            return True
        if node is False:
            return False
        op = node["op"]
        if op == "course":
            code = node["code"]
            if code in self.done:
                return True
            if code not in self.mc or code == without:
                return False
            for t in self.values(code, assign, dom, use_dom):
                if t and (t < s or (inclusive and t == s)):
                    return True
            return False
        hits = sum(self.node_possible(arg, s, inclusive, assign, dom, use_dom, without) for arg in node["args"])
        need = len(node["args"]) if op == "and" else (1 if op == "or" else node["n"])
        return hits >= need

    def tree_possible(self, code: str, s: int, assign, dom, use_dom, without=None) -> bool:
        prereq, coreq = self.trees[code]
        return (self.node_possible(prereq, s, False, assign, dom, use_dom, without)
                and self.node_possible(coreq, s, True, assign, dom, use_dom, without))

    def tree_exact(self, code: str, s: int, assign: dict) -> bool:
        prereq, coreq = self.trees[code]
        before = self.done | {c for c, t in assign.items() if t and t < s}
        same = self.done | {c for c, t in assign.items() if t and t <= s}
        return satisfied(prereq, before) and satisfied(coreq, same)

    def all_assigned(self, code: str, assign: dict) -> bool:
        return all(c in assign for c in self.tree_codes[code])

    def loads_ok(self, code: str, v: int, assign: dict, adding: bool) -> bool:
        others = sum(self.mc[c] for c, t in assign.items() if t == v and c != ATAP_CODE)
        if adding and code != ATAP_CODE:
            others += self.mc[code]
        if others > self.cap(v):
            return False
        atap_here = code == ATAP_CODE or assign.get(ATAP_CODE) == v
        return not (atap_here and others > ATAP_OTHER_CAP)

    def rule_holds(self, rule: tuple, assign: dict) -> bool:
        kind, a, b = rule
        x, y = assign[a], assign[b]
        if kind == "before":
            return x + 1 <= y
        if kind == "apart":
            return x != y
        return x == y

    def rule_possible(self, rule: tuple, code: str, v: int, assign, dom, use_dom) -> bool:
        kind, a, b = rule
        other = b if code == a else a
        for t in self.values(other, assign, dom, use_dom):
            if not t:
                continue
            x, y = (v, t) if code == a else (t, v)
            if kind == "before" and x + 1 <= y:
                return True
            if kind == "apart" and x != y:
                return True
            if kind == "same_sem" and x == y:
                return True
        return False

    def support_exact(self, extra: str, assign: dict) -> bool:
        t = assign[extra]
        for dependent, inclusive in self.supports.get(extra, ()):
            u = assign.get(dependent)
            if u and (u > t or (inclusive and u == t)):
                return True
        return False

    def support_known(self, extra: str, assign: dict) -> bool:
        return all(d in assign for d, _ in self.supports.get(extra, ()))

    def consistent(self, assign: dict, code: str) -> bool:
        v = assign[code]
        if v:
            self.checks += 1
            if not self.loads_ok(code, v, assign, False):
                return False
            for other in self.excl.get(code, ()):
                self.checks += 1
                if assign.get(other):
                    return False
            for rule in self.rules_of.get(code, ()):
                if rule[1] in assign and rule[2] in assign:
                    self.checks += 1
                    if not self.rule_holds(rule, assign):
                        return False
        for d in [code, *self.in_trees.get(code, ())]:
            sem = assign.get(d)
            if sem and self.all_assigned(d, assign):
                self.checks += 1
                if not self.tree_exact(d, sem, assign):
                    return False
        for extra in [code, *self.supported_by.get(code, ())]:
            if extra in self.extras and assign.get(extra) and self.support_known(extra, assign):
                self.checks += 1
                if not self.support_exact(extra, assign):
                    return False
        return True

    def value_ok(self, code: str, v: int, assign, dom, use_dom) -> bool:
        if v == 0:
            for dependent, _ in self.supports.get(code, ()):
                t = assign.get(dependent)
                if t:
                    self.checks += 1
                    if not self.tree_possible(dependent, t, assign, dom, use_dom, without=code):
                        return False
            return True
        self.checks += 1
        if not self.tree_possible(code, v, assign, dom, use_dom):
            return False
        if not self.loads_ok(code, v, assign, True):
            return False
        for other in self.excl.get(code, ()):
            if assign.get(other):
                return False
        for rule in self.rules_of.get(code, ()):
            if not self.rule_possible(rule, code, v, assign, dom, use_dom):
                return False
        if code in self.extras:
            ok = False
            for dependent, inclusive in self.supports.get(code, ()):
                for t in self.values(dependent, assign, dom, use_dom):
                    if t and (t > v or (inclusive and t == v)):
                        ok = True
                        break
                if ok:
                    break
            if not ok:
                return False
        if code == ATAP_CODE:
            ok = False
            for other in self.order:
                if other == ATAP_CODE:
                    continue
                if any(t and t > v for t in self.values(other, assign, dom, use_dom)):
                    ok = True
                    break
            if not ok:
                return False
        return True

    def prune(self, assign: dict, dom: dict, use_dom: bool):
        changed = False
        for code in self.order:
            if code in assign:
                continue
            keep = tuple(v for v in dom[code] if self.value_ok(code, v, assign, dom, use_dom))
            if len(keep) != len(dom[code]):
                dom[code] = keep
                changed = True
                if not keep:
                    return None
        return changed

    def propagate(self, assign: dict, dom: dict) -> bool:
        if self.use_mac:
            while True:
                changed = self.prune(assign, dom, True)
                if changed is None:
                    return False
                if not changed:
                    return True
        return self.prune(assign, dom, False) is not None

    def valid(self, assign: dict) -> bool:
        self.checks += 1
        planned = {c: s for c, s in assign.items() if s}
        for code, s in planned.items():
            if not self.tree_exact(code, s, assign):
                return False
        for code in planned:
            for other in self.excl.get(code, ()):
                if other in planned:
                    return False
        mc_min = self.spec.get("mc_min")
        for s in self.sems:
            here = [c for c, t in planned.items() if t == s]
            others = sum(self.mc[c] for c in here if c != ATAP_CODE)
            if others > self.cap(s):
                return False
            if ATAP_CODE in here and others > ATAP_OTHER_CAP:
                return False
            if mc_min is not None and here and sum(self.mc[c] for c in here) < mc_min:
                return False
        if ATAP_CODE in planned:
            if not any(t > planned[ATAP_CODE] for c, t in planned.items() if c != ATAP_CODE):
                return False
        for rule in self.rules:
            if not self.rule_holds(rule, assign):
                return False
        for extra in self.extras:
            if planned.get(extra) and not self.support_exact(extra, assign):
                return False
        return True

    def last_of(self, planned: dict) -> int:
        return max(planned.values(), default=self.current - 1)

    def total_mc(self, planned: dict) -> int:
        return sum(self.mc[c] for c in planned)

    def extras_count(self, planned: dict) -> int:
        return sum(1 for c in planned if c not in self.required)

    def other_loads(self, planned: dict) -> dict:
        loads = {s: 0 for s in self.sems}
        for code, s in planned.items():
            if code != ATAP_CODE:
                loads[s] += self.mc[code]
        return loads

    def peak_of(self, planned: dict) -> int:
        return max(self.other_loads(planned).values())

    def last_bound(self, assign: dict, dom: dict) -> int:
        bound = self.current - 1
        for code in self.order:
            if code in assign:
                if assign[code] > bound:
                    bound = assign[code]
            elif code in self.required:
                nonzero = [t for t in dom[code] if t]
                if nonzero:
                    bound = max(bound, min(nonzero))
        return bound

    def mc_bound(self, assign: dict, dom: dict) -> int:
        total = sum(self.mc[c] for c, t in assign.items() if t)
        return total + sum(self.mc[c] for c in self.required if c not in assign)

    def extras_bound(self, assign: dict, dom: dict) -> int:
        return sum(1 for c in self.extras if assign.get(c))

    def peak_bound(self, assign: dict, dom: dict) -> int:
        planned = {c: t for c, t in assign.items() if t}
        return max(self.other_loads(planned).values())

    def sem_bound(self, code: str, low: bool):
        def bound(assign: dict, dom: dict) -> int:
            if code in assign:
                return assign[code]
            nonzero = [t for t in dom[code] if t]
            return min(nonzero) if low else max(nonzero)
        return bound

    def light_entries(self) -> list:
        return [e for e in self.spec["light_sems"] if e == "last" or e >= self.current]

    def bonus_terms(self) -> list:
        return [e for e in self.light_entries() if e == "last" or e in self.sems]

    def bonus_leaf(self, planned: dict) -> int:
        loads = self.other_loads(planned)
        last = self.last_of(planned)
        total = 0
        for entry in self.bonus_terms():
            total += loads.get(last, 0) if entry == "last" and last >= self.current else (
                0 if entry == "last" else loads[entry])
        return total

    def bonus_bound(self, assign: dict, dom: dict) -> int:
        planned = {c: t for c, t in assign.items() if t}
        loads = self.other_loads(planned)
        return sum(loads[e] for e in self.bonus_terms() if e != "last")

    def build_prefs(self) -> list[Pref]:
        prefs: list[Pref] = []
        done = self.done
        for rule in self.spec["rules"]:
            if rule["strength"] != "prefer":
                continue
            kind = rule["type"]
            if kind == "in_sem":
                course, sem = rule["course"], rule["sem"]
                label = f"{course} in semester {sem}"
                if course in done or course not in self.initial or sem not in self.initial[course]:
                    prefs.append(Pref("const", label, False))
                else:
                    prefs.append(Pref("in_sem", label, course=course, sem=sem))
                continue
            a, b = rule["a"], rule["b"]
            label = {"before": f"{a} before {b}",
                     "apart": f"{a} and {b} in different semesters",
                     "same_sem": f"{a} and {b} in the same semester"}[kind]
            a_done, b_done = a in done, b in done
            if kind == "before" and a_done:
                prefs.append(Pref("const", label, True))
            elif kind == "before" and b_done:
                prefs.append(Pref("const", label, False))
            elif kind == "apart" and (a_done or b_done):
                prefs.append(Pref("const", label, True))
            elif kind == "same_sem" and a_done and b_done:
                prefs.append(Pref("const", label, True))
            elif kind == "same_sem" and (a_done or b_done):
                prefs.append(Pref("const", label, False))
            elif a not in self.mc or b not in self.mc:
                prefs.append(Pref("const", label, False))
            else:
                prefs.append(Pref("pair", label, rel=kind, a=a, b=b))
        for entry in self.light_entries():
            label = "last semester lighter than average" if entry == "last" else f"semester {entry} lighter than average"
            prefs.append(Pref("light", label, entry=entry))
        if self.spec["balance_load"] and self.sems:
            prefs.append(Pref("balance", "largest semester load is as small as possible"))
        wanted = [(c, True) for c in self.spec["early"]] + [(c, False) for c in self.spec["late"]]
        for code, early in wanted:
            label = f"{code} as {'early' if early else 'late'} as possible"
            if code in done:
                prefs.append(Pref("const", label, True))
            elif code not in self.required:
                prefs.append(Pref("const", label, False))
            else:
                prefs.append(Pref("sem", label, code=code, early=early))
        return prefs

    def light_holds(self, entry, planned: dict) -> bool:
        last = self.last_of(planned)
        if last < self.current:
            return False
        loads = self.other_loads(planned)
        total = sum(loads.values())
        window = LAST_SEM - self.current + 1 if self.objective == "none" else last - self.current + 1
        semester = last if entry == "last" else entry
        return loads.get(semester, 0) * window <= total - 1

    def holds(self, pref: Pref, planned: dict) -> bool:
        kind, d = pref.kind, pref.data
        if kind == "const":
            return pref.const
        if kind == "in_sem":
            return planned.get(d["course"]) == d["sem"]
        if kind == "pair":
            a, b = planned.get(d["a"]), planned.get(d["b"])
            if not a or not b:
                return False
            return {"before": a + 1 <= b, "apart": a != b, "same_sem": a == b}[d["rel"]]
        if kind == "light":
            return self.light_holds(d["entry"], planned)
        if kind == "balance":
            return self.peak_of(planned) <= pref.target
        return planned.get(d["code"]) == pref.target

    def possible(self, pref: Pref, assign: dict, dom: dict) -> bool:
        kind, d = pref.kind, pref.data
        if kind == "const":
            return pref.const
        if kind == "in_sem":
            course = d["course"]
            return assign[course] == d["sem"] if course in assign else d["sem"] in dom[course]
        if kind == "pair":
            xs = [t for t in self.values(d["a"], assign, dom, True) if t]
            ys = [t for t in self.values(d["b"], assign, dom, True) if t]
            rel = {"before": lambda x, y: x + 1 <= y, "apart": lambda x, y: x != y,
                   "same_sem": lambda x, y: x == y}[d["rel"]]
            return any(rel(x, y) for x in xs for y in ys)
        if kind == "light":
            return True
        if kind == "balance":
            return self.peak_bound(assign, dom) <= pref.target
        code = d["code"]
        return assign[code] == pref.target if code in assign else pref.target in dom[code]

    def within(self, assign: dict, dom: dict, stage: Stage, fixed: list) -> bool:
        for other, value in fixed:
            if other.bound is None:
                continue
            bound = other.bound(assign, dom)
            if other.sense == "min" and bound > value:
                return False
            if other.sense == "max" and bound < value:
                return False
        if stage.best is not None and stage.bound is not None:
            bound = stage.bound(assign, dom)
            if stage.sense == "min" and bound >= stage.best:
                return False
            if stage.sense == "max" and bound <= stage.best:
                return False
        return True

    def leaf(self, assign: dict, stage: Stage, fixed: list) -> None:
        if not self.valid(assign):
            return
        planned = {c: s for c, s in assign.items() if s}
        for other, value in fixed:
            if other.leaf(planned) != value:
                return
        value = stage.leaf(planned)
        if stage.sense == "first":
            stage.best, stage.best_assign = value, dict(assign)
            raise Found()
        better = stage.best is None or (value < stage.best if stage.sense == "min" else value > stage.best)
        if better:
            stage.best, stage.best_assign = value, dict(assign)
            if stage.limit is not None and value == stage.limit:
                raise Found()

    def pick(self, free: list, dom: dict, assign: dict):
        if not self.use_mrv:
            return free[0], dom[free[0]], False
        if self.use_forward:
            var = min(free, key=lambda c: (len(dom[c]), self.index[c]))
            return var, dom[var], False
        best = None
        for code in free:
            legal = []
            for value in dom[code]:
                assign[code] = value
                if self.consistent(assign, code):
                    legal.append(value)
                del assign[code]
            if best is None or len(legal) < len(best[1]):
                best = (code, legal)
            if not legal:
                break
        return best[0], best[1], True

    def dfs(self, assign: dict, dom: dict, stage: Stage, fixed: list) -> None:
        self.tick()
        free = [c for c in self.order if c not in assign]
        if not free:
            self.leaf(assign, stage, fixed)
            return
        var, values, checked = self.pick(free, dom, assign)
        if checked and not values:
            self.backtracks += 1
            return
        for value in values:
            self.nodes += 1
            self.tick()
            assign[var] = value
            new_dom = dom
            ok = checked or self.consistent(assign, var)
            if ok and self.use_forward:
                new_dom = dict(dom)
                new_dom[var] = (value,)
                ok = self.propagate(assign, new_dom)
            if ok:
                ok = self.within(assign, new_dom, stage, fixed)
            if ok:
                self.dfs(assign, new_dom, stage, fixed)
            else:
                self.backtracks += 1
            del assign[var]

    def optimize(self, stage: Stage, fixed: list):
        dom = dict(self.initial)
        if self.use_forward:
            ok = self.propagate({}, dom)
            if not ok:
                return None
        try:
            self.dfs({}, dom, stage, fixed)
        except Found:
            pass
        return stage.best_assign

    def no_plan(self, reasons: list[str]) -> dict:
        result = {"status": "NO_PLAN", "reasons": reasons}
        if self.spec["unsupported"]:
            result["not_applied"] = list(self.spec["unsupported"])
        return result

    def infeasible_reasons(self) -> list[str]:
        needed = sum(self.mc[c] for c in self.candidates if c in self.required and c != ATAP_CODE)
        room = sum(self.cap(s) for s in self.sems)
        if needed > room:
            return [f"the required courses need {needed} MC but the remaining semesters "
                    f"{self.sems} allow at most {room} MC"]
        return [GENERIC_REASON]

    def solve(self) -> dict:
        if self.reasons:
            return self.no_plan(self.reasons)
        fixed: list = []
        if self.objective == "earliest_graduation":
            stage = Stage("min", self.last_of, self.last_bound, self.current - 1)
        elif self.objective == "min_total_mc":
            stage = Stage("min", self.total_mc, self.mc_bound)
        else:
            stage = Stage("first", lambda planned: 0)
        final = self.optimize(stage, fixed)
        if final is None:
            return self.no_plan(self.infeasible_reasons())
        if stage.sense != "first":
            fixed.append((stage, stage.best))

        if self.extras:
            stage = Stage("min", self.extras_count, self.extras_bound, 0)
            final = self.optimize(stage, fixed)
            fixed.append((stage, stage.best))

        prefs = self.build_prefs()
        for pref in prefs:
            if pref.kind == "balance":
                stage = Stage("min", self.peak_of, self.peak_bound)
                self.optimize(stage, fixed)
                pref.target = stage.best
            elif pref.kind == "sem":
                code, early = pref.data["code"], pref.data["early"]
                stage = Stage("min" if early else "max", lambda planned, c=code: planned[c],
                              self.sem_bound(code, early))
                self.optimize(stage, fixed)
                pref.target = stage.best
        if any(p.kind != "const" for p in prefs):
            stage = Stage("max", lambda planned: sum(self.holds(p, planned) for p in prefs),
                          lambda assign, dom: sum(self.possible(p, assign, dom) for p in prefs),
                          len(prefs))
            final = self.optimize(stage, fixed)
            fixed.append((stage, stage.best))

        if self.bonus_terms():
            stage = Stage("min", self.bonus_leaf, self.bonus_bound, 0)
            final = self.optimize(stage, fixed)
            fixed.append((stage, stage.best))

        if self.objective != "earliest_graduation":
            stage = Stage("min", self.last_of, self.last_bound, self.current - 1)
            final = self.optimize(stage, fixed)
        return self.build_answer(final, prefs)

    def build_answer(self, assign: dict, prefs: list[Pref]) -> dict:
        planned = {c: s for c, s in assign.items() if s}
        last = self.last_of(planned)
        placed: dict[int, list[str]] = {}
        for code, s in planned.items():
            placed.setdefault(s, []).append(code)
        plan, per_semester = {}, {}
        if last >= self.current:
            for s in range(self.current, last + 1):
                courses = sorted(placed.get(s, []))
                plan[str(s)] = courses
                per_semester[str(s)] = sum(self.mc[c] for c in courses)
        met, not_met = [], []
        for pref in prefs:
            (met if self.holds(pref, planned) else not_met).append(pref.label)
        result = {
            "status": "PLAN",
            "objective": self.objective,
            "last_semester": last if last >= self.current else None,
            "plan": plan,
            "mc_per_semester": per_semester,
            "preferences_met": met,
            "preferences_not_met": not_met,
        }
        added = sorted(c for c in planned if c not in self.required)
        if added:
            result["added_prerequisites"] = added
        if self.notes:
            result["notes"] = list(self.notes)
        if self.spec["unsupported"]:
            result["not_applied"] = list(self.spec["unsupported"])
        return result


def solve_with_stats(spec, catalog=None, variant: str = "mac", time_limit: float = 60):
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {list(VARIANTS)}, got {variant!r}")
    catalog = catalog or Catalog.load()
    started = time.perf_counter()
    stats = {"nodes": 0, "backtracks": 0, "checks": 0, "seconds": 0.0, "timed_out": False}
    early, cleaned, warnings = prepare(spec, catalog)
    if early is not None:
        answer = early
    elif cleaned["query"] == "eligible":
        answer = q1.answer(cleaned, catalog)
        if warnings:
            answer["warnings"] = warnings
    else:
        search = Search(cleaned, catalog, variant, started + time_limit)
        try:
            answer = search.solve()
        except TimeLimit:
            stats["timed_out"] = True
            answer = {"status": "TIMED_OUT",
                      "reasons": [f"the search stopped at the time limit of {time_limit} seconds"]}
        stats["nodes"], stats["backtracks"], stats["checks"] = search.nodes, search.backtracks, search.checks
        if warnings:
            answer["warnings"] = warnings
    stats["seconds"] = time.perf_counter() - started
    return answer, stats
