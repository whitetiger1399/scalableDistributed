#!/usr/bin/env python3
"""Build polished SVG architecture figures for the Cassandra report.

Run from the repository root. PNG rendering is performed separately because
macOS Quick Look is used as the local SVG rasterizer.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
ICON_DIR = HERE / "icons"
SVG_DIR = HERE / "svg"

W, H = 1800, 1100
NAVY = "#17324D"
TEXT = "#243746"
MUTED = "#607386"
LINE = "#A8BAC8"
PANEL = "#F6F9FC"
BLUE = "#1779BA"
LIGHT_BLUE = "#EAF5FB"
PURPLE = "#7656A5"
LIGHT_PURPLE = "#F0EBF8"
GREEN = "#2E8B68"
LIGHT_GREEN = "#EAF7F1"
RED = "#C43D4B"
LIGHT_RED = "#FCECEF"
AMBER = "#C47A14"
LIGHT_AMBER = "#FFF4DD"


def icon_symbols() -> str:
    symbols = []
    for name in ("apachecassandra", "docker", "apple", "python", "ubuntu"):
        raw = (ICON_DIR / f"{name}.svg").read_text()
        viewbox = re.search(r'viewBox="([^"]+)"', raw).group(1)
        inner = re.search(r"<svg[^>]*>(.*)</svg>", raw, re.S).group(1)
        inner = re.sub(r"<title>.*?</title>", "", inner, flags=re.S)
        symbols.append(f'<symbol id="icon-{name}" viewBox="{viewbox}">{inner}</symbol>')
    symbols.append(
        '<symbol id="icon-windows" viewBox="0 0 24 24">'
        '<path fill="#0078D4" d="M1 3.4 10.4 2v9.1H1zm10.7-1.5L23 0.3v10.8H11.7zM1 12.4h9.4v9.1L1 20.2zm10.7 0H23v10.8l-11.3-1.6z"/>'
        '</symbol>'
    )
    return "".join(symbols)


def defs() -> str:
    return f"""
    <defs>
      {icon_symbols()}
      <marker id="arrow-blue" markerUnits="userSpaceOnUse" markerWidth="18" markerHeight="18" refX="1" refY="9" viewBox="0 0 18 18" orient="auto" overflow="visible"><path d="M1,2 L16,9 L1,16 z" fill="#D9EEF9" stroke="{BLUE}" stroke-width="1.8" stroke-linejoin="round"/></marker>
      <marker id="arrow-purple" markerUnits="userSpaceOnUse" markerWidth="18" markerHeight="18" refX="1" refY="9" viewBox="0 0 18 18" orient="auto" overflow="visible"><path d="M1,2 L16,9 L1,16 z" fill="#EBE4F5" stroke="{PURPLE}" stroke-width="1.8" stroke-linejoin="round"/></marker>
      <marker id="arrow-green" markerUnits="userSpaceOnUse" markerWidth="18" markerHeight="18" refX="1" refY="9" viewBox="0 0 18 18" orient="auto" overflow="visible"><path d="M1,2 L16,9 L1,16 z" fill="#DFF2EA" stroke="{GREEN}" stroke-width="1.8" stroke-linejoin="round"/></marker>
      <marker id="arrow-gray" markerUnits="userSpaceOnUse" markerWidth="18" markerHeight="18" refX="1" refY="9" viewBox="0 0 18 18" orient="auto" overflow="visible"><path d="M1,2 L16,9 L1,16 z" fill="#E8EEF2" stroke="{MUTED}" stroke-width="1.8" stroke-linejoin="round"/></marker>
      <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="4" stdDeviation="7" flood-color="#17324D" flood-opacity="0.12"/></filter>
      <style>
        text {{ font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; fill:{TEXT}; }}
        .title {{ font-size:42px; font-weight:750; fill:{NAVY}; }}
        .subtitle {{ font-size:20px; fill:{MUTED}; }}
        .section {{ font-size:24px; font-weight:700; fill:{NAVY}; }}
        .label {{ font-size:19px; font-weight:650; }}
        .body {{ font-size:17px; }}
        .small {{ font-size:15px; fill:{MUTED}; }}
        .tiny {{ font-size:13px; fill:{MUTED}; }}
      </style>
    </defs>"""


def canvas(title: str, subtitle: str, content: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
    {defs()}
    <rect width="{W}" height="{H}" fill="#FFFFFF"/>
    <rect x="0" y="0" width="{W}" height="12" fill="{BLUE}"/>
    <text x="80" y="74" class="title">{escape(title)}</text>
    <text x="80" y="110" class="subtitle">{escape(subtitle)}</text>
    {content}
    <text x="1720" y="1068" text-anchor="end" class="tiny">Cassandra client-centric consistency experiment • RF=3 • dc1</text>
    </svg>'''


def rect(x, y, w, h, fill="#FFFFFF", stroke=LINE, radius=18, sw=2, shadow=False, dash=None) -> str:
    attrs = f'filter="url(#shadow)"' if shadow else ""
    dash_attr = f'stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {attrs} {dash_attr}/>'


def txt(x, y, value, cls="body", anchor="start", fill=None, weight=None) -> str:
    attrs = ""
    if fill:
        attrs += f' fill="{fill}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}"{attrs}>{escape(str(value))}</text>'


def lines(x, y, values, cls="body", anchor="start", gap=25) -> str:
    body = [f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">']
    for i, value in enumerate(values):
        body.append(f'<tspan x="{x}" dy="{0 if i == 0 else gap}">{escape(str(value))}</tspan>')
    body.append("</text>")
    return "".join(body)


def icon(name, x, y, size) -> str:
    colors = {
        "apachecassandra": "#1287B1", "docker": "#2496ED", "windows": "#0078D4",
        "apple": "#000000", "python": "#3776AB", "ubuntu": "#E95420",
    }
    return f'<use href="#icon-{name}" x="{x}" y="{y}" width="{size}" height="{size}" fill="{colors.get(name, TEXT)}"/>'


def csv_icon(x, y, size=56) -> str:
    """Compact document/grid mark used for exported CSV evidence."""
    w, h = size * 0.78, size
    fold = size * 0.22
    rows = []
    for offset in (0.48, 0.64, 0.80):
        rows.append(f'<line x1="{x+size*0.12}" y1="{y+size*offset}" x2="{x+w-size*0.10}" y2="{y+size*offset}" stroke="{GREEN}" stroke-width="1.8"/>')
    for offset in (0.32, 0.53):
        rows.append(f'<line x1="{x+size*offset}" y1="{y+size*0.43}" x2="{x+size*offset}" y2="{y+size*0.84}" stroke="{GREEN}" stroke-width="1.6"/>')
    return "".join([
        f'<path d="M{x},{y} H{x+w-fold} L{x+w},{y+fold} V{y+h} H{x} Z" fill="#FFFFFF" stroke="{GREEN}" stroke-width="2.4"/>',
        f'<path d="M{x+w-fold},{y} V{y+fold} H{x+w}" fill="none" stroke="{GREEN}" stroke-width="2.2"/>',
        f'<text x="{x+w/2}" y="{y+size*0.34}" text-anchor="middle" font-size="{size*0.18}" font-weight="800" fill="{GREEN}">CSV</text>',
        *rows,
    ])


def arrow(x1, y1, x2, y2, color=BLUE, dash=None, width=4, marker=True) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    marker_attr = f' marker-end="url(#arrow-{color_name(color)})"' if marker else ""
    return f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"{dash_attr}{marker_attr}/>'


def curved(path, color=BLUE, dash=None, width=4, marker=True) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    marker_attr = f' marker-end="url(#arrow-{color_name(color)})"' if marker else ""
    return f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"{dash_attr}{marker_attr}/>'


def color_name(color: str) -> str:
    return {BLUE: "blue", PURPLE: "purple", GREEN: "green", MUTED: "gray"}.get(color, "gray")


def node(x, y, name, selected=False, status="UP / NORMAL") -> str:
    stroke = BLUE if selected else LINE
    fill = LIGHT_BLUE if selected else "#FFFFFF"
    badge = f'<rect x="{x+125}" y="{y+14}" width="112" height="26" rx="13" fill="{BLUE}"/><text x="{x+181}" y="{y+33}" text-anchor="middle" font-size="13" font-weight="700" fill="#FFFFFF">COORDINATOR</text>' if selected else ""
    return "".join([
        rect(x, y, 250, 125, fill, stroke, 18, 3 if selected else 2, True),
        icon("apachecassandra", x+22, y+28, 58),
        txt(x+95, y+50, name, "label"),
        txt(x+95, y+78, "Apache Cassandra 5.0.9", "tiny"),
        txt(x+95, y+103, status, "tiny", fill=GREEN, weight="700"), badge,
    ])


def legend(y=1008) -> str:
    return "".join([
        arrow(85, y, 145, y, BLUE, width=4), txt(160, y+6, "CQL request / response (9042)", "small"),
        arrow(460, y, 520, y, PURPLE, width=4), txt(535, y+6, "Replica / internode traffic (7000/7001)", "small"),
        arrow(960, y, 1020, y, MUTED, dash="10 8", width=3), txt(1035, y+6, "Orchestration / fault control", "small"),
        arrow(1395, y, 1455, y, GREEN, width=4), txt(1470, y+6, "Evidence output", "small"),
    ])


def cluster_core(x=380, y=545, selected="n2") -> str:
    origin_x = x
    positions = {"n1": x+150, "n2": x+455, "n3": x+760}
    out = [rect(x, y-70, 1090, 360, PANEL, "#8FA7B8", 24, 2), txt(x+30, y-30, "Docker network: lab", "section")]
    # Replica routes sit behind the node cards and use broad, symmetric arcs.
    sx = positions[selected] + 125
    for name, node_x in positions.items():
        if name != selected:
            tx = node_x + 125
            out.append(curved(f"M{sx},{y-3} C{sx},{y-78} {tx},{y-78} {tx},{y-18}", PURPLE, width=4))
    for name, node_x in positions.items():
        out.append(node(node_x, y, name, name == selected))
        out.append(rect(node_x+42, y+162, 166, 55, "#FFFFFF", LINE, 12, 2))
        out.append(txt(node_x+125, y+195, f"{name}-data volume", "small", "middle"))
        out.append(arrow(node_x+125, y+127, node_x+125, y+144, MUTED, dash="7 6", width=2))
    out.append(txt(origin_x+545, y+252, "RF=3 • NetworkTopologyStrategy • one datacenter (dc1)", "small", "middle"))
    return "".join(out)


def windows_figure() -> str:
    c = [
        rect(55, 140, 1690, 820, "#FCFDFE", "#6F8EA5", 28, 3),
        icon("windows", 85, 166, 54), txt(155, 202, "Windows 10/11 host", "section"),
        rect(100, 235, 1600, 700, "#FFF8F3", "#E95420", 24, 3),
        icon("ubuntu", 128, 260, 48), txt(192, 292, "WSL2 Linux environment (Ubuntu)", "section"),
        rect(145, 330, 1510, 570, "#F4FAFF", "#2496ED", 24, 3),
        icon("docker", 172, 352, 62), txt(248, 391, "Docker Desktop / Docker Engine", "section"),
        rect(180, 395, 285, 150, LIGHT_GREEN, GREEN, 18, 2, True), icon("python", 205, 420, 55),
        txt(278, 443, "Host controller", "label"), lines(278, 473, ["run_randomized.py", "Docker Compose + faults"], "small"),
        rect(890, 385, 280, 150, "#FFFFFF", BLUE, 18, 3, True), icon("python", 915, 413, 55),
        txt(988, 436, "client container", "label"), lines(988, 466, ["Cassandra Python driver", "CQL + routing evidence"], "small"),
        cluster_core(450, 600, "n2"),
        arrow(465, 470, 872, 470, MUTED, width=3),
        arrow(1030, 537, 1030, 582, BLUE, width=4),
        rect(1495, 405, 150, 115, LIGHT_GREEN, GREEN, 15, 2, True), txt(1570, 441, "results/", "label", "middle"),
        txt(1570, 491, "JSON • logs", "small", "middle"), txt(1570, 516, "CSV • hashes", "small", "middle"),
        curved("M465,420 C760,345 1260,350 1477,455", GREEN, width=4),
        rect(650, 342, 490, 36, "#F4FAFF", "#F4FAFF", 10, 0),
        txt(895, 368, "Linux containers and named volumes run inside Docker Desktop", "small", "middle"),
        legend(),
    ]
    return canvas("Windows deployment architecture", "Windows host → WSL2 → Docker Desktop → three-node Cassandra cluster", "".join(c))


def macos_figure() -> str:
    c = [
        rect(55, 140, 1690, 820, "#FCFDFE", "#566774", 28, 3),
        icon("apple", 85, 164, 56), txt(155, 202, "macOS host", "section"),
        rect(105, 240, 330, 170, LIGHT_GREEN, GREEN, 18, 2, True), icon("python", 135, 270, 60),
        txt(215, 292, "Experiment controller", "label"), lines(215, 322, ["Terminal / IDE", "run_randomized.py", "Docker Compose + faults"], "small"),
        rect(475, 235, 1225, 650, "#F4FAFF", "#2496ED", 24, 3),
        icon("docker", 505, 258, 64), txt(585, 298, "Docker Desktop managed Linux VM", "section"),
        rect(940, 350, 280, 145, "#FFFFFF", BLUE, 18, 3, True), icon("python", 965, 375, 55),
        txt(1038, 398, "client container", "label"), lines(1038, 428, ["Python driver", "mounted repository"], "small"),
        cluster_core(500, 600, "n2"),
        arrow(435, 325, 457, 325, MUTED, width=3),
        arrow(1080, 497, 1080, 582, BLUE, width=4),
        rect(105, 635, 330, 150, LIGHT_GREEN, GREEN, 18, 2, True),
        txt(270, 674, "Bind-mounted workspace", "label", "middle"), lines(270, 707, ["results/ evidence", "report exports + figures"], "small", "middle"),
        curved("M940,430 C700,430 610,610 453,685", GREEN, width=4),
        txt(1085, 335, "Container runtime boundary", "small", "middle"),
        legend(),
    ]
    return canvas("macOS deployment architecture", "macOS host → Docker Desktop Linux VM → isolated Compose network and persistent volumes", "".join(c))


def routing_figure() -> str:
    c = [
        rect(70, 155, 790, 760, "#FCFDFE", "#8FA7B8", 24, 2, True),
        rect(940, 155, 790, 760, "#FCFDFE", "#8FA7B8", 24, 2, True),
        txt(465, 205, "A. Harness-controlled random coordinator", "section", "middle"),
        txt(1335, 205, "B. Cassandra driver token-aware policy", "section", "middle"),
        rect(105, 255, 335, 135, LIGHT_GREEN, GREEN, 18, 2), icon("python", 130, 295, 52),
        lines(200, 290, ["Experiment harness", "independent random", "draw per operation"], "body", "start", 25),
        rect(980, 255, 315, 135, LIGHT_GREEN, GREEN, 18, 2), icon("python", 1005, 295, 52),
        lines(1070, 292, ["Application statement", "partition routing key", "no host selected by app"], "body", "start", 25),
        rect(1395, 260, 270, 125, LIGHT_BLUE, BLUE, 18, 2),
        lines(1530, 304, ["TokenAwarePolicy", "DC-aware child policy"], "body", "middle", 28),
        arrow(1295, 322, 1377, 322, BLUE, width=4),
        txt(1335, 300, "token map", "tiny", "middle"),
    ]
    for i, x in enumerate((95, 350, 605), 1):
        c.append(node(x, 520, f"n{i}", i == 3))
    for i, x in enumerate((965, 1220, 1475), 1):
        c.append(node(x, 520, f"n{i}", i == 2))
    c += [
        curved("M190,390 C190,420 220,420 220,448", BLUE, width=3, marker=False),
        curved("M272,390 C272,425 475,410 475,448", BLUE, width=3, marker=False),
        curved("M355,390 C355,420 730,405 730,448", BLUE, width=3, marker=False),
        rect(163, 452, 114, 34, "#FFFFFF", BLUE, 12, 1), txt(220, 475, "op₁", "small", "middle"),
        rect(418, 452, 114, 34, "#FFFFFF", BLUE, 12, 1), txt(475, 475, "op₂", "small", "middle"),
        rect(673, 452, 114, 34, "#FFFFFF", BLUE, 12, 1), txt(730, 475, "op₃", "small", "middle"),
        arrow(220, 488, 220, 502, BLUE, width=3),
        arrow(475, 488, 475, 502, BLUE, width=3),
        arrow(730, 488, 730, 502, BLUE, width=3),
        curved("M1530,387 C1530,414 1335,402 1335,412", BLUE, width=3),
        rect(1090, 430, 490, 42, "#FFFFFF", BLUE, 13, 1),
        txt(1335, 457, "stable first live local replica is usually reused", "small", "middle"),
        arrow(1345, 474, 1345, 502, BLUE, width=3),
        rect(180, 705, 570, 135, LIGHT_AMBER, AMBER, 16, 2),
        lines(465, 743, ["Maximizes route diversity", "Strong counterexample search across fault domains", "Artificial client-side coordinator intervention"], "body", "middle", 28),
        rect(1050, 705, 570, 135, LIGHT_BLUE, BLUE, 16, 2),
        lines(1335, 743, ["Matches production driver behavior", "Replica-aware and local-DC routing", "May provide little cross-partition exposure"], "body", "middle", 28),
        rect(520, 935, 760, 72, "#FFFFFF", PURPLE, 16, 2),
        txt(900, 978, "Both paths end at an ordinary Cassandra node acting as coordinator for that request", "label", "middle"),
    ]
    return canvas("Coordinator selection: two experimental routing designs", "Routing changes the histories observed; consistency levels still determine replica acknowledgement requirements", "".join(c))


def fault_panel(x, title, subtitle, kind):
    c = [rect(x, 220, 510, 650, "#FCFDFE", "#8FA7B8", 22, 2, True), txt(x+255, 268, title, "section", "middle"), txt(x+255, 300, subtitle, "small", "middle")]
    xs = [x+45, x+180, x+315]
    for i, nx in enumerate(xs, 1):
        c.append(rect(nx, 400, 120, 105, "#FFFFFF", LINE, 15, 2))
        c.append(icon("apachecassandra", nx+15, 420, 42))
        c.append(txt(nx+76, 445, f"n{i}", "label", "middle"))
        c.append(txt(nx+76, 475, "replica", "tiny", "middle"))
    if kind == "normal":
        c += [curved(f"M{x+105},505 C{x+150},555 {x+220},555 {x+240},505", PURPLE, width=4), curved(f"M{x+240},505 C{x+285},555 {x+350},555 {x+375},505", PURPLE, width=4),
              rect(x+90, 620, 330, 120, LIGHT_GREEN, GREEN, 15, 2), lines(x+255, 655, ["All replicas reachable", "ONE • QUORUM • ALL may complete", "Baseline for consistency histories"], "body", "middle", 27)]
    elif kind == "failure":
        c += [f'<g opacity="0.92"><line x1="{x+325}" y1="395" x2="{x+435}" y2="510" stroke="{RED}" stroke-width="17" stroke-linecap="round"/><line x1="{x+325}" y1="395" x2="{x+435}" y2="510" stroke="{LIGHT_RED}" stroke-width="10" stroke-linecap="round"/><line x1="{x+435}" y1="395" x2="{x+325}" y2="510" stroke="{RED}" stroke-width="17" stroke-linecap="round"/><line x1="{x+435}" y1="395" x2="{x+325}" y2="510" stroke="{LIGHT_RED}" stroke-width="10" stroke-linecap="round"/></g>',
              f'<text x="{x+391}" y="445" class="label" text-anchor="middle" paint-order="stroke" stroke="#FFFFFF" stroke-width="8" stroke-linejoin="round">n3</text>',
              txt(x+375, 548, "SIGKILL n3", "label", "middle", fill=RED),
              rect(x+90, 620, 330, 120, LIGHT_RED, RED, 15, 2), lines(x+255, 655, ["Two replicas remain", "ONE / QUORUM may complete", "ALL becomes unavailable"], "body", "middle", 27)]
    else:
        c += [f'<rect x="{x+292}" y="360" width="175" height="195" rx="16" fill="none" stroke="{RED}" stroke-width="4" stroke-dasharray="10 8"/>',
              f'<line x1="{x+285}" y1="365" x2="{x+285}" y2="555" stroke="{RED}" stroke-width="7"/>',
              txt(x+375, 585, "isolated side", "label", "middle", fill=RED),
              rect(x+65, 620, 380, 145, LIGHT_RED, RED, 15, 2), lines(x+255, 654, ["iptables DROP: 7000 / 7001", "CQL 9042 remains reachable", "QUORUM only on 2-node side; ALL fails"], "body", "middle", 27)]
    return "".join(c)


def faults_figure() -> str:
    c = [
        rect(80, 145, 1640, 55, PANEL, LINE, 14, 1),
        txt(120, 180, "Host controller", "label"),
        txt(340, 180, "inject fault", "small"), arrow(460, 173, 630, 173, MUTED, dash="10 8", width=3),
        txt(700, 180, "wait for detection / stabilization", "small"), arrow(1010, 173, 1180, 173, MUTED, dash="10 8", width=3),
        txt(1240, 180, "run 36 histories", "small"), arrow(1450, 173, 1600, 173, MUTED, dash="10 8", width=3),
        fault_panel(70, "Normal operation", "No injected fault", "normal"),
        fault_panel(645, "Node failure", "Abrupt container failure", "failure"),
        fault_panel(1220, "Network partition", "Bilateral 2|1 internode cut", "partition"),
        rect(240, 910, 1320, 90, "#FFFFFF", GREEN, 16, 2),
        txt(900, 948, "Recovery gate", "label", "middle"),
        txt(900, 978, "Restart or remove rules → require all nodes UN → record recovery evidence before the next episode", "body", "middle"),
    ]
    return canvas("Fault-injection architecture", "Each episode initializes fresh keys, applies one controlled fault, executes the workload, and verifies recovery", "".join(c))


def pipeline_figure() -> str:
    boxes = [
        (70, 245, 230, 150, LIGHT_AMBER, AMBER, "Configuration", ["design + seed", "rounds + CL pairs", "fault timings"]),
        (360, 245, 230, 150, LIGHT_GREEN, GREEN, "Python runner", ["schedule", "progress", "recovery gates"]),
        (650, 245, 230, 150, LIGHT_BLUE, BLUE, "client container", ["CQL histories", "routing evidence", "logical clients"]),
        (940, 245, 260, 150, LIGHT_PURPLE, PURPLE, "Cassandra cluster", ["n1 • n2 • n3", "RF=3 / dc1", "tunable CL"]),
        (1260, 245, 250, 150, "#F3F6F8", "#6F8EA5", "Raw evidence", ["trials + episodes", "faults + controls", "environment + hashes"]),
    ]
    c = []
    for i, (x, y, w, h, fill, stroke, title, body) in enumerate(boxes):
        title_x = x+w/2 + (22 if i in (1, 2) else 0)
        c += [rect(x, y, w, h, fill, stroke, 18, 2, True), txt(title_x, y+42, title, "label", "middle"), lines(x+w/2, y+75, body, "small", "middle", 24)]
        if i in (1, 2):
            c.append(icon("python", x+22, y+19, 46))
        if i < len(boxes)-1:
            c.append(arrow(x+w+12, y+75, boxes[i+1][0]-12, y+75, BLUE if i in (1,2) else MUTED, dash="10 8" if i==0 else None, width=4))
    c += [
        icon("apachecassandra", 1045, 166, 58),
        rect(250, 505, 520, 135, "#FCFDFE", "#8FA7B8", 18, 2),
        txt(510, 546, "Evidence validation gate", "section", "middle"),
        lines(510, 580, ["completion + schema + identity", "counts + unique IDs + source hashes"], "body", "middle", 27),
        arrow(1385, 405, 770, 552, MUTED, dash="10 8", width=4),
        rect(850, 505, 390, 135, LIGHT_GREEN, GREEN, 18, 2, True),
        csv_icon(880, 535, 60),
        txt(1065, 546, "Trial-level CSV", "section", "middle"),
        lines(1065, 580, ["75,692 tracked records", "operations + routing + faults"], "body", "middle", 27),
        rect(1310, 505, 390, 135, LIGHT_GREEN, GREEN, 18, 2, True),
        csv_icon(1340, 535, 60),
        txt(1525, 546, "Run-level matrix", "section", "middle"),
        lines(1525, 580, ["33 run IDs", "outcomes + metadata + cells"], "body", "middle", 27),
        arrow(770, 572, 845, 572, GREEN, width=4), arrow(1240, 572, 1305, 572, GREEN, width=4),
        rect(390, 735, 1020, 155, "#FFFFFF", BLUE, 20, 3, True),
        txt(900, 780, "Academic report layer", "section", "middle"),
        lines(900, 817, ["Compact result tables • violation traces • availability analysis • routing exposure", "Every claim points to a CSV row and the original JSON source"], "body", "middle", 30),
        arrow(1045, 650, 860, 730, GREEN, width=4), arrow(1505, 650, 940, 730, GREEN, width=4),
        rect(80, 945, 1640, 55, PANEL, LINE, 12, 1),
        txt(900, 980, "Analysis rule: incomplete runs stay visible for audit but are excluded from aggregate conclusions", "label", "middle"),
    ]
    return canvas("Experiment and evidence pipeline", "From parameterized execution to traceable report tables without losing run or trial provenance", "".join(c))


def model_card(x, y, title, subtitle, steps, test, color, fill):
    c = [rect(x, y, 790, 330, "#FFFFFF", color, 20, 3, True), rect(x, y, 790, 58, fill, color, 20, 0), txt(x+28, y+39, title, "section"), txt(x+760, y+38, subtitle, "small", "end")]
    positions = [x+260, x+530] if len(steps) == 2 else [x+130, x+395, x+660]
    for i, (client, action) in enumerate(steps):
        px = positions[i]
        c += [f'<circle cx="{px}" cy="{y+145}" r="38" fill="{fill}" stroke="{color}" stroke-width="3"/>', txt(px, y+151, str(i+1), "label", "middle"), txt(px, y+205, client, "small", "middle"), txt(px, y+230, action, "body", "middle")]
        if i < len(steps)-1:
            c.append(arrow(px+45, y+145, positions[i+1]-45, y+145, color if color in (BLUE,PURPLE,GREEN,MUTED) else MUTED, width=3))
    c += [rect(x+45, y+265, 700, 42, fill, color, 10, 1), txt(x+395, y+292, test, "small", "middle")]
    return "".join(c)


def models_figure() -> str:
    c = [
        model_card(70, 175, "Read-your-writes (RYW)", "single logical client", [("Client A", "write v1"), ("Client A", "read")], "Violation: the later read returns a value older than v1", BLUE, LIGHT_BLUE),
        model_card(940, 175, "Monotonic reads (MR)", "single logical client", [("Client A", "read v1"), ("Client A", "read v0")], "Violation: a later read regresses from v1 to v0", PURPLE, LIGHT_PURPLE),
        model_card(70, 555, "Monotonic writes (MW)", "ordered writes", [("Client A", "write a=1"), ("Client A", "write b=1"), ("Observer", "read")], "Violation witness: successor b=1 is visible while predecessor a=1 is absent", GREEN, LIGHT_GREEN),
        model_card(940, 555, "Writes-follow-reads (WFR)", "causal dependency", [("Client A", "read a=1"), ("Client B", "write b=1"), ("Observer", "read")], "Violation witness: dependent b=1 is visible without observed dependency a=1", AMBER, LIGHT_AMBER),
        icon("apachecassandra", 570, 932, 62),
        txt(655, 975, "Each oracle evaluates the saved operation history—not Cassandra's internal state that was not logged", "label"),
    ]
    return canvas("Client-centric consistency models and violation witnesses", "The experiment records finite histories; a missing witness means no violation was observed in that trial", "".join(c))


def token_aware_detail_figure() -> str:
    """Detailed view of coordinator selection by the Cassandra Python driver."""
    c = [
        # Driver decision pipeline.
        rect(65, 175, 300, 175, LIGHT_GREEN, GREEN, 18, 2, True),
        icon("python", 92, 194, 42),
        txt(210, 220, "Application", "section"),
        lines(215, 262, ["SimpleStatement + keyspace", "partition routing key", "requested consistency level"], "small", "middle", 25),
        rect(430, 175, 300, 175, LIGHT_BLUE, BLUE, 18, 2, True),
        txt(580, 218, "Token calculation", "section", "middle"),
        lines(580, 255, ["Murmur3(partition key)", "→ token-ring position", "metadata supplied by cluster"], "small", "middle", 25),
        rect(795, 175, 370, 175, LIGHT_PURPLE, PURPLE, 18, 2, True),
        icon("apachecassandra", 825, 218, 56),
        txt(990, 218, "Replica-aware ranking", "section", "middle"),
        lines(990, 255, ["TokenAwarePolicy", "DCAwareRoundRobinPolicy", "local_dc = dc1"], "small", "middle", 25),
        rect(1230, 175, 505, 175, "#FFFFFF", BLUE, 18, 3, True),
        txt(1482, 214, "Per-request query plan", "section", "middle"),
        rect(1270, 245, 120, 50, LIGHT_BLUE, BLUE, 13, 2), txt(1330, 277, "1  n2", "label", "middle"),
        rect(1422, 245, 120, 50, "#FFFFFF", LINE, 13, 2), txt(1482, 277, "2  n3", "label", "middle"),
        rect(1574, 245, 120, 50, "#FFFFFF", LINE, 13, 2), txt(1634, 277, "3  n1", "label", "middle"),
        txt(1482, 327, "first live eligible host becomes coordinator", "small", "middle"),
        arrow(365, 262, 412, 262, BLUE, width=4),
        arrow(730, 262, 777, 262, BLUE, width=4),
        arrow(1165, 262, 1212, 262, BLUE, width=4),

        # Cluster execution plane.
        rect(180, 470, 1440, 360, PANEL, "#8FA7B8", 24, 2),
        txt(220, 512, "Cassandra execution plane • RF=3 • dc1", "section"),
        node(265, 600, "n1", False), node(775, 600, "n2", True), node(1285, 600, "n3", False),
        curved("M1482,352 C1482,435 900,430 900,582", BLUE, width=4),
        txt(1245, 405, "driver sends CQL to preferred live host", "small", "middle"),
        curved("M900,597 C900,540 390,540 390,582", PURPLE, width=4),
        curved("M900,597 C900,540 1410,540 1410,582", PURPLE, width=4),
        txt(600, 455, "coordinator contacts replicas and waits for the requested CL", "small", "middle"),
        rect(240, 755, 410, 48, LIGHT_RED, RED, 12, 1),
        txt(445, 786, "If n2 is down → try n3, then n1", "small", "middle"),
        rect(695, 755, 410, 48, LIGHT_AMBER, AMBER, 12, 1),
        txt(900, 786, "Retries and speculative execution disabled", "small", "middle"),
        rect(1150, 755, 410, 48, LIGHT_GREEN, GREEN, 12, 1),
        txt(1355, 786, "Actual coordinator is recorded as evidence", "small", "middle"),

        # Interpretation band.
        rect(195, 890, 1410, 100, "#FFFFFF", BLUE, 18, 2, True),
        txt(900, 930, "Interpretation boundary", "label", "middle"),
        txt(900, 965, "Token awareness selects an efficient coordinator; ONE, QUORUM, or ALL still defines the replica response requirement.", "body", "middle"),
    ]
    return canvas("Cassandra token-aware coordinator selection", "How the Python driver turns a partition key into a stable, replica-aware local-DC query plan", "".join(c))


FIGURES = {
    "01_windows_deployment_architecture.svg": windows_figure,
    "02_macos_deployment_architecture.svg": macos_figure,
    "03_routing_policy_comparison.svg": routing_figure,
    "04_fault_injection_architecture.svg": faults_figure,
    "05_experiment_evidence_pipeline.svg": pipeline_figure,
    "06_client_centric_models.svg": models_figure,
    "07_token_aware_driver_policy_detail.svg": token_aware_detail_figure,
}


def main() -> None:
    SVG_DIR.mkdir(parents=True, exist_ok=True)
    for filename, builder in FIGURES.items():
        path = SVG_DIR / filename
        path.write_text(builder())
        print(path)


if __name__ == "__main__":
    main()
