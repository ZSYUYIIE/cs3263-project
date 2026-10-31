from __future__ import annotations

import argparse
import csv
import json
import statistics
import time

from m1_data.catalog import Catalog

from solver.backtrack import VARIANTS, solve_with_stats
from solver.run import run

COLUMNS = ["id", "engine", "status", "last_semester", "preferences_met",
           "seconds", "nodes", "backtracks", "checks", "timed_out"]
ENGINES = ["cpsat", *VARIANTS]


def row_of(instance_id: str, engine: str, answer: dict, seconds: float, stats: dict | None) -> dict:
    stats = stats or {}
    return {
        "id": instance_id,
        "engine": engine,
        "status": answer["status"],
        "last_semester": answer.get("last_semester"),
        "preferences_met": len(answer["preferences_met"]) if "preferences_met" in answer else None,
        "seconds": round(seconds, 4),
        "nodes": stats.get("nodes"),
        "backtracks": stats.get("backtracks"),
        "checks": stats.get("checks"),
        "timed_out": bool(stats.get("timed_out", False)),
    }


def run_instance(instance: dict, catalog, time_limit: float) -> list[dict]:
    rows = []
    started = time.perf_counter()
    answer = run(instance["spec"], catalog)
    rows.append(row_of(instance["id"], "cpsat", answer, time.perf_counter() - started, None))
    for variant in VARIANTS:
        answer, stats = solve_with_stats(instance["spec"], catalog, variant=variant, time_limit=time_limit)
        rows.append(row_of(instance["id"], variant, answer, stats["seconds"], stats))
    return rows


def same_answer(a: dict, b: dict) -> bool:
    return (a["status"], a["last_semester"], a["preferences_met"]) == (b["status"], b["last_semester"], b["preferences_met"])


def summarise(rows: list[dict]) -> list[dict]:
    reference = {r["id"]: r for r in rows if r["engine"] == "cpsat"}
    summary = []
    for engine in ENGINES:
        mine = [r for r in rows if r["engine"] == engine]
        finished = [r for r in mine if not r["timed_out"]]
        agree = sum(same_answer(r, reference[r["id"]]) for r in finished)
        nodes = [r["nodes"] for r in finished if r["nodes"] is not None]
        summary.append({
            "engine": engine,
            "instances": len(mine),
            "finished": len(finished),
            "median_seconds": round(statistics.median(r["seconds"] for r in finished), 4) if finished else None,
            "median_nodes": statistics.median(nodes) if nodes else None,
            "agree_with_cpsat": f"{agree}/{len(finished)}",
        })
    return summary


def print_table(summary: list[dict]) -> None:
    headers = ["engine", "instances", "finished", "median_seconds", "median_nodes", "agree_with_cpsat"]
    widths = [max(len(h), *(len(str(s[h])) for s in summary)) for h in headers]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    for s in summary:
        print("  ".join(str(s[h]).ljust(w) for h, w in zip(headers, widths)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare CP-SAT with the four backtracking variants.")
    parser.add_argument("instances", help="JSON file: a list of {\"id\": ..., \"spec\": {...}}")
    parser.add_argument("--limit", type=int, default=None, help="use only the first N instances")
    parser.add_argument("--out", default="ablation_rows.csv", help="CSV file for the per-instance rows")
    parser.add_argument("--time-limit", type=float, default=60, help="seconds per backtracking run")
    args = parser.parse_args()

    with open(args.instances, encoding="utf-8") as handle:
        instances = json.load(handle)
    if args.limit is not None:
        instances = instances[: args.limit]

    catalog = Catalog.load()
    rows: list[dict] = []
    for index, instance in enumerate(instances, 1):
        rows.extend(run_instance(instance, catalog, args.time_limit))
        print(f"{index}/{len(instances)} {instance['id']}", flush=True)

    with open(args.out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print_table(summarise(rows))
    print(f"\nrows written to {args.out}")


if __name__ == "__main__":
    main()
