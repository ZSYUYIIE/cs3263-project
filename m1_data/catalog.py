"""Load the processed catalogue and answer simple questions about it.

    from m1_data.catalog import Catalog
    cat = Catalog.load()                       # newest AY in data/processed
    cat["CS3263"]["prereq"]["text"]
    cat.can_take("CS3263", completed={"CS3244", "CS2040S", "MA1522", "ST2334"})
    # -> (False, ["blocked: completed CS3244 ... ", "missing prerequisite: ..."])

This is a convenience layer over catalog.json for T1 ground truth, debugging
and prompts. The evaluation checker (M3) should implement its own logic from
docs/DATA_SCHEMA.md so it stays independent of this code.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import paths
from .resolve import render


def satisfied(node, completed: set[str]) -> bool:
    """Does the set of completed course codes satisfy a logic tree?"""
    if node is None or node is True:
        return True
    if node is False:
        return False
    op = node["op"]
    if op == "course":
        return node["code"] in completed
    hits = sum(satisfied(a, completed) for a in node["args"])
    if op == "and":
        return hits == len(node["args"])
    if op == "or":
        return hits >= 1
    if op == "n_of":
        return hits >= node["n"]
    raise ValueError(op)


def unmet(node, completed: set[str]):
    """The part of a logic tree that is still unsatisfied (None if satisfied)."""
    if satisfied(node, completed):
        return None
    if node["op"] == "and":
        parts = [unmet(a, completed) for a in node["args"]]
        parts = [p for p in parts if p is not None]
        return parts[0] if len(parts) == 1 else {"op": "and", "args": parts}
    return node


class Catalog:
    def __init__(self, data: dict):
        self.data = data
        self.courses: dict[str, dict] = data["courses"]

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Catalog":
        if path is None:
            ays = sorted((paths.DATA / "processed").glob("AY*/catalog.json"))
            if not ays:
                raise FileNotFoundError("no catalog.json; run `python -m m1_data build`")
            path = ays[-1]
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def __getitem__(self, code: str) -> dict:
        return self.courses[code.upper()]

    def __contains__(self, code: str) -> bool:
        return code.upper() in self.courses

    def plannable(self) -> list[str]:
        """Courses that exist this AY and are open to the configured student."""
        return [c for c, v in self.courses.items() if v["exists_in_ay"] and v["available"]]

    def can_take(self, code: str, completed, semester: int | None = None):
        """T1-style eligibility. Returns (ok, reasons). Ignores MC caps."""
        code = code.upper()
        done = {c.upper() for c in completed}
        if code not in self.courses:
            return False, [f"{code} is not in the catalogue"]
        c = self.courses[code]
        why = []
        if code in done:
            why.append(f"{code} already completed")
        if not c["available"]:
            why += [f"unavailable: {r}" for r in c["unavailable_reasons"]]
        if semester is not None and semester not in c["offered"]:
            why.append(f"not offered in semester {semester} (offered: {c['offered'] or 'never'})")
        b = c["preclusion"]["blocked_if"]
        if b is not None and satisfied(b, done):
            hit = sorted(set(c["preclusion"]["courses"]) & done)
            why.append(f"precluded: already completed {', '.join(hit)}")
        mx = sorted(set(c["preclusion"]["mutually_exclusive_with"]) & done
                    - set(c["preclusion"]["courses"]))
        if mx:
            why.append(f"mutually exclusive with completed {', '.join(mx)} (listed on their page)")
        p = c["prereq"]["logic"]
        if p is False:
            why.append("prerequisite can never be met by this student")
        elif not satisfied(p, done):
            why.append(f"missing prerequisite: {render(unmet(p, done))}")
        return (not why), why

    def blocked_by(self, code: str, done: set[str]) -> list[str]:
        """Completed courses that rule `code` out (either direction)."""
        c = self.courses.get(code)
        if c is None:
            return []
        hit = set(c["preclusion"]["mutually_exclusive_with"]) & done
        b = c["preclusion"]["blocked_if"]
        if b is not None and satisfied(b, done):
            hit |= set(c["preclusion"]["courses"]) & done
        return sorted(hit)

    def reachable(self, code: str, completed) -> tuple[bool, str]:
        """Could the student still EVER take `code`, given what they completed?

        Explores prerequisite chains, dropping any course that a completed
        course rules out. Ignores semesters, MC caps and clashes between two
        future picks, so True means "not ruled out by preclusions", not
        "a plan exists". Useful for building infeasible instances (e.g.
        took CS3244 -> CS2109S and CS2109HS both blocked -> CS3263 unreachable)
        and for explaining why.
        """
        done = {x.upper() for x in completed}
        memo: dict[str, tuple[bool, str]] = {}

        def ok(x: str, stack: frozenset) -> tuple[bool, str]:
            if x in done:
                return True, f"{x} completed"
            if x in memo:
                return memo[x]
            if x in stack:
                return False, f"{x}: cycle"
            c = self.courses.get(x)
            if c is None or not c["exists_in_ay"] or not c["available"]:
                why = "; ".join(c["unavailable_reasons"]) if c else "unknown course"
                return False, f"{x} unavailable ({why})"
            hit = self.blocked_by(x, done)
            if hit:
                memo[x] = (False, f"{x} is ruled out by completed {', '.join(hit)}")
                return memo[x]
            res = tree(c["prereq"]["logic"], stack | {x})
            memo[x] = (res[0], f"{x}: {res[1]}" if not res[0] else f"{x} reachable")
            return memo[x]

        def tree(n, stack) -> tuple[bool, str]:
            if n is None or n is True:
                return True, "no prerequisite"
            if n is False:
                return False, "prerequisite can never be met"
            if n["op"] == "course":
                return ok(n["code"], stack)
            parts = [tree(a, stack) for a in n["args"]]
            good = sum(p[0] for p in parts)
            need = {"and": len(parts), "or": 1, "n_of": n.get("n", 1)}[n["op"]]
            if good >= need:
                return True, "satisfiable"
            fails = [p[1] for p in parts if not p[0]]
            if n["op"] == "and":
                return False, fails[0]
            return False, "every option fails: " + " | ".join(fails)

        return ok(code.upper(), frozenset())
