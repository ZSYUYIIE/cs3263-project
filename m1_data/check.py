"""Sanity checks on data/processed. Exit code 1 if any check fails.

Run after every build. These are invariants M2/M3 rely on; if one breaks,
fix the parser (or add an override) before handing data over.
"""
from __future__ import annotations

import json

from . import paths
from .catalog import Catalog


def check() -> list[str]:
    cfg = json.loads(paths.CONFIG.read_text(encoding="utf-8"))
    cat = Catalog.load(paths.processed_dir(cfg["acad_year"]) / "catalog.json")
    cs = cat.courses
    problems: list[str] = []

    def walk(node, where):
        if node is None:
            return
        if node is True or node is False:
            if where.endswith("logic") and node is False:
                return
            problems.append(f"{where}: bare boolean inside tree")
            return
        op = node.get("op")
        if op == "course":
            if node["code"] not in cs:
                problems.append(f"{where}: references {node['code']} which has no catalogue entry")
            return
        if op not in ("and", "or", "n_of"):
            problems.append(f"{where}: unknown op {op}")
            return
        if len(node["args"]) < 2:
            problems.append(f"{where}: {op} with <2 args (should be simplified)")
        if op == "n_of" and not (1 < node["n"] < len(node["args"])):
            problems.append(f"{where}: n_of n={node['n']} should have been simplified")
        for a in node["args"]:
            walk(a, where)

    for code, c in cs.items():
        walk(c["prereq"]["logic"], f"{code}.prereq.logic")
        walk(c["coreq"]["logic"], f"{code}.coreq.logic")
        walk(c["preclusion"]["blocked_if"], f"{code}.preclusion.blocked_if")
        if code in c["prereq"]["courses"]:
            problems.append(f"{code}: is its own prerequisite")
        if c["details"] == "full" and c["mc"] is None:
            problems.append(f"{code}: missing MC")
        if c["exists_in_ay"] and c["available"] and not c["offered"]:
            problems.append(f"{code}: available but offered in no semester")
        for x in c["preclusion"]["mutually_exclusive_with"]:
            if code not in cs[x]["preclusion"]["mutually_exclusive_with"]:
                problems.append(f"{code}: mutual exclusion with {x} is not symmetric")

    # Prerequisite cycles among plannable courses would make planning impossible.
    # Edges that only come from wildcards (e.g. "7 of NM1%..NM4%") are skipped:
    # they are large n-of pools, not hard requirements.
    def hard_refs(node, out):
        if node is None or isinstance(node, bool):
            return out
        if node["op"] == "course":
            if "via_pattern" not in node:
                out.add(node["code"])
        else:
            for a in node["args"]:
                hard_refs(a, out)
        return out

    graph = {c: hard_refs(v["prereq"]["logic"], set()) for c, v in cs.items()}
    state: dict[str, int] = {}

    def dfs(u, stack):
        state[u] = 1
        for v in graph.get(u, ()):
            if state.get(v) == 1:
                problems.append("prerequisite cycle: " + " -> ".join(stack[stack.index(v):] + [v]))
            elif v not in state:
                dfs(v, stack + [v])
        state[u] = 2

    for u in graph:
        if u not in state:
            dfs(u, [u])

    if problems:
        print(f"[check] {len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
    else:
        print(f"[check] OK: {len(cs)} courses, all invariants hold")
    return problems
