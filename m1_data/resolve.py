"""Turn literal rule trees (rules.py) into course-only logic for one student.

Every non-course condition (programme, cohort, A-level subjects, GPA, ...)
is evaluated against data/config/student_context.json and folded away, so
what is left only mentions courses. Each fold is logged as an assumption.

Course-logic nodes (the format M2/M3 consume):

    {"op": "course", "code": "CS2040S", "min_grade": "D"}
    {"op": "course", ..., "via_pattern": "CS2040%"}   # came from a wildcard
    {"op": "and", "args": [...]}
    {"op": "or",  "args": [...]}
    {"op": "n_of", "n": 2, "args": [...]}      # at least n of args

`True` means "no requirement" and `False` means "can never be satisfied";
neither appears inside a tree (they are simplified away), only at the top.
"""
from __future__ import annotations

import fnmatch
import json
import re

GROUP_FIELD = {"PROGRAMS": "programs", "2ND_MAJOR": "second_major",
               "MINOR": "minor", "SPECIAL_PROGRAMME": "special_programme"}
POSITIVE = {"MUST_BE_IN", "IF_IN"}


class Resolver:
    def __init__(self, context: dict, known_codes: set[str], self_code: str | None = None):
        self.ctx = context
        self.known = known_codes
        self.self_code = self_code   # excluded from its own wildcard expansions
        self.assumptions: list[str] = []
        self.warnings: list[str] = []

    # ---------------------------------------------------------------- helpers
    def _note(self, msg: str):
        if msg not in self.assumptions:
            self.assumptions.append(msg)

    def _unknown(self, what: str) -> bool:
        policy = self.ctx.get("unknown_policy", "assume_true")
        self._note(f"{what}: unknown for this student, {policy}")
        return policy == "assume_true"

    def expand(self, item: dict) -> list[dict]:
        """One COURSES item -> course nodes (patterns expanded)."""
        g = item.get("min_grade") or "D"
        if not item["pattern"]:
            return [{"op": "course", "code": item["code"], "min_grade": g}]
        pat = item["code"] + "*"
        hits = sorted(c for c in self.known
                      if fnmatch.fnmatchcase(c, pat) and c != self.self_code)
        if not hits:
            self.warnings.append(f"pattern {item['code']}% matches no known course")
        else:
            self._note(f"pattern {item['code']}% expanded to {', '.join(hits)}")
        return [{"op": "course", "code": c, "min_grade": g, "via_pattern": item["code"] + "%"}
                for c in hits]

    # -------------------------------------------------- non-course conditions
    def cond_value(self, node: dict) -> bool:
        op = node["op"]
        if op == "program_type":
            hit = self.ctx.get("program_type") in node["values"]
            return hit if node["rule"] in POSITIVE else not hit
        if op == "group":
            mine = set(self.ctx.get(GROUP_FIELD[node["group"]], []) or [])
            hit = bool(mine & set(node["values"]))
            res = hit if node["rule"] in POSITIVE else not hit
            self._note(f"{node['group']} {node['rule']} {','.join(node['values'])} -> {res}")
            return res
        if op == "cohort":
            c = self.ctx.get("cohort")
            if c is None:
                return self._unknown("cohort condition")
            hit = any(_cohort_match(c, v) for v in node["values"])
            res = hit if node["rule"] in POSITIVE else not hit
            self._note(f"cohort {node['rule']} {','.join(node['values'])} with cohort {c} -> {res}")
            return res
        if op == "subjects":
            held = self.ctx.get("subjects_held")
            items = ", ".join(f"{i['subject']}:{i['grade']}" for i in node["items"])
            if held is None:
                return self._unknown(f"pre-university subjects ({items})")
            k = node["n"] if node["n"] is not None else 1
            have = sum(i["subject"] in held for i in node["items"])
            res = have >= k
            self._note(f"pre-university subjects ({items}) -> {res} (student holds {', '.join(held) or 'none'})")
            return res
        if op in ("units", "gpa"):
            field = "units_completed" if op == "units" else "gpa"
            v = self.ctx.get(field)
            if v is None:
                return self._unknown(f"{op} >= {node['min']}")
            return v >= node["min"]
        if op == "special":
            m = re.match(r"(\w+)=(.*)", node["value"])
            if m and m.group(1) == "ACAD_LEVEL" and self.ctx.get("acad_level") is not None:
                ok = str(self.ctx["acad_level"]) in m.group(2).split("-")
                return ok if node["rule"] in POSITIVE else not ok
            if m and m.group(1) == "SUBJECT_LEVEL" and self.ctx.get("subject_level") is not None:
                ok = self.ctx["subject_level"] == m.group(2)
                self._note(f"{node['value']} with subject level {self.ctx['subject_level']} -> {ok}")
                return ok if node["rule"] in POSITIVE else not ok
            return self._unknown(f"special condition {node['value']}")
        raise ValueError(f"not a condition node: {op}")

    # ------------------------------------------------------- requirement trees
    def requirement(self, node):
        """Literal prerequisite/corequisite tree -> course logic (or bool)."""
        if node is None:
            return True
        op = node["op"]
        if op == "courses":
            args = [c for it in node["items"] for c in self.expand(it)]
            # No "(n)" written means "any one of" (NUSMods shows it as A/B and
            # its prereqTree agrees), e.g. "COURSES CS2106:D, CG2271:D".
            n = node["n"] if node["n"] is not None else 1
            return simplify({"op": "n_of", "n": n, "args": args})
        if op in ("and", "or"):
            return simplify({"op": op, "args": [self.requirement(a) for a in node["args"]]})
        if op == "if":
            cond = self.condition(node["cond"])
            if cond is False:
                return True          # rule does not apply to this student
            return self.requirement(node["then"])
        return self.cond_value(node)

    def condition(self, node) -> bool:
        """Evaluate an IF-condition (no courses inside)."""
        op = node["op"]
        if op == "and":
            return all(self.condition(a) for a in node["args"])
        if op == "or":
            return any(self.condition(a) for a in node["args"])
        if op == "courses":
            self.warnings.append("course list inside an IF condition; treated as unknown")
            return self._unknown("course condition in IF")
        return self.cond_value(node)

    # ---------------------------------------------------------- preclusions
    def preclusion(self, node):
        """Literal preclusion rule -> (blocked_if logic, restriction reasons).

        A preclusion rule lists things the student must NOT have. We read
        every clause as an independent block: the course is blocked if ANY
        listed course group has been completed or ANY programme exclusion
        matches the student. For rules joined only by AND (almost all of
        them) this is exactly the literal meaning; for the few that use OR,
        the literal reading would let excluded students through, so we use
        this intended reading and log a warning for the spot-check.
        """
        reasons: list[str] = []
        blocks = []

        def walk(n):
            if n is None:
                return
            op = n["op"]
            if op == "if":
                if self.condition(n["cond"]) is not False:
                    walk(n["then"])
                return
            if op in ("and", "or"):
                if op == "or":
                    self.warnings.append("preclusion rule uses OR; read as 'any clause blocks'")
                for a in n["args"]:
                    walk(a)
                return
            if op == "courses":
                args = [c for it in n["items"] for c in self.expand(it)]
                k = n["n"] if n["n"] is not None else 1
                blocks.append(simplify({"op": "n_of", "n": k, "args": args}))
                return
            if op == "group" and n["rule"] not in POSITIVE:
                mine = set(self.ctx.get(GROUP_FIELD[n["group"]], []) or [])
                hit = sorted(mine & set(n["values"]))
                if hit:
                    reasons.append(f"not open to {n['group']} {', '.join(hit)}")
                return
            if op in ("cohort", "program_type", "subjects", "units", "gpa", "special", "group"):
                # e.g. "COHORT_YEARS MUST_BE_IN ..." inside a preclusion: a
                # condition on who the preclusion applies to; keep as note.
                self._note(f"preclusion clause {op} ignored for blocking: {json.dumps(n)}")
                return
            raise ValueError(op)

        walk(node)
        blocked = simplify({"op": "or", "args": blocks}) if blocks else False
        return blocked, reasons


