"""
Validation suite for the formulation engine.

These tests encode the published constraints that make or break the
drink. If one fails, the recipe is physically wrong - not merely
unfashionable.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from formulation import (  # noqa: E402
    SWISS_MERINGUE_HOLD_MINUTES,
    YOLK_SWEETENED_AFTER,
    ESPRESSO_PH_RANGE,
    FOAM_DAMAGE_THRESHOLD_YOLK_FRACTION,
    MERINGUE_SUGAR_TO_WHITE_RATIO,
    OPTIMAL_FOAM_PH,
    SWISS_MERINGUE_TARGET_C,
    WHITE_MASS_G,
    YOLK_CUSTARD_TARGET_C,
    YOLK_HOLD_MINUTES,
    YOLK_MASS_G,
    Recipe,
    assess_foam,
    build_sepid_o_zarrin,
    describe,
    foam_density_g_per_ml,
    sugar_percent_of_base,
    sugar_syrup_density_g_per_ml,
    will_layer_float,
)
from thermal_safety import (  # noqa: E402
    EGG_WHITE_PH78,
    EGG_YOLK_PLAIN,
    ThermalHistory,
    accumulated_log_reduction,
    assess,
    pessimistic_sugared_white,
)


def _foam_sugar_percent() -> float:
    """Sugar as % of total foam-layer mass, from the live recipe."""
    r = build_sepid_o_zarrin()
    return r.mass_of("caster sugar (foam)") / r.layer_mass_g("foam") * 100.0


# --------------------------------------------------------------------------
# The whole-egg premise
# --------------------------------------------------------------------------

def test_recipe_uses_both_yolk_and_white():
    """
    The entire purpose: nothing from the egg is discarded.

    The white now arrives in TWO places, because a few grams are diverted
    into the yolk base as its diluent (see YOLK_DILUENT_WHITE_G). The
    invariant is that the two portions still add up to the whole white -
    otherwise the "nothing wasted" premise quietly breaks.
    """
    from formulation import YOLK_DILUENT_WHITE_G

    r = build_sepid_o_zarrin()
    assert r.mass_of("egg yolk") == YOLK_MASS_G

    foam_white = r.mass_of("egg white")
    base_white = r.mass_of("egg white (base diluent)")
    assert base_white == YOLK_DILUENT_WHITE_G
    assert abs(foam_white + base_white - WHITE_MASS_G) < 1e-9, (
        f"white accounting leak: {foam_white} + {base_white} != "
        f"{WHITE_MASS_G}"
    )


def test_recipe_uses_a_realistic_single_egg():
    """
    Total egg mass must be consistent with ONE large egg, otherwise the
    'zero waste from your existing zabaione' premise breaks.
    """
    r = build_sepid_o_zarrin()
    egg_total = r.mass_of("egg yolk") + r.mass_of("egg white")
    assert 45.0 <= egg_total <= 60.0, f"egg total {egg_total} g"


def test_white_is_the_larger_fraction():
    """
    A large egg's white outweighs its yolk roughly 2:1. This is exactly
    why discarding the white is such a waste, and the recipe must
    reflect the real proportion.
    """
    r = build_sepid_o_zarrin()
    assert r.mass_of("egg white") > r.mass_of("egg yolk")


# --------------------------------------------------------------------------
# Foam integrity: the make-or-break constraint
# --------------------------------------------------------------------------

def test_clean_separation_gives_viable_foam():
    """With no yolk carryover the foam must be assessed as viable."""
    r = build_sepid_o_zarrin()
    a = assess_foam(
        white_g=r.mass_of("egg white"),
        sugar_in_foam_g=r.mass_of("caster sugar (foam)"),
        yolk_carryover_g=0.0,
        ph_estimate=OPTIMAL_FOAM_PH,
    )
    assert a.foam_will_survive, a.render()
    assert not a.warnings, a.warnings


def test_half_gram_yolk_carryover_is_flagged():
    """
    0.5 g yolk in 35 g white is ~1.4% w/w - nearly triple the 0.5%
    level at which Li et al. 2021 measured significant foam loss.
    The engine must refuse this, because visually it looks like a
    trivial smear that a home cook would ignore.
    """
    a = assess_foam(
        white_g=WHITE_MASS_G,
        sugar_in_foam_g=28.0,
        yolk_carryover_g=0.5,
        ph_estimate=OPTIMAL_FOAM_PH,
    )
    assert not a.foam_will_survive
    assert any("carryover" in w for w in a.warnings)


def test_yolk_carryover_evidence_points_match_published_values():
    """
    Guard BOTH published damage observations against silent drift.

    This test replaces one that asserted a single "threshold" of 0.005.
    That framing was the bug: it implied anything under 0.5% was
    acceptable, when Wang & Wang 2009 measured significant foaming loss
    at 0.022% - roughly 23x lower. Verified against the primary source.
    """
    from formulation import (
        FOAM_DAMAGE_MOST_SENSITIVE_FRACTION,
        YOLK_CARRYOVER_EVIDENCE_POINTS,
        YOLK_CARRYOVER_REQUIREMENT,
    )

    assert set(YOLK_CARRYOVER_EVIDENCE_POINTS) == {0.00022, 0.005}
    for frac, cite in YOLK_CARRYOVER_EVIDENCE_POINTS.items():
        assert 0.0 < frac < 1.0
        assert len(cite) > 40, "each datapoint must carry its citation"

    # The operative constant must be the MOST SENSITIVE observation,
    # not the most convenient one.
    assert FOAM_DAMAGE_MOST_SENSITIVE_FRACTION == 0.00022
    assert FOAM_DAMAGE_MOST_SENSITIVE_FRACTION == min(
        YOLK_CARRYOVER_EVIDENCE_POINTS
    )

    # And the operational rule must be a rule, not a tolerance.
    assert "zero" in YOLK_CARRYOVER_REQUIREMENT.lower()


def test_deprecated_threshold_alias_took_the_safe_value():
    """
    The old name survives, but must carry the SAFER value.

    Keeping backwards compatibility by preserving 0.005 would have
    preserved the error, so the alias deliberately changed value.
    """
    from formulation import FOAM_DAMAGE_MOST_SENSITIVE_FRACTION

    assert FOAM_DAMAGE_THRESHOLD_YOLK_FRACTION == (
        FOAM_DAMAGE_MOST_SENSITIVE_FRACTION
    )
    assert FOAM_DAMAGE_THRESHOLD_YOLK_FRACTION < 0.005


def test_any_yolk_carryover_is_flagged_even_below_published_levels():
    """
    Sub-0.022% carryover must still warn.

    The most sensitive published observation is ~8 mg in 35 g of white -
    below kitchen detection. So "under the threshold" cannot be treated
    as "fine"; absence of evidence of damage is not evidence of absence.
    """
    tiny = assess_foam(
        white_g=35.0,
        sugar_in_foam_g=28.0,
        yolk_carryover_g=0.001,  # 0.0029% - below both datapoints
        ph_estimate=OPTIMAL_FOAM_PH,
    )
    assert tiny.warnings, "any detected yolk must produce a warning"
    joined = " ".join(tiny.warnings)
    assert "NOT evidence of safety" in joined
    assert "re-separate" in joined

    # Zero carryover, by contrast, must be silent on that axis.
    clean = assess_foam(
        white_g=35.0,
        sugar_in_foam_g=28.0,
        yolk_carryover_g=0.0,
        ph_estimate=OPTIMAL_FOAM_PH,
    )
    assert not any("carryover" in w for w in clean.warnings)


def test_wang_and_wang_level_is_cited_when_crossed():
    """At >=0.022% the warning must name the more sensitive study."""
    a = assess_foam(
        white_g=35.0,
        sugar_in_foam_g=28.0,
        yolk_carryover_g=0.0077,  # ~0.022%
        ph_estimate=OPTIMAL_FOAM_PH,
    )
    joined = " ".join(a.warnings)
    assert "0.022%" in joined
    assert "Wang" in joined


def test_foam_sugar_ratio_is_within_structural_optimum():
    """Sugar:white must not exceed the 2:1 meringue ceiling."""
    r = build_sepid_o_zarrin()
    ratio = r.mass_of("caster sugar (foam)") / r.mass_of("egg white")
    assert ratio <= MERINGUE_SUGAR_TO_WHITE_RATIO, f"ratio {ratio:.2f}"
    # And it should be enough to actually build structure.
    assert ratio >= 0.5, f"ratio {ratio:.2f} too low for stable meringue"


def test_excessive_sugar_is_flagged():
    """A 3:1 sugar load must produce a warning, not silent acceptance."""
    a = assess_foam(
        white_g=35.0,
        sugar_in_foam_g=105.0,
        yolk_carryover_g=0.0,
        ph_estimate=OPTIMAL_FOAM_PH,
    )
    assert any("2:1" in w or "ratio" in w for w in a.warnings)


def test_out_of_band_ph_is_flagged():
    """Alkaline egg white (fresh, pH ~8.6-9.5) must trigger a warning."""
    a = assess_foam(
        white_g=35.0,
        sugar_in_foam_g=28.0,
        yolk_carryover_g=0.0,
        ph_estimate=9.0,
    )
    assert any("pH" in w for w in a.warnings)


def test_espresso_ph_sits_near_the_foam_optimum():
    """
    The design leans on the coffee itself as the acidifier. Verify the
    published espresso pH range really is close to the pH 4.8 optimum,
    rather than assuming it.
    """
    low, high = ESPRESSO_PH_RANGE
    assert low < 5.2 and high < 5.3
    assert abs(low - OPTIMAL_FOAM_PH) < 0.5


def test_assess_foam_rejects_nonsense_input():
    for kwargs in (
        dict(white_g=0.0, sugar_in_foam_g=10.0, yolk_carryover_g=0.0, ph_estimate=5.0),
        dict(white_g=35.0, sugar_in_foam_g=10.0, yolk_carryover_g=-1.0, ph_estimate=5.0),
    ):
        try:
            assess_foam(**kwargs)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {kwargs}")


# --------------------------------------------------------------------------
# Layering physics: the drink must actually stratify
# --------------------------------------------------------------------------

def test_foam_is_far_less_dense_than_coffee():
    """Meringue foam must float on espresso, not sink into it."""
    foam = foam_density_g_per_ml(overrun_percent=200.0)
    espresso = 1.01
    assert will_layer_float(foam, espresso), f"foam {foam:.3f} g/mL"
    assert foam < 0.5


def test_higher_overrun_gives_lighter_foam():
    """Monotonicity check on the overrun-density relation."""
    assert foam_density_g_per_ml(400.0) < foam_density_g_per_ml(100.0)


def test_sweet_yolk_base_is_denser_than_espresso():
    """
    The base must sit UNDER the coffee. With 14 g sugar in a 38.2 g base
    the estimated syrup density is comfortably above espresso's, so
    stratification is EXPECTED to be robust rather than lucky.

    Note the wording: this is a rule-of-thumb density estimate, not a
    measurement. An earlier draft called the stack "thermodynamically
    stable", which overstated a back-of-envelope calculation.
    """
    r = build_sepid_o_zarrin()
    base_mass = r.layer_mass_g("base")
    sugar = r.mass_of("caster sugar (base)")
    brix = sugar / base_mass * 100.0
    base_density = sugar_syrup_density_g_per_ml(brix)
    espresso = 1.01
    assert base_density > espresso, (
        f"base {base_density:.3f} g/mL vs espresso {espresso}"
    )


def test_full_stack_orders_correctly():
    """base (densest) < coffee < foam (lightest), bottom to top."""
    r = build_sepid_o_zarrin()
    brix = r.mass_of("caster sugar (base)") / r.layer_mass_g("base") * 100.0
    base = sugar_syrup_density_g_per_ml(brix)
    coffee = 1.01
    foam = foam_density_g_per_ml(200.0)
    assert base > coffee > foam


def test_syrup_density_rejects_out_of_range_brix():
    try:
        sugar_syrup_density_g_per_ml(90.0)
    except ValueError:
        return
    raise AssertionError("expected ValueError for 90 Brix")


def test_foam_density_rejects_negative_overrun():
    try:
        foam_density_g_per_ml(-10.0)
    except ValueError:
        return
    raise AssertionError("expected ValueError for negative overrun")


# --------------------------------------------------------------------------
# Cross-module: the recipe's own thermal steps must pass FSIS targets
# --------------------------------------------------------------------------

def test_recipe_yolk_step_is_pasteurized():
    """
    The recipe's declared yolk step must clear 5 log10 against the
    FSIS-calibrated yolk model. Reads the live constants, so the
    formulation and the safety engine cannot drift apart.
    """
    history = ThermalHistory(
        times_min=[0.0, 2.0, 2.0 + YOLK_HOLD_MINUTES],
        temps_c=[20.0, YOLK_CUSTARD_TARGET_C, YOLK_CUSTARD_TARGET_C],
        label="recipe yolk step",
    )
    verdict = assess("recipe yolk base", history, EGG_YOLK_PLAIN, target_log=5.0)
    assert verdict.is_safe, verdict.render()


def test_recipe_white_step_survives_pessimistic_sugar_assumption():
    """
    The white cannot be pasteurized plain - it would coagulate
    (Garibaldi Fig. 5). So it must clear 5 log10 in a SWEETENED matrix.

    Since no published D-value exists for ~44% sucrose egg white, the
    step is stress-tested against a deliberately harsh compounding
    extrapolation. Passing that is the strongest claim available without
    our own microbiology.
    """
    foam_sugar_pct = _foam_sugar_percent()
    pess = pessimistic_sugared_white(foam_sugar_pct)

    history = ThermalHistory(
        times_min=[
            0.0,
            3.0,
            3.0 + SWISS_MERINGUE_HOLD_MINUTES,
        ],
        temps_c=[20.0, SWISS_MERINGUE_TARGET_C, SWISS_MERINGUE_TARGET_C],
        label="recipe white step",
    )
    achieved = accumulated_log_reduction(history, pess)
    assert achieved >= 5.0, (
        f"white step yields only {achieved:.2f} log10 at "
        f"{foam_sugar_pct:.1f}% sugar under the pessimistic model"
    )


def test_white_step_temperature_is_high_enough_to_be_robust():
    """
    Guards the decision to keep 71 C rather than lowering it. At our
    actual sugar level the pessimistic model must need well under a
    minute at the specified temperature.
    """
    pess = pessimistic_sugared_white(_foam_sugar_percent())
    needed = pess.minutes_for_target(SWISS_MERINGUE_TARGET_C, 5.0)
    assert needed < 1.0, f"needs {needed:.2f} min - margin too thin"


def test_foam_sugar_far_exceeds_garibaldi_tested_concentration():
    """
    Honesty check. Garibaldi measured 10% sucrose; our foam is much
    sweeter, so the measured model is NOT conservative for us. This test
    exists so that fact stays visible rather than being forgotten.
    """
    assert _foam_sugar_percent() > 20.0


def test_yolk_target_exceeds_fsis_minimum_but_stays_below_scrambling():
    """
    The target must sit in the usable window: above the FSIS yolk
    pasteurization temperature (61.1 C) yet at or below ~65 C, where a
    PLAIN yolk begins to set.

    Note the changed reasoning: the yolk is now heated plain, so we can
    no longer lean on sugar raising the denaturation temperature. The
    ceiling is therefore the plain-yolk setting point, not a sweetened
    one.
    """
    assert YOLK_CUSTARD_TARGET_C > 61.1
    assert YOLK_CUSTARD_TARGET_C <= 65.0


def test_yolk_is_pasteurized_before_sugar_is_added():
    """
    THE CENTRAL PROCESS FIX.

    Sugar must not be present during the yolk kill step, because it
    raises Salmonella heat resistance roughly tenfold in yolk
    (Garibaldi 1969: D60 0.40 -> 4.0 min). The flag asserts the recipe
    sequences sugar AFTER heating.
    """
    assert YOLK_SWEETENED_AFTER is True


def test_base_sugar_note_documents_the_post_heat_addition():
    """
    The instruction must be carried in the recipe data itself, not only
    in prose docs, so it cannot drift out of sync.
    """
    note = build_sepid_o_zarrin().find("caster sugar (base)").note
    assert "AFTER pasteurization" in note
    assert "Garibaldi" in note


def test_base_sugar_concentration_is_high_enough_to_protect_protein():
    """
    Donovan's protective effect scales with sucrose concentration. The
    base should be a genuinely concentrated syrup, not lightly sweetened.
    """
    r = build_sepid_o_zarrin()
    pct = sugar_percent_of_base(r)
    assert pct > 30.0, f"base is only {pct:.1f}% sugar"


# --------------------------------------------------------------------------
# Recipe bookkeeping
# --------------------------------------------------------------------------

def test_total_mass_is_a_plausible_serving():
    r = build_sepid_o_zarrin()
    total = r.total_mass_g()
    assert 90.0 < total < 220.0, f"total {total:.1f} g"


def test_every_layer_is_populated():
    r = build_sepid_o_zarrin()
    for layer in ("base", "coffee", "foam", "garnish"):
        assert r.layer_mass_g(layer) > 0.0, f"{layer} empty"


def test_every_ingredient_documents_its_reason():
    """
    No unexplained ingredients. Anything in the glass must carry a note
    saying why it is there.
    """
    r = build_sepid_o_zarrin()
    missing = [i.name for i in r.ingredients if not i.note]
    assert not missing, f"undocumented ingredients: {missing}"


def test_layer_masses_sum_to_total():
    r = build_sepid_o_zarrin()
    parts = sum(r.layer_mass_g(l) for l in ("base", "coffee", "foam", "garnish"))
    assert abs(parts - r.total_mass_g()) < 1e-9


def test_recipe_rejects_negative_mass():
    r = Recipe("bad")
    try:
        r.add("impossible", -5.0, "base")
    except ValueError:
        return
    raise AssertionError("expected ValueError on negative mass")


def test_describe_renders_without_error():
    text = describe(build_sepid_o_zarrin())
    assert "Sepid-o-Zarrin" in text
    assert "egg white" in text
    assert "FOAM" in text


# --------------------------------------------------------------------------
# Kill-step matrix invariants
#
# These are the load-bearing tests for the Round-4 fix. The whole reason
# the yolk D-value models may be applied at all is that the matrix in the
# pan resembles the matrix they were measured on. If sugar or salt drifts
# back into the heat step, or the dilution changes, the models silently
# stop applying and every log10 figure in this repo becomes fiction.
# --------------------------------------------------------------------------


def test_only_whitelisted_ingredients_are_in_the_pan():
    """
    Nothing may be heated except yolk and its egg-white diluent.

    This is the single test that would fail if a future edit moved sugar
    or salt back before the heat step - the exact error this round was
    spent correcting. It asserts on the recipe object, not on a comment.
    """
    from formulation import PREHEAT_BASE_INGREDIENTS

    r = build_sepid_o_zarrin()
    base_items = [i for i in r.ingredients if i.layer == "base"]

    # Sanity: the whitelist must not be vacuous, or this test proves nothing.
    assert len(PREHEAT_BASE_INGREDIENTS) == 2
    heated = [i for i in base_items if i.name in PREHEAT_BASE_INGREDIENTS]
    assert len(heated) == 2, (
        f"expected exactly 2 heated ingredients, found {[i.name for i in heated]}"
    )

    # Every base ingredient NOT in the pan must say so in its note, so the
    # written recipe cannot contradict the model's assumption.
    for item in base_items:
        if item.name not in PREHEAT_BASE_INGREDIENTS:
            assert "AFTER pasteurization" in item.note, (
                f"{item.name!r} is excluded from the kill step but its note "
                f"does not say when it is added: {item.note!r}"
            )


def test_no_salt_is_present_during_the_yolk_kill_step():
    """
    Salt must be 0% of the pre-heat matrix.

    Garibaldi 1969 measured D60 for yolk rising from 0.40 to 5.1 min
    (12.75x) with 10% NaCl, and 9 CFR 590.570 Table I reclassifies yolk
    at >=2% salt into a category demanding 146 F instead of 142 F. Both
    reasons point the same way: keep salt out of the pan.
    """
    from formulation import preheat_salt_percent
    from thermal_safety import SALT_CATEGORY_THRESHOLD_PERCENT

    r = build_sepid_o_zarrin()
    salt_pct = preheat_salt_percent(r)

    assert salt_pct == 0.0, f"salt leaked into the kill step: {salt_pct}%"
    assert salt_pct < SALT_CATEGORY_THRESHOLD_PERCENT

    # The salt still exists in the drink - it was moved, not deleted.
    assert r.mass_of("fine salt (base)") > 0.0


def test_no_sugar_is_present_during_the_yolk_kill_step():
    """
    Sugar must likewise be absent from the pan.

    Same logic as salt: ~10x protection in yolk (Garibaldi 1969) and a
    stricter CFR row at >=2% sugar. The sugar is added off the heat.
    """
    from formulation import PREHEAT_BASE_INGREDIENTS, preheat_base_mass_g
    from thermal_safety import SUGAR_CATEGORY_THRESHOLD_PERCENT

    r = build_sepid_o_zarrin()
    sugar_in_pan = sum(
        i.grams
        for i in r.ingredients
        if i.layer == "base"
        and "sugar" in i.name
        and i.name in PREHEAT_BASE_INGREDIENTS
    )
    assert sugar_in_pan == 0.0

    pct = sugar_in_pan / preheat_base_mass_g(r) * 100.0
    assert pct < SUGAR_CATEGORY_THRESHOLD_PERCENT

    # But the sugar is definitely still in the drink.
    assert r.mass_of("caster sugar (base)") > 0.0


def test_preheat_matrix_matches_the_solids_garibaldi_measured():
    """
    The heated matrix must sit at ~43% egg solids.

    Garibaldi 1969 states its yolk was "diluted with egg white to
    approximately 43% egg solids". Diluting with water instead - as an
    earlier draft did - would have moved the matrix AWAY from the one the
    D-values came from while appearing to be a neutral thinning step.
    """
    from formulation import (
        GARIBALDI_YOLK_SOLIDS_TARGET,
        preheat_egg_solids_percent,
    )

    r = build_sepid_o_zarrin()
    solids = preheat_egg_solids_percent(r)
    target = GARIBALDI_YOLK_SOLIDS_TARGET * 100.0

    assert abs(solids - target) < 0.5, (
        f"pre-heat solids {solids:.2f}% deviates from Garibaldi's "
        f"{target:.1f}% by more than 0.5 points"
    )

    # Undiluted yolk would be materially further away - this is the
    # quantitative justification for diluting at all.
    from formulation import YOLK_SOLIDS_FRACTION

    undiluted_gap = abs(YOLK_SOLIDS_FRACTION * 100.0 - target)
    assert undiluted_gap > abs(solids - target), (
        "dilution must move the matrix closer to the measured composition"
    )


def test_preheat_mass_is_the_sum_of_its_heated_parts():
    """preheat_base_mass_g must be arithmetic, not a stored constant."""
    from formulation import YOLK_DILUENT_WHITE_G, preheat_base_mass_g

    r = build_sepid_o_zarrin()
    assert abs(
        preheat_base_mass_g(r) - (YOLK_MASS_G + YOLK_DILUENT_WHITE_G)
    ) < 1e-9


def test_yolk_step_passes_plain_yolk_cfr_row_but_not_the_salted_one():
    """
    The regulatory result that motivates the whole process change.

    9 CFR 590.570 Table I is law, not a model, so it needs no calibration
    window. Our 62 C / 10 min clears the "plain yolk" row (140 F / 6.2
    min) but falls 0.22 C short of the salt/sugar yolk row (144 F / 6.2
    min). That gap is precisely what salt-after-heat buys us.
    """
    from thermal_safety import f_to_c, meets_historical_cfr_row

    T, H = YOLK_CUSTARD_TARGET_C, YOLK_HOLD_MINUTES

    assert meets_historical_cfr_row("plain yolk", T, H) is True
    assert meets_historical_cfr_row("salt yolk (2-12% salt)", T, H) is False
    assert meets_historical_cfr_row("sugar yolk (>=2% sugar)", T, H) is False

    # Quantify the shortfall so the claim "0.2 C short" is checked, not
    # merely written down.
    shortfall = f_to_c(144.0) - T
    assert 0.15 < shortfall < 0.30, f"shortfall drifted to {shortfall:.3f} C"


def test_docstring_cross_checks_match_the_real_process():
    """
    Documentation-drift guard for the YOLK_HOLD_MINUTES docstring.

    An earlier draft quoted log10 figures computed with a 4.0 min ramp
    while the specified process uses 1.5 min. The quoted numbers were
    therefore too HIGH - drift in the flattering direction. This test
    recomputes them from the live constants and compares against the
    text, so the two cannot diverge again unnoticed.
    """
    import inspect

    import formulation
    from formulation import YOLK_RAMP_MINUTES, YOLK_STEP_CROSS_CHECKS
    from thermal_safety import (
        EGG_YOLK_PLAIN,
        YOLK_SALTED_10PCT,
        YOLK_SUGARED_10PCT,
    )

    history = ThermalHistory(
        times_min=[
            0.0,
            YOLK_RAMP_MINUTES,
            YOLK_RAMP_MINUTES + YOLK_HOLD_MINUTES,
        ],
        temps_c=[20.0, YOLK_CUSTARD_TARGET_C, YOLK_CUSTARD_TARGET_C],
    )

    models = (EGG_YOLK_PLAIN, YOLK_SUGARED_10PCT, YOLK_SALTED_10PCT)

    # 1. The machine-readable table must match the integrator exactly.
    assert set(YOLK_STEP_CROSS_CHECKS) == {m.name for m in models}, (
        "cross-check dict and the tested model set have diverged"
    )
    for model in models:
        actual = accumulated_log_reduction(history, model)
        quoted = YOLK_STEP_CROSS_CHECKS[model.name]
        assert abs(actual - quoted) < 0.005, (
            f"{model.name}: table says {quoted}, code computes {actual:.4f}"
        )

    # 2. The human-readable prose must agree with the dict, since that is
    #    what a reader actually sees. The prose lives as a bare string
    #    literal, so it is read from the module source.
    source = inspect.getsource(formulation)
    table = source.split("MODEL CROSS-CHECKS")[-1].split('"""')[0]

    assert f"{YOLK_RAMP_MINUTES} min ramp" in table, (
        "cross-check prose must state the ramp it was computed with"
    )
    for value in YOLK_STEP_CROSS_CHECKS.values():
        assert f"{value:.2f}" in table, (
            f"{value:.2f} is in the dict but missing from the prose table"
        )

    # 3. The retired, over-flattering 4.0 min-ramp figures must not be
    #    presented as live results anywhere in the table.
    for stale in ("8.08", "6.65", "5.44"):
        assert f"->  {stale}" not in table, (
            f"stale 4.0 min-ramp figure {stale} is still presented as live"
        )

    # 4. Guard the guard: if the ramp constant were ever raised back to
    #    4.0 min, the recomputed values would move by a detectable amount,
    #    so this test genuinely constrains the process.
    inflated = ThermalHistory(
        times_min=[0.0, 4.0, 4.0 + YOLK_HOLD_MINUTES],
        temps_c=[20.0, YOLK_CUSTARD_TARGET_C, YOLK_CUSTARD_TARGET_C],
    )
    drift = accumulated_log_reduction(
        inflated, EGG_YOLK_PLAIN
    ) - accumulated_log_reduction(history, EGG_YOLK_PLAIN)
    assert drift > 0.1, (
        "the ramp length must measurably affect lethality, otherwise this "
        f"drift test proves nothing (observed {drift:.4f})"
    )


# --------------------------------------------------------------------------
# Manual runner
# --------------------------------------------------------------------------

def _main() -> int:
    tests = [(n, o) for n, o in sorted(globals().items())
             if n.startswith("test_") and callable(o)]
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
