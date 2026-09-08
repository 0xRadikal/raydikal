"""
Validation suite for the thermal-lethality engine.

The single most important tests here are the ones that make the engine
REPRODUCE the published FSIS Appendix III tables. If the engine cannot
regenerate the regulator's own numbers from an independent row, then any
safety claim it makes about the recipe is worthless.

Run with:  python3 -m pytest tests/ -v
       or:  python3 tests/test_thermal_safety.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from thermal_safety import (  # noqa: E402
    SUBDIVISION_STEPS,
    EGG_WHITE_PH78,
    EGG_YOLK_PLAIN,
    Evidence,
    GARIBALDI_EQUIVALENCE_POINTS_F,
    MAX_CREDITED_LOG,
    SUCROSE_PROTECTION_PER_10PCT,
    WHITE_PLAIN_GARIBALDI,
    WHITE_SUGARED_10PCT,
    YOLK_PLAIN_GARIBALDI,
    YOLK_SUGARED_10PCT,
    YOLK_SALTED_10PCT,
    pessimistic_sugared_white,
    ESPRESSO_IN_CUP_C,
    ESPRESSO_IN_CUP_TOLERANCE_C,
    ESPRESSO_SHOT_MASS_G,
    YOLK_SPECIFIC_HEAT,
    ThermalHistory,
    accumulated_log_reduction,
    assess,
    c_to_f,
    equilibrium_mix_temperature,
    f_to_c,
    newtonian_mix_then_cool,
)


# --------------------------------------------------------------------------
# Unit conversions
# --------------------------------------------------------------------------

def _recipe_yolk_history() -> ThermalHistory:
    """
    The recipe's actual yolk thermal history, built from the live
    formulation constants.

    Tests use this instead of hardcoded temperatures so that changing the
    process cannot leave stale assertions quietly passing - which is
    exactly what happened when the target moved from 64 C to 62 C.
    """
    from formulation import (
        YOLK_CUSTARD_TARGET_C,
        YOLK_HOLD_MINUTES,
        YOLK_RAMP_MINUTES,
    )

    ramp_min = YOLK_RAMP_MINUTES
    return ThermalHistory(
        times_min=[0.0, ramp_min, ramp_min + YOLK_HOLD_MINUTES],
        temps_c=[20.0, YOLK_CUSTARD_TARGET_C, YOLK_CUSTARD_TARGET_C],
        label="recipe yolk step",
    )


def test_unit_conversions_are_exact():
    assert abs(f_to_c(32.0) - 0.0) < 1e-9
    assert abs(f_to_c(212.0) - 100.0) < 1e-9
    # FSIS quotes 134 F as 56.7 C
    assert abs(f_to_c(134.0) - 56.666) < 0.01
    # FSIS quotes 140 F as 60.0 C
    assert abs(f_to_c(140.0) - 60.0) < 0.01
    # FSIS quotes 142 F as 61.1 C
    assert abs(f_to_c(142.0) - 61.11) < 0.01
    assert abs(c_to_f(f_to_c(150.0)) - 150.0) < 1e-9


# --------------------------------------------------------------------------
# CRITICAL: reproduce the published FSIS tables
# --------------------------------------------------------------------------

def test_egg_white_model_reproduces_unused_fsis_row():
    """
    The egg-white model was calibrated on the 132.0 F and 134.0 F rows.
    The 133.0 F / 22.56 min row was NOT used in calibration, so it is a
    genuine hold-out test of the D-z model against FSIS Appendix III.A.
    """
    predicted = EGG_WHITE_PH78.minutes_for_target(f_to_c(133.0), 5.7)
    published = 22.56
    rel_err = abs(predicted - published) / published
    assert rel_err < 0.05, (
        f"model predicts {predicted:.2f} min vs FSIS {published} min "
        f"(relative error {rel_err:.1%})"
    )


def test_egg_yolk_model_reproduces_unused_fsis_row():
    """
    The yolk model was calibrated on the 139.0 F and 150.0 F rows.
    The 142.0 F / 10.48 min row is a hold-out test against Appendix III.C.
    """
    predicted = EGG_YOLK_PLAIN.minutes_for_target(f_to_c(142.0), 6.2)
    published = 10.48
    rel_err = abs(predicted - published) / published
    assert rel_err < 0.10, (
        f"model predicts {predicted:.2f} min vs FSIS {published} min "
        f"(relative error {rel_err:.1%})"
    )


def test_yolk_model_is_consistent_with_table_1_safe_harbour():
    """
    FSIS Table 1 safe harbour for plain yolk: 142 F (61.1 C) / 3.5 min.
    Appendix III.C requires 10.48 min at the same temperature for 6.2 log.
    Therefore 3.5 min at 61.1 C should land in the 2-3 log range.
    This cross-check confirms the two FSIS tables target different
    lethality levels, exactly as the guideline states.
    """
    achieved = EGG_YOLK_PLAIN.log_reduction_isothermal(f_to_c(142.0), 3.5)
    assert 1.5 < achieved < 3.5, f"got {achieved:.2f} log10"


def test_derived_z_values_are_physically_plausible():
    """
    Salmonella z-values in egg matrices are typically ~4-10 C.
    A model whose z falls outside that band would indicate a
    calibration or transcription error.
    """
    assert 3.0 < EGG_WHITE_PH78.z_c < 12.0, EGG_WHITE_PH78.z_c
    assert 3.0 < EGG_YOLK_PLAIN.z_c < 12.0, EGG_YOLK_PLAIN.z_c


def test_yolk_is_more_heat_resistant_than_white():
    """
    Yolk lipids and solids protect Salmonella, so yolk needs a HIGHER
    temperature than white for equivalent lethality. This is why FSIS
    pasteurizes white at 56.7 C but yolk at 61.1 C. If our models had
    this backwards, they would be wrong.
    """
    d_white = EGG_WHITE_PH78.d_at(60.0)
    d_yolk = EGG_YOLK_PLAIN.d_at(60.0)
    assert d_yolk > d_white, (
        f"yolk D={d_yolk:.3f} should exceed white D={d_white:.3f} at 60 C"
    )


# --------------------------------------------------------------------------
# The historic 134 F / 3.5 min egg-white trap
# --------------------------------------------------------------------------

def test_historic_egg_white_process_does_not_reach_5_log():
    """
    FSIS states explicitly that the former egg-white process
    (134 F / 3.5 min) does NOT achieve the same lethality as other
    liquid egg products. Our engine must independently show that this
    process falls well short of 5 log10, or we would be repeating a
    dangerous misreading of the old regulation.
    """
    achieved = EGG_WHITE_PH78.log_reduction_isothermal(f_to_c(134.0), 3.5)
    assert achieved < 5.0, (
        f"engine claims {achieved:.2f} log10 for the historic process; "
        "FSIS says it is insufficient"
    )


# --------------------------------------------------------------------------
# Non-isothermal integration
# --------------------------------------------------------------------------

def test_integrator_is_converged_not_just_coarse():
    """
    REGRESSION GUARD for the numerical bug an external reviewer found.

    The original integrator applied the trapezoidal rule directly to the
    caller's segment endpoints. Because the lethal rate 1/D(T) is
    EXPONENTIAL in temperature, a straight line from the rate at 20 C to
    the rate at 62 C sits far above the true curve, crediting lethality
    that never occurred. On this project's own yolk step the old method
    overstated the result by ~0.95 log10 - in the UNSAFE direction.

    A mutation test showed that simply fixing SUBDIVISION_STEPS was not
    enough: setting it back to 1 still passed every other test. This
    test closes that hole by demanding the default be converged.
    """
    history = _recipe_yolk_history()

    coarse = accumulated_log_reduction(history, EGG_YOLK_PLAIN, steps_per_segment=1)
    default = accumulated_log_reduction(history, EGG_YOLK_PLAIN)
    fine = accumulated_log_reduction(history, EGG_YOLK_PLAIN, steps_per_segment=8192)

    # The default must agree with a very fine integration.
    assert abs(default - fine) < 0.01, (
        f"default integration ({default:.4f}) has not converged; "
        f"8192-step reference is {fine:.4f}. Is SUBDIVISION_STEPS too low?"
    )

    # And the coarse method must be demonstrably worse, confirming the
    # bug was real rather than hypothetical.
    assert coarse - fine > 0.1, (
        "the 1-step method no longer overstates lethality; if the model "
        "changed, re-derive whether subdivision is still required"
    )

    # The error direction matters: coarse OVERSTATES safety.
    assert coarse > fine


def test_subdivision_default_is_high_enough():
    """
    Directly pin the constant. Kills the mutation where someone lowers
    SUBDIVISION_STEPS and every other test still passes.
    """
    assert SUBDIVISION_STEPS >= 128, (
        f"SUBDIVISION_STEPS={SUBDIVISION_STEPS} is too low for a "
        "converged exponential integral"
    )


def test_integrator_rejects_zero_steps():
    try:
        accumulated_log_reduction(
            _recipe_yolk_history(), EGG_YOLK_PLAIN, steps_per_segment=0
        )
    except ValueError:
        return
    raise AssertionError("expected ValueError for steps_per_segment=0")


def test_isothermal_history_matches_closed_form():
    """A flat history must agree with the analytic isothermal result."""
    temp = f_to_c(134.0)
    minutes = 15.43
    history = ThermalHistory(
        times_min=[0.0, minutes],
        temps_c=[temp, temp],
        label="flat",
    )
    integrated = accumulated_log_reduction(history, EGG_WHITE_PH78)
    closed_form = EGG_WHITE_PH78.log_reduction_isothermal(temp, minutes)
    assert abs(integrated - closed_form) < 1e-6


def test_sub_lethal_temperatures_are_not_credited():
    """Holding at 40 C for an hour must earn zero credited lethality."""
    history = ThermalHistory(
        times_min=[0.0, 60.0],
        temps_c=[40.0, 40.0],
        label="warm but not lethal",
    )
    assert accumulated_log_reduction(history, EGG_WHITE_PH78) == 0.0


def test_lethality_is_monotonic_in_time():
    """Longer holds at the same temperature must never reduce lethality."""
    temp = 57.0
    short = ThermalHistory([0.0, 5.0], [temp, temp])
    long = ThermalHistory([0.0, 20.0], [temp, temp])
    assert accumulated_log_reduction(long, EGG_WHITE_PH78) > accumulated_log_reduction(
        short, EGG_WHITE_PH78
    )


# --------------------------------------------------------------------------
# The core physical claim: espresso cannot pasteurize a yolk
# --------------------------------------------------------------------------

def test_espresso_in_cup_constant_matches_published_standard():
    """
    Guard against the exact mistake this project already made once:
    substituting the 88 C brew-water temperature for the in-cup
    beverage temperature. INEI specifies 67 +/- 3 C in the cup.
    """
    assert ESPRESSO_IN_CUP_C == 67.0
    assert ESPRESSO_IN_CUP_TOLERANCE_C == 3.0
    # It must be nowhere near the group-head brew temperature.
    assert ESPRESSO_IN_CUP_C < 80.0


def test_espresso_mixing_temperature_is_below_yolk_pasteurization():
    """
    Energy balance for the classic zabaione build, using the PUBLISHED
    in-cup espresso temperature rather than the brew temperature:

        30 g espresso at 67 C  +  18 g yolk/sugar base at 20 C

    The vessel's heat capacity is ignored, which makes this an UPPER
    bound on the real mixture temperature. Even so it lands far below
    the 61.1 C that FSIS requires for yolk.
    """
    t_mix = equilibrium_mix_temperature(
        masses_g=[ESPRESSO_SHOT_MASS_G, 18.0],
        temps_c=[ESPRESSO_IN_CUP_C, 20.0],
        specific_heats=[1.0, YOLK_SPECIFIC_HEAT],
    )
    assert t_mix < 61.1, f"mix reached {t_mix:.1f} C"


def test_espresso_mix_stays_unsafe_even_at_the_hottest_tolerance():
    """
    Worst-case / adversarial scenario. Stack every assumption in favour
    of the mixture being hot:
      * espresso at the TOP of the INEI tolerance band (70 C)
      * a pre-warmed yolk base at 30 C rather than fridge-cold
      * a large 40 g shot

    Even in this deliberately stacked case the mixture must not reach
    the yolk pasteurization temperature. If this test ever fails, the
    "espresso alone cannot pasteurize" claim needs re-examining rather
    than repeating.
    """
    t_mix = equilibrium_mix_temperature(
        masses_g=[40.0, 18.0],
        temps_c=[ESPRESSO_IN_CUP_C + ESPRESSO_IN_CUP_TOLERANCE_C, 30.0],
        specific_heats=[1.0, YOLK_SPECIFIC_HEAT],
    )
    assert t_mix < 61.1, f"even the stacked worst case reached {t_mix:.1f} C"


def test_espresso_poured_on_yolk_fails_pasteurization():
    """
    THE HEADLINE SAFETY RESULT.

    Model the real cup: mixture starts at its equilibrium temperature
    and cools by Newton's law. Even generously assuming a slow cooling
    constant and integrating for a full 10 minutes, the accumulated
    lethality is nowhere near 5 log10.

    Conclusion: the traditional cafe zabaione / egg-yolk latte is a
    RAW EGG drink. Any recipe we publish must pasteurize deliberately
    rather than pretend the espresso did the job.
    """
    t_mix = equilibrium_mix_temperature(
        masses_g=[ESPRESSO_SHOT_MASS_G, 18.0],
        temps_c=[ESPRESSO_IN_CUP_C, 20.0],
        specific_heats=[1.0, YOLK_SPECIFIC_HEAT],
    )
    history = newtonian_mix_then_cool(
        t_start_c=t_mix,
        t_ambient_c=22.0,
        cooling_constant_per_min=0.08,  # deliberately slow = generous
        total_min=10.0,
        label="espresso on yolk, cooling in cup",
    )
    verdict = assess(
        "traditional zabaione (espresso poured on raw yolk)",
        history,
        EGG_YOLK_PLAIN,
        target_log=5.0,
    )
    assert not verdict.is_safe
    assert verdict.achieved_log < 0.5, (
        f"claimed {verdict.achieved_log:.2f} log10 - too high to be credible"
    )


def test_yolk_latte_peak_temperature_is_deceptively_high():
    """
    An honest, initially surprising result worth recording.

    The egg-yolk latte adds ~150 g of steamed milk at ~65 C. Unlike the
    plain zabaione, this DOES push the mixture past 61.1 C:

        30 g espresso @ 67 C + 18 g yolk base @ 20 C + 150 g milk @ 65 C
        -> ~61.7 C

    So a naive "is it hot enough?" check would wrongly pass this drink.
    The peak temperature is NOT the safety criterion - see the next test.
    """
    t_mix = equilibrium_mix_temperature(
        masses_g=[ESPRESSO_SHOT_MASS_G, 18.0, 150.0],
        temps_c=[ESPRESSO_IN_CUP_C, 20.0, 65.0],
        specific_heats=[1.0, YOLK_SPECIFIC_HEAT, 0.95],
    )
    assert t_mix > 61.1, (
        "if this fails, the peak-temperature trap this test documents "
        "no longer exists and the docs should be updated"
    )


def test_yolk_latte_still_fails_because_it_has_no_hold_time():
    """
    THE POINT THAT PEAK TEMPERATURE HIDES.

    FSIS safe harbours are time-AT-temperature, not touch-temperature.
    Plain yolk needs 61.1 C sustained for 3.5 min (Table 1), or 10.48
    min for the full 6.2 log10 of Appendix III.C. A latte merely PASSES
    THROUGH ~61.7 C on its way to cooling down; it never holds there.

    Integrating the real cooling curve gives roughly 0.5-2 log10
    depending on how well the cup is insulated - far below the 5 log10
    requirement. This is why the recipe pasteurizes the yolk BEFORE it
    ever meets the coffee.
    """
    t_mix = equilibrium_mix_temperature(
        masses_g=[ESPRESSO_SHOT_MASS_G, 18.0, 150.0],
        temps_c=[ESPRESSO_IN_CUP_C, 20.0, 65.0],
        specific_heats=[1.0, YOLK_SPECIFIC_HEAT, 0.95],
    )
    # k = 0.03/min is an unrealistically well-insulated cup: generous.
    history = newtonian_mix_then_cool(
        t_start_c=t_mix,
        t_ambient_c=22.0,
        cooling_constant_per_min=0.03,
        total_min=15.0,
        label="yolk latte cooling in cup",
    )
    verdict = assess("egg-yolk latte as served", history, EGG_YOLK_PLAIN, target_log=5.0)
    assert not verdict.is_safe, verdict.render()
    assert verdict.achieved_log < 3.0, (
        f"claimed {verdict.achieved_log:.2f} log10 from a cooling cup"
    )


def test_true_isothermal_hold_at_latte_peak_would_take_minutes():
    """
    Quantify the gap: to actually earn 5 log10 at the latte's own peak
    temperature you would need a genuine multi-minute isothermal hold,
    which no open cup provides.
    """
    minutes = EGG_YOLK_PLAIN.minutes_for_target(61.7, 5.0)
    assert 3.0 < minutes < 20.0, f"got {minutes:.1f} min"


# --------------------------------------------------------------------------
# The designed process must pass
# --------------------------------------------------------------------------

def test_designed_yolk_process_passes_with_margin():
    """
    The designed yolk step, taken from the live recipe constants.

    Note the reasoning changed twice: the yolk is now heated PLAIN (so
    Donovan's sugar-stabilisation no longer applies) and the target was
    lowered so every cross-check model is in-window.
    """
    history = _recipe_yolk_history()
    verdict = assess("designed yolk base", history, EGG_YOLK_PLAIN, target_log=5.0)
    assert verdict.is_safe, verdict.render()
    assert verdict.margin_log > 0.5


def test_designed_white_process_passes_with_margin():
    """
    Designed white step (Swiss-meringue method): whisk white + sugar over
    a bain-marie to 71 C. Confirm that reaching 71 C with only a short
    dwell already clears 5 log10 comfortably, since the white model's
    D-value collapses far above its 56.7 C reference.
    """
    history = ThermalHistory(
        times_min=[0.0, 3.0, 4.0],
        temps_c=[20.0, 71.0, 71.0],
        label="white swiss meringue to 71 C",
    )
    verdict = assess("designed white foam", history, EGG_WHITE_PH78, target_log=5.0)
    assert verdict.is_safe, verdict.render()
    assert verdict.margin_log > 1.0


def test_60c_white_looks_fine_on_the_plain_model_which_is_the_trap():
    """
    Documents WHY the 60 C fallback was withdrawn.

    Against the PLAIN-white FSIS model, a 60 C / 10 min hold looks
    comfortably safe. That is exactly the trap: our foam is not plain
    white, it is ~44% sugar, and sugar protects Salmonella. The
    companion test test_sixty_degree_white_hold_has_too_thin_a_margin
    shows the
    same process losing its margin once sugar is accounted for.

    Keeping both tests side by side records the reasoning, so nobody
    reinstates the fallback by rerunning only the flattering model.
    """
    history = ThermalHistory(
        times_min=[0.0, 2.0, 12.0],
        temps_c=[20.0, 60.0, 60.0],
        label="white 60 C / 10 min, PLAIN model",
    )
    verdict = assess(
        "white gentle hold (plain-matrix model only)",
        history,
        EGG_WHITE_PH78,
        target_log=5.0,
    )
    # Passes on the plain model...
    assert verdict.is_safe
    # ...but 60 C is outside FSIS's egg-white calibration window, so it
    # is not audit-grade evidence even before the sugar issue.
    assert verdict.evidence is Evidence.MODELLED_EXTRAPOLATED
    assert not verdict.is_defensible


# --------------------------------------------------------------------------
# Input validation
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Honesty guards: no absurd extrapolated numbers
# --------------------------------------------------------------------------

def test_reported_lethality_is_never_absurd():
    """
    Regression test for a real bug found in this project.

    An earlier build reported "12020.03 log10" for the 71 C meringue
    step. That is nonsense: it came from extrapolating the egg-white
    D-z model ~14 C past its calibration window. No process reduces a
    pathogen by twelve thousand orders of magnitude.

    Any temperature must now yield a capped, defensible figure.
    """
    for temp in (60.0, 71.0, 85.0, 100.0):
        history = ThermalHistory([0.0, 30.0], [temp, temp])
        achieved = accumulated_log_reduction(history, EGG_WHITE_PH78)
        assert achieved <= MAX_CREDITED_LOG, (
            f"{temp} C produced {achieved:.2f} log10, above the cap"
        )


def test_cap_is_a_sane_value():
    """
    12 log10 already means one survivor in a trillion, which exceeds
    any plausible bioburden in one egg. The cap should be generous
    enough never to mask a real failure, but finite.
    """
    assert 6.0 <= MAX_CREDITED_LOG <= 20.0


def test_capped_verdicts_are_disclosed_not_hidden():
    """
    When the cap binds, the report must say so explicitly rather than
    printing a fake-precise number.
    """
    history = ThermalHistory([0.0, 3.0, 4.0], [20.0, 71.0, 71.0])
    verdict = assess("white foam", history, EGG_WHITE_PH78, target_log=5.0)
    assert verdict.is_safe
    assert verdict.was_capped
    rendered = verdict.render()
    assert "capped" in rendered
    # And the out-of-window condition must be surfaced as a note.
    assert any("calibrated" in n for n in verdict.notes)
    assert verdict.evidence is Evidence.MODELLED_EXTRAPOLATED
    # An extrapolated figure must NOT be presented as audit-grade.
    assert not verdict.is_defensible


def test_in_window_results_are_not_flagged_as_extrapolation():
    """
    The recipe's yolk hold sits INSIDE Appendix III.C's 59.4-65.6 C span,
    so it must report a precise figure with no extrapolation caveat.
    """
    history = _recipe_yolk_history()
    verdict = assess("yolk base", history, EGG_YOLK_PLAIN, target_log=5.0)
    assert verdict.is_safe
    assert not verdict.was_capped
    assert not any("calibrated" in n for n in verdict.notes)
    assert verdict.evidence is Evidence.MODELLED_IN_WINDOW
    assert verdict.is_defensible


def test_validity_windows_bracket_the_recipe_steps():
    """
    The yolk model must genuinely cover the hold we rely on.
    If it did not, the recipe's central safety claim would itself be
    an extrapolation.
    """
    from formulation import YOLK_CUSTARD_TARGET_C

    t = YOLK_CUSTARD_TARGET_C
    assert not EGG_YOLK_PLAIN.is_extrapolation(t)
    assert EGG_YOLK_PLAIN.valid_min_c < t < EGG_YOLK_PLAIN.valid_max_c


# --------------------------------------------------------------------------
# THE SUGAR MATRIX PROBLEM
# The most important tests in this file. External review found that the
# original project applied plain-matrix models to sweetened food. These
# tests make that class of error impossible to reintroduce silently.
# --------------------------------------------------------------------------

def test_sugar_massively_increases_yolk_heat_resistance():
    """
    Garibaldi et al. 1969 measured, at 60 C:
        plain yolk            D = 0.40 min
        yolk + 10% sucrose    D = 4.0 min

    A tenfold rise from 10% sugar. If our constants ever stop reflecting
    that, every yolk safety claim downstream becomes wrong.
    """
    d_plain = YOLK_PLAIN_GARIBALDI.d_at(60.0)
    d_sugared = YOLK_SUGARED_10PCT.d_at(60.0)
    assert abs(d_plain - 0.40) < 0.01, d_plain
    assert abs(d_sugared - 4.0) < 0.01, d_sugared
    ratio = d_sugared / d_plain
    assert 9.0 < ratio < 11.0, f"expected ~10x, got {ratio:.1f}x"


def test_sugar_increases_white_heat_resistance():
    """Garibaldi at 55 C: white 0.55 min -> white + 10% sucrose 1.2 min."""
    d_plain = WHITE_PLAIN_GARIBALDI.d_at(55.0)
    d_sugared = WHITE_SUGARED_10PCT.d_at(55.0)
    assert abs(d_plain - 0.55) < 0.01
    assert abs(d_sugared - 1.20) < 0.01
    ratio = d_sugared / d_plain
    assert abs(ratio - SUCROSE_PROTECTION_PER_10PCT) < 0.05, ratio


def test_matrix_mismatch_is_flagged_loudly():
    """
    Assessing sweetened food against a plain-matrix model must produce a
    MATRIX_MISMATCH grade, an explicit warning, and must NOT be reported
    as defensible - even though the arithmetic completes fine.

    This is the guard against the project's original error.
    """
    history = _recipe_yolk_history()
    verdict = assess(
        "sugared yolk assessed with plain model",
        history,
        EGG_YOLK_PLAIN,
        target_log=5.0,
        matrix_matches_model=False,
    )
    assert verdict.evidence is Evidence.MATRIX_MISMATCH
    assert not verdict.is_defensible
    assert any("OVERSTATES" in n for n in verdict.notes)


def test_garibaldi_z_values_agree_with_published_range():
    """
    Garibaldi reported all egg-product z-values in 4.2-5.3 C, average
    4.6 C. Our transcribed constants must fall in that band.
    """
    for model in (
        YOLK_PLAIN_GARIBALDI,
        YOLK_SUGARED_10PCT,
        WHITE_PLAIN_GARIBALDI,
        WHITE_SUGARED_10PCT,
    ):
        assert 4.0 <= model.z_c <= 5.5, f"{model.name}: z={model.z_c}"


def test_garibaldi_equivalence_points_are_ordered_sensibly():
    """
    Garibaldi's measured equivalence temperatures must rank in the order
    physical chemistry demands: plain white easiest to pasteurize,
    sugared white harder, yolk hardest.
    """
    p = GARIBALDI_EQUIVALENCE_POINTS_F
    assert p["egg white pH 9.2"] < p["egg white pH 9.2 + 10% sucrose"]
    assert p["egg white pH 9.2 + 10% sucrose"] < p["egg yolk"]
    # The 140 F whole-egg standard is the historical reference point.
    assert p["whole egg"] == 140.0


# --------------------------------------------------------------------------
# The corrected process must pass on INDEPENDENT models
# --------------------------------------------------------------------------

def test_yolk_step_passes_on_three_independent_models():
    """
    The recipe's yolk step must clear 5 log10 against:
      1. FSIS Appendix III.C plain yolk  (the design basis)
      2. Garibaldi 1969 plain yolk       (independent study)
      3. Garibaldi 1969 sugared yolk     (partial cushion if sugar present)

    Bound to the recipe constants, not hardcoded numbers, so lowering
    the target temperature cannot silently pass a stale test.
    """
    history = _recipe_yolk_history()
    for model in (EGG_YOLK_PLAIN, YOLK_PLAIN_GARIBALDI, YOLK_SUGARED_10PCT):
        achieved = accumulated_log_reduction(history, model)
        assert achieved >= 5.0, f"{model.name}: only {achieved:.2f} log10"


def test_yolk_step_is_in_window_for_the_design_model():
    """The yolk hold must be interpolation, not extrapolation, on FSIS."""
    history = _recipe_yolk_history()
    verdict = assess("yolk base", history, EGG_YOLK_PLAIN, target_log=5.0)
    assert verdict.evidence is Evidence.MODELLED_IN_WINDOW
    assert verdict.is_defensible, verdict.render()


def test_garibaldi_model_windows_match_the_published_figure():
    """
    GUARD AGAINST THE ERROR THAT PRODUCED THE FALSE "ALL IN-WINDOW" CLAIM.

    The Garibaldi yolk models once declared a 50-62 C window, taken from
    Fig. 4's AXIS rather than its DATA. The axis does span 50-62 C; the
    plotted points do not. Reading the page scan (PMC377728 p. 493) gave
    the true extents, which are recorded in
    GARIBALDI_YOLK_DATA_EXTENT_C.

    This test pins each model's window to that transcription, so nobody
    can widen a window without also editing the recorded source data.
    """
    from thermal_safety import GARIBALDI_YOLK_DATA_EXTENT_C

    for model in (YOLK_PLAIN_GARIBALDI, YOLK_SUGARED_10PCT, YOLK_SALTED_10PCT):
        lo, hi = GARIBALDI_YOLK_DATA_EXTENT_C[model.name]
        assert model.valid_min_c == lo and model.valid_max_c == hi, (
            f"{model.name} window {model.valid_min_c}-{model.valid_max_c} "
            f"does not match published data extent {lo}-{hi}"
        )


def test_no_temperature_puts_all_three_yolk_models_in_window():
    """
    THE RETIRED CLAIM, NOW ASSERTED AS FALSE.

    The docs once said the 62 C yolk hold was confirmed by three
    independent models with all three in-window. This test proves that
    statement was not merely mis-tuned but IMPOSSIBLE: the three windows
    barely intersect.

    Keeping it as a test means the claim cannot be reintroduced by
    someone "fixing" the temperature.
    """
    lo = max(
        EGG_YOLK_PLAIN.valid_min_c,
        YOLK_PLAIN_GARIBALDI.valid_min_c,
        YOLK_SUGARED_10PCT.valid_min_c,
    )
    hi = min(
        EGG_YOLK_PLAIN.valid_max_c,
        YOLK_PLAIN_GARIBALDI.valid_max_c,
        YOLK_SUGARED_10PCT.valid_max_c,
    )
    # 59.4 - 59.5 C: a 0.1 C sliver, unusable as a process target.
    assert hi - lo < 0.5, (
        f"intersection {lo:.1f}-{hi:.1f} C is wider than expected; "
        "re-derive the claim from the source before trusting it"
    )


def test_yolk_step_evidence_grade_is_stated_honestly_per_model():
    """
    Each cross-check model must report its OWN extrapolation status at
    the process temperature. Two of them are out of window at 62 C, and
    the code must say so rather than presenting four agreeing numbers as
    if they were equally strong.
    """
    from formulation import YOLK_CUSTARD_TARGET_C

    expected = {
        EGG_YOLK_PLAIN: False,           # FSIS III.C spans 59.4-65.6 C
        YOLK_PLAIN_GARIBALDI: True,      # 53.0-59.5 C  -> +2.5 C out
        YOLK_SUGARED_10PCT: True,        # 55.0-61.5 C  -> +0.5 C out
        YOLK_SALTED_10PCT: False,        # 50.0-62.5 C  -> in window
    }
    for model, is_extrap in expected.items():
        assert model.is_extrapolation(YOLK_CUSTARD_TARGET_C) is is_extrap, (
            f"{model.name}: expected extrapolation={is_extrap} at "
            f"{YOLK_CUSTARD_TARGET_C} C"
        )


def test_yolk_step_meets_the_cfr_plain_yolk_safe_harbour():
    """
    THE STRONGEST CLAIM IN THE PROJECT, AND THE ONLY NON-MODELLED ONE.

    9 CFR 590.570 Table I is law, not a model: meeting a row IS a
    recognised pasteurization. The yolk step must clear the plain-yolk
    row on both temperature and time.
    """
    from formulation import YOLK_CUSTARD_TARGET_C, YOLK_HOLD_MINUTES
    from thermal_safety import meets_historical_cfr_row

    assert meets_historical_cfr_row(
        "plain yolk", YOLK_CUSTARD_TARGET_C, YOLK_HOLD_MINUTES
    ), (
        f"{YOLK_CUSTARD_TARGET_C} C / {YOLK_HOLD_MINUTES} min fails the "
        "9 CFR 590.570 plain-yolk safe harbour"
    )


def test_salted_yolk_would_need_a_hotter_process_than_we_run():
    """
    WHY SALT IS ADDED AFTER THE HEAT STEP - QUANTIFIED.

    This is the reviewer's objection, verified and turned into a test.
    Table I puts salted yolk in a stricter category (144 F / 6.2 min =
    62.2 C). Our 62 C hold is 0.2 C SHORT of it.

    So if salt were left in the pan the process would no longer meet any
    safe harbour. The test asserts that failure explicitly, because it
    is the concrete justification for the process order.
    """
    from formulation import YOLK_CUSTARD_TARGET_C, YOLK_HOLD_MINUTES
    from thermal_safety import meets_historical_cfr_row

    assert not meets_historical_cfr_row(
        "salt yolk (2-12% salt)", YOLK_CUSTARD_TARGET_C, YOLK_HOLD_MINUTES
    ), (
        "the salted-yolk row now passes at our process conditions; "
        "the rationale for adding salt after heating must be re-derived"
    )
    assert not meets_historical_cfr_row(
        "sugar yolk (>=2% sugar)", YOLK_CUSTARD_TARGET_C, YOLK_HOLD_MINUTES
    )


def test_garibaldi_measured_salt_protection_in_yolk_not_just_buffer():
    """
    CORRECTION OF A MISQUOTATION THIS PROJECT MADE.

    An earlier revision cited Garibaldi as reporting that "salt has no
    protective effect on Salmonella". The paper's actual sentence is
    qualified: no protective effect "in A BUFFER SYSTEM". In the YOLK
    matrix the same paper measured D60 rising from 0.40 to 5.1 min.

    Dropping that qualifier erred in the unsafe direction, so the
    measured factor is pinned here.
    """
    plain = YOLK_PLAIN_GARIBALDI.d_at(60.0)
    salted = YOLK_SALTED_10PCT.d_at(60.0)
    assert abs(plain - 0.40) < 0.005
    assert abs(salted - 5.10) < 0.005
    assert abs(salted / plain - 12.75) < 0.05, (
        f"salt protection factor {salted / plain:.2f}x, expected 12.75x"
    )


def test_worst_case_yolk_model_still_clears_target():
    """
    Judge the step by its WEAKEST model, not its most flattering one.
    Garibaldi's sugared yolk is the binding constraint.
    """
    history = _recipe_yolk_history()
    worst = min(
        accumulated_log_reduction(history, m)
        for m in (EGG_YOLK_PLAIN, YOLK_PLAIN_GARIBALDI, YOLK_SUGARED_10PCT)
    )
    assert worst >= 5.0, f"worst-case model gives only {worst:.2f} log10"
    # And it should not be a hair's breadth.
    assert worst >= 5.5, f"worst-case margin too thin: {worst:.2f} log10"


# --------------------------------------------------------------------------
# The pessimistic high-sugar model, and why 60 C was removed
# --------------------------------------------------------------------------

def test_pessimistic_model_is_harsher_than_measured_data():
    """
    The stress-test model must be strictly more pessimistic than
    Garibaldi's measured 10% figure, or it provides no safety value.
    """
    pess = pessimistic_sugared_white(10.0)
    assert pess.d_at(55.0) >= WHITE_SUGARED_10PCT.d_at(55.0) * 0.99
    # And it must grow with concentration.
    assert pessimistic_sugared_white(44.0).d_at(55.0) > pess.d_at(55.0)


def test_sixty_degree_white_hold_has_too_thin_a_margin():
    """
    REGRESSION GUARD for the decision to withdraw the 60 C fallback.

    Being precise about the reason, because a draft of the docs
    overstated it: 60 C / 10 min is NOT unsafe on paper. It clears
    5 log10. The problem is the SIZE of the margin.

    Under a pessimistic model of our actual ~44% sugar foam:
        5 log10 at 60 C requires ~5.7 min
        so a 10-min hold sits only ~1.8x above requirement
        while 71 C / 3 min sits ~190x above requirement

    A process needing an accurately timed 10-minute hold to land 1.8x
    above the limit - at the very temperature where Garibaldi
    photographed plain egg white coagulating - is not one to recommend.
    """
    pess = pessimistic_sugared_white(43.7)

    needed = pess.minutes_for_target(60.0, 5.0)
    assert 4.0 < needed < 8.0, f"expected ~5.7 min, got {needed:.2f}"

    # A 5-minute hold does NOT reliably clear the target.
    short = ThermalHistory([0.0, 1.5, 6.5], [20.0, 60.0, 60.0])
    assert accumulated_log_reduction(short, pess) < 6.0

    # A 10-minute hold does clear it, but only modestly.
    long_hold = ThermalHistory([0.0, 1.5, 11.5], [20.0, 60.0, 60.0])
    assert accumulated_log_reduction(long_hold, pess) >= 5.0
    assert (10.0 / needed) < 3.0, "margin is larger than documented"


def test_71c_margin_is_orders_of_magnitude_better_than_60c():
    """Quantifies why 71 C was kept and 60 C dropped."""
    pess = pessimistic_sugared_white(43.7)
    need_60 = pess.minutes_for_target(60.0, 5.0)
    need_71 = pess.minutes_for_target(71.0, 5.0)
    margin_60 = 10.0 / need_60          # the old 10-min fallback
    margin_71 = 3.0 / need_71           # the specified 3-min hold
    assert margin_71 > 50 * margin_60, (
        f"71 C margin {margin_71:.0f}x vs 60 C {margin_60:.1f}x"
    )


def test_seventy_one_degree_white_hold_is_robust_even_pessimistically():
    """
    71 C must clear 5 log10 with a large margin even under the harsh
    compounding sugar assumption. This is what justifies keeping the
    Swiss-meringue temperature rather than lowering it.
    """
    pess = pessimistic_sugared_white(43.7)
    minutes_needed = pess.minutes_for_target(71.0, 5.0)
    assert minutes_needed < 0.5, f"needs {minutes_needed:.2f} min"

    history = ThermalHistory([0.0, 3.0, 6.0], [20.0, 71.0, 71.0])
    achieved = accumulated_log_reduction(history, pess)
    assert achieved >= 5.0


def test_pessimistic_model_rejects_impossible_concentrations():
    for bad in (-1.0, 75.0):
        try:
            pessimistic_sugared_white(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad}%")


def test_pessimistic_model_never_reports_as_in_window():
    """
    Subtle failure mode caught in a self-audit.

    The pessimistic sugared-white model has a wide TEMPERATURE window,
    so at 71 C it was initially graded 'MODELLED (in-window)' - which
    hid the fact that its SUGAR CONCENTRATION is extrapolated. A model
    can be comfortably inside its temperature range while resting on an
    unmeasured composition.

    The composition-extrapolation flag must force an honest grade.
    """
    pess = pessimistic_sugared_white(43.7)
    assert pess.is_composition_extrapolation
    # Even at a temperature well inside its window:
    assert pess.valid_min_c < 71.0 < pess.valid_max_c
    assert pess.is_extrapolation(71.0)

    history = ThermalHistory([0.0, 3.0, 6.0], [20.0, 71.0, 71.0])
    verdict = assess("white foam", history, pess, 5.0)
    assert verdict.evidence is Evidence.MODELLED_EXTRAPOLATED
    assert verdict.is_safe          # it does clear the target
    assert not verdict.is_defensible  # but is not audit-grade


def test_measured_models_are_not_composition_extrapolations():
    """Garibaldi's and FSIS's models are measured, so must not carry the flag."""
    for model in (
        EGG_YOLK_PLAIN,
        EGG_WHITE_PH78,
        YOLK_PLAIN_GARIBALDI,
        YOLK_SUGARED_10PCT,
        WHITE_PLAIN_GARIBALDI,
        WHITE_SUGARED_10PCT,
    ):
        assert not model.is_composition_extrapolation, model.name


def test_pessimistic_model_declares_itself_unmeasured():
    """
    The source string must make clear this is an extrapolation, so it
    can never be quoted as a measured value.
    """
    src = pessimistic_sugared_white(40.0).source
    assert "PESSIMISTIC" in src
    assert "Not a measured value" in src


# --------------------------------------------------------------------------
# Evidence grading
# --------------------------------------------------------------------------

def test_only_measured_and_in_window_count_as_lab_grade():
    assert Evidence.MEASURED.is_model_supported
    assert Evidence.MODELLED_IN_WINDOW.is_model_supported
    assert not Evidence.MODELLED_EXTRAPOLATED.is_model_supported
    assert not Evidence.MATRIX_MISMATCH.is_model_supported
    assert not Evidence.UNSUPPORTED.is_model_supported


def test_only_measured_counts_as_lab_validated():
    """
    Semantic correction from review. The old `is_lab_grade` name treated
    an in-window MODEL as equivalent to a laboratory measurement. It is
    not. Only MEASURED may claim lab validation.
    """
    assert Evidence.MEASURED.is_lab_validated
    assert not Evidence.MODELLED_IN_WINDOW.is_lab_validated
    assert not Evidence.MODELLED_EXTRAPOLATED.is_lab_validated
    assert not Evidence.MATRIX_MISMATCH.is_lab_validated
    assert not Evidence.UNSUPPORTED.is_lab_validated


def test_no_computed_recipe_step_claims_lab_validation():
    """
    Guard the central honesty property of this project: nothing we
    compute may present itself as laboratory-validated, however
    comfortable the margin.
    """
    history = _recipe_yolk_history()
    verdict = assess("yolk base", history, EGG_YOLK_PLAIN, 5.0)
    assert verdict.is_defensible        # our strongest honest claim
    assert not verdict.is_lab_validated  # but never this one


def test_verdict_render_always_shows_evidence_grade():
    """No result may be printed without stating how good the basis is."""
    history = _recipe_yolk_history()
    rendered = assess("yolk", history, EGG_YOLK_PLAIN, 5.0).render()
    assert "evidence grade" in rendered


def test_history_rejects_mismatched_arrays():
    try:
        ThermalHistory(times_min=[0.0, 1.0], temps_c=[60.0])
    except ValueError:
        return
    raise AssertionError("expected ValueError on mismatched lengths")


def test_history_rejects_time_travel():
    try:
        ThermalHistory(times_min=[0.0, 5.0, 3.0], temps_c=[60.0, 60.0, 60.0])
    except ValueError:
        return
    raise AssertionError("expected ValueError on decreasing time")


def test_mix_rejects_misaligned_inputs():
    try:
        equilibrium_mix_temperature(masses_g=[10.0, 20.0], temps_c=[50.0])
    except ValueError:
        return
    raise AssertionError("expected ValueError on misaligned mix inputs")


# --------------------------------------------------------------------------
# THREE LEVELS OF SAFETY EVIDENCE
#
# Level 1 mathematical : is the model right?
# Level 2 process      : did the real product follow the modelled curve?
# Level 3 microbiology : does the finished matrix achieve the reduction?
#
# This project is at Level 1 only. These tests make that structural
# rather than a promise in prose.
# --------------------------------------------------------------------------


def test_thermal_history_defaults_to_the_weakest_provenance_claim():
    """An unspecified history must default to ASSUMED, never MEASURED."""
    h = ThermalHistory([0.0, 1.0], [20.0, 60.0])
    assert h.provenance == "ASSUMED"
    assert h.is_measured is False


def test_claiming_a_measured_history_requires_naming_the_instrument():
    """
    'MEASURED' without an instrument is an unfalsifiable claim.

    Rejecting it in the constructor is the only place the check cannot
    be forgotten.
    """
    try:
        ThermalHistory(
            [0.0, 1.0], [20.0, 60.0], provenance="MEASURED"
        )
    except ValueError as exc:
        assert "instrument" in str(exc)
    else:
        raise AssertionError("MEASURED without instrument must raise")

    ok = ThermalHistory(
        [0.0, 1.0],
        [20.0, 60.0],
        provenance="MEASURED",
        instrument="type-K thermocouple, ice-point checked, +/-0.5 C",
    )
    assert ok.is_measured is True


def test_bogus_provenance_is_rejected():
    for bad in ("measured", "GUESSED", "", "probably"):
        try:
            ThermalHistory([0.0, 1.0], [20.0, 60.0], provenance=bad)
        except ValueError:
            continue
        raise AssertionError(f"provenance {bad!r} should be rejected")


def test_assumed_history_is_model_defensible_but_not_process_measured():
    """
    THE BUG THIS ENCODES.

    A review found is_defensible returned True for a history labelled
    'PURELY ASSUMED, no thermocouple'. Reproduced and confirmed. Model
    correctness and process measurement are now separate properties.
    """
    history = _recipe_yolk_history()
    verdict = assess("yolk", history, EGG_YOLK_PLAIN, 5.0)

    assert verdict.is_safe is True
    assert verdict.is_model_defensible is True     # Level 1: yes
    assert verdict.is_process_measured is False    # Level 2: NO
    assert verdict.is_lab_validated is False       # Level 3: NO

    # The verdict must also carry the provenance forward, so it cannot
    # be read in isolation and mistaken for data.
    assert verdict.history_provenance == "ASSUMED"
    assert any("provenance" in n for n in verdict.notes)


def test_no_recipe_step_claims_process_measurement_or_lab_validation():
    """Nothing computed here may claim Level 2 or Level 3."""
    from formulation import (
        SWISS_MERINGUE_HOLD_MINUTES,
        SWISS_MERINGUE_TARGET_C,
    )

    yolk = assess("yolk", _recipe_yolk_history(), EGG_YOLK_PLAIN, 5.0)
    white_hist = ThermalHistory(
        [0.0, 3.0, 3.0 + SWISS_MERINGUE_HOLD_MINUTES],
        [20.0, SWISS_MERINGUE_TARGET_C, SWISS_MERINGUE_TARGET_C],
    )
    white = assess("white", white_hist, pessimistic_sugared_white(47.5), 5.0)

    for verdict in (yolk, white):
        assert verdict.is_process_measured is False
        assert verdict.is_lab_validated is False


def test_regulatory_historical_grade_exists_and_is_not_current_law():
    """
    Finding: docs printed a 'REGULATORY' grade absent from the enum.

    Two parallel evidence systems, one undocumented, is how an
    overclaim survives. The grade now exists - and asserts its own
    limits.
    """
    grade = Evidence.REGULATORY_HISTORICAL
    assert "historical" in grade.value.lower()
    assert "superseded" in grade.value.lower()

    # It must NOT masquerade as measurement or as live law.
    assert grade.is_lab_validated is False
    assert grade.is_current_law is False

    # No grade whatsoever may claim to be current law.
    for member in Evidence:
        assert member.is_current_law is False, (
            f"{member.name} claims current-law status; that requires "
            "an operative citation, which this project does not have"
        )


def test_removed_safe_harbour_helper_raises_instead_of_answering():
    """
    The old name asserted a live safe harbour that does not exist.

    It must fail loudly rather than return a comfortable bool.
    """
    from thermal_safety import meets_cfr_safe_harbour

    try:
        meets_cfr_safe_harbour("plain yolk", 62.0, 10.0)
    except NotImplementedError as exc:
        msg = str(exc)
        assert "2022-10-31" in msg
        assert "meets_historical_cfr_row" in msg
    else:
        raise AssertionError("removed helper must raise")


def test_current_cfr_text_contains_no_times_or_temperatures():
    """
    Guard the claim that the current rule is a performance standard.

    Verified against eCFR: the entire section is prose. If a future
    edit pastes the old table back in as if it were current, this
    fails.
    """
    from thermal_safety import CFR_590_570_CURRENT_TEXT

    text = CFR_590_570_CURRENT_TEXT
    assert "edible without additional preparation" in text
    for token in ("142", "140", "146", "3.5", "6.2", "Table"):
        assert token not in text, (
            f"current 590.570 text must not contain {token!r}"
        )


def test_historical_row_check_reports_the_recipe_correctly():
    """
    The recipe's yolk step vs the historical rows.

    Clears plain yolk; misses the salt/sugar yolk row by 0.22 C. That
    gap is the quantified cost of adding either protectant early.
    """
    from formulation import YOLK_CUSTARD_TARGET_C, YOLK_HOLD_MINUTES
    from thermal_safety import meets_historical_cfr_row

    T, H = YOLK_CUSTARD_TARGET_C, YOLK_HOLD_MINUTES
    assert meets_historical_cfr_row("plain yolk", T, H) is True
    assert meets_historical_cfr_row("salt yolk (2-12% salt)", T, H) is False
    assert meets_historical_cfr_row("sugar yolk (>=2% sugar)", T, H) is False

    shortfall = f_to_c(144.0) - T
    assert 0.15 < shortfall < 0.30


def test_finished_sweetened_base_is_documented_as_uncovered():
    """
    The finished base matches NO historical row - 38% added nonegg
    versus category caps of <2% and 2-12%. This was a valid review
    finding and must stay written down.
    """
    from thermal_safety import FINISHED_BASE_NOT_IN_ANY_ROW

    note = FINISHED_BASE_NOT_IN_ANY_ROW
    assert "38.0%" in note
    assert "not covered by ANY row" in note
    assert "RECONTAMINATION" in note


# --------------------------------------------------------------------------
# CLOSED-FORM VALIDATION OF THE INTEGRATOR
#
# Convergence tests (512 vs 1024 vs 8192) only prove the integrator
# agrees with ITSELF. They cannot detect a systematically wrong formula.
#
# For a LINEAR ramp the lethality integral has an exact closed form, so
# the numerical result can be checked against mathematics instead:
#
#   T(t) = T0 + m t,  rate(t) = (1/Dref) * 10**((T(t) - Tref)/z)
#
#   integral rate dt = (1/Dref) * 10**((T0-Tref)/z)
#                      * (10**(m dt/z) - 1) * z / (m ln10)
#
# Derivation: substitute u = m t / z, giving integral of 10**u du,
# whose antiderivative is 10**u / ln10.
# --------------------------------------------------------------------------


def _closed_form_log_reduction(t0_c, t1_c, dt_min, model):
    """Exact analytical lethality for one linear temperature ramp."""
    import math

    d_ref, t_ref, z = model.d_ref_min, model.t_ref_c, model.z_c
    if abs(t1_c - t0_c) < 1e-12:
        # Isothermal: trivially time / D.
        return dt_min / (d_ref * 10 ** ((t_ref - t0_c) / z))
    slope = (t1_c - t0_c) / dt_min
    lead = (1.0 / d_ref) * 10 ** ((t0_c - t_ref) / z)
    return lead * (10 ** (slope * dt_min / z) - 1.0) * z / (
        slope * math.log(10)
    )


def test_integrator_matches_the_exact_analytical_solution():
    """
    The numerical integrator must agree with the closed form.

    This is a stronger check than convergence: it validates the FORMULA,
    not merely the step count. If accumulated_log_reduction ever
    integrated the wrong quantity, self-consistency tests would still
    pass while this one would fail.
    """
    cases = [
        (20.0, 62.0, 1.5),   # the recipe's actual yolk ramp
        (50.0, 62.0, 3.0),
        (20.0, 71.0, 2.0),   # steepest ramp used anywhere here
        (55.0, 60.0, 0.5),
        (62.0, 62.0, 10.0),  # isothermal hold
    ]
    for t0, t1, dt in cases:
        exact = _closed_form_log_reduction(t0, t1, dt, EGG_YOLK_PLAIN)
        history = ThermalHistory([0.0, dt], [t0, t1])
        got = accumulated_log_reduction(
            history, EGG_YOLK_PLAIN, floor_c=0.0
        )
        assert abs(got - exact) < 0.01, (
            f"{t0}->{t1} C over {dt} min: numerical {got:.6f} vs "
            f"analytical {exact:.6f}"
        )


def test_endpoint_trapezoid_is_provably_wrong_not_merely_coarse():
    """
    Quantify the retired bug against exact mathematics.

    The original integrator used the caller's segment endpoints only.
    Comparing that to the closed form shows it was not a small
    discretisation error but a large, one-directional overstatement -
    which is why it mattered for safety.
    """
    t0, t1, dt = 20.0, 71.0, 2.0
    exact = _closed_form_log_reduction(t0, t1, dt, EGG_YOLK_PLAIN)
    history = ThermalHistory([0.0, dt], [t0, t1])

    endpoint = accumulated_log_reduction(
        history, EGG_YOLK_PLAIN, floor_c=0.0, steps_per_segment=1
    )
    converged = accumulated_log_reduction(
        history, EGG_YOLK_PLAIN, floor_c=0.0
    )

    assert abs(converged - exact) < 0.01
    # The old method overstated lethality by a large margin...
    assert endpoint - exact > 1.0, (
        f"endpoint method should grossly overstate; got {endpoint:.4f} "
        f"vs exact {exact:.4f}"
    )
    # ...and always in the UNSAFE direction (never conservative).
    assert endpoint > exact


def test_closed_form_agrees_across_all_recipe_models():
    """The formula check must hold for every model, not just one."""
    for model in (
        EGG_WHITE_PH78,
        EGG_YOLK_PLAIN,
        YOLK_SUGARED_10PCT,
        YOLK_SALTED_10PCT,
        WHITE_SUGARED_10PCT,
    ):
        exact = _closed_form_log_reduction(45.0, 58.0, 2.0, model)
        history = ThermalHistory([0.0, 2.0], [45.0, 58.0])
        got = accumulated_log_reduction(history, model, floor_c=0.0)
        rel = abs(got - exact) / max(exact, 1e-12)
        assert rel < 0.005, (
            f"{model.name}: numerical {got:.6f} vs analytical "
            f"{exact:.6f} (rel err {rel:.4%})"
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