def _cohort_match(cohort: int, value: str) -> bool:
    """'S:2017' = cohort 2017 onwards, 'E:2016' = up to 2016, '2019' = exactly."""
    m = re.fullmatch(r"(?:([SE]):)?(\d{4})(?:/\d{2})?", value)
    if not m:
        return False
    kind, year = m.group(1), int(m.group(2))
    if kind == "S":
        return cohort >= year
    if kind == "E":
        return cohort <= year
    return cohort == year


# --------------------------------------------------------------- simplify
def _key(n) -> str:
    return json.dumps(n, sort_keys=True)


def simplify(node):
    """Fold constants, flatten, dedupe, and canonicalise n_of."""
    if isinstance(node, bool) or node["op"] == "course":
        return node
    op = node["op"]
    args = [simplify(a) for a in node["args"]]

    if op == "n_of":
        n = node["n"]
        n -= sum(1 for a in args if a is True)
        args = [a for a in args if not isinstance(a, bool)]
        args = list({_key(a): a for a in args}.values())
        if n <= 0:
            return True
        if n > len(args):
            return False
        if n == 1:
            op = "or"
        elif n == len(args):
            op = "and"
        else:
            return {"op": "n_of", "n": n, "args": sorted(args, key=_key)}

    if op == "and":
        if any(a is False for a in args):
            return False
        args = [a for a in args if a is not True]
    else:  # or
        if any(a is True for a in args):
            return True
        args = [a for a in args if a is not False]

    flat = []
    for a in args:
        if isinstance(a, dict) and a["op"] == op:
            flat.extend(a["args"])
        else:
            flat.append(a)
    flat = list({_key(a): a for a in flat}.values())
    if not flat:
        return op == "and"
    if len(flat) == 1:
        return flat[0]
    return {"op": op, "args": flat}


# ----------------------------------------------------------------- render
def render(node, top: bool = True) -> str:
    """Human-readable one-liner, e.g. '(CS2109S or CS2109HS) and CS2040S'."""
    if node is True:
        return "none"
    if node is False:
        return "impossible"
    op = node["op"]
    if op == "course":
        g = node.get("min_grade") or "D"
        return node["code"] if g == "D" else f"{node['code']}[>={g}]"
    if op == "n_of":
        return f"{node['n']} of ({', '.join(render(a, False) for a in node['args'])})"
    s = f" {op} ".join(render(a, False) for a in node["args"])
    return s if top else f"({s})"


def courses_in(node) -> list[str]:
    out: set[str] = set()

    def walk(n):
        if isinstance(n, bool):
            return
        if n["op"] == "course":
            out.add(n["code"])
        else:
            for a in n["args"]:
                walk(a)

    walk(node)
    return sorted(out)
