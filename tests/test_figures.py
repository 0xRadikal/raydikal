"""
FIGURE AUDIT: the pictures must agree with the code.

WHY THIS FILE EXISTS
====================
A diagram is the first thing a reader believes and the last thing
anyone re-checks. That combination is why this project's worst bug so
far was `report.py` printing "137 tests" long after the true figure was
145: a claim about the project's own rigour, stale, in the most
prominent position available.

README figures are that same hazard with a bigger blast radius. If
YOLK_HOLD_MINUTES changes and a hand-typed "10 min" stays inside an
SVG, the repository ships a false statement in the first thing a
visitor sees, and every numeric test still passes because none of them
has ever looked at a picture.

So the figures are GENERATED from the same constants the recipe uses
(tools/make_figures.py), and these tests close the loop:

  * the committed SVGs must be byte-identical to a fresh generation,
    so a hand-edited figure cannot survive
  * the numbers visible in them must equal the numbers in the modules
  * they must be safe and self-contained, because GitHub renders
    README SVG inside an <img> where remote references silently fail

WHAT THIS FILE CANNOT DO
========================
It cannot tell whether a figure is well designed, or whether its text
is honest prose. It only guarantees the figures cannot drift from the
code, and cannot smuggle in a remote reference or a script.
"""

from __future__ import annotations

import os
import re
import sys
import xml.dom.minidom

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

import formulation as F  # noqa: E402
import make_figures as MF  # noqa: E402
import thermal_safety as T  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(REPO, "assets")


def _read(name: str) -> str:
    with open(os.path.join(ASSETS, name), encoding="utf-8") as handle:
        return handle.read()


def _all() -> dict[str, str]:
    return {name: _read(name) for name in MF.FIGURES}


# --------------------------------------------------------------------------
# 1. The committed files must BE the generated files
# --------------------------------------------------------------------------
def test_committed_figures_match_a_fresh_generation():
    """
    The single most important test here.

    If someone opens an SVG and edits a number by hand, every other
    check in this file could still pass while the picture lies. This
    regenerates each figure in memory and demands byte equality, so
    the only way to change a figure is to change the code it is
    derived from.
    """
    for name, builder in MF.FIGURES.items():
        expected = builder()
        actual = _read(name)
        assert actual == expected, (
            f"assets/{name} differs from a fresh generation. Do not "
            f"edit figures by hand - change the constants and run "
            f"`python3 tools/make_figures.py`."
        )


def test_every_declared_figure_exists_and_is_non_trivial():
    for name in MF.FIGURES:
        path = os.path.join(ASSETS, name)
        assert os.path.isfile(path), f"missing assets/{name}"
        assert os.path.getsize(path) > 1200, f"assets/{name} is a stub"


def test_no_orphan_figures_in_the_assets_directory():
    """
    A figure nobody generates is a figure nobody checks - it would sit
    in assets/ drifting quietly, which is the exact failure mode this
    file exists to prevent.
    """
    on_disk = {f for f in os.listdir(ASSETS) if f.endswith(".svg")}
    declared = set(MF.FIGURES)
    assert on_disk == declared, (
        f"assets/ and FIGURES disagree. Only in assets: "
        f"{sorted(on_disk - declared)}; only declared: "
        f"{sorted(declared - on_disk)}"
    )


# --------------------------------------------------------------------------
# 2. Structural validity and safety
# --------------------------------------------------------------------------
def test_every_figure_is_well_formed_xml():
    for name in MF.FIGURES:
        try:
            doc = xml.dom.minidom.parseString(_read(name))
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"assets/{name} is not valid XML: {exc}")
        assert doc.documentElement.tagName == "svg"


def test_figures_carry_a_viewbox_and_accessible_text():
    """
    Without a viewBox the figure will not scale in a README column,
    and without <title> it is unreadable to a screen reader - the
    latter matters because these figures carry the safety caveats.
    """
    for name in MF.FIGURES:
        text = _read(name)
        assert "viewBox=" in text, f"{name} lacks a viewBox"
        assert "<title>" in text, f"{name} lacks a <title>"
        assert "<desc>" in text, f"{name} lacks a <desc>"
        assert 'role="img"' in text, f"{name} lacks role=img"


def test_figures_are_self_contained_and_inert():
    """
    GitHub renders README SVG inside an <img>: scripts do not run and
    remote references silently fail, so anything of the sort is either
    dead weight or a broken figure. Checked rather than assumed.
    """
    forbidden = (
        (r"<script", "script element"),
        (r"\son\w+\s*=", "event handler attribute"),
        (r"xlink:href", "xlink reference"),
        (r"\bhref\s*=", "href reference"),
        (r"url\(\s*['\"]?(?:https?:|//)", "remote url()"),
        (r"@import", "css @import"),
        (r"<image\b", "raster image element"),
        (r"<foreignObject", "foreignObject"),
        (r"data:", "data uri"),
    )
    for name in MF.FIGURES:
        text = _read(name)
        for pattern, label in forbidden:
            assert not re.search(pattern, text, re.IGNORECASE), (
                f"assets/{name} contains a {label}; README figures must "
                f"be inert and self-contained"
            )


