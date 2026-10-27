"""Parser for NUSMods rule strings (prerequisiteRule / preclusionRule /
corequisiteRule) into a literal, lossless JSON tree.

Grammar (informal; precedence low -> high: IF..THEN, OR, AND):

    expr     := or_expr ["THEN" expr]          (IF..THEN binds loosest)
    or_expr  := and_expr ("OR" and_expr)*
    and_expr := unary ("AND" unary)*
    unary    := "(" expr ")" | atom
    atom     := "PROGRAM_TYPES" OP name ("," name)*      name may contain spaces
              | "COURSES"  ["(" n ")"] item ("," item)*      item = CODE[%][:GRADE]
              | "SUBJECTS" ["(" n ")"] item ("," item)*      item = KEY:GRADE (A-level etc.)
              | "UNITS" "(" n ")"  |  "GPA" "(" x ")"
              | "COHORT_YEARS" OP value ("," value)*         value = S:2017 | E:2016 ...
              | GROUP OP ["(" n ")"] value ("," value)*      GROUP = PROGRAMS | 2ND_MAJOR
                                                             | MINOR | SPECIAL_PROGRAMME
              | "SPECIAL" OP "quoted string"
    OP       := MUST_BE_IN | MUST_NOT_BE_IN | IF_IN | IF_NOT_IN

Output nodes (literal: nothing is evaluated or simplified here):

    {"op": "and" | "or", "args": [...]}
    {"op": "if", "cond": node, "then": node}
    {"op": "program_type", "rule": OP, "values": ["Undergraduate Degree", ...]}
    {"op": "courses", "n": int | None, "items": [{"code", "pattern", "min_grade"}]}
    {"op": "subjects", "n": int | None, "items": [{"subject", "grade"}]}
    {"op": "units", "min": float} / {"op": "gpa", "min": float}
    {"op": "cohort", "rule": OP, "values": [...]}
    {"op": "group", "group": "PROGRAMS"|..., "rule": OP, "n": int|None, "values": [...]}
    {"op": "special", "rule": OP, "value": str}

`n` is None when the source wrote no "(n)"; resolve.py decides what that means.
"""
from __future__ import annotations

import re

GROUPS = {"PROGRAMS", "2ND_MAJOR", "MINOR", "SPECIAL_PROGRAMME"}
OPS = {"MUST_BE_IN", "MUST_NOT_BE_IN", "IF_IN", "IF_NOT_IN"}
STOP = {"AND", "OR", "THEN", ")", None}

_TOKEN = re.compile(r'\s*(?:(\()|(\))|(,)|("[^"]*")|([^\s(),"]+))')


class RuleParseError(ValueError):
    pass


def tokenize(s: str) -> list[str]:
    toks, pos = [], 0
    s = s.strip()
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m or m.end() == pos:
            raise RuleParseError(f"cannot tokenize at {pos}: {s[pos:pos+20]!r}")
        toks.append(next(g for g in m.groups() if g is not None))
        pos = m.end()
        while pos < len(s) and s[pos].isspace():
            pos += 1
    return toks


