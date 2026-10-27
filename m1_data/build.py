"""Raw NUSMods JSON -> data/processed/AY<ay>/

Outputs (see docs/DATA_SCHEMA.md for every field):
    catalog.json        one record per course; what M2/M3 load
    rules_literal.json  the parsed rule trees before any resolution (audit)
    edges.csv           course -> course relations, for graphs / spreadsheets
    COURSES.md          human/agent-readable catalogue, one block per course
    PARSE_REPORT.md     warnings, cross-check results, things to spot-check
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone

from . import SCHEMA_VERSION, paths
from .resolve import Resolver, _key, courses_in, render, simplify
from .rules import has_mixed_and_or, parse_rule

SEM_NAME = {1: "Sem 1", 2: "Sem 2", 3: "Special Term I", 4: "Special Term II"}


def _load_json(p, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _mc(v):
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return None


def tree_to_literal(t):
    """NUSMods prereqTree -> the literal node format of rules.py (for cross-check)."""
    if isinstance(t, str):
        code, _, g = t.partition(":")
        return {"op": "courses", "n": None,
                "items": [{"code": code.rstrip("%"), "pattern": code.endswith("%"), "min_grade": g or None}]}
    if "and" in t or "or" in t:
        op = "and" if "and" in t else "or"
        return {"op": op, "args": [tree_to_literal(x) for x in t[op]]}
    if "nOf" in t:
        k, xs = t["nOf"]
        items = []
        for x in xs:
            if not isinstance(x, str):
                return {"op": "and", "args": []}   # not expected; makes mismatch visible
            code, _, g = x.partition(":")
            items.append({"code": code.rstrip("%"), "pattern": code.endswith("%"), "min_grade": g or None})
        return {"op": "courses", "n": k, "items": items}
    if "programType" in t:
        pt = t["programType"]
        return {"op": "if", "cond": {"op": "program_type", "rule": pt["rule"], "values": pt["types"]},
                "then": tree_to_literal(t["then"])}
    if "cohort" in t:
        c = t["cohort"]
        node = {"op": "cohort", "rule": c["rule"], "values": c["years"]}
        return {"op": "if", "cond": node, "then": tree_to_literal(t["then"])} if "then" in t else node
    raise ValueError(f"unknown prereqTree node {t}")


def canonical(n):
    """Order-insensitive form for comparing two logic trees."""
    if isinstance(n, bool):
        return n
    if n["op"] == "course":
        return {"op": "course", "code": n["code"]}
    args = sorted((canonical(a) for a in n["args"]), key=_key)
    out = {"op": n["op"], "args": args}
    if n["op"] == "n_of":
        out["n"] = n["n"]
    return out


def build() -> dict:
    cfg = json.loads(paths.CONFIG.read_text(encoding="utf-8"))
    ay = cfg["acad_year"]
    ctx = json.loads((paths.DATA / "config" / "student_context.json").read_text(encoding="utf-8"))
    ctx = {k: v for k, v in ctx.items() if not k.startswith("_")}
    raw = paths.raw_dir(ay)
    manifest = _load_json(raw / "manifest.json", {})
    module_list = _load_json(raw / "module_list.json", [])
    overrides = _load_json(paths.MANUAL / "overrides.json", {}).get("courses", {})

    mods = {}
    for f in sorted((raw / "modules").glob("*.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        mods[m["moduleCode"]] = m
    missing = sorted(set(manifest.get("missing_in_ay", [])) - set(mods))
    known = set(mods) | set(missing) | {m["moduleCode"] for m in module_list}
    reasons = manifest.get("reasons", {})
    expanded = set(manifest.get("expanded", mods))

    courses: dict[str, dict] = {}
    literal: dict[str, dict] = {}
    crosscheck = {"match": [], "mismatch": [], "no_tree": []}
    parse_errors = []

    for code, m in mods.items():
        r = Resolver(ctx, known, code)
        lit = {}
        for field in ("prerequisiteRule", "corequisiteRule", "preclusionRule"):
            try:
                lit[field] = parse_rule(m.get(field))
            except Exception as e:  # keep going; surface in report
                lit[field] = None
                parse_errors.append(f"{code} {field}: {e}")
                r.warnings.append(f"could not parse {field}; treated as empty")
        literal[code] = {k: v for k, v in lit.items() if v is not None}

        pre = r.requirement(lit["prerequisiteRule"])
        co = r.requirement(lit["corequisiteRule"])
        blocked, restrict = r.preclusion(lit["preclusionRule"])

        # Cross-check our parse of prerequisiteRule against NUSMods' own prereqTree.
        if m.get("prereqTree"):
            r2 = Resolver(ctx, known, code)
            other = r2.requirement(tree_to_literal(m["prereqTree"]))
            row = {"code": code, "from_rule": render(pre), "from_prereqTree": render(other)}
            if canonical(other) == canonical(pre):
                crosscheck["match"].append(row)
            elif has_mixed_and_or(m.get("prerequisiteRule")):
                # "A AND B OR C" without brackets: follow NUSMods' reading,
                # which is what students see on nusmods.com.
                r.warnings.append("prerequisiteRule mixes AND/OR without brackets; using NUSMods "
                                  f"prereqTree reading. Usual-precedence reading was: {render(pre)}")
                pre = other
                row["resolution"] = "used prereqTree (ambiguous AND/OR)"
                crosscheck["mismatch"].append(row)
            else:
                row["resolution"] = _explain(lit["prerequisiteRule"])
                crosscheck["mismatch"].append(row)
        elif lit["prerequisiteRule"] is not None:
            crosscheck["no_tree"].append(code)

        sems = sorted({s["semester"] for s in m.get("semesterData", [])})
        unavailable = list(restrict)
        if pre is False:
            unavailable.append("prerequisite can never be met by this student (programme/cohort gate)")
        if not sems:
            unavailable.append(f"not offered in any semester in AY{ay}")
        scope = reasons.get(code, "seed")
        courses[code] = {
            "code": code,
            "title": m.get("title"),
            "mc": _mc(m.get("moduleCredit")),
            "offered": sems,
            "exists_in_ay": True,
            "details": "full",
            "scope": "seed" if scope.startswith("seed") else
                     ("prereq_closure" if code in expanded else "referenced_only"),
            "available": not unavailable,
            "unavailable_reasons": unavailable,
            "prereq": _req_block(pre, m.get("prerequisite")),
            "coreq": _req_block(co, m.get("corequisite")),
            "preclusion": {
                "text": render(blocked) if blocked is not False else "none",
                "blocked_if": blocked if blocked is not False else None,
                "courses": courses_in(blocked),
                "mutually_exclusive_with": [],      # filled below
                "source_text": m.get("preclusion"),
            },
            "unlocks": [],                          # filled below
            "department": m.get("department"),
            "faculty": m.get("faculty"),
            "assumptions": r.assumptions,
            "warnings": sorted(set(r.warnings)),
            "overrides": [],
            "source": {
                "url": f"https://nusmods.com/courses/{code}",
                "prerequisiteRule": m.get("prerequisiteRule"),
                "corequisiteRule": m.get("corequisiteRule"),
                "preclusionRule": m.get("preclusionRule"),
            },
        }

    for code in missing:
        courses[code] = {
            "code": code, "title": None, "mc": None, "offered": [],
            "exists_in_ay": False, "details": "stub", "scope": "referenced_only",
            "available": False,
            "unavailable_reasons": [f"no AY{ay} page on NUSMods (retired, renamed or not offered)"],
            "prereq": _req_block(True, None), "coreq": _req_block(True, None),
            "preclusion": {"text": "none", "blocked_if": None, "courses": [],
                           "mutually_exclusive_with": [], "source_text": None},
            "unlocks": [], "department": None, "faculty": None,
            "assumptions": [], "warnings": [], "overrides": [],
            "source": {"url": f"https://nusmods.com/courses/{code}"},
        }

    # Courses named in some rule (e.g. via a CS2040% wildcard) that were not
    # fetched get a light stub from the AY module list, so every code in every
    # tree has an entry.
    listing = {m["moduleCode"]: m for m in module_list}
    referenced = set()
    for c in courses.values():
        referenced.update(c["prereq"]["courses"], c["coreq"]["courses"], c["preclusion"]["courses"])
    for code in sorted(referenced - set(courses)):
        lm = listing.get(code)
        courses[code] = {
            "code": code, "title": lm.get("title") if lm else None, "mc": None,
            "offered": sorted(lm.get("semesters", [])) if lm else [],
            "exists_in_ay": bool(lm), "details": "stub", "scope": "referenced_only",
            "available": False,
            "unavailable_reasons": ["outside fetch scope (details not downloaded)" if lm else
                                    f"no AY{ay} page on NUSMods (retired, renamed or not offered)"],
            "prereq": _req_block(True, None), "coreq": _req_block(True, None),
            "preclusion": {"text": "none", "blocked_if": None, "courses": [],
                           "mutually_exclusive_with": [], "source_text": None},
            "unlocks": [], "department": None, "faculty": None,
            "assumptions": [], "warnings": [], "overrides": [],
            "source": {"url": f"https://nusmods.com/courses/{code}"},
        }

    # Manual overrides (data/manual/overrides.json), applied last and logged.
    for code, ov in overrides.items():
        if code not in courses:
            parse_errors.append(f"override for unknown course {code}")
            continue
        c = courses[code]
        why = ov.get("reason", "(no reason given)")
        if "prereq_logic" in ov:
            logic = simplify(ov["prereq_logic"]) if isinstance(ov["prereq_logic"], dict) else ov["prereq_logic"]
            c["prereq"] = _req_block(logic if logic is not None else True, c["prereq"]["source_text"])
        if "preclusion_courses" in ov:
            args = [{"op": "course", "code": x, "min_grade": "D"} for x in ov["preclusion_courses"]]
            b = simplify({"op": "or", "args": args}) if args else False
            c["preclusion"].update(text=render(b) if b is not False else "none",
                                   blocked_if=b if b is not False else None, courses=courses_in(b))
        for k in ("offered", "mc", "available", "unavailable_reasons"):
            if k in ov:
                c[k] = ov[k]
        c["overrides"].append(why)

    # Derived, cross-course fields.
    unlocks = defaultdict(set)
    mutual = defaultdict(set)
    for code, c in courses.items():
        for x in c["prereq"]["courses"]:
            unlocks[x].add(code)
        for x in c["preclusion"]["courses"]:
            if x != code:
                mutual[code].add(x)
                mutual[x].add(code)
    for code, c in courses.items():
        c["unlocks"] = sorted(unlocks.get(code, ()))
        c["preclusion"]["mutually_exclusive_with"] = sorted(mutual.get(code, ()))

    stats = {
        "courses_total": len(courses),
        "courses_with_full_details": len(mods),
        "stubs_not_in_ay": sum(not c["exists_in_ay"] for c in courses.values()),
        "stubs_outside_fetch_scope": sum(c["exists_in_ay"] and c["code"] not in mods
                                         for c in courses.values()),
        "available_to_student": sum(c["available"] for c in courses.values()),
        "with_prereq": sum(c["prereq"]["logic"] is not None for c in courses.values()),
        "with_preclusion": sum(bool(c["preclusion"]["courses"]) for c in courses.values()),
        "crosscheck_match": len(crosscheck["match"]),
        "crosscheck_mismatch": len(crosscheck["mismatch"]),
        "parse_errors": len(parse_errors),
        "courses_with_warnings": sum(bool(c["warnings"]) for c in courses.values()),
        "courses_with_overrides": sum(bool(c["overrides"]) for c in courses.values()),
    }
    catalog = {
        "schema_version": SCHEMA_VERSION,
        "acad_year": ay,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fetched_at": manifest.get("fetched_at"),
        "source": manifest.get("source"),
        "student_context": ctx,
        "conventions": {
            "logic_nodes": "course | and | or | n_of (at least n of args). See docs/DATA_SCHEMA.md.",
            "prereq.logic": "null = no prerequisite; false = can never be met; else a logic tree",
            "preclusion.blocked_if": "null = never blocked; else the student cannot take the course "
                                     "if this tree is satisfied by their completed courses",
            "min_grade": "minimum grade to count as completed; 'D' unless stated",
            "offered": "1 = Sem 1, 2 = Sem 2, 3 = Special Term I, 4 = Special Term II",
        },
        "stats": stats,
        "courses": dict(sorted(courses.items())),
    }

    out = paths.processed_dir(ay)
    out.mkdir(parents=True, exist_ok=True)
    (out / "catalog.json").write_text(dumps(catalog), encoding="utf-8", newline="\n")
    (out / "rules_literal.json").write_text(
        dumps(dict(sorted(literal.items()))), encoding="utf-8", newline="\n")
    _write_edges(out / "edges.csv", catalog["courses"])
    from .docs import write_courses_md, write_report_md, write_spot_check_md
    write_courses_md(out / "COURSES.md", catalog)
    write_spot_check_md(paths.MANUAL / "SPOT_CHECK.md", catalog)
    write_report_md(out / "PARSE_REPORT.md", catalog, crosscheck, parse_errors)
    from .graph import build_graph, write_graphml
    graph = build_graph(catalog)
    (out / "graph.json").write_text(dumps(graph), encoding="utf-8", newline="\n")
    write_graphml(out / "course_graph.graphml", catalog, graph)
    from .diagrams import write_diagrams
    write_diagrams(out / "diagrams", catalog, graph)
    from .overviews import write_overviews
    write_overviews(paths.ROOT / "docs" / "diagrams", catalog)
    print(f"[build] wrote {out} :: " + ", ".join(f"{k}={v}" for k, v in stats.items()))
    return catalog


def _explain(lit) -> str:
    """Why a rule/tree mismatch is expected (best effort, for the report)."""
    s = json.dumps(lit or {})
    why = []
    if '"subjects"' in s or '"special"' in s:
        why.append("rule has a pre-university-subject alternative that prereqTree drops")
    if '"group"' in s or '"cohort"' in s:
        why.append("rule has a programme/cohort gate that prereqTree drops")
    return "; ".join(why) or "UNEXPLAINED: check by hand"


def dumps(obj, width: int = 110, indent: str = "  ", _lvl: int = 0) -> str:
    """JSON that keeps small objects on one line, e.g.
    {"op": "course", "code": "CS2040S", "min_grade": "D"}, so files stay
    short and diff-friendly while big objects still get one key per line."""
    flat = json.dumps(obj, ensure_ascii=False)
    if len(flat) + len(indent) * _lvl <= width or not isinstance(obj, (dict, list)) or not obj:
        return flat
    pad, inner = indent * _lvl, indent * (_lvl + 1)
    if isinstance(obj, dict):
        items = [f"{inner}{json.dumps(k)}: {dumps(v, width, indent, _lvl + 1)}" for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    items = [f"{inner}{dumps(v, width, indent, _lvl + 1)}" for v in obj]
    return "[\n" + ",\n".join(items) + f"\n{pad}]"


def _req_block(logic, source_text):
    return {
        "text": render(logic),
        "logic": None if logic is True else logic,
        "courses": courses_in(logic),
        "source_text": source_text,
    }


def _write_edges(path, courses):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["course", "relation", "other", "other_in_ay"])
        for code, c in courses.items():
            for rel, xs in (("needs_prereq", c["prereq"]["courses"]),
                            ("needs_coreq", c["coreq"]["courses"]),
                            ("precluded_by", c["preclusion"]["courses"])):
                for x in xs:
                    w.writerow([code, rel, x, courses.get(x, {}).get("exists_in_ay", False)])
