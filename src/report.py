"""
report.py
=========
Command-line report generator. Prints the full verified analysis:

  1. Safety audit of the drinks the user already orders
  2. The Sepid-o-Zarrin formulation
  3. Foam-integrity check
  4. Layering physics
  5. Lethality verification of each pasteurization step

Run:  python3 src/report.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from formulation import (
    OPTIMAL_FOAM_PH,
    POST_LETHALITY_CONTROLS,
    SWISS_MERINGUE_HOLD_MINUTES,
    SWISS_MERINGUE_TARGET_C,
    YOLK_CUSTARD_TARGET_C,
    YOLK_HOLD_MINUTES,
    YOLK_RAMP_MINUTES,
    assess_foam,
    build_sepid_o_zarrin,
    describe,
    foam_density_g_per_ml,
    preheat_base_mass_g,
    preheat_egg_solids_percent,
    preheat_salt_percent,
    sugar_percent_of_base,
    sugar_syrup_density_g_per_ml,
)
from thermal_safety import (
    EGG_WHITE_PH78,
    EGG_YOLK_PLAIN,
    YOLK_PLAIN_GARIBALDI,
    YOLK_SALTED_10PCT,
    YOLK_SUGARED_10PCT,
    f_to_c,
    meets_historical_cfr_row,
    pessimistic_sugared_white,
    ESPRESSO_IN_CUP_C,
    ESPRESSO_SHOT_MASS_G,
    YOLK_SPECIFIC_HEAT,
    ThermalHistory,
    accumulated_log_reduction,
    assess,
    equilibrium_mix_temperature,
    f_to_c,
    newtonian_mix_then_cool,
)

RULE = "=" * 74
THIN = "-" * 74


def section(title: str) -> None:
    print()
    print(RULE)
    print(f"  {title}")
    print(RULE)


def audit_existing_drinks() -> None:
    section("1. AUDIT OF THE DRINKS YOU CURRENTLY ORDER")

    print("Model calibration (reproducing the regulator's own tables):")
    print(f"  egg white model : z = {EGG_WHITE_PH78.z_c:.2f} C, "
          f"D@{EGG_WHITE_PH78.t_ref_c:.1f}C = {EGG_WHITE_PH78.d_ref_min:.3f} min")
    print(f"  egg yolk  model : z = {EGG_YOLK_PLAIN.z_c:.2f} C, "
          f"D@{EGG_YOLK_PLAIN.t_ref_c:.1f}C = {EGG_YOLK_PLAIN.d_ref_min:.3f} min")
    print()
    print("  Hold-out validation against FSIS rows not used in calibration:")
    pred_w = EGG_WHITE_PH78.minutes_for_target(f_to_c(133.0), 5.7)
    pred_y = EGG_YOLK_PLAIN.minutes_for_target(f_to_c(142.0), 6.2)
    print(f"    egg white 133 F -> predicted {pred_w:5.2f} min | FSIS 22.56 min")
    print(f"    egg yolk  142 F -> predicted {pred_y:5.2f} min | FSIS 10.48 min")

    print()
    print(THIN)
    print("A. Cafe zabaione (espresso poured onto raw sweetened yolk)")
    print(THIN)
    t_mix = equilibrium_mix_temperature(
        [ESPRESSO_SHOT_MASS_G, 18.0],
        [ESPRESSO_IN_CUP_C, 20.0],
        [1.0, YOLK_SPECIFIC_HEAT],
    )
    print(f"  espresso in cup (INEI standard) : {ESPRESSO_IN_CUP_C:.1f} C")
    print(f"  equilibrium mixture temperature : {t_mix:.1f} C")
    print(f"  FSIS yolk requirement           : 61.1 C held 3.5 min")
    hist = newtonian_mix_then_cool(t_mix, 22.0, 0.08, 10.0)
    # Cafe zabaione is a SWEETENED yolk, so the plain-yolk model does not
    # describe it. Sugar would make the pathogen HARDER to kill, so the
    # plain model is optimistic - and the drink still fails badly. The
    # mismatch is declared rather than hidden.
    v = assess(
        "zabaione as served",
        hist,
        EGG_YOLK_PLAIN,
        5.0,
        matrix_matches_model=False,
    )
    print()
    print(v.render())
    print()
    print("  Note the MATRIX MISMATCH grade: the real drink is sweetened,")
    print("  and sugar makes Salmonella harder to kill. So this already-")
    print("  failing figure is the OPTIMISTIC one. Using Garibaldi's")
    print("  sugared-yolk model instead:")
    got = accumulated_log_reduction(hist, YOLK_SUGARED_10PCT)
    print(f"    Garibaldi yolk + 10% sucrose -> {got:.3f} log10 of 5.00 needed")

    print()
    print(THIN)
    print("B. Egg-yolk latte (espresso + raw yolk + steamed milk)")
    print(THIN)
    t_latte = equilibrium_mix_temperature(
        [ESPRESSO_SHOT_MASS_G, 18.0, 150.0],
        [ESPRESSO_IN_CUP_C, 20.0, 65.0],
        [1.0, YOLK_SPECIFIC_HEAT, 0.95],
    )
    print(f"  equilibrium mixture temperature : {t_latte:.1f} C")
    print("  NOTE: this DOES exceed 61.1 C, which is why a naive")
    print("        'is it hot enough' check would wrongly pass it.")
    print("        But FSIS limits are time-AT-temperature. The cup only")
    print("        passes through that temperature while cooling.")
    print()
    for k, desc in ((0.03, "very well insulated"), (0.08, "typical ceramic cup")):
        h = newtonian_mix_then_cool(t_latte, 22.0, k, 15.0)
        logs = accumulated_log_reduction(h, EGG_YOLK_PLAIN)
        print(f"    cooling k={k:.2f}/min ({desc:19s}) -> {logs:.2f} log10 / 5.00 needed")
    need = EGG_YOLK_PLAIN.minutes_for_target(t_latte, 5.0)
    print()
    print(f"  A genuine isothermal hold at {t_latte:.1f} C would need "
          f"{need:.1f} min.")

    print()
    print("  VERDICT: both drinks are effectively RAW-EGG beverages.")
    print("  This is not a criticism of your cafe - it is how the")
    print("  classic recipe works. It is simply a risk you should be")
    print("  making a deliberate, informed choice about.")


def present_recipe() -> None:
    section("2. SEPID-O-ZARRIN - THE PROPOSED WHOLE-EGG DRINK")
    r = build_sepid_o_zarrin()
    print(describe(r))
    print(f"  base sugar concentration: {sugar_percent_of_base(r):.1f}% "
          "(drives the Donovan denaturation-temperature protection)")


def check_foam() -> None:
    section("3. FOAM INTEGRITY - THE MAKE-OR-BREAK CONSTRAINT")
    r = build_sepid_o_zarrin()

    print("Published failure mode:")
    print("  Lomakina & Mikova 2006: ONE DROP of yolk cut egg-white foam")
    print("  volume from 135 mL to 40 mL.")
    print("  Li et al. 2021: 0.5% w/w yolk significantly degraded both")
    print("  foam capacity and foam stability.")
    print()
    print("  Cause: yolk LDL/lipid outcompetes albumen at the air-water")
    print("  interface but cannot form a cohesive viscoelastic film.")
    print()
    print("  => The yolk and white must NEVER share a whipping vessel.")
    print()

    print(THIN)
    print("Clean separation (as specified):")
    print(THIN)
    good = assess_foam(
        r.mass_of("egg white"),
        r.mass_of("caster sugar (foam)"),
        0.0,
        OPTIMAL_FOAM_PH,
    )
    print(good.render())

    print()
    print(THIN)
    print("Sloppy separation (0.5 g yolk smear left in the white):")
    print(THIN)
    bad = assess_foam(
        r.mass_of("egg white"),
        r.mass_of("caster sugar (foam)"),
        0.5,
        OPTIMAL_FOAM_PH,
    )
    print(bad.render())


def check_layers() -> None:
    section("4. LAYERING PHYSICS - WHY IT STRATIFIES")
    r = build_sepid_o_zarrin()
    brix = r.mass_of("caster sugar (base)") / r.layer_mass_g("base") * 100.0
    base = sugar_syrup_density_g_per_ml(brix)
    coffee = 1.01
    foam = foam_density_g_per_ml(200.0)

    print(f"  yolk base    : {base:.3f} g/mL   ({brix:.1f} Brix syrup)")
    print(f"  espresso     : {coffee:.3f} g/mL")
    print(f"  meringue foam: {foam:.3f} g/mL   (200% overrun)")
    print()
    print(f"  ordering: {base:.3f} > {coffee:.3f} > {foam:.3f}  ->  stable")
    print()
    print("  The stack holds because of a real density gradient, not")
    print("  because of a careful pour. That is what makes it repeatable.")


def verify_process() -> None:
    section("5. LETHALITY VERIFICATION OF EACH PASTEURIZATION STEP")

    recipe = build_sepid_o_zarrin()

    print("  THE SUGAR PROBLEM, and why the process was redesigned")
    print(THIN)
    print("  Garibaldi, Straka & Ijichi 1969 (Appl Microbiol 17:491-496)")
    print("  measured Salmonella D-values at 60 C:")
    print()
    print("      plain egg yolk           D = 0.40 min")
    print("      egg yolk + 10% sucrose   D = 4.0  min   <- 10x")
    print("      egg yolk + 10% NaCl      D = 5.1  min")
    print()
    print("  Sugar PROTECTS the pathogen. An earlier version of this")
    print("  project heated a 36.6%-sugar yolk and then scored it with")
    print("  FSIS's PLAIN yolk model - a matrix mismatch that overstates")
    print("  lethality. The process below fixes that by sequencing.")

    print()
    print(THIN)
    print(f"Step 1 - yolk: heated PLAIN at {YOLK_CUSTARD_TARGET_C:.0f} C for "
          f"{YOLK_HOLD_MINUTES:.0f} min, sweetened AFTER")
    print(THIN)
    h1 = ThermalHistory(
        [0.0, YOLK_RAMP_MINUTES, YOLK_RAMP_MINUTES + YOLK_HOLD_MINUTES],
        [20.0, YOLK_CUSTARD_TARGET_C, YOLK_CUSTARD_TARGET_C],
    )
    print(f"  Thermal history: {YOLK_RAMP_MINUTES:.1f} min ramp from 20 C, "
          f"then {YOLK_HOLD_MINUTES:.1f} min hold.")
    print()
    print(assess("yolk base (plain during kill step)", h1, EGG_YOLK_PLAIN, 5.0).render())
    print()

    # ---- Historical benchmark - explicitly NOT current law ------------
    print("  HISTORICAL REGULATORY BENCHMARK - *NOT* CURRENT LAW")
    print("  " + "-" * 66)
    print("  An earlier version of this report called the following a")
    print("  'regulatory safe harbour' and 'law, not a model'. That was")
    print("  WRONG. Verified against the eCFR versioner API:")
    print()
    print("    9 CFR 590.570 Table I was operative 1971-05-28 to")
    print("    2022-10-30, and was removed on 2022-10-31 by 85 FR 68680.")
    print("    The section today is a PERFORMANCE STANDARD with no times,")
    print("    no temperatures and no product categories at all.")
    print()
    print("  The safe harbours did not vanish - they moved into the FSIS")
    print("  Food Safety Guideline for Egg Products, which is already the")
    print("  source of the D-z models used here. FSIS's own words:")
    print('    "The tables in the appendix of the compliance guideline')
    print('     for pasteurization times and temperatures are not minimum')
    print('     lethalities, but rather safe harbors for plants to')
    print('     follow ... plants are not required to follow the safe')
    print('     harbors and may use alternate procedures."')
    print()
    print("  Also note: safe harbours apply to FSIS-inspected official")
    print("  plants. A home kitchen has no safe harbour of any era.")
    print()
    print("  Would the yolk step have satisfied the historical rows?")
    for product in ("plain yolk", "salt yolk (2-12% salt)",
                    "sugar yolk (>=2% sugar)"):
        ok = meets_historical_cfr_row(
            product, YOLK_CUSTARD_TARGET_C, YOLK_HOLD_MINUTES)
        mark = "would PASS" if ok else "would FAIL"
        print(f"    {product:26s} -> {mark}")
    print()
    print("  It matches the PLAIN YOLK row, and only because the pan")
    print("  contains nothing but yolk and egg white:")
    print(f"    salt in pan  = {preheat_salt_percent(recipe):.2f}%"
          "   (stricter row starts at 2%)")
    print(f"    egg solids   = {preheat_egg_solids_percent(recipe):.2f}%"
          "  (Garibaldi measured 43%)")
    print(f"  We fall {f_to_c(144.0) - YOLK_CUSTARD_TARGET_C:.2f} C short of "
          "the salt/sugar yolk row. That gap is")
    print("  exactly what adding salt and sugar AFTER the heat step buys.")
    print()
    print("  BUT THE FINISHED SWEETENED BASE MATCHES NO ROW AT ALL:")
    print(f"    egg material  = {preheat_base_mass_g(recipe):.2f} g")
    print(f"    added nonegg  = "
          f"{recipe.mass_of('caster sugar (base)') + recipe.mass_of('fine salt (base)'):.2f} g")
    print(f"    -> {(recipe.mass_of('caster sugar (base)') + recipe.mass_of('fine salt (base)')) / recipe.layer_mass_g('base') * 100:.1f}% added nonegg ingredients")
    print("    categories cap at <2% (blends) and 2-12% (fortified).")
    print("  So the benchmark speaks to the PRE-HEAT EGG PHASE only.")
    print("  Sugar and salt arrive after lethality, so they cannot weaken")
    print("  the kill step - but the remaining hazard for the finished")
    print("  base is RECONTAMINATION, a hygiene control and not a thermal")
    print("  one. See the post-lethality controls below.")
    print()

    # ---- Secondary: models, each labelled with its true window --------
    print("  SECONDARY - D-z model cross-checks. These do NOT all share a")
    print("  validity window; an earlier version of this report claimed")
    print("  they were 'ALL in-window at 62 C', which was FALSE. The true")
    print("  Fig. 4 data extents make that impossible at ANY temperature:")
    worst = None
    for model, label in (
        (EGG_YOLK_PLAIN, "FSIS III.C plain yolk (design basis)"),
        (YOLK_PLAIN_GARIBALDI, "Garibaldi 1969 plain yolk"),
        (YOLK_SUGARED_10PCT, "Garibaldi 1969 yolk + 10% sucrose"),
        (YOLK_SALTED_10PCT, "Garibaldi 1969 yolk + 10% NaCl"),
    ):
        got = accumulated_log_reduction(h1, model)
        extrap = model.is_extrapolation(YOLK_CUSTARD_TARGET_C)
        window = "EXTRAPOLATED" if extrap else "in-window"
        print(f"    {label:38s} -> {got:5.2f} log10  [{window}"
              f" {model.valid_min_c:.1f}-{model.valid_max_c:.1f} C]")
        # Only models actually applicable at this temperature may set the
        # worst case; extrapolated ones are not evidence.
        if not extrap:
            worst = got if worst is None else min(worst, got)
    print()
    print(f"  Judge the step by its weakest IN-WINDOW model: {worst:.2f} log10")
    print("  vs a 5.00 target. Note that this worst case is the 10% NaCl")
    print("  matrix - twelve times more salt than the recipe ever held,")
    print("  and it is now zero during the heat step.")
    print()
    print("  Why 62 C and not 64 C: at 64 C the FSIS plain-yolk model is")
    print("  still in-window but every Garibaldi curve is extrapolating,")
    print("  and 62 C already clears the regulatory safe harbour while")
    print("  leaving 3 C below the plain-yolk setting point instead of 1 C.")
    print()
    print("  On the sugared-yolk line, precisely: it shows the step stays")
    print("  above target under the only sweetened matrix anyone has")
    print("  published a D-value for (10% sucrose). It does NOT validate")
    print("  the recipe's finished ~37% sugar level. Adding sugar early is")
    print("  a real error with a partial cushion, not a harmless one.")

    print()
    print(THIN)
    print(f"Step 2 - white foam: Swiss meringue to "
          f"{SWISS_MERINGUE_TARGET_C:.0f} C, held "
          f"{SWISS_MERINGUE_HOLD_MINUTES:.0f} min")
    print(THIN)
    print("  The white CANNOT be pasteurized plain. Garibaldi's Fig. 5")
    print("  measured plain white going turbid in 2 min and heavily")
    print("  coagulating by 9 min at 60 C, while white + 10% sucrose was")
    print("  only slightly turbid at 21 min. So sugar must be present,")
    print("  and we must accept a sugared matrix for this component.")
    print()
    recipe = build_sepid_o_zarrin()
    foam_pct = (recipe.mass_of("caster sugar (foam)")
                / recipe.layer_mass_g("foam") * 100.0)
    print(f"  Our foam is {foam_pct:.1f}% sugar - far above the 10% Garibaldi")
    print("  tested, so even his measured model is not conservative here.")
    print("  There is no published D-value for this concentration, so the")
    print("  step is stress-tested against a deliberately harsh model")
    print("  (compounding 2.18x protection per 10% sucrose):")
    print()
    pess = pessimistic_sugared_white(foam_pct)
    h2 = ThermalHistory(
        [0.0, 3.0, 3.0 + SWISS_MERINGUE_HOLD_MINUTES],
        [20.0, SWISS_MERINGUE_TARGET_C, SWISS_MERINGUE_TARGET_C],
    )
    print(assess("white meringue foam", h2, pess, 5.0).render())
    print()
    needed = pess.minutes_for_target(SWISS_MERINGUE_TARGET_C, 5.0)
    print(f"  Even pessimistically, 5 log10 needs only {needed:.2f} min at "
          f"{SWISS_MERINGUE_TARGET_C:.0f} C.")

    print()
    print(THIN)
    print("Step 3 - POST-LETHALITY: the hazard the sequencing created")
    print(THIN)
    print("  Moving sugar and salt after the heat step fixed the matrix")
    print("  problem. It also introduced a NEW hazard that this project")
    print("  previously did not address at all: 14.2 g of never-heated")
    print("  material is stirred into product whose entire safety claim")
    print("  rests on a thermal process.")
    print()
    print("  No log reduction is claimed for any of these. They reduce a")
    print("  hazard; they do not quantify it:")
    print()
    for i, control in enumerate(POST_LETHALITY_CONTROLS, 1):
        words = control.split()
        line = f"    {i}. "
        for w in words:
            if len(line) + len(w) > 72:
                print(line)
                line = "       " + w + " "
            else:
                line += w + " "
        print(line.rstrip())
    print()
    print(THIN)
    print("HAZARD SCOPE - what organism these numbers are about")
    print(THIN)
    print("  Every log10 figure here is for SALMONELLA and nothing else.")
    print("  '5 log10 achieved' must NOT be read as 'all pathogens")
    print("  eliminated'. In particular Listeria monocytogenes has")
    print("  different thermal resistance and can be MORE heat resistant")
    print("  than Salmonella under some conditions in liquid egg white")
    print("  (Sampedro et al. 2019, PMID 31195451). Spore-formers are")
    print("  entirely out of scope at these temperatures.")
    print()
    print(THIN)
    print("WITHDRAWN: the old '60 C / 10 min' white fallback")
    print(THIN)
    print("  Earlier documentation offered a gentler 60 C hold. It is not")
    print("  unsafe on paper - it is unsafe to RECOMMEND, because the")
    print("  margin is thin and the temperature is unforgiving.")
    print()
    need_60 = pess.minutes_for_target(60.0, 5.0)
    need_71 = pess.minutes_for_target(SWISS_MERINGUE_TARGET_C, 5.0)
    print(f"    5 log10 at 60 C needs {need_60:5.2f} min")
    print(f"    5 log10 at 71 C needs {need_71:5.2f} min")
    print()
    for hold in (5.0, 10.0):
        h3 = ThermalHistory([0.0, 1.5, 1.5 + hold], [20.0, 60.0, 60.0])
        got = accumulated_log_reduction(h3, pess)
        ratio = hold / need_60
        print(f"    60 C / {hold:4.1f} min hold -> {got:5.2f} log10 "
              f"({ratio:.1f}x the required time)")
    ratio_71 = SWISS_MERINGUE_HOLD_MINUTES / need_71
    print(f"    71 C / {SWISS_MERINGUE_HOLD_MINUTES:4.1f} min hold -> "
          f"capped        ({ratio_71:.0f}x the required time)")
    print()
    print(f"  A process needing an accurate 10-min hold to sit "
          f"{10.0 / need_60:.1f}x above")
    print("  the limit is not one to hand a home cook - especially at the")
    print("  temperature where Garibaldi photographed plain white")
    print("  coagulating. Withdrawn rather than footnoted.")

    print()
    print(THIN)
    print("Nutritional side effects of pasteurizing (both favourable)")
    print(THIN)
    print("  Heat denatures avidin, the egg-white protein that binds")
    print("  biotin and blocks its absorption (~1800 ug per egg).")
    print()
    print("  Raw egg protein is only ~51% digestible vs ~91% cooked")
    print("  (Evenepoel et al. 1998, true ileal digestibility), so")
    print("  pasteurizing nearly doubles the protein actually absorbed.")

    print()
    print(THIN)
    print("The trap in the OLD regulation (worth knowing)")
    print(THIN)
    old = EGG_WHITE_PH78.log_reduction_isothermal(f_to_c(134.0), 3.5)
    print(f"  Former egg-white safe harbour, 134 F / 3.5 min -> {old:.2f} log10")
    print("  FSIS states this does NOT reach the lethality of other")
    print("  liquid egg products, and supplies the longer Appendix III.A")
    print("  times instead. Anyone copying the old number alone would")
    print("  under-process the white.")


def main() -> int:
    print()
    print(RULE)
    print("  SEPID-O-ZARRIN : a whole-egg espresso drink")
    print("  Verified formulation and food-safety report")
    print(RULE)
    print()
    print("  Every temperature, time and threshold below is traceable to")
    print("  a published source. See docs/SOURCES.md for the full list.")

    audit_existing_drinks()
    present_recipe()
    check_foam()
    check_layers()
    verify_process()

    section("SUMMARY")
    print("  * Your current zabaione / yolk latte are raw-egg drinks.")
    print("    The espresso is not hot enough, and the latte is hot")
    print("    enough only instantaneously, with no hold time.")
    print()
    print("  * The white you have been discarding is the best foaming")
    print("    agent in the kitchen - but it is destroyed by as little")
    print("    as 0.5% yolk contamination, so the two must be built")
    print("    separately and layered, never whisked together.")
    print()
    print("  * Sepid-o-Zarrin uses the whole egg: yolk as a pasteurized")
    print("    custard base, white as a pasteurized meringue foam,")
    print("    espresso between them supplying both flavour and the")
    print("    acidity that favours foam stability.")
    print()
    print("  * The two egg steps do NOT rest on equally strong evidence,")
    print("    and the difference is stated rather than averaged away:")
    print()
    print("      yolk  - 7.93 log10 on a matrix-MATCHED model, evaluated")
    print("              inside its calibration window. It would also")
    print("              have met the plain-yolk row of the FORMER")
    print("              9 CFR 590.570 Table I - a historical benchmark,")
    print("              removed 2022-10-31, NOT current law.")
    print("      white - NO regulatory benchmark and NO published")
    print("              D-value exist for a 47.5%-sugar meringue.")
    print("              71 C / 3 min is a MODELLED EXTRAPOLATION,")
    print("              stress-tested against a deliberately harsh")
    print("              assumption. It is not a validated or")
    print("              laboratory-confirmed process, and nothing here")
    print("              should be read as claiming so.")
    print()
    print("  * WHAT THIS PROJECT HAS AND HAS NOT ESTABLISHED:")
    print()
    print("      Level 1  IMPLEMENTATION - is the arithmetic right?")
    print("               ESTABLISHED. 146 tests; the integrator is")
    print("               checked against a closed-form analytical")
    print("               solution; the models reproduce FSIS table")
    print("               rows they were never calibrated on; 15")
    print("               mutations each revert a real shipped bug and")
    print("               all are caught; primary sources read from")
    print("               page scans.")
    print("      Level 2  PROCESS        - did the real drink follow")
    print("               the modelled curve?  NOT ESTABLISHED. No")
    print("               thermocouple data exists. Every thermal")
    print("               history here is provenance=ASSUMED.")
    print("      Level 3  MICROBIOLOGY   - does the finished matrix")
    print("               achieve the reduction?  NOT ESTABLISHED. No")
    print("               microbiological challenge study has been done.")
    print()
    print("    A precision worth keeping: Level 1 establishes that this")
    print("    SOFTWARE correctly implements published D-z kinetics. It")
    print("    does not establish that D-z is the best physical model")
    print("    for every matrix here - that is a separate question, and")
    print("    an earlier phrasing ('a mathematical model has been")
    print("    validated') blurred the two.")
    print()
    print("    So the honest one-line summary is:")
    print("      'The implementation has been checked against published")
    print("       values and exact mathematics. The DRINK has not been")
    print("       validated.'")
    print()
    print("    Note also that the CURRENT authority for these models -")
    print("    the FSIS Food Safety Guideline for Egg Products - states")
    print("    verbatim that it 'does not create any new legal")
    print("    requirements or have the force and effect of law'. Its")
    print("    May 2026 revision was open for comment until 2026-07-06.")
    print("    Guidance, not law, all the way down.")
    print()
    print("  * Anyone serving this commercially, or to a pregnant,")
    print("    elderly, infant or immunocompromised person, should")
    print("    use commercially pasteurized egg rather than rely on")
    print("    the white step - see docs/LIMITATIONS.md.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
