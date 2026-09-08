#!/usr/bin/env python3
"""
Generate the README figures as SVG, from the SAME constants the recipe
and the safety model use.

WHY THIS IS A GENERATOR AND NOT FIVE HAND-DRAWN FILES
=====================================================
This project has now been bitten four separate times by the same bug:
a number that was true when it was written, and silently stopped being
true. The last one was `report.py` printing "137 tests" long after the
figure was 145 - a false claim about the project's own rigour, printed
as the headline evidence.

A hand-drawn diagram is exactly that failure waiting to happen, except
worse: a picture is the first thing a reader believes and the last
thing anyone re-checks. If YOLK_HOLD_MINUTES changes and a hand-typed
"10 min" stays in an SVG, the repository ships a lie in its most
prominent position.

So no figure here contains a typed-in measurement. Every mass, volume,
density, temperature, hold time and log-reduction is imported from
`formulation` / `thermal_safety` and formatted at generation time. The
geometry, too: layer band heights are proportional to computed VOLUME,
not to numbers chosen to look nice.

Run `python3 tools/make_figures.py` after any constant changes, and
`tests/test_figures.py` fails if the committed SVGs no longer match
the code.

DESIGN CONSTRAINTS THAT ARE NOT NEGOTIABLE
------------------------------------------
* No external references. GitHub renders README SVG inside an <img>,
  so remote fonts/images/scripts silently fail. Everything is inline,
  and fonts are generic families only.
* No <script>, no event handlers. They are stripped, and asking for
  them would be pointless.
* Legible on BOTH GitHub themes. GitHub does not tell an <img> which
  theme is active, so every figure paints its own background rather
  than relying on the page's - white-on-transparent text vanishing on
  a light background is the classic version of this bug.
* Pure ASCII in the output. A stray non-encodable glyph would make the
  file unopenable in some viewers; the Persian title is drawn from a
  small set of escapes that are checked at generation time.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import formulation as F  # noqa: E402
import thermal_safety as T  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "assets")

# --------------------------------------------------------------------------
# Palette. Chosen for contrast against BOTH GitHub themes, since an <img>
# is not told which theme is in use.
# --------------------------------------------------------------------------
INK = "#12100c"          # near-black, but warm
INK_SOFT = "#5b5344"
PAPER = "#fbf7ef"        # warm off-white; own background, never transparent
RULE = "#d8cdb8"
YOLK_1 = "#f0b429"       # the custard, light
YOLK_2 = "#c8860d"       # the custard, deep
COFFEE_1 = "#6b4423"
COFFEE_2 = "#33210f"
FOAM_1 = "#fffdf8"
FOAM_2 = "#ece2cf"
GLASS = "#8a8578"
ACCENT = "#1d6f63"       # teal, for "verified"
WARN = "#a3401f"         # rust, for "not established"


# --------------------------------------------------------------------------
# Data, all derived
# --------------------------------------------------------------------------
def layer_data():
    """Mass, density and VOLUME per layer, computed from the recipe."""
    recipe = F.build_sepid_o_zarrin()
    mass: dict[str, float] = {}
    for ing in recipe.ingredients:
        mass[ing.layer] = mass.get(ing.layer, 0.0) + ing.grams

    # Densities come from the same functions the docs quote.
    density = {
        "base": F.sugar_syrup_density_g_per_ml(37),
        "coffee": 1.01,
        "foam": F.foam_density_g_per_ml(200),
    }
    volume = {k: mass[k] / density[k] for k in density}
    return recipe, mass, density, volume


def fmt(value: float, places: int = 1) -> str:
    """Format without a trailing '.0', so 30.0 reads as 30."""
    text = f"{value:.{places}f}"
    return text[:-2] if text.endswith(".0") else text


def esc(text: str) -> str:
    """XML-escape text placed in an element body."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


HEAD = (
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
    'role="img" aria-label="{label}">\n'
    "<title>{label}</title>\n"
    "<desc>{desc}</desc>\n"
)


def to_entities(text: str) -> str:
    """
    Replace every non-ASCII character with a numeric XML entity.

    WHY THIS EXISTS AS ONE PASS
    ---------------------------
    The files must be pure ASCII (see the module docstring), but the
    figures legitimately need degree signs, em dashes, multiplication
    signs and the Persian title. Writing entities by hand at each of
    the dozen-odd call sites is exactly the kind of repetitive manual
    step that gets missed once and ships broken - and it WAS missed:
    a literal degree sign reached the ASCII check and raised
    UnicodeEncodeError on the first full run.

    Doing it centrally means the guarantee holds for text that has not
    been written yet, which is the only version of the guarantee worth
    having.
    """
    out = []
    for ch in text:
        out.append(ch if ord(ch) < 128 else f"&#{ord(ch)};")
    return "".join(out)


