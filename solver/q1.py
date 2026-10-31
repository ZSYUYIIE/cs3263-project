from __future__ import annotations


def term_of(semester: int) -> int:
    return 1 if semester % 2 == 1 else 2


def answer(spec: dict, catalog) -> dict:
    semester = spec.get("current_sem")
    if semester is None:
        return answer_without_semester(spec, catalog)
    ok, reasons = catalog.can_take(spec["target"], spec["completed"], semester=term_of(semester))
    result = {
        "status": "ELIGIBLE" if ok else "NOT_ELIGIBLE",
        "target": spec["target"],
        "semester": semester,
        "reasons": reasons,
    }
    add_reachability(result, spec, catalog, ok)
    return result


def add_reachability(result: dict, spec: dict, catalog, ok: bool) -> None:
    if not ok and spec["target"] not in spec["completed"]:
        reachable, note = catalog.reachable(spec["target"], spec["completed"])
        result["can_still_become_eligible"] = reachable
        if not reachable:
            result["never_eligible_because"] = note
    if spec["unsupported"]:
        result["not_applied"] = list(spec["unsupported"])


def answer_without_semester(spec: dict, catalog) -> dict:
    target = spec["target"]
    ok, reasons = catalog.can_take(target, spec["completed"])
    offered_in = [term for term in catalog[target]["offered"] if term in (1, 2)]
    if ok and not offered_in:
        ok = False
        reasons = ["not offered in Semester 1 or Semester 2"]
    result = {
        "status": "ELIGIBLE" if ok else "NOT_ELIGIBLE",
        "target": target,
        "reasons": reasons,
    }
    if ok:
        result["offered_in"] = offered_in
        if len(offered_in) == 2:
            result["notes"] = ["no semester given; the course is offered in both Semester 1 and Semester 2, so the term does not matter"]
        else:
            result["notes"] = [f"no semester given; the course is offered in Semester {offered_in[0]} only, so it can only be taken in that term"]
    add_reachability(result, spec, catalog, ok)
    return result
