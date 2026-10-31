import csv
import json
import random
import subprocess
import sys

import pytest

from m1_data.catalog import Catalog
from experiments.run_ablation import COLUMNS, ENGINES, run_instance, same_answer, summarise
from test_q2 import random_request


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


def test_run_instance_gives_one_row_per_engine(cat):
    rows = run_instance({"id": "x", "spec": random_request(random.Random(3))}, cat, 30)
    assert [r["engine"] for r in rows] == ENGINES
    assert all(set(r) == set(COLUMNS) for r in rows)
    assert rows[0]["nodes"] is None and rows[1]["nodes"] > 0
    assert all(same_answer(r, rows[0]) for r in rows)


def test_summary_counts_agreement(cat):
    rows = []
    for i in range(4):
        rows.extend(run_instance({"id": f"i{i}", "spec": random_request(random.Random(i))}, cat, 30))
    for s in summarise(rows):
        assert s["instances"] == 4 and s["finished"] == 4 and s["agree_with_cpsat"] == "4/4"


def test_timed_out_rows_are_left_out_of_agreement(cat):
    rows = run_instance({"id": "a", "spec": random_request(random.Random(8))}, cat, 30)
    rows[1]["timed_out"] = True
    rows[1]["status"] = "TIMED_OUT"
    summary = {s["engine"]: s for s in summarise(rows)}
    assert summary["plain"]["finished"] == 0 and summary["plain"]["agree_with_cpsat"] == "0/0"
    assert summary["mac"]["finished"] == 1


def test_command_line_writes_csv(tmp_path):
    instances = tmp_path / "instances.json"
    out = tmp_path / "rows.csv"
    data = [{"id": f"c{i}", "spec": random_request(random.Random(20 + i))} for i in range(3)]
    instances.write_text(json.dumps(data), encoding="ascii")
    done = subprocess.run([sys.executable, "-m", "experiments.run_ablation", str(instances),
                           "--limit", "2", "--out", str(out), "--time-limit", "30"],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    assert len(rows) == 2 * len(ENGINES)
    assert list(rows[0]) == COLUMNS
    assert "agree_with_cpsat" in done.stdout
