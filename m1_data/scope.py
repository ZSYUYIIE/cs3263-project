"""What the project answers, and what it must decline.

The catalogue is resolved for ONE kind of student (data/config/student_context.json):
BComp (CS) Hons, single major, no second major, no minor, no DDP / double major,
AY2026/27 rules. NUSMods rules depend on programme (CS2109HS, CS2040HS, MA2001
are closed to CS Hons but open to others; some rules mention the CS second
major or minor), so answering for any other student from this data would be
confidently wrong. Such requests get a third answer type, OUT_OF_SCOPE.

    from m1_data.scope import check_scope
    check_scope({"programme": "BComp CS Hons", "second_major": "Mathematics"})
    # -> ScopeResult(in_scope=False, reasons=["second major (Mathematics) is not modelled"], ...)

Used by M3 to label instances and by pipeline B's solver: a spec whose
programme is not CS Hons, or that names any second major / minor / DDP,
returns OUT_OF_SCOPE instead of a plan.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from . import paths

# Spellings of the in-scope programme that may appear in a spec or a request.
CS_HONS = {"0300cshon", "bcomp cs hons", "bcomp (cs) hons", "bcomp cs", "bcomp (cs)",
           "computer science", "cs", "bachelor of computing (computer science) (hons)",
           "bachelor of computing in computer science", "bcomp computer science"}

OUT_OF_SCOPE_MESSAGE = (
    "I can only plan for BComp (CS) Hons single-major students under AY{ay} rules, and this "
    "request is outside that ({why}). Course rules differ by programme and aren't in my data "
    "for your case, so please check with your faculty or academic advisor."
)

# Phrases that put a natural-language request out of scope. M3 can use these to
# sanity-check instance labels; they are not a substitute for the LLM's own judgement.
_PATTERNS = [
    (r"\bddp\b|double degree|double-degree", "a double degree programme (DDP) is not modelled"),
    (r"double major", "a double major is not modelled"),
    (r"second major|2nd major", "a second major is not modelled"),
    (r"\bminor\b", "a minor is not modelled"),
    (r"concurrent degree|\bcdp\b", "a concurrent degree programme is not modelled"),
    (r"\b(business analytics|information systems|information security|computer engineering|"
     r"data science|mathematics major|business|engineering|economics)\s+(student|major|programme|"
     r"degree)\b", "only the BComp (CS) Hons programme is modelled"),
    (r"\b(exchange student|non-graduating|graduate student|master'?s|phd)\b",
     "only undergraduate BComp (CS) Hons students are modelled"),
]


@dataclass
class ScopeResult:
    in_scope: bool
    reasons: list[str] = field(default_factory=list)
    message: str = ""

    def as_answer(self) -> dict:
        """The OUT_OF_SCOPE answer object (see docs/DATA_SCHEMA.md#scope)."""
        return {"status": "OUT_OF_SCOPE" if not self.in_scope else "IN_SCOPE",
                "reasons": self.reasons, "message": self.message}


def _ay() -> str:
    cfg = json.loads(paths.CONFIG.read_text(encoding="utf-8"))
    return cfg["acad_year"].replace("-", "/")


def _ay_norm(v) -> str:
    """'AY2026/27', '2026-2027', '2026/2027' -> '2026/2027'."""
    m = re.search(r"(\d{4})\s*[/-]\s*(\d{2,4})", str(v))
    if not m:
        return _norm(v)
    a, b = m.group(1), m.group(2)
    return f"{a}/{a[:2] + b if len(b) == 2 else b}"


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s).strip().lower())


def check_scope(profile: dict | None) -> ScopeResult:
    """Structured check, e.g. on pipeline B's spec.

    Recognised keys (all optional): programme, second_major, minor, ddp,
    double_major, program_type, acad_year. Unknown programme -> out of scope.
    """
    profile = profile or {}
    reasons = []
    prog = profile.get("programme", profile.get("program"))
    if prog not in (None, "") and _norm(prog) not in CS_HONS:
        reasons.append(f"programme '{prog}' is not BComp (CS) Hons")
    for key, label in (("second_major", "second major"), ("double_major", "double major"),
                       ("minor", "minor"), ("ddp", "double degree programme (DDP)")):
        v = profile.get(key)
        if v not in (None, False, "", [], "none", "None"):
            what = f" ({', '.join(v) if isinstance(v, list) else v})" if v is not True else ""
            reasons.append(f"{label}{what} is not modelled")
    pt = profile.get("program_type")
    if pt not in (None, "") and _norm(pt) != "undergraduate degree":
        reasons.append(f"programme type '{pt}' is not modelled (undergraduate only)")
    ay = profile.get("acad_year")
    if ay not in (None, "") and _ay_norm(ay) != _ay():
        reasons.append(f"academic year {ay} is not modelled (data is AY{_ay()})")
    return _result(reasons)


def scan_request(text: str) -> ScopeResult:
    """Keyword screen of a natural-language request. Conservative and only a
    hint for labelling: it flags phrases, it does not understand them."""
    t = text.lower()
    reasons = []
    for pat, why in _PATTERNS:
        if re.search(pat, t) and why not in reasons:
            reasons.append(why)
    return _result(reasons)


def _result(reasons) -> ScopeResult:
    if not reasons:
        return ScopeResult(True)
    return ScopeResult(False, reasons, OUT_OF_SCOPE_MESSAGE.format(ay=_ay(), why="; ".join(reasons)))