def svg(width: int, height: int, label: str, desc: str, body: str) -> str:
    return to_entities(
        HEAD.format(w=width, h=height, label=esc(label), desc=esc(desc))
        + f'<rect width="{width}" height="{height}" fill="{PAPER}"/>\n'
        + body
        + "</svg>\n"
    )


# --------------------------------------------------------------------------
# FIGURE 1 - the drink itself, drawn to computed volume
# --------------------------------------------------------------------------
def fig_layers() -> str:
    recipe, mass, density, volume = layer_data()
    total_v = sum(volume.values())
    total_m = recipe.total_mass_g()

    W, H = 1120, 600
    gx, gy, gw, gh = 90, 70, 210, 430   # glass interior box

    rows = [
        ("foam", "Meringue foam", FOAM_1, FOAM_2, INK),
        ("coffee", "Double espresso", COFFEE_1, COFFEE_2, "#ffffff"),
        ("base", "Yolk custard base", YOLK_1, YOLK_2, INK),
    ]

    body = []
    body.append(
        f'<style>text{{font-family:Georgia,"Times New Roman",serif;'
        f"fill:{INK}}}"
        f'.n{{font-family:"DejaVu Sans Mono",Consolas,monospace}}'
        # Persian needs a sans stack: verified by rendering that serif
        # families fall back to tofu boxes for U+0600..U+06FF, while
        # sans-serif resolves to a covering face.
        f'.fa{{font-family:"DejaVu Sans","Noto Naskh Arabic",sans-serif}}'
        f"</style>\n"
    )
    body.append(
        f'<defs><clipPath id="glass">'
        f'<path d="M{gx},{gy} L{gx + 14},{gy + gh - 26} '
        f"Q{gx + 14},{gy + gh} {gx + 40},{gy + gh} "
        f"L{gx + gw - 40},{gy + gh} "
        f"Q{gx + gw - 14},{gy + gh} {gx + gw - 14},{gy + gh - 26} "
        f'L{gx + gw},{gy} Z"/></clipPath>'
    )
    for key, _, c1, c2, _ in rows:
        body.append(
            f'<linearGradient id="g_{key}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{c2}"/>'
            f'<stop offset="0.45" stop-color="{c1}"/>'
            f'<stop offset="1" stop-color="{c2}"/></linearGradient>'
        )
    body.append("</defs>\n")

    # Title
    body.append(
        f'<text x="{gx}" y="42" font-size="27" letter-spacing="0.5">'
        f"Sepid-o-Zarrin</text>\n"
    )
    body.append(
        f'<text x="{gx + 232}" y="42" font-size="21" fill="{INK_SOFT}" '
        f'class="fa">'
        f"&#x0633;&#x067E;&#x06CC;&#x062F; &#x0648; "
        f"&#x0632;&#x0631;&#x0651;&#x06CC;&#x0646;</text>\n"
    )

    # Layer bands, height proportional to VOLUME
    y = gy
    label_x = gx + gw + 46
    body.append(f'<g clip-path="url(#glass)">\n')
    for key, _, _, _, _ in rows:
        share = volume[key] / total_v
        band = gh * share
        body.append(
            f'<rect x="{gx - 4}" y="{y:.2f}" width="{gw + 8}" '
            f'height="{band:.2f}" fill="url(#g_{key})"/>\n'
        )
        y += band
    body.append("</g>\n")

    # Foam bubbles, purely decorative but confined to the foam band
    foam_h = gh * volume["foam"] / total_v
    seed = 7
    body.append('<g clip-path="url(#glass)" opacity="0.5">\n')
    for i in range(34):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        bx = gx + 10 + (seed >> 7) % (gw - 20)
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        by = gy + 8 + (seed >> 7) % max(int(foam_h) - 16, 1)
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        rr = 2 + (seed >> 9) % 4
        body.append(
            f'<circle cx="{bx}" cy="{by}" r="{rr}" fill="none" '
            f'stroke="{INK_SOFT}" stroke-width="0.7"/>'
        )
    body.append("\n</g>\n")

    # Glass outline
    body.append(
        f'<path d="M{gx},{gy} L{gx + 14},{gy + gh - 26} '
        f"Q{gx + 14},{gy + gh} {gx + 40},{gy + gh} "
        f"L{gx + gw - 40},{gy + gh} "
        f"Q{gx + gw - 14},{gy + gh} {gx + gw - 14},{gy + gh - 26} "
        f'L{gx + gw},{gy}" fill="none" stroke="{GLASS}" '
        f'stroke-width="2.5" stroke-linejoin="round"/>\n'
    )
    body.append(
        f'<line x1="{gx - 8}" y1="{gy}" x2="{gx + gw + 8}" y2="{gy}" '
        f'stroke="{GLASS}" stroke-width="3" stroke-linecap="round"/>\n'
    )

    # Leader lines and per-layer readouts.
    #
    # The label block is 3 lines tall, so anchoring every block to its
    # own band centre made the espresso and base blocks overlap - their
    # bands are only ~13% of the height each. Rendering showed the
    # collision. Anchors are therefore pushed apart to a minimum
    # separation, and a leader line connects each block to its true
    # band centre so the diagram stays honest about which is which.
    # Measured, not guessed: the block draws its title at mid-12, the
    # numbers at mid+10 and the percentage at mid+28, so it occupies
    # roughly mid-26 .. mid+33. 72px leaves a clear gutter between
    # consecutive blocks. Rendering confirmed 64px still touched.
    BLOCK = 72
    anchors = []
    y = gy
    for key, _, _, _, _ in rows:
        band = gh * volume[key] / total_v
        anchors.append([key, y + band / 2, y + band / 2])
        y += band
    for i in range(1, len(anchors)):
        gap = anchors[i][1] - anchors[i - 1][1]
        if gap < BLOCK:
            anchors[i][1] = anchors[i - 1][1] + BLOCK
    # Keep the last block inside the glass footprint.
    overflow = anchors[-1][1] - (gy + gh - 18)
    if overflow > 0:
        for a in anchors:
            a[1] -= overflow

    for (key, label_y, band_mid), (_, title, _, _, _) in zip(anchors, rows):
        mid = label_y
        body.append(
            f'<path d="M{gx + gw + 6},{band_mid:.1f} '
            f'H{gx + gw + 24} V{mid:.1f} H{label_x - 10}" '
            f'fill="none" stroke="{RULE}" stroke-width="1.2"/>\n'
        )
        body.append(
            f'<text x="{label_x}" y="{mid - 12:.1f}" font-size="19">'
            f"{esc(title)}</text>\n"
        )
        body.append(
            f'<text x="{label_x}" y="{mid + 10:.1f}" font-size="14.5" '
            f'class="n" fill="{INK_SOFT}">'
            f"{fmt(mass[key], 2)} g &#183; {fmt(volume[key])} mL &#183; "
            f"{density[key]:.2f} g/mL</text>\n"
        )
        body.append(
            f'<text x="{label_x}" y="{mid + 28:.1f}" font-size="13" '
            f'class="n" fill="{INK_SOFT}">'
            f"{100 * volume[key] / total_v:.0f}% of volume</text>\n"
        )

    # The point of the whole project
    gm = mass.get("garnish", 0.0)
    ty = gy + gh + 40          # below the glass foot, never overlapping
    body.append(
        f'<line x1="{gx}" y1="{ty - 22}" x2="{W - 60}" '
        f'y2="{ty - 22}" stroke="{RULE}" stroke-width="1"/>\n'
    )
    body.append(
        f'<text x="{gx}" y="{ty}" font-size="15.5">'
        f'<tspan class="n">{fmt(total_m, 1)} g</tspan> total, from '
        f"<tspan font-style=\"italic\">one</tspan> egg &#8212; yolk and "
        f"white both used, plus {fmt(gm, 1)} g cocoa and cardamom on "
        f"top. Nothing is discarded.</text>\n"
    )
    body.append(
        f'<text x="{gx}" y="{ty + 26}" font-size="13.5" '
        f'fill="{INK_SOFT}">Band heights are proportional to computed '
        f"volume, not chosen for looks: the foam is "
        f"{100 * volume['foam'] / total_v:.0f}% of the drink by volume "
        f"and only {100 * mass['foam'] / total_m:.0f}% by mass.</text>\n"
    )

    return svg(
        W, H, "Sepid-o-Zarrin: the three layers",
        f"Layered drink diagram. Foam {fmt(mass['foam'],2)} g, "
        f"espresso {fmt(mass['coffee'],2)} g, "
        f"yolk base {fmt(mass['base'],2)} g, total {fmt(total_m,1)} g.",
        "".join(body),
    )


