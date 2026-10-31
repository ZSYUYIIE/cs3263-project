from __future__ import annotations

from ortools.sat.python import cp_model

from solver.explain import conflict_reasons
from solver.model import ATAP_CODE, LAST_SEM, PlanModel

TIME_LIMIT_SECONDS = 60


def solve(pm: PlanModel, expr=None, maximize: bool = False):
    if expr is None:
        pm.model.ClearObjective()
    elif maximize:
        pm.model.Maximize(expr)
    else:
        pm.model.Minimize(expr)
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = 1
    solver.parameters.max_time_in_seconds = TIME_LIMIT_SECONDS
    status = solver.Solve(pm.model)
    return status, solver


def solved(status) -> bool:
    return status == cp_model.OPTIMAL


def no_plan(reasons: list[str], spec: dict) -> dict:
    result = {"status": "NO_PLAN", "reasons": reasons}
    if spec["unsupported"]:
        result["not_applied"] = list(spec["unsupported"])
    return result


GENERIC_REASON = ("no plan satisfies all the rules together (prerequisite order, offering terms, "
                  "MC caps, exclusions and your must-rules conflict)")


def infeasible_reasons(pm: PlanModel, spec: dict, catalog) -> list[str]:
    needed = sum(pm.mc[c] for c in pm.candidates if c in pm.required and c != ATAP_CODE)
    room = sum(pm.cap(s) for s in pm.sems)
    if needed > room:
        return [f"the required courses need {needed} MC but the remaining semesters "
                f"{pm.sems} allow at most {room} MC"]
    return conflict_reasons(spec, catalog) or [GENERIC_REASON]


class Soft:
    def __init__(self, label: str, literal):
        self.label = label
        self.literal = literal

    @property
    def constant(self):
        return isinstance(self.literal, bool)


def rule_literal(pm: PlanModel, rule: dict):
    m = pm.model
    kind = rule["type"]
    done = pm.done
    if kind == "in_sem":
        course, sem = rule["course"], rule["sem"]
        label = f"{course} in semester {sem}"
        if course in done:
            return Soft(label, False)
        return Soft(label, pm.var.get((course, sem), False))
    a, b = rule["a"], rule["b"]
    labels = {
        "before": f"{a} before {b}",
        "apart": f"{a} and {b} in different semesters",
        "same_sem": f"{a} and {b} in the same semester",
    }
    label = labels[kind]
    a_done, b_done = a in done, b in done
    if kind == "before":
        if a_done:
            return Soft(label, True)
        if b_done:
            return Soft(label, False)
    elif kind == "apart":
        if a_done or b_done:
            return Soft(label, True)
    else:
        if a_done and b_done:
            return Soft(label, True)
        if a_done or b_done:
            return Soft(label, False)
    if a not in pm.planned or b not in pm.planned:
        return Soft(label, False)
    flag = m.NewBoolVar(f"pref_{kind}_{a}_{b}")
    m.AddImplication(flag, pm.planned[a])
    m.AddImplication(flag, pm.planned[b])
    if kind == "before":
        m.Add(pm.sem_expr(a) + 1 <= pm.sem_expr(b)).OnlyEnforceIf(flag)
    elif kind == "apart":
        m.Add(pm.sem_expr(a) != pm.sem_expr(b)).OnlyEnforceIf(flag)
    else:
        m.Add(pm.sem_expr(a) == pm.sem_expr(b)).OnlyEnforceIf(flag)
    return Soft(label, flag)


def light_literal(pm: PlanModel, entry, total_other) -> Soft:
    m = pm.model
    fixed_window = pm.spec["objective"] == "none"
    flag = m.NewBoolVar(f"light_{entry}")
    window = LAST_SEM - pm.current + 1
    m.AddImplication(flag, pm.is_last[pm.current - 1].Not())

    def other(semester: int):
        return pm.other_var[semester] if semester in pm.other_var else 0

    if entry == "last":
        for value in range(pm.current, LAST_SEM + 1):
            n = window if fixed_window else value - pm.current + 1
            m.Add(other(value) * n <= total_other - 1).OnlyEnforceIf([flag, pm.is_last[value]])
        return Soft("last semester lighter than average", flag)
    for value in range(pm.current, LAST_SEM + 1):
        n = window if fixed_window else value - pm.current + 1
        if fixed_window:
            if value == pm.current:
                m.Add(other(entry) * n <= total_other - 1).OnlyEnforceIf(flag)
            continue
        m.Add(other(entry) * n <= total_other - 1).OnlyEnforceIf([flag, pm.is_last[value]])
    return Soft(f"semester {entry} lighter than average", flag)


