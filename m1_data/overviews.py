"""Hand-laid overview diagrams (diagram-design skill, dependency-graph type).

Positions are fixed by hand (4px grid, crossing-free routes worked out
below); labels and titles come from the catalogue, and every drawn edge is
checked against the catalogue on each build, so a data change that makes a
drawing wrong fails loudly instead of silently going stale.

    docs/diagrams/cs-core-chain.html   the BComp CS path from year 1 to CS3263
    docs/diagrams/exclusion-trap.html  why completing CS3244 makes CS3263 impossible
"""
from __future__ import annotations

from .catalog import satisfied
from .diagrams import (ACCENT, INK, MONO, MUTED, PAPER, SANS, SERIF, SOFT, TREAT, box, esc,
                       page, tag, badge)

W, H = 960, 600


def _node(x, y, name, sub, label, kind="backend", fan=None, w=160, h=56, href=None):
    cx = x + w / 2
    parts = [box(x, y, w, h, kind), tag(x + 8, y + 6, label)]
    if fan is not None:
        parts.append(badge(x + w - 8, y + 8, f"{fan} IN"))
    parts.append(f'<text x="{cx:g}" y="{y + 32}" fill="{INK}" font-size="12" font-weight="600" '
                 f'font-family="{SANS}" text-anchor="middle">{esc(name)}</text>')
    parts.append(f'<text x="{cx:g}" y="{y + 48}" fill="{MUTED}" font-size="9" font-family="{MONO}" '
                 f'text-anchor="middle">{esc(sub)}</text>')
    g = "".join(parts)
    return f'<a href="{href}">{g}</a>' if href else g


def _path(d, accent=False):
    if accent:
        return (f'<path d="{d}" fill="none" stroke="{ACCENT}" stroke-width="1.2" stroke-dasharray="5,4" '
                f'marker-end="url(#arrow-accent)"/>')
    return f'<path d="{d}" fill="none" stroke="{MUTED}" stroke-width="1" marker-end="url(#arrow)"/>'


def _svg(slug, title, desc, body, height=H):
    return (f'<svg viewBox="0 0 {W} {height}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-labelledby="{slug}-title {slug}-desc">'
            f'<title id="{slug}-title">{esc(title)}</title><desc id="{slug}-desc">{esc(desc)}</desc>'
            '<defs>'
            f'<marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
            f'<polygon points="0 0, 8 3, 0 6" fill="{MUTED}"/></marker>'
            f'<marker id="arrow-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
            f'<polygon points="0 0, 8 3, 0 6" fill="{ACCENT}"/></marker>'
            '</defs>'
            f'<rect width="100%" height="100%" fill="{PAPER}"/>' + "\n".join(body) + "</svg>")


