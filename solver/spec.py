from __future__ import annotations

QUERIES = ("eligible", "plan")
OBJECTIVES = ("earliest_graduation", "min_total_mc", "none")
RULE_TYPES = ("before", "in_sem", "apart", "same_sem")
STRENGTHS = ("must", "prefer")

COMMON_FIELDS = ("query", "current_sem", "completed", "programme", "unsupported")
Q1_ONLY_FIELDS = ("target",)
Q2_ONLY_FIELDS = (
    "must_take", "mc_max", "mc_min", "sem_caps", "atap_sems", "rules",
    "objective", "light_sems", "balance_load", "early", "late",
)
ALL_FIELDS = COMMON_FIELDS + Q1_ONLY_FIELDS + Q2_ONLY_FIELDS

MISSING_ORDER = ("completed", "current_sem", "target", "must_take")

DEFAULT_MC_MAX = 20
LAST_SEM = 8


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _absent(spec: dict, key: str) -> bool:
    return spec.get(key) is None


def _is_code_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)


def _check_semester(value, name: str, errors: list[str], problems: list[str]) -> None:
    if not _is_int(value):
        errors.append(f"{name} must be an integer, got {value!r}")
    elif not 1 <= value <= LAST_SEM:
        problems.append(f"{name} is {value}, outside the modelled semesters 1 to {LAST_SEM}")


def _upper_list(codes: list[str]) -> list[str]:
    return _unique([c.strip().upper() for c in codes])


def _unique(items: list) -> list:
    seen = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def validate(spec, catalog=None):
    errors: list[str] = []
    problems: list[str] = []
    warnings: list[str] = []
    missing: list[str] = []

    if not isinstance(spec, dict):
        return ["spec must be a JSON object"], problems, warnings, None, missing

    spec = {key: value for key, value in spec.items() if value is not None or key not in ALL_FIELDS}

    for key in spec:
        if key not in ALL_FIELDS:
            errors.append(f"unknown field '{key}'")

    query = spec.get("query")
    if query not in QUERIES:
        errors.append(f"query must be one of {list(QUERIES)}, got {query!r}")

    if not _absent(spec, "current_sem"):
        _check_semester(spec["current_sem"], "current_sem", errors, problems)
    elif query == "plan":
        missing.append("current_sem")

    if _absent(spec, "completed"):
        missing.append("completed")
    elif not _is_code_list(spec["completed"]):
        errors.append("completed must be a list of course codes")

    programme = spec.get("programme")
    if programme is not None and not isinstance(programme, str):
        errors.append("programme must be a string or left out")

    unsupported = spec.get("unsupported", [])
    if not isinstance(unsupported, list) or not all(isinstance(x, str) for x in unsupported):
        errors.append("unsupported must be a list of strings")

    if query == "eligible":
        for key in Q2_ONLY_FIELDS:
            if key in spec:
                warnings.append(f"field '{key}' belongs to query 'plan', not 'eligible', and was ignored")
        target = spec.get("target")
        if target is None or (isinstance(target, str) and not target.strip()):
            missing.append("target")
        elif not isinstance(target, str):
            errors.append("target must be a course code")
    elif query == "plan":
        if "target" in spec:
            warnings.append("field 'target' belongs to query 'eligible', not 'plan', and was ignored")
        if _absent(spec, "must_take"):
            missing.append("must_take")
        elif not _is_code_list(spec["must_take"]):
            errors.append("must_take must be a list of course codes")
        _validate_plan_fields(spec, errors, problems)

    missing = [field for field in MISSING_ORDER if field in missing]

    if errors:
        return errors, problems, warnings, None, missing

    cleaned = {key: spec[key] for key in COMMON_FIELDS if not _absent(spec, key)}
    if "completed" in cleaned:
        cleaned["completed"] = _upper_list(spec["completed"])
    cleaned["unsupported"] = list(unsupported)
    if query == "eligible":
        if "target" not in missing:
            cleaned["target"] = spec["target"].strip().upper()
    else:
        _clean_plan_fields(spec, cleaned)

    if catalog is not None:
        _check_catalogue(cleaned, catalog, problems, warnings)

    return errors, problems, warnings, cleaned, missing