def test_figures_are_pure_ascii():
    """
    Non-ASCII bytes have made these files unopenable in some viewers.
    The generator converts every such character to a numeric entity;
    this proves it did.
    """
    for name in MF.FIGURES:
        raw = open(os.path.join(ASSETS, name), "rb").read()
        non_ascii = [b for b in raw if b > 127]
        assert not non_ascii, (
            f"assets/{name} has {len(non_ascii)} non-ASCII bytes; the "
            f"generator should have emitted numeric entities"
        )


# --------------------------------------------------------------------------
# 3. The numbers in the pictures must be the numbers in the code
# --------------------------------------------------------------------------
def test_layer_figure_states_the_real_masses():
    text = _read("01-layers.svg")
    recipe = F.build_sepid_o_zarrin()
    mass: dict[str, float] = {}
    for ing in recipe.ingredients:
        mass[ing.layer] = mass.get(ing.layer, 0.0) + ing.grams

    for layer in ("base", "coffee", "foam"):
        needle = f"{mass[layer]:.2f} g"
        assert needle in text, (
            f"01-layers.svg does not show the {layer} mass {needle}"
        )
    assert f"{recipe.total_mass_g():.1f} g" in text, (
        "01-layers.svg does not show the real total mass"
    )


def test_layer_bands_are_proportional_to_computed_volume():
    """
    The bands must encode VOLUME, not numbers chosen to look right.

    This reads the rect heights back out of the SVG and compares their
    ratios against the computed volume ratios. A figure that showed
    three equal bands would pass every text check above and still
    misrepresent the drink.
    """
    text = _read("01-layers.svg")
    _, _, _, volume = MF.layer_data()
    total_v = sum(volume.values())

    heights = [
        float(h)
        for h in re.findall(r'<rect x="86" y="[\d.]+" width="218" '
                            r'height="([\d.]+)"', text)
    ]
    assert len(heights) == 3, (
        f"expected 3 layer bands, found {len(heights)}"
    )
    total_h = sum(heights)
    # SVG order is foam, coffee, base - the order rows are drawn in.
    for measured, key in zip(heights, ("foam", "coffee", "base")):
        want = volume[key] / total_v
        got = measured / total_h
        assert abs(got - want) < 0.005, (
            f"{key} band is {got:.3f} of the height but "
            f"{want:.3f} of the volume"
        )


def test_thermal_figure_states_the_real_step():
    text = _read("02-thermal.svg")
    assert f"{MF.fmt(F.YOLK_CUSTARD_TARGET_C)} &#176;C" in text, (
        "02-thermal.svg does not show the real target temperature"
    )
    assert f"hold {MF.fmt(F.YOLK_HOLD_MINUTES)} min" in text, (
        "02-thermal.svg does not show the real hold time"
    )
    assert f"{MF.fmt(F.YOLK_RAMP_MINUTES)}-minute ramp" in text, (
        "02-thermal.svg does not show the real ramp time"
    )
    # every cross-check figure must appear, to two decimals
    for value in F.YOLK_STEP_CROSS_CHECKS.values():
        assert f"{value:.2f}" in text, (
            f"02-thermal.svg omits the {value:.2f} log cross-check"
        )
    assert f"{MF.fmt(T.TARGET_LOG_DEFAULT)}-log target" in text


def test_asymmetry_figure_states_the_real_d_values():
    text = _read("03-asymmetry.svg")
    models = (
        T.YOLK_PLAIN_GARIBALDI,
        T.YOLK_SUGARED_10PCT,
        T.YOLK_SALTED_10PCT,
        T.WHITE_PLAIN_GARIBALDI,
        T.WHITE_SUGARED_10PCT,
    )
    for model in models:
        needle = f"D{model.t_ref_c:.0f}={model.d_ref_min:.2f}"
        assert needle in text, f"03-asymmetry.svg omits {needle}"

    # The salt multiplier is the headline number of the whole project.
    salt_x = T.YOLK_SALTED_10PCT.d_ref_min / T.YOLK_PLAIN_GARIBALDI.d_ref_min
    assert f"{salt_x:.2f}" in text, (
        f"03-asymmetry.svg omits the {salt_x:.2f}x salt multiplier"
    )

    # And the base sugar mass must be the BASE sugar, not the yolk mass:
    # an early draft printed the yolk mass here and it rendered wrong.
    base_sugar = F.build_sepid_o_zarrin().find("caster sugar (base)").grams
    assert f"{MF.fmt(base_sugar)} g of sugar" in text, (
        "03-asymmetry.svg does not state the real base sugar mass"
    )


