"""Download raw course JSON from the NUSMods API v2.

Scope comes from data/config/scope.json:
  1. seed  = every course whose code starts with a seed prefix and whose level
             is within [seed_level_min, seed_level_max], plus seed_codes.
  2. close = repeatedly add every course named in a fetched course's
             prerequisites (transitive closure).
  3. refs  = add (without expanding) courses named in preclusions and
             corequisites, so a transcript containing them can be checked.

Raw files are written to data/raw/AY<ay>/modules/<CODE>.json with the
per-lesson timetable removed (it is large and not needed). A manifest with
the fetch time and why each course was included goes next to them.

Only the standard library is used, so `python -m m1_data fetch` works on a
fresh Python install.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import paths

API = "https://api.nusmods.com/v2/{ay}"
CODE_RE = re.compile(r"\b([A-Z]{2,4}\d{4}[A-Z]{0,3})\b")
USER_AGENT = "cs3263-project-m1-data/1.0 (NUS course project)"


def _get(url: str, retries: int = 3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def _level(code: str) -> int | None:
    m = re.match(r"[A-Z]+(\d{4})", code)
    return int(m.group(1)) if m else None


def _slim(mod: dict) -> dict:
    """Drop the lesson timetable; keep everything else verbatim."""
    mod = dict(mod)
    mod.pop("timetable", None)
    sems = []
    for s in mod.get("semesterData", []):
        s = dict(s)
        s.pop("timetable", None)
        sems.append(s)
    mod["semesterData"] = sems
    return mod


def _prereq_refs(mod: dict) -> set[str]:
    refs: set[str] = set()

    def walk(t):
        if isinstance(t, str):
            refs.update(CODE_RE.findall(t.split(":")[0].replace("%", "")))
        elif isinstance(t, list):
            for x in t:
                walk(x)
        elif isinstance(t, dict):
            for v in t.values():
                walk(v)

    walk(mod.get("prereqTree"))
    refs.update(CODE_RE.findall(mod.get("prerequisiteRule", "") or ""))
    return refs


def _other_refs(mod: dict, cfg: dict) -> set[str]:
    refs: set[str] = set()
    if cfg.get("fetch_preclusion_refs", True):
        for f in ("preclusionRule", "preclusion"):
            refs.update(CODE_RE.findall(mod.get(f, "") or ""))
    if cfg.get("fetch_corequisite_refs", True):
        for f in ("corequisiteRule", "corequisite"):
            refs.update(CODE_RE.findall(mod.get(f, "") or ""))
    return refs


def fetch(workers: int = 8) -> dict:
    cfg = json.loads(paths.CONFIG.read_text(encoding="utf-8"))
    ay = cfg["acad_year"]
    base = API.format(ay=ay)
    out = paths.raw_dir(ay) / "modules"
    out.mkdir(parents=True, exist_ok=True)

    print(f"[fetch] module list for AY{ay}")
    module_list = _get(f"{base}/moduleList.json") or []
    known = {m["moduleCode"] for m in module_list}
    paths.raw_dir(ay).mkdir(parents=True, exist_ok=True)
    # Every course code in the AY (used to expand wildcards like CS2040%).
    (paths.raw_dir(ay) / "module_list.json").write_text(
        json.dumps(module_list, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
    exclude = set(cfg.get("exclude_codes", []))

    reason: dict[str, str] = {}
    for m in module_list:
        c = m["moduleCode"]
        lvl = _level(c)
        if (any(c.startswith(p) and re.match(p + r"\d", c) for p in cfg["seed_prefixes"])
                and lvl is not None
                and cfg["seed_level_min"] <= lvl <= cfg["seed_level_max"]):
            reason[c] = "seed:prefix"
    for c in cfg.get("seed_codes", []):
        reason.setdefault(c, "seed:explicit")
    for c in exclude:
        reason.pop(c, None)

    fetched: dict[str, dict | None] = {}
    expand = set(reason)            # codes whose prereqs we follow
    frontier = sorted(reason)
    with ThreadPoolExecutor(workers) as pool:
        while frontier:
            todo = [c for c in frontier if c not in fetched]
            print(f"[fetch] {len(todo)} courses (total so far {len(fetched)})")
            for c, mod in zip(todo, pool.map(lambda c: _get(f"{base}/modules/{c}.json"), todo)):
                fetched[c] = _slim(mod) if mod else None
            nxt: set[str] = set()
            for c in todo:
                mod = fetched[c]
                if not mod:
                    continue
                if c in expand:
                    for r in _prereq_refs(mod) - exclude:
                        if r not in reason:
                            reason[r] = f"prereq-of:{c}"
                        expand.add(r)
                        nxt.add(r)
                for r in _other_refs(mod, cfg) - exclude:
                    if r not in reason:
                        reason[r] = f"referenced-by:{c}"
                        nxt.add(r)
            frontier = sorted(nxt - set(fetched))

    missing = sorted(c for c, m in fetched.items() if m is None)
    for c, mod in fetched.items():
        if mod:
            (out / f"{c}.json").write_text(
                json.dumps(mod, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    manifest = {
        "acad_year": ay,
        "source": base,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count_fetched": len(fetched) - len(missing),
        "missing_in_ay": missing,
        "missing_note": "Codes referenced by other courses but with no AY page "
                        "(retired, renamed, or not offered). Kept as stubs.",
        "in_module_list_but_404": sorted(c for c in missing if c in known),
        "reasons": dict(sorted(reason.items())),
        "expanded": sorted(expand & set(fetched)),
    }
    (paths.raw_dir(ay) / "manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8", newline="\n")
    print(f"[fetch] done: {manifest['count_fetched']} fetched, {len(missing)} missing")
    return manifest
