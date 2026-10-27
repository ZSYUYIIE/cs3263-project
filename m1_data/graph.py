"""Graph exports of the catalogue.

graph.json (node-link; what code and agents should traverse)
    nodes:
      {"id": "CS3263", "kind": "course", "title", "mc", "offered", "available",
       "exists_in_ay", "details", "fan_in", "depth"}
      {"id": "CS3263#p0", "kind": "all" | "any" | "n_of", "n": 2, "of": "CS3263",
       "role": "prereq" | "coreq" | "excludes"}
    edges:
      {"source": "CS3263", "target": "CS3263#p0", "kind": "prereq"}   course -> its logic root
      {"source": "CS3263#p0", "target": "CS3263#p1", "kind": "arg"}    logic -> sub-logic
      {"source": "CS3263#p1", "target": "CS2109S",  "kind": "arg"}     logic -> course
      {"source": "CS3263", "target": "CS2040S", "kind": "prereq"}      direct when the
                                                                       requirement is one course
      {"source": "CS3263", "target": "CS3243", "kind": "excludes"}     mutual; listed once (a < b)
    Reading it: a course's requirement is satisfied when its prereq target is
    satisfied; an "all" node needs every arg, "any" one arg, "n_of" n args.

    "fan_in" = number of courses whose prereq mentions this one ("unlocks").
    "depth"  = length of the longest chain of hard prerequisites below the
               course, taking the shortest option at every OR (0 = no prereq).
               A rough "how far down the tree" rank for layouts.

course_graph.graphml (courses only, for yEd / Gephi / Cytoscape)
    One node per course; edges "needs" (course -> prerequisite course, from any
    option) and "excludes". Logic structure is flattened, so use graph.json
    when the and/or structure matters.
"""
from __future__ import annotations

import json
from xml.sax.saxutils import escape

KIND = {"and": "all", "or": "any", "n_of": "n_of"}


def build_graph(catalog: dict) -> dict:
    cs = catalog["courses"]
    nodes, edges = [], []
    depth = _depths(cs)

    for code, c in cs.items():
        nodes.append({
            "id": code, "kind": "course", "title": c["title"], "mc": c["mc"],
            "offered": c["offered"], "available": c["available"],
            "exists_in_ay": c["exists_in_ay"], "details": c["details"],
            "fan_in": len(c["unlocks"]), "depth": depth.get(code),
        })

    for code, c in cs.items():
        for role, logic in (("prereq", c["prereq"]["logic"]), ("coreq", c["coreq"]["logic"])):
            if not isinstance(logic, dict):
                continue
            counter = [0]

            def emit(node, parent, kind):
                if node["op"] == "course":
                    edges.append({"source": parent, "target": node["code"], "kind": kind})
                    return
                nid = f"{code}#{role[0]}{counter[0]}"
                counter[0] += 1
                n = {"id": nid, "kind": KIND[node["op"]], "of": code, "role": role}
                if node["op"] == "n_of":
                    n["n"] = node["n"]
                nodes.append(n)
                edges.append({"source": parent, "target": nid, "kind": kind})
                for a in node["args"]:
                    emit(a, nid, "arg")

            emit(logic, code, role)

        for x in c["preclusion"]["mutually_exclusive_with"]:
            if code < x:
                edges.append({"source": code, "target": x, "kind": "excludes"})

    return {
        "schema": "m1_data graph v1 (see m1_data/graph.py docstring)",
        "acad_year": catalog["acad_year"],
        "student_context": catalog["student_context"],
        "nodes": nodes,
        "edges": edges,
    }


def _depths(cs: dict) -> dict:
    memo: dict[str, int] = {}

    def d(code, stack=frozenset()):
        if code in memo:
            return memo[code]
        if code in stack or code not in cs:
            return 0
        memo[code] = 1 + tree(cs[code]["prereq"]["logic"], stack | {code}) if cs[code]["prereq"]["logic"] else 0
        return memo[code]

    def tree(n, stack):
        if not isinstance(n, dict):
            return -1
        if n["op"] == "course":
            return d(n["code"], stack) if "via_pattern" not in n else 0
        vals = sorted(tree(a, stack) for a in n["args"])
        if n["op"] == "and":
            return max(vals)
        if n["op"] == "or":
            return vals[0]
        return vals[n["n"] - 1]          # n_of: the n cheapest options

    for code in cs:
        d(code)
    return memo


def write_graphml(path, catalog: dict, graph: dict) -> None:
    cs = catalog["courses"]
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
         '  <key id="title" for="node" attr.name="title" attr.type="string"/>',
         '  <key id="mc" for="node" attr.name="mc" attr.type="double"/>',
         '  <key id="offered" for="node" attr.name="offered" attr.type="string"/>',
         '  <key id="available" for="node" attr.name="available" attr.type="boolean"/>',
         '  <key id="in_ay" for="node" attr.name="exists_in_ay" attr.type="boolean"/>',
         '  <key id="fan_in" for="node" attr.name="fan_in" attr.type="int"/>',
         '  <key id="depth" for="node" attr.name="depth" attr.type="int"/>',
         '  <key id="kind" for="edge" attr.name="kind" attr.type="string"/>',
         f'  <graph id="AY{catalog["acad_year"]}" edgedefault="directed">']
    for n in graph["nodes"]:
        if n["kind"] != "course":
            continue
        L.append(f'    <node id="{n["id"]}">'
                 f'<data key="title">{escape(n["title"] or "")}</data>'
                 + (f'<data key="mc">{n["mc"]}</data>' if n["mc"] is not None else "")
                 + f'<data key="offered">{",".join(map(str, n["offered"]))}</data>'
                 f'<data key="available">{str(n["available"]).lower()}</data>'
                 f'<data key="in_ay">{str(n["exists_in_ay"]).lower()}</data>'
                 f'<data key="fan_in">{n["fan_in"]}</data>'
                 + (f'<data key="depth">{n["depth"]}</data>' if n["depth"] is not None else "")
                 + '</node>')
    i = 0
    for code, c in cs.items():
        for x in c["prereq"]["courses"]:
            L.append(f'    <edge id="e{i}" source="{code}" target="{x}"><data key="kind">needs</data></edge>')
            i += 1
    for e in graph["edges"]:
        if e["kind"] == "excludes":
            L.append(f'    <edge id="e{i}" source="{e["source"]}" target="{e["target"]}">'
                     f'<data key="kind">excludes</data></edge>')
            i += 1
    L += ["  </graph>", "</graphml>"]
    path.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
