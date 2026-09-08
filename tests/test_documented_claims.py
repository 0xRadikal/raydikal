"""
test_documented_claims.py
=========================
End-to-end guard against DOCUMENTATION DRIFT.

WHY THIS FILE EXISTS
--------------------
An external reviewer challenged two figures published in the README and
PR ("8.52 log10" and "9.79 log10"), saying they could not be reproduced
from the committed code. Investigating showed something worse than a
typo: the numbers WERE what the code emitted, but the code contained a
numerical bug (see thermal_safety.SUBDIVISION_STEPS). Both the docs and
the code were wrong together, so no amount of "machine-verified against
code output" would have caught it.

The lesson is that agreement between docs and code is necessary but not
sufficient. This file therefore does two distinct jobs:

  1. Recompute every headline number the docs publish, from the live
     modules, and assert the docs match.
  2. Independently sanity-check the physics with hand-derivable
     closed-form values, so a bug in the shared integrator cannot make
     docs and code agree on a wrong answer.

If a number in the docs changes, this file must be updated in the same
commit. That is the point.

Run:  python3 tests/test_documented_claims.py
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "src"))

from formulation import (  # noqa: E402
    SWISS_MERINGUE_HOLD_MINUTES,
    SWISS_MERINGUE_TARGET_C,
    YOLK_CUSTARD_TARGET_C,
    YOLK_HOLD_MINUTES,
    build_sepid_o_zard,
    foam_density_g_per_ml,
    sugar_percent_of_base,
    sugar_syrup_density_g_per_ml,
)
from thermal_safety import (  # noqa: E402
    EGG_WHITE_PH78,
    EGG_YOLK_PLAIN,
    ESPRESSO_IN_CUP_C,
    ESPRESSO_SHOT_MASS_G,
    YOLK_PLAIN_GARIBALDI,
    YOLK_SPECIFIC_HEAT,
    YOLK_SUGARED_10PCT,
    ThermalHistory,
    accumulated_log_reduction,
    equilibrium_mix_temperature,
    f_to_c,
    pessimistic_sugared_white,
)

RAMP_MIN = 1.5
"""Assumed ramp-to-temperature time used consistently in all docs."""


def _yolk_history() -> ThermalHistory:
    return ThermalHistory(
        [0.0, RAMP_MIN, RAMP_MIN + YOLK_HOLD_MINUTES],
        [20.0, YOLK_CUSTARD_TARGET_C, YOLK_CUSTARD_TARGET_C],
    )


def _foam_sugar_percent() -> float:
    r = build_sepid_o_zard()
    return r.mass_of("caster sugar (foam)") / r.layer_mass_g("foam") * 100.0


# --------------------------------------------------------------------------
# 1. Documented figures must match the live code
# --------------------------------------------------------------------------

def test_documented_zabaione_mixture_temperature():
    """README/RECIPE: zabaione mixture lands at 51.1 C."""
    t = equilibrium_mix_temperature(
        [ESPRESSO_SHOT_MASS_G, 18.0],
        [ESPRESSO_IN_CUP_C, 20.0],
        [1.0, YOLK_SPECIFIC_HEAT],
    )
    assert abs(t - 51.1) < 0.05, f"docs say 51.1 C, code gives {t:.2f}"


def test_documented_latte_mixture_temperature():
    """README/RECIPE: yolk latte reaches 61.7 C."""
    t = equilibrium_mix_temperature(
        [ESPRESSO_SHOT_MASS_G, 18.0, 150.0],
        [ESPRESSO_IN_CUP_C, 20.0, 65.0],
        [1.0, YOLK_SPECIFIC_HEAT, 0.95],
    )
    assert abs(t - 61.7) < 0.05, f"docs say 61.7 C, code gives {t:.2f}"


def test_documented_yolk_step_lethality_all_three_models():
    """
    RECIPE/README publish the yolk step against three models.
    These are the CORRECTED figures for 62 C / 10 min after the
    integrator fix; the previous 8.52 / 9.79 pair was inflated.
    """
    history = _yolk_history()
    expected = {
        "FSIS": (EGG_YOLK_PLAIN, 7.93),
        "Garibaldi plain": (YOLK_PLAIN_GARIBALDI, 12.00),
        "Garibaldi sugared": (YOLK_SUGARED_10PCT, 6.57),
    }
    for label, (model, doc_value) in expected.items():
        got = accumulated_log_reduction(history, model)
        assert abs(got - doc_value) < 0.05, (
            f"{label}: docs say {doc_value}, code gives {got:.2f}"
        )


def test_documented_worst_case_yolk_figure():
    """The docs quote 6.57 log10 as the binding worst case."""
    history = _yolk_history()
    worst = min(
        accumulated_log_reduction(history, m)
        for m in (EGG_YOLK_PLAIN, YOLK_PLAIN_GARIBALDI, YOLK_SUGARED_10PCT)
    )
    assert abs(worst - 6.57) < 0.05, f"docs say 6.57, code gives {worst:.2f}"


def test_documented_foam_sugar_percentage():
    """
    RECIPE/LIMITATIONS quote 47.5% sugar in the foam layer.

    Rose from 43.7% when 5.2 g of white was diverted into the yolk base
    to match Garibaldi's 43%-egg-solids matrix. The foam got smaller, so
    the same 28 g of sugar is a larger share of it.
    """
    assert abs(_foam_sugar_percent() - 47.5) < 0.05


def test_documented_white_step_time_requirements():
    """
    RECIPE quotes, under the pessimistic model:
        5 log10 at 71 C needs ~0.02 min
        5 log10 at 60 C needs ~5.7 min
    """
    pess = pessimistic_sugared_white(_foam_sugar_percent())
    at_71 = pess.minutes_for_target(SWISS_MERINGUE_TARGET_C, 5.0)
    at_60 = pess.minutes_for_target(60.0, 5.0)
    assert abs(at_71 - 0.02) < 0.005, f"docs say 0.02 min, code {at_71:.4f}"
    assert abs(at_60 - 7.7) < 0.1, f"docs say 7.7 min, code {at_60:.2f}"


def test_documented_60c_margin_ratio():
    """
    RECIPE quotes ~1.3x margin for the withdrawn 60 C / 10 min hold.

    This margin got WORSE (1.8x -> 1.3x) when the foam's sugar share
    rose, which strengthens the original decision to withdraw the 60 C
    fallback rather than weakening it.
    """
    pess = pessimistic_sugared_white(_foam_sugar_percent())
    ratio = 10.0 / pess.minutes_for_target(60.0, 5.0)
    assert abs(ratio - 1.3) < 0.1, f"docs say 1.3x, code gives {ratio:.2f}x"


def test_documented_fsis_holdout_validation_figures():
    """README quotes the hold-out checks: 22.28 min and 10.48 min."""
    white = EGG_WHITE_PH78.minutes_for_target(f_to_c(133.0), 5.7)
    yolk = EGG_YOLK_PLAIN.minutes_for_target(f_to_c(142.0), 6.2)
    assert abs(white - 22.28) < 0.05, f"docs 22.28, code {white:.2f}"
    assert abs(yolk - 10.48) < 0.05, f"docs 10.48, code {yolk:.2f}"


def test_documented_superseded_egg_white_process_figure():
    """Docs quote ~1.3 log10 for the old 134 F / 3.5 min process."""
    got = EGG_WHITE_PH78.log_reduction_isothermal(f_to_c(134.0), 3.5)
    assert abs(got - 1.29) < 0.05, f"docs ~1.29, code {got:.2f}"


def test_documented_garibaldi_d_values():
    """
    Docs quote Garibaldi's measured D-values. These are TRANSCRIBED from
    a paper, so this test guards against transcription drift.
    """
    assert abs(YOLK_PLAIN_GARIBALDI.d_at(60.0) - 0.40) < 0.005
    assert abs(YOLK_SUGARED_10PCT.d_at(60.0) - 4.00) < 0.005


def test_documented_recipe_masses_and_densities():
    """RECIPE quotes total mass and the layering density estimates."""
    r = build_sepid_o_zard()
    assert abs(r.total_mass_g() - 126.9) < 0.05
    assert abs(sugar_percent_of_base(r) - 37.4) < 0.1

    brix = r.mass_of("caster sugar (base)") / r.layer_mass_g("base") * 100.0
    base = sugar_syrup_density_g_per_ml(brix)
    foam = foam_density_g_per_ml(200.0)
    assert abs(base - 1.15) < 0.01, f"docs ~1.15, code {base:.3f}"
    assert abs(foam - 0.35) < 0.01, f"docs ~0.35, code {foam:.3f}"
    assert base > 1.01 > foam


# --------------------------------------------------------------------------
# 2. Independent physics checks
#    These do NOT use the shared integrator, so a bug in it cannot make
#    the docs and the code agree on a wrong answer.
# --------------------------------------------------------------------------

def test_yolk_hold_matches_hand_calculation():
    """
    Independent closed-form check of the hold portion only:

        log reduction = hold_minutes / D(T)

    No integrator involved. If this and the integrated figure ever
    disagree by more than the ramp's plausible contribution, something
    is wrong with the integration.
    """
    d = EGG_YOLK_PLAIN.d_at(YOLK_CUSTARD_TARGET_C)
    hold_only = YOLK_HOLD_MINUTES / d

    integrated = accumulated_log_reduction(_yolk_history(), EGG_YOLK_PLAIN)

    # The ramp can only ADD lethality, never remove it.
    assert integrated >= hold_only

    # But a 1.5 min ramp from 20 C cannot plausibly contribute more than
    # the equivalent of its full duration at the target temperature.
    max_plausible_ramp = RAMP_MIN / d
    assert integrated <= hold_only + max_plausible_ramp, (
        f"ramp contributed {integrated - hold_only:.2f} log10, which "
        f"exceeds the {max_plausible_ramp:.2f} log10 ceiling"
    )


def test_dz_model_obeys_its_defining_property():
    """
    A z-value means: raising temperature by z divides D by ten.
    Checked directly, independent of any recipe or integrator.
    """
    for model in (EGG_YOLK_PLAIN, EGG_WHITE_PH78, YOLK_SUGARED_10PCT):
        base = model.d_at(58.0)
        shifted = model.d_at(58.0 + model.z_c)
        assert abs(shifted - base / 10.0) < 1e-9, model.name


def test_energy_balance_conserves_energy():
    """
    Mixing temperature must lie between the coldest and hottest inputs.
    A trivial invariant, but it catches sign and weighting errors.
    """
    t = equilibrium_mix_temperature([30.0, 18.0], [67.0, 20.0], [1.0, 0.85])
    assert 20.0 < t < 67.0


def test_report_runs_and_states_evidence_grades():
    """
    End-to-end smoke test: the report must execute and every verdict it
    prints must carry an evidence grade. Guards against a result being
    published without its provenance.
    """
    import io
    import contextlib

    import report

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        report.main()
    text = buffer.getvalue()

    verdicts = text.count("] ")           # crude count of rendered headers
    grades = text.count("evidence grade")
    assert grades >= 3, f"only {grades} evidence grades in report"
    assert verdicts >= grades, "a verdict was printed without a grade"

    # The report must not contain the discredited figures.
    for stale in ("8.52 log10", "9.79 log10", "12020"):
        assert stale not in text, f"stale figure {stale!r} still in report"


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
