from __future__ import annotations

from ortools.sat.python import cp_model

from solver.model import PlanModel

GROUP_ORDER = ("rule", "prereq", "caps", "mc_min", "offering", "preclusion", "atap")
TIME_LIMIT_SECONDS = 20


def order_key(key: tuple):
    return (GROUP_ORDER.index(key[0]), key[1:])


def build(spec: dict, catalog):
    pm = PlanModel(spec, catalog, explain=True)
    if pm.reasons:
        return None
    return pm


def solve_assuming(pm: PlanModel, keys):
    pm.model.ClearAssumptions()
    pm.model.AddAssumptions([pm.guards[key] for key in keys])
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = 1
    solver.parameters.max_time_in_seconds = TIME_LIMIT_SECONDS
    return solver.Solve(pm.model), solver


def holds_together(spec: dict, catalog, keys) -> bool:
    pm = build(spec, catalog)
    status, _ = solve_assuming(pm, keys)
    return status in (cp_model.OPTIMAL, cp_model.FEASIBLE)


def find_conflict(spec: dict, catalog):
    pm = build(spec, catalog)
    if pm is None:
        return None
    keys = sorted(pm.guards, key=order_key)
    status, solver = solve_assuming(pm, keys)
    if status != cp_model.INFEASIBLE:
        return None
    by_index = {pm.guards[key].Index(): key for key in keys}
    core = sorted((by_index[i] for i in solver.SufficientAssumptionsForInfeasibility()), key=order_key)
    if not core:
        return None
    for key in list(core):
        trial = [k for k in core if k != key]
        status, _ = solve_assuming(pm, trial)
        if status == cp_model.INFEASIBLE:
            core = trial
    return core


def rule_text(rule: dict) -> str:
    kind = rule["type"]
    if kind == "in_sem":
        return f'{rule["course"]} in semester {rule["sem"]}'
    a, b = rule["a"], rule["b"]
    if kind == "before":
        return f"{a} before {b}"
    if kind == "apart":
        return f"{a} and {b} in different semesters"
    return f"{a} and {b} in the same semester"


def caps_text(spec: dict) -> str:
    parts = [f'at most {spec["mc_max"]} MC per semester']
    blocked = sorted(s for s, cap in spec["sem_caps"].items() if cap == 0)
    limited = sorted((s, cap) for s, cap in spec["sem_caps"].items() if cap != 0)
    if blocked:
        parts.append("semesters " + ", ".join(str(s) for s in blocked) + " blocked")
    if limited:
        parts.append("; ".join(f"semester {s} at most {cap} MC" for s, cap in limited))
    return "the MC limits (" + "; ".join(parts) + ")"


def describe(key: tuple, spec: dict) -> str:
    kind = key[0]
    if kind == "rule":
        return "your rule: " + rule_text(spec["rules"][key[1]])
    if kind == "prereq":
        return f"the prerequisites of {key[1]}"
    if kind == "caps":
        return caps_text(spec)
    if kind == "mc_min":
        return f'your minimum of {spec["mc_min"]} MC in every semester that has courses'
    if kind == "offering":
        return "the semesters in which the courses are offered"
    if kind == "preclusion":
        return "the course exclusions (courses that cannot be taken together)"
    return "the ATAP rules (allowed semesters, not the last semester, at most 8 MC beside it)"


def conflict_reasons(spec: dict, catalog) -> list[str]:
    core = find_conflict(spec, catalog)
    if not core:
        return []
    listed = "; ".join(describe(key, spec) for key in core)
    return [f"these cannot all hold together with the courses you must take: {listed}"]