def answer(spec: dict, catalog) -> dict:
    pm = PlanModel(spec, catalog)
    if pm.reasons:
        return no_plan(pm.reasons, spec)
    m = pm.model
    objective = spec["objective"]

    if objective == "earliest_graduation":
        expr = pm.last
    elif objective == "min_total_mc":
        expr = sum(pm.mc[c] * pm.planned[c] for c in pm.candidates)
    else:
        expr = None
    status, solver = solve(pm, expr)
    if status == cp_model.INFEASIBLE:
        return no_plan(infeasible_reasons(pm, spec, catalog), spec)
    if not solved(status):
        return no_plan(["the solver ran out of time before finding a plan"], spec)
    if expr is not None:
        m.Add(expr == int(round(solver.ObjectiveValue())))

    extras = [pm.planned[c] for c in pm.candidates if c not in pm.required]
    if extras:
        status, solver = solve(pm, sum(extras))
        m.Add(sum(extras) == int(round(solver.ObjectiveValue())))

    soft: list[Soft] = []
    for rule in spec["rules"]:
        if rule["strength"] == "prefer":
            soft.append(rule_literal(pm, rule))

    total_other = sum(pm.other_var.values())
    light_entries = [e for e in spec["light_sems"] if e == "last" or e >= pm.current]
    for entry in light_entries:
        soft.append(light_literal(pm, entry, total_other))

    if spec["balance_load"] and pm.other_var:
        peak = m.NewIntVar(0, 200, "peak")
        m.AddMaxEquality(peak, list(pm.other_var.values()))
        status, solver = solve(pm, peak)
        best_peak = int(round(solver.ObjectiveValue()))
        flag = m.NewBoolVar("balance")
        m.Add(peak <= best_peak).OnlyEnforceIf(flag)
        soft.append(Soft("largest semester load is as small as possible", flag))

    wanted = [(code, True) for code in spec["early"]] + [(code, False) for code in spec["late"]]
    for code, is_early in wanted:
        word = "early" if is_early else "late"
        label = f"{code} as {word} as possible"
        if code in pm.done:
            soft.append(Soft(label, True))
            continue
        if code not in pm.required:
            soft.append(Soft(label, False))
            continue
        status, solver = solve(pm, pm.sem_expr(code), maximize=not is_early)
        target = int(round(solver.ObjectiveValue()))
        soft.append(Soft(label, pm.var[(code, target)]))

    variable = [s for s in soft if not s.constant]
    if variable:
        status, solver = solve(pm, sum(s.literal for s in variable), maximize=True)
        m.Add(sum(s.literal for s in variable) == int(round(solver.ObjectiveValue())))

    bonus = []
    for entry in light_entries:
        if entry == "last":
            last_load = m.NewIntVar(0, 200, "last_load")
            for value in range(pm.current, LAST_SEM + 1):
                other = pm.other_var.get(value)
                if other is None:
                    m.Add(last_load == 0).OnlyEnforceIf(pm.is_last[value])
                else:
                    m.Add(last_load == other).OnlyEnforceIf(pm.is_last[value])
            bonus.append(last_load)
        elif entry in pm.other_var:
            bonus.append(pm.other_var[entry])
    if bonus:
        status, solver = solve(pm, sum(bonus))
        m.Add(sum(bonus) == int(round(solver.ObjectiveValue())))

    if objective != "earliest_graduation":
        status, solver = solve(pm, pm.last)
        m.Add(pm.last == int(round(solver.ObjectiveValue())))

    status, solver = solve(pm)
    return build_answer(pm, solver, soft)


def build_answer(pm: PlanModel, solver, soft: list[Soft]) -> dict:
    spec = pm.spec
    last = solver.Value(pm.last)
    placed: dict[int, list[str]] = {}
    for (code, s), v in pm.var.items():
        if solver.Value(v):
            placed.setdefault(s, []).append(code)
    plan, per_semester = {}, {}
    if last >= pm.current:
        for s in range(pm.current, last + 1):
            courses = sorted(placed.get(s, []))
            plan[str(s)] = courses
            per_semester[str(s)] = sum(pm.mc[c] for c in courses)
    met, not_met = [], []
    for item in soft:
        value = item.literal if item.constant else bool(solver.Value(item.literal))
        (met if value else not_met).append(item.label)
    result = {
        "status": "PLAN",
        "objective": spec["objective"],
        "last_semester": last if last >= pm.current else None,
        "plan": plan,
        "mc_per_semester": per_semester,
        "preferences_met": met,
        "preferences_not_met": not_met,
    }
    added = sorted(c for c in pm.candidates if c not in pm.required and solver.Value(pm.planned[c]))
    if added:
        result["added_prerequisites"] = added
    if pm.notes:
        result["notes"] = list(pm.notes)
    if spec["unsupported"]:
        result["not_applied"] = list(spec["unsupported"])
    return result