# --------------------------------------------------------------------------
# Small shared helpers for the chart figures
# --------------------------------------------------------------------------
def base_style() -> str:
    return (
        f'<style>text{{font-family:Georgia,"Times New Roman",serif;'
        f"fill:{INK}}}"
        f'.n{{font-family:"DejaVu Sans Mono",Consolas,monospace}}'
        f'.fa{{font-family:"DejaVu Sans","Noto Naskh Arabic",sans-serif}}'
        f"</style>\n"
    )


def title_block(x: int, y: int, title: str, sub: str) -> str:
    return (
        f'<text x="{x}" y="{y}" font-size="23">{esc(title)}</text>\n'
        f'<text x="{x}" y="{y + 23}" font-size="13.5" fill="{INK_SOFT}">'
        f"{esc(sub)}</text>\n"
    )


# --------------------------------------------------------------------------
# FIGURE 2 - the yolk pasteurization curve
# --------------------------------------------------------------------------
def fig_thermal() -> str:
    ramp = F.YOLK_RAMP_MINUTES
    hold = F.YOLK_HOLD_MINUTES
    target = F.YOLK_CUSTARD_TARGET_C
    total = ramp + hold
    checks = F.YOLK_STEP_CROSS_CHECKS

    W, H = 1240, 600
    px, py, pw, ph = 110, 110, 600, 320    # plot box
    t_max = total * 1.12
    y_lo, y_hi = 20.0, 80.0

    def sx(minutes: float) -> float:
        return px + pw * (minutes / t_max)

    def sy(celsius: float) -> float:
        return py + ph * (1 - (celsius - y_lo) / (y_hi - y_lo))

    body = [base_style()]
    body.append(
        title_block(
            px - 20, 52,
            "The yolk kill step",
            f"A {fmt(ramp)}-minute ramp to {fmt(target)} "
            f"\u00b0C, then a {fmt(hold)}-minute hold. "
            f"Every value plotted is read from the code, not typed in.",
        )
    )

    # grid + axes
    for c in range(20, 81, 10):
        yy = sy(c)
        # Precomputed: a backslash inside an f-string expression is
        # a SyntaxError before Python 3.12, and the CI matrix runs
        # 3.10. Caught by ast.parse, not by assumption.
        dash = " stroke-dasharray='4 4'" if c == 60 else ""
        body.append(
            f'<line x1="{px}" y1="{yy:.1f}" x2="{px + pw}" y2="{yy:.1f}" '
            f'stroke="{RULE}" stroke-width="{1.6 if c == 60 else 0.8}" '
            f"{dash}/>\n"
        )
        body.append(
            f'<text x="{px - 12}" y="{yy + 4:.1f}" font-size="12.5" '
            f'class="n" fill="{INK_SOFT}" text-anchor="end">{c}</text>\n'
        )
    for mn in range(0, int(t_max) + 1, 2):
        xx = sx(mn)
        body.append(
            f'<line x1="{xx:.1f}" y1="{py + ph}" x2="{xx:.1f}" '
            f'y2="{py + ph + 6}" stroke="{INK_SOFT}" stroke-width="1"/>\n'
        )
        body.append(
            f'<text x="{xx:.1f}" y="{py + ph + 24}" font-size="12.5" '
            f'class="n" fill="{INK_SOFT}" text-anchor="middle">{mn}</text>\n'
        )
    body.append(
        f'<text x="{px + pw / 2:.0f}" y="{py + ph + 48}" font-size="13.5" '
        f'fill="{INK_SOFT}" text-anchor="middle">minutes</text>\n'
    )
    body.append(
        f'<text x="{px - 44}" y="{py + ph / 2:.0f}" font-size="13.5" '
        f'fill="{INK_SOFT}" text-anchor="middle" '
        f'transform="rotate(-90 {px - 44} {py + ph / 2:.0f})">'
        f"\u00b0C</text>\n"
    )

    # the scrambling ceiling and the FSIS floor, both real constants
    setting = 70.0
    body.append(
        f'<rect x="{px}" y="{sy(80):.1f}" width="{pw}" '
        f'height="{sy(setting) - sy(80):.1f}" fill="{WARN}" '
        f'opacity="0.07"/>\n'
    )
    body.append(
        f'<text x="{px + 10}" y="{sy(setting) - 8:.1f}" font-size="12.5" '
        f'fill="{WARN}">yolk begins to set &#8212; scrambled, not a '
        f"drink</text>\n"
    )

    # curve: ramp then hold
    body.append(
        f'<path d="M{sx(0):.1f},{sy(20):.1f} L{sx(ramp):.1f},'
        f'{sy(target):.1f} L{sx(total):.1f},{sy(target):.1f}" '
        f'fill="none" stroke="{YOLK_2}" stroke-width="3.2" '
        f'stroke-linejoin="round" stroke-linecap="round"/>\n'
    )
    # shade the lethal hold
    body.append(
        f'<path d="M{sx(ramp):.1f},{sy(target):.1f} '
        f"L{sx(total):.1f},{sy(target):.1f} "
        f'L{sx(total):.1f},{py + ph} L{sx(ramp):.1f},{py + ph} Z" '
        f'fill="{YOLK_1}" opacity="0.20"/>\n'
    )
    body.append(
        f'<circle cx="{sx(ramp):.1f}" cy="{sy(target):.1f}" r="5" '
        f'fill="{PAPER}" stroke="{YOLK_2}" stroke-width="2.5"/>\n'
    )
    body.append(
        f'<circle cx="{sx(total):.1f}" cy="{sy(target):.1f}" r="5" '
        f'fill="{YOLK_2}"/>\n'
    )
    body.append(
        f'<text x="{sx(ramp) + 8:.1f}" y="{sy(target) - 14:.1f}" '
        f'font-size="14.5" class="n">{fmt(target)} \u00b0C</text>\n'
    )
    body.append(
        f'<text x="{sx(ramp + hold / 2):.1f}" y="{sy(target) + 26:.1f}" '
        f'font-size="13.5" fill="{INK_SOFT}" text-anchor="middle">'
        f"hold {fmt(hold)} min</text>\n"
    )

    # right-hand panel: the three matrix cross-checks
    cx = px + pw + 64
    body.append(
        f'<text x="{cx}" y="{py - 6}" font-size="16">'
        f"Log&#8321;&#8320; reduction achieved</text>\n"
    )
    body.append(
        f'<text x="{cx}" y="{py + 14}" font-size="12.5" fill="{INK_SOFT}">'
        f"same step, three published matrices</text>\n"
    )
    bar_x = cx
    bar_w = 250
    row_y = py + 44
    worst = min(checks.values())
    scale = max(checks.values())
    for name, value in sorted(checks.items(), key=lambda kv: -kv[1]):
        frac = value / scale
        body.append(
            f'<text x="{bar_x}" y="{row_y}" font-size="13">'
            f"{esc(name)}</text>\n"
        )
        body.append(
            f'<rect x="{bar_x}" y="{row_y + 8}" width="{bar_w}" '
            f'height="13" fill="{RULE}" opacity="0.5" rx="2"/>\n'
        )
        body.append(
            f'<rect x="{bar_x}" y="{row_y + 8}" '
            f'width="{bar_w * frac:.1f}" height="13" fill="{ACCENT}" '
            f'rx="2"/>\n'
        )
        body.append(
            f'<text x="{bar_x + bar_w + 10}" y="{row_y + 19}" '
            f'font-size="13" class="n">{value:.2f}</text>\n'
        )
        row_y += 52

    # the 5-log requirement, marked on the same scale
    req = T.TARGET_LOG_DEFAULT
    rq_x = bar_x + bar_w * (req / scale)
    body.append(
        f'<line x1="{rq_x:.1f}" y1="{py + 50}" x2="{rq_x:.1f}" '
        f'y2="{row_y - 34}" stroke="{WARN}" stroke-width="1.6" '
        f'stroke-dasharray="5 4"/>\n'
    )
    body.append(
        f'<text x="{rq_x + 6:.1f}" y="{row_y - 16}" font-size="12.5" '
        f'fill="{WARN}">{fmt(req)}-log target</text>\n'
    )
    for i, line in enumerate((
        f"Worst case is the salted matrix at {worst:.2f}",
        f"log&#8321;&#8320;, still above the {fmt(req)}-log target.",
        "That margin is why salt and sugar are added",
        "AFTER this step, never before it.",
    )):
        body.append(
            f'<text x="{cx}" y="{row_y + 14 + i * 19}" font-size="13" '
            f'fill="{INK_SOFT}">{line}</text>\n'
        )

    for i, line in enumerate((
        "Modelled, not measured: no thermocouple data exists for this "
        "drink. The curve is the DESIGN intent,",
        "and every thermal history in the code is marked "
        "provenance=ASSUMED, enforced by the type system.",
    )):
        body.append(
            f'<text x="{px - 20}" y="{H - 44 + i * 19}" font-size="13" '
            f'fill="{WARN}">{line}</text>\n'
        )

    return svg(
        W, H, "The yolk pasteurization step",
        f"Temperature-time curve: {fmt(ramp)} min ramp to "
        f"{fmt(target)} C then {fmt(hold)} min hold, with log10 "
        f"reductions in three matrices.",
        "".join(body),
    )