def _validate_plan_fields(spec: dict, errors: list[str], problems: list[str]) -> None:
    current = spec.get("current_sem")
    current_ok = _is_int(current) and 1 <= current <= LAST_SEM

    mc_max = spec.get("mc_max", DEFAULT_MC_MAX)
    if not _is_int(mc_max) or mc_max <= 0:
        errors.append("mc_max must be a positive integer")
    if "mc_min" in spec:
        mc_min = spec["mc_min"]
        if not _is_int(mc_min) or mc_min < 0:
            errors.append("mc_min must be a non-negative integer")
        elif _is_int(mc_max) and mc_max > 0 and mc_min > mc_max:
            errors.append("mc_min cannot be larger than mc_max")

    if "sem_caps" in spec:
        caps = spec["sem_caps"]
        if not isinstance(caps, dict):
            errors.append("sem_caps must be an object like {\"6\": 0}")
        else:
            for sem, cap in caps.items():
                try:
                    sem_int = int(sem)
                except (TypeError, ValueError):
                    errors.append(f"sem_caps key {sem!r} is not a semester number")
                    continue
                _check_semester(sem_int, f"sem_caps key {sem!r}", errors, problems)
                if not _is_int(cap) or cap < 0:
                    errors.append(f"sem_caps value for semester {sem} must be a non-negative integer")

    if "atap_sems" in spec:
        atap = spec["atap_sems"]
        if not isinstance(atap, list) or not atap:
            errors.append("atap_sems must be a non-empty list of semesters, or left out")
        else:
            for sem in atap:
                _check_semester(sem, "atap_sems entry", errors, problems)
                if current_ok and _is_int(sem) and sem < current:
                    errors.append(f"atap_sems entry {sem} is before current_sem {current}")

    if "rules" in spec:
        rules = spec["rules"]
        if not isinstance(rules, list):
            errors.append("rules must be a list")
        else:
            for i, rule in enumerate(rules):
                _validate_rule(rule, i, errors, problems)

    if "objective" in spec and spec["objective"] not in OBJECTIVES:
        errors.append(f"objective must be one of {list(OBJECTIVES)}, got {spec['objective']!r}")

    if "light_sems" in spec:
        light = spec["light_sems"]
        if not isinstance(light, list):
            errors.append("light_sems must be a list of semesters, optionally including \"last\"")
        else:
            for entry in light:
                if entry == "last":
                    continue
                _check_semester(entry, "light_sems entry", errors, problems)

    if "balance_load" in spec and not isinstance(spec["balance_load"], bool):
        errors.append("balance_load must be true or false")

    for key in ("early", "late"):
        if key in spec and not _is_code_list(spec[key]):
            errors.append(f"{key} must be a list of course codes")


def _validate_rule(rule, index: int, errors: list[str], problems: list[str]) -> None:
    where = f"rules[{index}]"
    if not isinstance(rule, dict):
        errors.append(f"{where} must be an object")
        return
    rule_type = rule.get("type")
    if rule_type not in RULE_TYPES:
        errors.append(f"{where}.type must be one of {list(RULE_TYPES)}, got {rule_type!r}")
        return
    if rule.get("strength") not in STRENGTHS:
        errors.append(f"{where}.strength must be one of {list(STRENGTHS)}, got {rule.get('strength')!r}")
    if rule_type == "in_sem":
        allowed = {"type", "course", "sem", "strength"}
        if not isinstance(rule.get("course"), str) or not rule["course"].strip():
            errors.append(f"{where}.course must be a course code")
        _check_semester(rule.get("sem"), f"{where}.sem", errors, problems)
    else:
        allowed = {"type", "a", "b", "strength"}
        for key in ("a", "b"):
            if not isinstance(rule.get(key), str) or not rule[key].strip():
                errors.append(f"{where}.{key} must be a course code")
        a, b = rule.get("a"), rule.get("b")
        if isinstance(a, str) and isinstance(b, str) and a.strip().upper() == b.strip().upper():
            errors.append(f"{where}: a and b must be different courses")
    for key in rule:
        if key not in allowed:
            errors.append(f"{where} has unknown key '{key}'")


def _clean_plan_fields(spec: dict, cleaned: dict) -> None:
    if not _absent(spec, "must_take"):
        cleaned["must_take"] = _upper_list(spec["must_take"])
    cleaned["mc_max"] = spec.get("mc_max", DEFAULT_MC_MAX)
    cleaned["sem_caps"] = {int(k): v for k, v in spec.get("sem_caps", {}).items()}
    if "mc_min" in spec:
        cleaned["mc_min"] = spec["mc_min"]
    cleaned["objective"] = spec.get("objective", "none")
    cleaned["balance_load"] = spec.get("balance_load", False)
    cleaned["light_sems"] = _unique(list(spec.get("light_sems", [])))
    cleaned["early"] = _upper_list(spec.get("early", []))
    cleaned["late"] = _upper_list(spec.get("late", []))
    rules = []
    for rule in spec.get("rules", []):
        new = dict(rule)
        for key in ("a", "b", "course"):
            if key in new:
                new[key] = new[key].strip().upper()
        if new not in rules:
            rules.append(new)
    cleaned["rules"] = rules
    if "atap_sems" in spec:
        cleaned["atap_sems"] = sorted(set(spec["atap_sems"]))


def _check_catalogue(cleaned: dict, catalog, problems: list[str], warnings: list[str]) -> None:
    for code in cleaned.get("completed", []):
        if code not in catalog:
            warnings.append(f"completed course {code} is not in the catalogue and was ignored")

    named: list[tuple[str, str]] = []
    if cleaned["query"] == "eligible":
        if "target" in cleaned:
            named.append(("target", cleaned["target"]))
    else:
        named += [("must_take", c) for c in cleaned.get("must_take", [])]
        named += [("early", c) for c in cleaned["early"]]
        named += [("late", c) for c in cleaned["late"]]
        for rule in cleaned["rules"]:
            for key in ("a", "b", "course"):
                if key in rule:
                    named.append(("rules", rule[key]))
    for field, code in named:
        if code not in catalog:
            problems.append(f"course {code} (in {field}) is not in the catalogue")