def test_density_figure_states_the_real_densities_in_order():
    text = _read("04-density.svg")
    _, _, density, _ = MF.layer_data()
    for key in ("base", "coffee", "foam"):
        assert f"{density[key]:.2f}" in text, (
            f"04-density.svg omits the {key} density"
        )
    # the ordering claim must be present and TRUE
    assert density["base"] > density["coffee"] > density["foam"], (
        "the densities no longer stratify; the figure's claim is false"
    )
    ordering = " &gt; ".join(
        f"{density[k]:.2f}" for k in ("base", "coffee", "foam")
    )
    assert ordering in text, "04-density.svg lost its ordering statement"

    frac = F.FOAM_DAMAGE_MOST_SENSITIVE_FRACTION
    assert f"{frac * 100:.3f}%" in text, (
        "04-density.svg omits the foam-damage evidence point"
    )


def test_evidence_figure_says_no_twice():
    """
    The figure's whole purpose is to refuse a claim. If it ever shows
    three greens, it is lying about the project.
    """
    text = _read("05-evidence.svg")
    assert text.count("NOT ESTABLISHED") == 2, (
        "05-evidence.svg must mark Levels 2 and 3 NOT ESTABLISHED"
    )
    # "ESTABLISHED" also occurs inside "NOT ESTABLISHED", so count the
    # standalone badge by excluding the negated form.
    assert text.count("ESTABLISHED") - text.count("NOT ESTABLISHED") == 1, (
        "05-evidence.svg must mark exactly one level ESTABLISHED"
    )
    assert "has not been" in text, (
        "05-evidence.svg must state that the drink is not validated"
    )
    assert "provenance=ASSUMED" in text


def test_no_figure_claims_the_drink_is_validated():
    """
    The same prohibition the prose carries, applied to the pictures -
    which is where a reader is most likely to take a claim on trust.
    """
    # The negative lookbehinds are load-bearing. 04-density.svg says
    # "not a proven safe threshold", which is a DENIAL of exactly the
    # claim being policed - and the first version of this guard failed
    # on it. A guard that cannot tell an assertion from its refutation
    # would push an author to delete the caveat in order to go green,
    # making the figures less honest rather than more. Same lesson as
    # the prose quarantine logic in test_claim_surface.py.
    negation = r"(?<!not )(?<!never )(?<!not a )(?<!isn't )"
    forbidden = re.compile(
        negation + r"lab[- ]validated"
        r"|" + negation + r"laboratory[- ]validated"
        r"|" + negation + r"proven safe"
        r"|" + negation + r"guaranteed safe"
        r"|" + negation + r"validated (?:and )?safe",
        re.IGNORECASE,
    )
    for name in MF.FIGURES:
        text = _read(name)
        match = forbidden.search(text)
        assert not match, (
            f"assets/{name} claims validation: {match.group(0)!r}"
        )


def test_the_validation_claim_guard_knows_denial_from_assertion():
    """Guard the guard: it must fire on claims and not on refutations."""
    negation = r"(?<!not )(?<!never )(?<!not a )(?<!isn't )"
    forbidden = re.compile(
        negation + r"lab[- ]validated"
        r"|" + negation + r"laboratory[- ]validated"
        r"|" + negation + r"proven safe"
        r"|" + negation + r"guaranteed safe"
        r"|" + negation + r"validated (?:and )?safe",
        re.IGNORECASE,
    )
    for claim in (
        "this drink is lab-validated",
        "the process is proven safe",
        "guaranteed safe for pregnancy",
        "the result is validated and safe to serve",
    ):
        assert forbidden.search(claim), f"guard missed {claim!r}"
    for denial in (
        "not a proven safe threshold",
        "this is not lab-validated",
        "never proven safe",
        "the drink has not been validated",
        "no challenge study has been run",
    ):
        assert not forbidden.search(denial), (
            f"guard wrongly fired on the denial {denial!r}"
        )


# --------------------------------------------------------------------------
# 4. The README must actually use them
# --------------------------------------------------------------------------
def test_readme_references_every_figure():
    with open(os.path.join(REPO, "README.md"), encoding="utf-8") as handle:
        readme = handle.read()
    for name in MF.FIGURES:
        assert f"assets/{name}" in readme, (
            f"README.md does not embed assets/{name}; an unused figure "
            f"is an unchecked figure"
        )


def test_readme_figures_all_have_alt_text():
    """
    Every embedded figure needs alt text: these carry safety caveats,
    so a reader using a screen reader must not lose them.
    """
    with open(os.path.join(REPO, "README.md"), encoding="utf-8") as handle:
        readme = handle.read()
    for name in MF.FIGURES:
        for match in re.finditer(
            r'<img[^>]*src="[^"]*' + re.escape(name) + r'"[^>]*>', readme
        ):
            tag = match.group(0)
            alt = re.search(r'alt="([^"]*)"', tag)
            assert alt and alt.group(1).strip(), (
                f"the <img> for {name} has no alt text"
            )
        for match in re.finditer(
            r"!\[([^\]]*)\]\([^)]*" + re.escape(name) + r"\)", readme
        ):
            assert match.group(1).strip(), (
                f"the markdown image for {name} has empty alt text"
            )


# --------------------------------------------------------------------------
# Manual runner
# --------------------------------------------------------------------------
def _main() -> int:
    tests = [
        (n, o)
        for n, o in sorted(globals().items())
        if n.startswith("test_") and callable(o)
    ]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  FAIL  {name}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_main())