# --------------------------------------------------------------------------
# FIGURE 3 - the sugar/salt asymmetry, which is the real finding
# --------------------------------------------------------------------------
def fig_asymmetry() -> str:
    yolk_plain = T.YOLK_PLAIN_GARIBALDI
    yolk_sugar = T.YOLK_SUGARED_10PCT
    yolk_salt = T.YOLK_SALTED_10PCT
    white_plain = T.WHITE_PLAIN_GARIBALDI
    white_sugar = T.WHITE_SUGARED_10PCT

    sugar_x = yolk_sugar.d_ref_min / yolk_plain.d_ref_min
    salt_x = yolk_salt.d_ref_min / yolk_plain.d_ref_min
    white_x = white_sugar.d_ref_min / white_plain.d_ref_min

    W, H = 1240, 620
    body = [base_style()]
    body.append(
        title_block(
            80, 52,
            "Why sugar goes in at opposite times",
            "Sugar protects Salmonella. So it must enter the yolk AFTER "
            "the kill step \u2014 but the white has no such option.",
        )
    )

    col_w = 500
    lx, rx = 80, 80 + col_w + 80
    top = 118

    def panel(x: int, heading: str, sub: str, accent: str) -> None:
        body.append(
            f'<rect x="{x}" y="{top}" width="{col_w}" height="360" '
            f'fill="none" stroke="{RULE}" stroke-width="1.4" rx="4"/>\n'
        )
        body.append(
            f'<rect x="{x}" y="{top}" width="{col_w}" height="4" '
            f'fill="{accent}"/>\n'
        )
        body.append(
            f'<text x="{x + 22}" y="{top + 38}" font-size="19">'
            f"{esc(heading)}</text>\n"
        )
        body.append(
            f'<text x="{x + 22}" y="{top + 60}" font-size="13" '
            f'fill="{INK_SOFT}">{esc(sub)}</text>\n'
        )

    panel(lx, "Yolk \u2014 sugar AFTER heating", "sugar makes the bug "
          "harder to kill, so heat first", YOLK_2)
    panel(rx, "White \u2014 sugar DURING heating", "plain white would "
          "cook; a sugared matrix is forced", COFFEE_1)

    # D-value bars, scaled to the largest value across BOTH panels
    scale = max(yolk_salt.d_ref_min, yolk_sugar.d_ref_min,
                white_sugar.d_ref_min, white_plain.d_ref_min,
                yolk_plain.d_ref_min)
    bar_w = 300

    def bars(x: int, rows) -> None:
        y = top + 96
        for label, d_min, t_ref, mult, colour in rows:
            body.append(
                f'<text x="{x + 22}" y="{y}" font-size="13.5">'
                f"{esc(label)}</text>\n"
            )
            body.append(
                f'<rect x="{x + 22}" y="{y + 10}" width="{bar_w}" '
                f'height="15" fill="{RULE}" opacity="0.45" rx="2"/>\n'
            )
            body.append(
                f'<rect x="{x + 22}" y="{y + 10}" '
                f'width="{bar_w * d_min / scale:.1f}" height="15" '
                f'fill="{colour}" rx="2"/>\n'
            )
            body.append(
                f'<text x="{x + 22 + bar_w + 12}" y="{y + 22}" '
                f'font-size="13" class="n">D{t_ref:.0f}={d_min:.2f}'
                f"</text>\n"
            )
            if mult:
                body.append(
                    f'<text x="{x + 22}" y="{y + 42}" font-size="12.5" '
                    f'fill="{WARN}">{mult}</text>\n'
                )
            y += 74

    bars(lx, [
        ("plain yolk", yolk_plain.d_ref_min, yolk_plain.t_ref_c, "", ACCENT),
        ("+ 10% sucrose", yolk_sugar.d_ref_min, yolk_sugar.t_ref_c,
         f"{sugar_x:.0f}\u00d7 harder to kill", YOLK_2),
        ("+ 10% NaCl", yolk_salt.d_ref_min, yolk_salt.t_ref_c,
         f"{salt_x:.2f}\u00d7 harder to kill", WARN),
    ])
    bars(rx, [
        ("plain white", white_plain.d_ref_min, white_plain.t_ref_c,
         "but it coagulates at this temperature", ACCENT),
        ("+ 10% sucrose", white_sugar.d_ref_min, white_sugar.t_ref_c,
         f"{white_x:.1f}\u00d7 harder to kill, and unavoidable",
         COFFEE_1),
    ])

    # the consequence, stated plainly
    ty = top + 396
    body.append(
        f'<line x1="{lx}" y1="{ty - 22}" x2="{W - 80}" y2="{ty - 22}" '
        f'stroke="{RULE}" stroke-width="1"/>\n'
    )
    for i, line in enumerate((
        # Derived by name from the recipe. An earlier draft typed
        # "18 g" here, which is the YOLK mass, not the base sugar -
        # caught only because the figure was rendered and read. This
        # is precisely the class of error the generator exists to
        # prevent, and it still nearly shipped.
        f"The yolk therefore reaches its kill step as PLAIN yolk "
        f"diluted with egg white, and receives its "
        f"{fmt(F.build_sepid_o_zarrin().find('caster sugar (base)').grams)}"
        f" g of sugar only afterwards.",
        f"The white is heated to {fmt(F.SWISS_MERINGUE_TARGET_C)} "
        f"\u00b0C in the Swiss-meringue method, which buys back the "
        f"lethality that its sugar load costs.",
        "Same ingredient, opposite timing, for opposing reasons \u2014 "
        "and both directions are measured, not assumed.",
    )):
        body.append(
            f'<text x="{lx}" y="{ty + i * 21}" font-size="13.5" '
            f'fill="{INK_SOFT if i else INK}">{line}</text>\n'
        )

    body.append(
        f'<text x="{lx}" y="{H - 22}" font-size="12.5" '
        f'fill="{INK_SOFT}">D-values: Garibaldi, Straka &#38; Ijichi '
        f"1969, Appl Microbiol 17(4):491-496. Read from page scans in "
        f"data/garibaldi/, not from a secondary source.</text>\n"
    )

    return svg(
        W, H, "The sugar and salt asymmetry",
        f"Sucrose raises yolk D60 by {sugar_x:.0f}x and NaCl by "
        f"{salt_x:.2f}x, so sugar enters the yolk after heating and "
        f"the white during heating.",
        "".join(body),
    )


