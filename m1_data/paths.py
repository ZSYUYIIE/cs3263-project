"""Repository paths. Everything is relative to the repo root."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = DATA / "config" / "scope.json"
MANUAL = DATA / "manual"


def raw_dir(ay: str) -> Path:
    return DATA / "raw" / f"AY{ay}"


def processed_dir(ay: str) -> Path:
    return DATA / "processed" / f"AY{ay}"
