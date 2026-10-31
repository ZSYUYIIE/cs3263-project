from __future__ import annotations

import json
import sys

from m1_data.catalog import Catalog
from m1_data.scope import OUT_OF_SCOPE_MESSAGE, ScopeResult, check_scope

from solver import objectives, q1
from solver.spec import validate


def out_of_scope(reasons: list[str], catalog) -> dict:
    ay = str(catalog.data["acad_year"]).replace("-", "/")
    message = OUT_OF_SCOPE_MESSAGE.format(ay=ay, why="; ".join(reasons))
    return ScopeResult(False, reasons, message).as_answer()


MISSING_PROMPTS = {
    "completed": "the courses you have already completed (say so if there are none)",
    "current_sem": "the semester you are in now (1 to 8)",
    "target": "the course you want to check",
    "must_take": "the courses you still have to take",
}


def missing_info(missing: list[str]) -> dict:
    asked = "; ".join(MISSING_PROMPTS[field] for field in missing)
    return {
        "status": "MISSING_INFO",
        "missing": list(missing),
        "message": f"This cannot be answered yet. Please give: {asked}.",
    }


def prepare(spec, catalog):
    errors, problems, warnings, cleaned, missing = validate(spec, catalog)
    if errors:
        return {"status": "INVALID_SPEC", "errors": errors}, None, warnings
    reasons = list(problems) + check_scope(cleaned).reasons
    if reasons:
        return out_of_scope(reasons, catalog), None, warnings
    if missing:
        return missing_info(missing), None, warnings
    return None, cleaned, warnings


def run(spec, catalog=None) -> dict:
    catalog = catalog or Catalog.load()
    early, cleaned, warnings = prepare(spec, catalog)
    if early is not None:
        return early
    if cleaned["query"] == "eligible":
        result = q1.answer(cleaned, catalog)
    else:
        result = objectives.answer(cleaned, catalog)
    if warnings:
        result["warnings"] = warnings
    return result


def run_text(text: str, catalog=None) -> dict:
    try:
        spec = json.loads(text)
    except json.JSONDecodeError as error:
        return {"status": "INVALID_SPEC", "errors": [f"not valid JSON: {error}"]}
    return run(spec, catalog)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m solver.run path/to/spec.json")
    with open(sys.argv[1], encoding="utf-8") as f:
        print(json.dumps(run_text(f.read()), indent=2))