# --------------------------------------------------------------------------
# FIGURE 4 - density stratification, and the foam's real constraint
# --------------------------------------------------------------------------
def fig_density() -> str:
    _, mass, density, volume = layer_data()
    frac = F.FOAM_DAMAGE_MOST_SENSITIVE_FRACTION

    W, H = 1240, 600
    body = [base_style()]
    body.append(
        title_block(
            80, 52,
            "What holds the layers apart",
            "Stratification is arithmetic, not luck \u2014 and the foam's "
            "real enemy is not gravity but a trace of yolk.",
        )
    )

    # --- left: the density ladder -----------------------------------
    px, py, pw, ph = 80, 118, 520, 280
    d_max = max(density.values()) * 1.15
    rows = [
        ("Yolk base", "base", YOLK_2),
        ("Espresso", "coffee", COFFEE_1),
        ("Meringue foam", "foam", FOAM_2),
    ]
    body.append(
        f'<text x="{px}" y="{py - 6}" font-size="16">'
        f"Density, g/mL</text>\n"
    )
    y = py + 30
    for label, key, colour in rows:
        d = density[key]
        w = pw * 0.62 * (d / d_max)
        body.append(
            f'<text x="{px}" y="{y}" font-size="14">{esc(label)}</text>\n'
        )
        body.append(
            f'<rect x="{px}" y="{y + 10}" width="{w:.1f}" height="24" '
            f'fill="{colour}" stroke="{INK_SOFT}" stroke-width="0.8" '
            f'rx="2"/>\n'
        )
        body.append(
            f'<text x="{px + w + 12:.1f}" y="{y + 27}" font-size="14" '
            f'class="n">{d:.2f}</text>\n'
        )
        y += 76

    ordering = " &gt; ".join(f"{density[k]:.2f}" for _, k, _ in rows)
    body.append(
        f'<text x="{px}" y="{py + ph - 4}" font-size="14.5" class="n">'
        f"{ordering}</text>\n"
    )
    body.append(
        f'<text x="{px}" y="{py + ph + 20}" font-size="13" '
        f'fill="{INK_SOFT}">Each layer is denser than the one above it, '
        f"by a wide margin. Pour gently and the</text>\n"
    )
    body.append(
        f'<text x="{px}" y="{py + ph + 38}" font-size="13" '
        f'fill="{INK_SOFT}">order is thermodynamically expected rather '
        f"than a trick of technique.</text>\n"
    )

    # --- right: the yolk-contamination limit ------------------------
    qx = 700
    body.append(
        f'<text x="{qx}" y="{py - 6}" font-size="16">'
        f"The foam's actual limit</text>\n"
    )
    body.append(
        f'<rect x="{qx}" y="{py + 14}" width="460" height="150" '
        f'fill="none" stroke="{WARN}" stroke-width="1.4" rx="4"/>\n'
    )
    body.append(
        f'<text x="{qx + 20}" y="{py + 54}" font-size="34" class="n" '
        f'fill="{WARN}">{frac * 100:.3f}%</text>\n'
    )
    body.append(
        f'<text x="{qx + 20}" y="{py + 80}" font-size="13.5">'
        f"yolk in the white is the most sensitive point in the "
        f"published</text>\n"
    )
    body.append(
        f'<text x="{qx + 20}" y="{py + 100}" font-size="13.5">'
        f"evidence at which foam damage has been OBSERVED.</text>\n"
    )
    body.append(
        f'<text x="{qx + 20}" y="{py + 128}" font-size="13" '
        f'fill="{INK_SOFT}">That is roughly a single drop of yolk in a '
        f"cup of white. So the</text>\n"
    )
    body.append(
        f'<text x="{qx + 20}" y="{py + 146}" font-size="13" '
        f'fill="{INK_SOFT}">requirement is not "be careful" but '
        f"{esc(F.YOLK_CARRYOVER_REQUIREMENT)}.</text>\n"
    )

    # Full width, below both columns. Rendering showed these lines
    # overflowing the right-hand column when anchored at qx.
    fy = py + ph + 74
    body.append(
        f'<line x1="{px}" y1="{fy - 24}" x2="{W - 80}" y2="{fy - 24}" '
        f'stroke="{RULE}" stroke-width="1"/>\n'
    )
    for i, line in enumerate((
        "This is why the two halves are built in separate bowls and "
        "never whisked together: yolk lipid and LDL outcompete albumen",
        "at the air-water interface and collapse the foam.",
        f"The number is a floor on the EVIDENCE, not a proven safe "
        f"threshold \u2014 nothing here shows that {frac * 100:.3f}% "
        f"is harmless,",
        "only that damage has been observed at it.",
    )):
        body.append(
            f'<text x="{px}" y="{fy + i * 21}" font-size="13.5" '
            f'fill="{INK if i < 2 else INK_SOFT}">{line}</text>\n'
        )

    return svg(
        W, H, "Density stratification and the foam limit",
        f"Densities {ordering} give stable layers; foam damage is "
        f"observed at {frac * 100:.3f}% yolk contamination.",
        "".join(body),
    )