def _legend(y, items, note=None):
    out = [f'<line x1="40" y1="{y}" x2="{W - 40}" y2="{y}" stroke="rgba(45,49,66,0.10)" stroke-width="0.8"/>',
           f'<text x="40" y="{y + 16}" fill="{MUTED}" font-size="8" font-family="{MONO}" '
           f'letter-spacing="0.18em">LEGEND</text>']
    x = 40
    for kind, tr, text in items:
        if kind == "box":
            fill, stroke, sw, dash = TREAT[tr]
            d = f' stroke-dasharray="{dash}"' if dash else ""
            out.append(f'<rect x="{x}" y="{y + 28}" width="16" height="12" rx="2" fill="{fill}" '
                       f'stroke="{stroke}" stroke-width="{sw}"{d}/>')
            tx = x + 24
        elif kind == "line":
            out.append(f'<line x1="{x}" y1="{y + 34}" x2="{x + 20}" y2="{y + 34}" stroke="{ACCENT}" '
                       f'stroke-width="1.2" stroke-dasharray="5,4"/>')
            tx = x + 28
        else:
            tx = x
        out.append(f'<text x="{tx}" y="{y + 37}" fill="{MUTED}" font-size="8.5" font-family="{SANS}">'
                   f'{esc(text)}</text>')
        x = int(((tx + len(text) * 8.5 * 0.6 + 32) // 4) * 4)
    if note:
        out.append(f'<text x="40" y="{y + 56}" fill="{MUTED}" font-size="8.5" font-family="{SANS}">'
                   f'{esc(note)}</text>')
    return out


def _check_edges(cat, edges):
    """Each (course, needs) edge must be one option of course's prerequisite."""
    bad = []
    for a, b in edges:
        if b not in cat[a]["prereq"]["courses"]:
            bad.append(f"{a} -> {b}")
    if bad:
        raise ValueError("overview diagram is stale; update m1_data/overviews.py: " + ", ".join(bad))


# ---------------------------------------------------------------------------
def core_chain(cat) -> str:
    """Ranks by longest path from CS3263. Positions (x of left edge, y of top):

        rank0 y=80 : CS3263 400
        rank1 y=200: ST2334 160 | CS2109S 400 | MA1522 720
        rank2 y=320: MA1521 240 | CS2040S 560
        rank3 y=440: CS1101S 520 | CS1231S 720
    """
    edges = [("CS3263", "ST2334"), ("CS3263", "CS2109S"), ("CS3263", "CS2040S"), ("CS3263", "MA1522"),
             ("ST2334", "MA1521"), ("CS2109S", "MA1521"), ("CS2109S", "CS2040S"),
             ("CS2040S", "CS1101S"), ("CS2040S", "CS1231S")]
    _check_edges(cat, edges)
    t = lambda c: cat[c]["title"]
    body = []
    for i, y in enumerate((80, 200, 320, 440)):
        body.append(f'<text x="40" y="{y + 32}" fill="{MUTED}" font-size="8" font-family="{MONO}" '
                    f'letter-spacing="0.18em">RANK {i}</text>')
    # connectors (painted before boxes)
    body += [
        # CS3263 bottom (y=136) fans out at x=432,480,496,528
        _path("M 432,136 V 144 Q 432,152 424,152 H 248 Q 240,152 240,160 V 200"),          # -> ST2334
        _path("M 480,136 V 200"),                                                          # -> CS2109S
        _path("M 496,136 V 156 Q 496,164 504,164 H 660 Q 668,164 668,172 V 320"),          # -> CS2040S
        _path("M 528,136 V 144 Q 528,152 536,152 H 792 Q 800,152 800,160 V 200"),          # -> MA1522
        # rank1 -> rank2 (y=256 -> 320)
        _path("M 292,256 V 320"),                                                          # ST2334 -> MA1521
        _path("M 452,256 V 264 Q 452,272 444,272 H 356 Q 348,272 348,280 V 320"),          # CS2109S -> MA1521
        _path("M 508,256 V 264 Q 508,272 516,272 H 604 Q 612,272 612,280 V 320"),          # CS2109S -> CS2040S
        # rank2 -> rank3 (y=376 -> 440)
        _path("M 600,376 V 440"),                                                          # CS2040S -> CS1101S
        _path("M 668,376 V 384 Q 668,392 676,392 H 792 Q 800,392 800,400 V 440"),          # CS2040S -> CS1231S
    ]
    body += [
        _node(400, 80, "CS3263", "Foundations of AI", "TARGET", fan=0, href="../../data/processed/AY2026-2027/diagrams/CS3263.html"),
        _node(160, 200, "ST2334", "Probability & Statistics", "STATS", fan=1, href="../../data/processed/AY2026-2027/diagrams/ST2334.html"),
        _node(400, 200, "CS2109S", "Intro to AI & ML", "AI", fan=1, href="../../data/processed/AY2026-2027/diagrams/CS2109S.html"),
        _node(720, 200, "MA1522", "Linear Algebra", "MATH", "store", fan=1, href="../../data/processed/AY2026-2027/diagrams/MA1522.html"),
        _node(240, 320, "MA1521", "Calculus for Computing", "MATH", "store", fan=2, href="../../data/processed/AY2026-2027/diagrams/MA1521.html"),
        _node(560, 320, "CS2040S", "Data Structures & Algos", "CORE", fan=2, href="../../data/processed/AY2026-2027/diagrams/CS2040S.html"),
        _node(520, 440, "CS1101S", "Programming Methodology", "CORE", "store", fan=1, href="../../data/processed/AY2026-2027/diagrams/CS1101S.html"),
        _node(720, 440, "CS1231S", "Discrete Structures", "CORE", "store", fan=1, href="../../data/processed/AY2026-2027/diagrams/CS1231S.html"),
    ]
    body += _legend(524, [("box", "backend", "Course with prerequisites"),
                          ("box", "store", "Entry course (nothing needed for an H2 Maths student)"),
                          ("text", None, "N IN = arrows into it here")],
                    note="Arrows show the option a BComp CS Hons student takes from each “any 1 of” group "
                         "(CS2109S, since CS2109HS is closed to CS Hons). Click a box to open its page.")
    svg = _svg("cs-core-chain", "BComp CS path to CS3263",
               "Ranked dependency graph from CS3263 down to year-1 courses; CS2040S and MA1521 are the shared "
               "dependencies, each needed by two courses.", body)
    return page("BComp CS path to CS3263", "Dependency graph · AY2026/27 · M1 data",
                "<h1>From year 1 to CS3263: the BComp CS path</h1>"
                f'<div class="diagram-container">{svg}</div>')


def exclusion_trap(cat) -> str:
    """Positions:

        rank0 y=80 : CS3263 400
        rank1 y=200: other groups 184 (w=192) | "any 1 of" 560
        rank2 y=320: CS3244 (transcript) 200 | CS2109S 480 | CS2109HS 720
    """
    _check_edges(cat, [("CS3263", "CS2109S"), ("CS3263", "CS2109HS"), ("CS3263", "CS2040S"),
                       ("CS3263", "MA1522"), ("CS3263", "ST2334")])
    done = {"CS1101S", "CS1231S", "CS2030S", "CS2040S", "MA1521", "MA1522", "ST2334", "CS3244"}
    blocked = cat["CS2109S"]["preclusion"]["blocked_if"]
    if not satisfied(blocked, done) or cat["CS2109HS"]["available"]:
        raise ValueError("exclusion-trap diagram no longer matches the data; update m1_data/overviews.py")
    body = []
    for label, y in (("WANTS", 80), ("NEEDS", 200), ("OPTIONS", 320)):
        body.append(f'<text x="40" y="{y + 32}" fill="{MUTED}" font-size="8" font-family="{MONO}" '
                    f'letter-spacing="0.18em">{label}</text>')
    body += [
        _path("M 452,136 V 144 Q 452,152 444,152 H 288 Q 280,152 280,160 V 200"),          # -> other groups
        _path("M 508,136 V 144 Q 508,152 516,152 H 632 Q 640,152 640,160 V 200"),          # -> any 1 of
        _path("M 612,256 V 264 Q 612,272 604,272 H 568 Q 560,272 560,280 V 320"),          # -> CS2109S
        _path("M 668,256 V 264 Q 668,272 676,272 H 792 Q 800,272 800,280 V 320"),          # -> CS2109HS
        # the editorial edge: completed CS3244 excludes CS2109S (accent, 1 of 2)
        f'<line x1="360" y1="348" x2="480" y2="348" stroke="{ACCENT}" stroke-width="1.2" '
        f'stroke-dasharray="5,4" marker-end="url(#arrow-accent)"/>',
        # its label (accent, 2 of 2): mask 8px above the stroke
        f'<rect x="394" y="328" width="52" height="12" rx="2" fill="{PAPER}"/>'
        f'<text x="420" y="337" fill="{ACCENT}" font-size="8" font-family="{MONO}" text-anchor="middle" '
        f'letter-spacing="0.06em">EXCLUDES</text>',
    ]
    body += [
        _node(400, 80, "CS3263", "wanted next semester", "TARGET",
              href="../../data/processed/AY2026-2027/diagrams/CS3263.html"),
        _node(184, 200, "3 other groups", "CS2040S · MA1522 · ST2334", "ALL MET", "store", w=192),
        _node(560, 200, "AI foundation", "CS2109S or CS2109HS", "ANY 1 OF", "store"),
        _node(200, 320, "CS3244", "Machine Learning", "COMPLETED", "input"),
        _node(480, 320, "CS2109S", "ruled out by CS3244", "COURSE",
              href="../../data/processed/AY2026-2027/diagrams/CS2109S.html"),
        _node(720, 320, "CS2109HS", "closed to CS Hons", "COURSE", "external",
              href="../../data/processed/AY2026-2027/diagrams/CS2109HS.html"),
        f'<text x="200" y="424" fill="{INK}" font-size="14" font-style="italic" font-family="{SERIF}">'
        "Neither option survives, so no plan reaches CS3263.</text>",
        f'<text x="200" y="444" fill="{SOFT}" font-size="14" font-style="italic" font-family="{SERIF}">'
        "A good assistant says “impossible” and names both reasons instead of inventing a plan.</text>",
    ]
    body += _legend(500, [("box", "backend", "Course"), ("box", "store", "Requirement group"),
                          ("box", "external", "Not open to this student"),
                          ("box", "input", "Already completed"),
                          ("line", None, "Mutually exclusive")],
                    note="The project doc's infeasible example. Student: BComp CS Hons, has CS1101S, CS1231S, "
                         "CS2030S, CS2040S, MA1521, MA1522, ST2334, CS3244.")
    svg = _svg("exclusion-trap", "Why CS3244 blocks CS3263",
               "CS3263 needs CS2109S or CS2109HS; a completed CS3244 excludes CS2109S and CS2109HS is closed to "
               "BComp CS Hons, so CS3263 is unreachable.", body, height=580)
    return page("Why CS3244 blocks CS3263", "Dependency graph · AY2026/27 · M1 data",
                "<h1>The CS3244 trap: one course that makes CS3263 impossible</h1>"
                f'<div class="diagram-container">{svg}</div>')


def write_overviews(out_dir, catalog: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cat = catalog["courses"]
    (out_dir / "cs-core-chain.html").write_text(core_chain(cat), encoding="utf-8", newline="\n")
    (out_dir / "exclusion-trap.html").write_text(exclusion_trap(cat), encoding="utf-8", newline="\n")
    print(f"[overviews] 2 diagrams -> {out_dir}")