class _Parser:
    def __init__(self, text: str):
        self.text = text
        self.t = tokenize(text)
        self.i = 0
        self._bare_and: set[int] = set()   # ids of AND nodes not wrapped in ()
        self.mixed = False                 # saw "A AND B OR C" with no brackets

    # -- helpers ---------------------------------------------------------
    def peek(self, k: int = 0):
        j = self.i + k
        return self.t[j] if j < len(self.t) else None

    def take(self, expect: str | None = None) -> str:
        tok = self.peek()
        if tok is None or (expect is not None and tok != expect):
            raise RuleParseError(f"expected {expect!r}, got {tok!r} at token {self.i} in: {self.text}")
        self.i += 1
        return tok

    def count(self):
        """Optional "(n)" right after a keyword."""
        if self.peek() == "(" and self.peek(2) == ")" and re.fullmatch(r"\d+(\.\d+)?", self.peek(1) or ""):
            self.take("(")
            n = self.take()
            self.take(")")
            return float(n) if "." in n else int(n)
        return None

    def csv_items(self) -> list[str]:
        items = [self.take()]
        while self.peek() == ",":
            self.take(",")
            items.append(self.take())
        return items

    # -- grammar ---------------------------------------------------------
    def parse(self):
        node = self.expr()
        if self.peek() is not None:
            raise RuleParseError(f"trailing tokens {self.t[self.i:]} in: {self.text}")
        return node

    def expr(self):
        node = self.or_expr()
        if self.peek() == "THEN":
            self.take("THEN")
            node = {"op": "if", "cond": node, "then": self.expr()}
        return node

    def or_expr(self):
        args = [self.and_expr()]
        while self.peek() == "OR":
            self.take("OR")
            args.append(self.and_expr())
        if len(args) > 1 and any(id(a) in self._bare_and for a in args):
            self.mixed = True
        return args[0] if len(args) == 1 else {"op": "or", "args": args}

    def and_expr(self):
        args = [self.unary()]
        while self.peek() == "AND":
            self.take("AND")
            args.append(self.unary())
        if len(args) == 1:
            return args[0]
        node = {"op": "and", "args": args}
        self._bare_and.add(id(node))
        return node

    def unary(self):
        if self.peek() == "(":
            self.take("(")
            node = self.expr()
            self.take(")")
            self._bare_and.discard(id(node))   # brackets make it unambiguous
            return node
        return self.atom()

    def atom(self):
        kw = self.take()
        if kw == "PROGRAM_TYPES":
            rule = self.take()
            names, words = [], []
            while self.peek() not in STOP:
                tok = self.take()
                if tok == ",":
                    names.append(" ".join(words))
                    words = []
                else:
                    words.append(tok)
            names.append(" ".join(words))
            return {"op": "program_type", "rule": rule, "values": [n for n in names if n]}
        if kw == "COURSES":
            n = self.count()
            items = []
            for raw in self.csv_items():
                code, _, grade = raw.partition(":")
                code = code.upper()
                items.append({"code": code.rstrip("%"), "pattern": code.endswith("%"),
                              "min_grade": grade or None})
            return {"op": "courses", "n": n, "items": items}
        if kw == "SUBJECTS":
            n = self.count()
            items = []
            for raw in self.csv_items():
                subj, _, grade = raw.partition(":")
                items.append({"subject": subj, "grade": grade or None})
            return {"op": "subjects", "n": n, "items": items}
        if kw in ("UNITS", "GPA"):
            n = self.count()
            if n is None:
                raise RuleParseError(f"{kw} without value in: {self.text}")
            return {"op": kw.lower(), "min": n}
        if kw == "COHORT_YEARS":
            rule = self.take()
            return {"op": "cohort", "rule": rule, "values": self.csv_items()}
        if kw in GROUPS:
            rule = self.take()
            if rule not in OPS:
                raise RuleParseError(f"unknown operator {rule!r} in: {self.text}")
            n = self.count()
            return {"op": "group", "group": kw, "rule": rule, "n": n, "values": self.csv_items()}
        if kw == "SPECIAL":
            rule = self.take()
            return {"op": "special", "rule": rule, "value": self.take().strip('"')}
        raise RuleParseError(f"unknown keyword {kw!r} in: {self.text}")


def parse_rule(text: str | None):
    """Parse one rule string. Returns None for empty input.

    Uses the usual precedence (AND binds tighter than OR)."""
    if not text or not text.strip():
        return None
    return _Parser(text).parse()


def has_mixed_and_or(text: str | None) -> bool:
    """True if the rule writes "A AND B OR C" with no brackets. NUSMods and the
    usual-precedence reading can disagree on such rules."""
    if not text or not text.strip():
        return False
    p = _Parser(text)
    p.parse()
    return p.mixed