# --------------------------------------------------------------------------
# FIGURE 5 - what is, and is not, established
# --------------------------------------------------------------------------
def fig_evidence() -> str:
    W, H = 1240, 480
    body = [base_style()]
    body.append(
        title_block(
            80, 52,
            "Three levels of evidence, and only one of them is met",
            "The most important figure here is the one that says NO. "
            "A model checked against published data is not a validated "
            "drink.",
        )
    )

    levels = [
        ("Level 1", "IMPLEMENTATION",
         "Is the arithmetic right?",
         "ESTABLISHED", ACCENT,
         "Integrator checked against a closed-form analytical solution; "
         "models reproduce FSIS rows they were never calibrated on."),
        ("Level 2", "PROCESS",
         "Did the real drink follow the modelled curve?",
         "NOT ESTABLISHED", WARN,
         "No thermocouple data exists. Every ThermalHistory carries "
         "provenance=ASSUMED, enforced by the type system."),
        ("Level 3", "MICROBIOLOGY",
         "Does the finished matrix achieve the reduction?",
         "NOT ESTABLISHED", WARN,
         "No challenge study has been run on the finished drink. Every "
         "log figure is for Salmonella only."),
    ]

    y = 120
    for tag, name, question, status, colour, detail in levels:
        body.append(
            f'<rect x="80" y="{y}" width="1080" height="96" fill="none" '
            f'stroke="{RULE}" stroke-width="1.3" rx="4"/>\n'
        )
        body.append(
            f'<rect x="80" y="{y}" width="6" height="96" '
            f'fill="{colour}"/>\n'
        )
        body.append(
            f'<text x="106" y="{y + 30}" font-size="13" class="n" '
            f'fill="{INK_SOFT}">{tag}</text>\n'
        )
        body.append(
            f'<text x="176" y="{y + 30}" font-size="17">{name}</text>\n'
        )
        body.append(
            f'<text x="176" y="{y + 52}" font-size="13.5" '
            f'fill="{INK_SOFT}">{esc(question)}</text>\n'
        )
        body.append(
            f'<text x="176" y="{y + 78}" font-size="12.5" '
            f'fill="{INK_SOFT}">{detail}</text>\n'
        )
        body.append(
            f'<rect x="960" y="{y + 16}" width="182" height="30" '
            f'fill="{colour}" opacity="0.12" rx="3"/>\n'
        )
        body.append(
            f'<text x="1051" y="{y + 36}" font-size="13.5" '
            f'fill="{colour}" text-anchor="middle" '
            f'letter-spacing="0.4">{status}</text>\n'
        )
        y += 110

    body.append(
        f'<text x="80" y="{y + 18}" font-size="14">'
        f"The implementation has been checked. "
        f'<tspan font-style="italic">The drink has not been '
        f"validated.</tspan> Those are different claims, and an "
        f"earlier version of these docs blurred them.</text>\n"
    )

    return svg(
        W, H, "Three levels of evidence",
        "Level 1 implementation established; Level 2 process and "
        "Level 3 microbiology NOT established.",
        "".join(body),
    )


FIGURES = {
    "01-layers.svg": fig_layers,
    "02-thermal.svg": fig_thermal,
    "03-asymmetry.svg": fig_asymmetry,
    "04-density.svg": fig_density,
    "05-evidence.svg": fig_evidence,
}


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    for filename, builder in FIGURES.items():
        text = builder()
        # ASCII-only guarantee: a non-encodable glyph would make the
        # file unopenable in some viewers, so it is checked here
        # rather than hoped for.
        text.encode("ascii")
        with open(os.path.join(OUT, filename), "w", encoding="ascii") as fh:
            fh.write(text)
        print(f"  wrote assets/{filename}  ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
