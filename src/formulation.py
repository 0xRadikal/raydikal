"""
formulation.py
==============
Formulation engine for "SEPID-O-ZARRIN" (Persian: white-and-yolk), an
espresso beverage that uses BOTH the yolk and the white of one egg.

WHY THIS DRINK EXISTS
---------------------
Cafe zabaione and the "egg yolk latte" both use only the yolk and throw
the white away. The white is ~11 g of protein-rich, nearly fat-free
albumen and it is the single best natural foaming agent in a kitchen.
Discarding it is a waste. This module designs a build that uses the
whole egg without letting the two halves destroy each other.

THE CENTRAL TECHNICAL PROBLEM (and why naive recipes fail)
----------------------------------------------------------
You CANNOT simply whisk yolk and white together and expect foam.

Li et al. 2021 (Foods 10:2238) simulated industrial egg white
contaminated with just 0.5% w/w yolk and measured a significant drop in
both foam capacity and foam stability. Lomakina & Mikova 2006 (Czech J.
Food Sci. 24:110-118) report the classic figure: a SINGLE DROP of yolk
cut egg-white foam volume from 135 mL to 40 mL - a ~70% collapse.

Mechanism: yolk lipids, and specifically the low-density lipoprotein
(LDL) fraction of yolk plasma, compete with albumen proteins for the
air-water interface. Lipids adsorb faster but cannot form the cohesive
viscoelastic film that stabilizes a bubble, so the lamellae rupture.
Notably Li et al. found yolk GRANULES were far less damaging than yolk
PLASMA, confirming the LDL/lipid fraction as the culprit.

DESIGN CONSEQUENCE: architectural separation.
The yolk becomes a dense sweet custard base at the BOTTOM of the glass.
The white becomes a separately-whipped meringue foam on TOP. They meet
only at a visible interface, never in a shared whipping vessel. This is
not a stylistic choice - it is the only way both functions survive.

PRECEDENT (this is not an unprecedented invention)
--------------------------------------------------
The 1820s Tom & Jerry does exactly this separation: yolks beaten with
sugar, whites beaten separately to stiff peaks, folded and topped with
hot liquid. In the cocktail canon the same egg split defines three
drinks: Silver Fizz (white), Golden Fizz (yolk), Royal Fizz (whole egg).
Sepid-o-Zarrin is the espresso-native, food-safe member of that family.

SOURCED CONSTANTS
-----------------
* Sugar raises egg-protein denaturation temperature by up to ~13 C at
  54% sucrose w/w (Donovan 1977, via Renzetti et al. 2020,
  Food Hydrocolloids). NOTE: this is why the sweetened WHITE tolerates
  71 C. It no longer applies to the yolk, which is heated plain - see
  YOLK_SWEETENED_AFTER.
* Egg-white foam overrun peaks near pH 4.8; long-term drainage
  resistance is also best at pH 4.8 (Hammershoj & Larsen 1999).
  Citric acid raised egg-white foaminess from 50% to 178.2%
  (Zhang et al. 2025, Foods 14:198).
* Espresso pH is ~4.85-5.13 (National Coffee Association) - already in
  the favourable window, so the coffee itself acts as the acidifier.
* Sucrose delays foam formation and requires longer whipping; add it
  gradually, not all at once (Hanning 1945, via Lomakina & Mikova 2006).
* Sugar:egg-white ratio of 2:1 is optimal for meringue structure
  (Deleu et al., meringue microstructure study).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# --------------------------------------------------------------------------
# Sourced physical constants
# --------------------------------------------------------------------------

YOLK_MASS_G = 18.0
"""Mass of one large hen egg yolk. Typical range 17-19 g."""

WHITE_MASS_G = 35.0
"""
Mass of one large hen egg white. Bar-Vademecum's Tom & Jerry analysis
gives 40 g white / 20 g yolk per egg; 35 g is a conservative mid value
for a large egg after separation losses.
"""

YOLK_LIPID_FRACTION = 0.27
"""
Egg yolk is roughly 27% lipid by mass. Used to quantify how much fat a
cross-contamination event would drag into the white.
"""

YOLK_CARRYOVER_EVIDENCE_POINTS = {
    0.00022: (
        "Wang & Wang 2009 (J Food Sci 74:C147, AEB final report): "
        "'A concentration as low as 0.022% (as-is basis) of yolk "
        "contamination caused significant reductions in foaming "
        "capacity and foaming speed.' Whipping method, fresh liquid "
        "egg white."
    ),
    0.005: (
        "Li et al. 2021 (Comparative Study on Foaming Properties of "
        "Egg White with Yolk Fractions): significant loss of foam "
        "capacity and stability at 0.5% w/w yolk in a simulated "
        "industrial system."
    ),
}
"""
Published yolk-carryover levels at which foam damage was MEASURED.

THIS IS NOT A PERMITTED-CONTAMINATION TABLE. It is a list of
observations, each valid for its own assay and matrix.

THE ERROR THIS REPLACES
-----------------------
This module previously defined a single constant,
FOAM_DAMAGE_THRESHOLD_YOLK_FRACTION = 0.005, and described 0.5% as "a
hard design limit". A review pointed out that Wang & Wang 2009 measured
significant foaming loss at 0.022% - about 23x lower. That was checked
against the primary source (full text retrieved) and CONFIRMED verbatim.

Encoding 0.5% as "the threshold" therefore implied that anything below
it was acceptable, which the literature does not support. For 35 g of
white the two datapoints differ starkly:

    0.022%  ->  0.0077 g   (about 8 mg - far below visible)
    0.5%    ->  0.175  g

Neither number is a universal threshold; they are assay-specific. The
honest operational rule is not a number at all - see
YOLK_CARRYOVER_REQUIREMENT.
"""

YOLK_CARRYOVER_REQUIREMENT = "zero deliberate yolk carryover"
"""
The actual operational requirement for the foam.

Stated as a rule rather than a tolerance because the most sensitive
published observation (0.022% w/w, ~8 mg in 35 g) is BELOW what a cook
can see or weigh in a kitchen. A tolerance you cannot measure is not a
control; it is a false reassurance.

Practical consequence, unchanged from before but now for a defensible
reason: if the yolk breaks into the white, start over. There is no
"small enough amount" to proceed with.
"""

FOAM_DAMAGE_MOST_SENSITIVE_FRACTION = 0.00022
"""
The lowest published yolk fraction shown to significantly reduce
foaming (Wang & Wang 2009, 0.022% as-is basis).

Used by assess_foam() as the level at or above which any detected
carryover is reported as foam-damaging. Chosen as the most sensitive
datapoint rather than the most convenient one, which is the direction
that costs us margin rather than the direction that flatters us.
"""

FOAM_DAMAGE_THRESHOLD_YOLK_FRACTION = FOAM_DAMAGE_MOST_SENSITIVE_FRACTION
"""
DEPRECATED name, retained so no caller silently changes behaviour.

Note the VALUE changed (0.005 -> 0.00022) even though the name did not.
That is deliberate: the old value was the unsafe one, so preserving it
for compatibility would preserve the error.
"""

OPTIMAL_FOAM_PH = 4.8
"""
pH of maximum egg-white foam overrun and best long-term drainage
resistance (Hammershoj & Larsen 1999).
"""

ESPRESSO_PH_RANGE = (4.85, 5.13)
"""Brewed coffee pH per the National Coffee Association."""

MERINGUE_SUGAR_TO_WHITE_RATIO = 2.0
"""Optimal sugar:egg-white mass ratio for meringue structure."""

SWISS_MERINGUE_TARGET_C = 71.0
"""
Swiss-meringue bain-marie target, 71 C / 160 F.

WHY 71 C AND NOT LOWER (this changed after external review)
-----------------------------------------------------------
The white MUST carry its sugar during heating: Garibaldi 1969 Fig. 5
measured plain egg white at 60 C going turbid within 2 min and heavily
coagulating by 9 min, whereas white + 10% sucrose was only slightly
turbid at 21 min with no coagulation at 27 min. So unlike the yolk, we
cannot pasteurize this component plain and sweeten afterwards.

That forces us to accept a sugared matrix for the white, and sugar
protects Salmonella. Our foam is ~44% sugar, far above Garibaldi's
tested 10%. Stress-testing against a deliberately pessimistic model
(see thermal_safety.pessimistic_sugared_white) showed:

    60 C / 5 min  ->  ~5.05 log10   (+0.05 margin: NOT a margin)
    71 C / 3 min  ->  5 log10 reached in ~0.02 min (huge margin)

A previously documented "60 C fallback" was therefore REMOVED as
insufficiently robust. 71 C survives even the harsh assumption, and is
standard global pastry practice, so it is retained.
"""

SWISS_MERINGUE_HOLD_MINUTES = 3.0
"""
Hold at SWISS_MERINGUE_TARGET_C once reached. Generous: the pessimistic
model needs only ~0.02 min at this temperature for 5 log10.
"""

YOLK_CUSTARD_TARGET_C = 62.0
"""
Hold temperature for the yolk, heated PLAIN (see YOLK_SWEETENED_AFTER).

LOWERED FROM 64 C AFTER A SECOND REVIEW ROUND
---------------------------------------------
A reviewer pointed out that at 64 C the Garibaldi 1969 yolk models are
OUTSIDE their calibration range, so describing the 64 C step as
confirmed by "three independent models" was overstated. Two of the
three were extrapolating.

>>> RETIRED JUSTIFICATION - DO NOT REINSTATE <<<

An earlier version of THIS DOCSTRING justified 62 C as follows:

    "62 C is the top of the intersection of both evidence windows:
         FSIS Appendix III.C   : 59.4 - 65.6 C
         Garibaldi 1969 Fig. 4 : 50.0 - 62.0 C
         -> usable overlap     : 59.4 - 62.0 C
     At 62 C all three models are genuinely in-window."

Every line of that was WRONG, and it survived three review rounds and a
green 126-test suite because the tests only checked NUMBERS, never
PROSE. Specifically:

  * "50.0 - 62.0 C" was read off Fig. 4's AXIS, not its plotted data.
    The true per-curve extents are 53.0-59.5 (plain), 55.0-61.5
    (+sucrose) and 50.0-62.5 C (+NaCl).
  * The real three-way intersection is therefore 59.4-59.5 C, not
    59.4-62.0 C. See thermal_safety.YOLK_MODEL_WINDOW_NOTE, which is
    the single source of truth for these windows.
  * So "all three models in-window at 62 C" is not merely false, it is
    UNACHIEVABLE at any temperature - the intersection is 0.1 C wide
    and does not contain 62 C.

The numeric constants were corrected in an earlier round; this prose
was not, and the contradiction sat two hundred lines from its own
correction inside the same file. That is why
test_source_text_contains_no_retired_claims() now scans this file's
TEXT, and why EVIDENCE_REGISTRY exists.

WHY 62 C IS STILL THE RIGHT TARGET
----------------------------------
The conclusion survived the collapse of its original argument, but on
different and weaker grounds - which is worth stating plainly rather
than quietly keeping the number:

  1. It is in-window for the DESIGN-BASIS model. FSIS Appendix III.C
     spans 59.4-65.6 C, and that model is matrix-matched to plain,
     white-diluted yolk. This is the actual justification.
  2. It would have satisfied the plain-yolk row of the former 9 CFR
     590.570 Table I - a historical benchmark, superseded 2022-10-31,
     NOT current law. See thermal_safety.CFR_TABLE_I_F.
  3. It leaves texture margin: plain yolk begins setting around 65 C
     (Baldwin's custard state is 64.5 C), so 62 C leaves 3 C rather
     than 1 C - and the yolk is now heated PLAIN, without sugar's
     protein-stabilising effect, so that margin matters more.

The Garibaldi curves are cross-checks only, each labelled individually
with whether it interpolates or extrapolates at 62 C. Two of the three
extrapolate. That is disclosed, not averaged away.

It is also SAFER for texture. Plain yolk begins setting around 65 C
(Baldwin's custard state is 64.5 C), so 62 C leaves 3 C of margin
instead of 1 C - and the yolk is now heated plain, without sugar's
protein-stabilising effect, so that extra margin matters.

Cost: a longer hold. Accepted - see YOLK_HOLD_MINUTES.
"""

YOLK_RAMP_MINUTES = 1.5
"""
Time to bring the yolk base from room temperature to
YOLK_CUSTARD_TARGET_C in a bain-marie.

Defined as a named constant because every log10 figure quoted in this
project is the integral of an EXPONENTIAL rate over the whole history,
ramp included - so the ramp length is not a cosmetic detail. An earlier
draft of the cross-check table below was computed with a 4.0 min ramp
while the tests used 1.5 min, which inflated the quoted lethality. The
constant exists so that the recipe, the report and the tests cannot
disagree about it again.

1.5 min is the conservative end for ~23 g of liquid in a bain-marie: a
FASTER ramp accumulates less lethality, so under-stating the ramp is the
safe direction to err in.
"""

YOLK_HOLD_MINUTES = 10.0
"""
Hold at YOLK_CUSTARD_TARGET_C.

Lengthened from 5 min when the target dropped from 64 C to 62 C, and
after a numerical bug in the integrator was fixed (see
thermal_safety.SUBDIVISION_STEPS - the old code overstated lethality by
~0.95 log10 on this very step).

DESIGN BASIS: A MATRIX-MATCHED MODEL, CROSS-CHECKED AGAINST A
SUPERSEDED REGULATORY BENCHMARK
-------------------------------------------------------------
>>> RETIRED FRAMING - DO NOT REINSTATE <<<

An earlier version of this docstring was headed "PRIMARY JUSTIFICATION
IS NOW REGULATORY, NOT MODELLED" and said a safe harbour "makes it
stronger evidence than anything else in this project". Both claims are
withdrawn:

  * 9 CFR 590.570 Table I ceased to be operative on 2022-10-31
    (85 FR 68680). It is a HISTORICAL benchmark, not law.
  * Safe harbours apply to FSIS-inspected official plants. A home
    kitchen has none, of any era. So no safe harbour was ever
    "available to us" in the legal sense.
  * Even the CURRENT authority - the FSIS Food Safety Guideline for
    Egg Products (revised May 2026, FR doc 2026-08702) - states
    verbatim that it "does not create any new legal requirements or
    have the force and effect of law", and was still open for comment
    until 2026-07-06. Guidance, not law.

The actual design basis is therefore the MODEL, applied to a matrix it
was calibrated on: FSIS Appendix III.C plain egg yolk, in-window at
62 C, giving 7.93 log10 against a 5.00 target.

HISTORICAL CROSS-CHECK (secondary, and superseded)
--------------------------------------------------
62 C / 10 min WOULD HAVE satisfied both plain-yolk rows of the former
Table I:

    142 F (61.1 C) / 3.5 min   <- exceeded on both axes
    140 F (60.0 C) / 6.2 min   <- exceeded on both axes

That is worth computing because it is an independent judgement, reached
by a regulator rather than by our own arithmetic - but it is a
historical one. It applies to the PRE-HEAT EGG PHASE only, and only
because that phase is categorically plain yolk: no sugar and no salt in
the pan (see PREHEAT_BASE_INGREDIENTS).

Worth stating plainly: this step would NOT have satisfied the "salt
yolk" or "sugar yolk" row, which required 144 F (62.2 C) / 6.2 min. We
are 0.22 C short. That is the concrete cost of letting salt or sugar
into the kill step, and the reason both are added afterwards.

And the FINISHED sweetened base matched no row at all - 38.0% added
nonegg ingredients against category caps of <2% and 2-12%. See
thermal_safety.FINISHED_BASE_NOT_IN_ANY_ROW.

MODEL CROSS-CHECKS (secondary, and honestly labelled)
-----------------------------------------------------
Evaluated on the canonical recipe history - a 1.5 min ramp from 20 C to
62 C, then a 10.0 min hold - integrated with 512 subdivisions per
segment. This is the same history the test suite and the report build,
so these figures are test-locked rather than transcribed:

    FSIS Appendix III.C plain yolk    ->  7.93 log10   in-window
    Garibaldi plain yolk              -> >=12   log10   EXTRAPOLATED +2.5 C
    Garibaldi yolk + 10% sucrose      ->  6.57 log10   EXTRAPOLATED +0.5 C
    Garibaldi yolk + 10% NaCl         ->  5.37 log10   in-window

The ramp length is stated explicitly because an earlier draft of this
docstring quoted 8.08 / 6.65 / 5.44 - the values for a 4.0 min ramp,
which is not the process we specify. Those figures were higher, i.e.
the drift flattered the design, so it is recorded here rather than
silently corrected. test_docstring_cross_checks_match_the_real_process
now recomputes these from the live constants.

An earlier version of this docstring also claimed all three models were
in-window at 62 C. That was FALSE, and it was our own error rather than
a reviewer's catch - see thermal_safety.YOLK_MODEL_WINDOW_NOTE. The real
Fig. 4 data extents make a simultaneous in-window cross-check impossible
at any temperature.

HOW TO READ THE 5.37 FIGURE - CORRECTED AFTER REVIEW
----------------------------------------------------
An earlier version of this docstring called 5.37 log10 the "worst
credible case". That was challenged, checked, and the challenge was
UPHELD. 5.37 is computed on Garibaldi's yolk + 10% NaCl matrix. The
recipe's kill step contains 0% NaCl. So 5.37 is not a worst case for
our product at all - it is a STRESS TEST against a deliberately
different, deliberately harsher matrix.

The distinction matters because nothing in the literature establishes
that salt protection scales linearly, or even monotonically, from 0% to
10%. Interpolating our 0% matrix onto that curve would be invented
precision. The honest statement is:

    "The step still clears 5 log10 even if evaluated on a matrix
     carrying 10% salt, which ours does not."

That is a robustness observation, not a lower bound on our own product.

The design-basis figure for the actual pre-heat matrix (plain,
white-diluted yolk at ~43% egg solids) remains the FSIS Appendix III.C
result: 7.93 log10. It is in-window and matrix-matched, which is why it
is the design basis rather than the more dramatic number.
"""

YOLK_STEP_CROSS_CHECKS = {
    "liquid egg yolk, plain": 7.93,
    "egg yolk + 10% sucrose": 6.57,
    "egg yolk + 10% NaCl": 5.37,
}
"""
The cross-check figures quoted in the YOLK_HOLD_MINUTES prose above, in
machine-readable form, keyed by DzModel.name.

Prose can drift; a dict can be asserted against. test_formulation's
test_docstring_cross_checks_match_the_real_process recomputes each value
from YOLK_RAMP_MINUTES / YOLK_CUSTARD_TARGET_C / YOLK_HOLD_MINUTES and
fails if either the dict or the prose disagrees with the integrator.

Garibaldi's PLAIN yolk model is deliberately absent: at 62 C it is
extrapolated 2.5 C past its data and saturates the MAX_CREDITED_LOG cap,
so quoting a precise number for it would be false precision.
"""

YOLK_SOLIDS_FRACTION = 0.52
"""
Total solids of hen egg yolk, ~52% (i.e. ~48% water). Used to compute
the egg-solids content of the pre-heat base so it can be compared with
the matrix Garibaldi actually measured.
"""

WHITE_SOLIDS_FRACTION = 0.121
"""
Total solids of hen egg white, ~12.1% (i.e. ~88% water).
"""

GARIBALDI_YOLK_SOLIDS_TARGET = 0.43
"""
The egg-solids content of the yolk Garibaldi, Straka & Ijichi 1969
actually heated, quoted verbatim from their Materials & Methods:

    "(vii) yolk equivalent to the commercial product (i.e., diluted
     with egg white to approximately 43% egg solids)"

THIS IS THE SINGLE MOST USEFUL SENTENCE FOUND IN THIS PROJECT.

A reviewer argued the recipe's "plain yolk" step was invalid because
water was present during heating, and proposed heating the yolk neat
instead. Checking the primary source showed the opposite: the published
D-values were NEVER measured on neat yolk. Heating undiluted yolk (52%
solids) would have moved the process FURTHER from the tested matrix.

But the reviewer's instinct was still productive, because the paper says
diluted WITH EGG WHITE - and the earlier recipe diluted with water. Water
matches the solids number while contributing no protein; egg white
matches both. Since this drink already separates a whole egg, a few grams
of its own white are free. See YOLK_DILUENT_WHITE_G.
"""

YOLK_DILUENT_WHITE_G = 5.2
"""
Egg white whisked into the yolk BEFORE pasteurizing, to bring the base
to Garibaldi's ~43% egg solids.

Solved from the mass balance, not chosen by taste:

    (18.0 x 0.52 + w x 0.121) / (18.0 + w) = 0.43   ->   w = 5.24 g

Rounded to 5.2 g, which lands at 43.06% egg solids.

This white is taken from the SAME egg whose white becomes the foam, so
the drink still uses one egg and still wastes nothing. It costs the foam
about 15% of its volume, which the 2:1 sugar ceiling and the whipping
protocol absorb.
"""

YOLK_SWEETENED_AFTER = True
"""
PROCESS-DESIGN FIX from external review.

The original process whisked sugar into the yolk BEFORE pasteurizing,
then evaluated lethality with FSIS's PLAIN yolk model. That is a matrix
mismatch, and not a harmless one: Garibaldi et al. 1969 measured
D60 = 0.40 min for plain yolk versus 4.0 min for yolk + 10% sucrose -
a TENFOLD increase in Salmonella heat resistance from sugar alone.

Rather than model the sweetened matrix, the process now pasteurizes the
yolk plain and stirs the sugar in afterwards, off the heat. The
lethality step then genuinely happens in the matrix the model describes.

The safest fix for a modelling problem is a process that does not need
the model.

Trade-off accepted: without sugar's protective effect on the PROTEINS
(Donovan 1977), a plain yolk is more delicate, so continuous whisking
and accurate temperature control matter more. Lowering the target to
62 C buys back 3 C of margin below the setting point, which offsets
much of this.

HOW FAR THE "TOLERATES EARLY SWEETENING" CLAIM ACTUALLY GOES
------------------------------------------------------------
An earlier draft said the design is "robust to that mistake". A
reviewer correctly objected that this overstates the evidence.

What is actually supported: the step stays above target when evaluated
against Garibaldi's yolk + 10% SUCROSE model (6.57 log10 at 62 C /
10 min). That is the only sweetened-yolk matrix anyone has published a
D-value for.

What is NOT supported: that the same holds at the recipe's finished
sugar level (~37% of the base). Garibaldi measured 10%, not 37%, and
protection rises with concentration. Nobody has measured a 37% sucrose
yolk, so the honest statement is:

    "remains above target under the tested 10% sucrose model; this does
     not validate higher sugar concentrations"

So the correct reading is: adding sugar early is a real error with a
partial safety cushion, not a harmless deviation. Follow the sequence.
"""


# --------------------------------------------------------------------------
# Ingredient and recipe model
# --------------------------------------------------------------------------

Layer = Literal["base", "coffee", "foam", "garnish"]


@dataclass(frozen=True)
class Ingredient:
    """One weighed component of the drink."""

    name: str
    grams: float
    layer: Layer
    note: str = ""

    def __post_init__(self) -> None:
        if self.grams < 0:
            raise ValueError(f"{self.name}: mass cannot be negative")


@dataclass
class Recipe:
    """A complete, weighed formulation."""

    name: str
    ingredients: list[Ingredient] = field(default_factory=list)

    def add(self, name: str, grams: float, layer: Layer, note: str = "") -> "Recipe":
        self.ingredients.append(Ingredient(name, grams, layer, note))
        return self

    def total_mass_g(self) -> float:
        return sum(i.grams for i in self.ingredients)

    def layer_mass_g(self, layer: Layer) -> float:
        return sum(i.grams for i in self.ingredients if i.layer == layer)

    def find(self, name: str) -> Ingredient:
        for ing in self.ingredients:
            if ing.name == name:
                return ing
        raise KeyError(name)

    def mass_of(self, name: str) -> float:
        try:
            return self.find(name).grams
        except KeyError:
            return 0.0


# --------------------------------------------------------------------------
# Foam integrity analysis
# --------------------------------------------------------------------------

@dataclass
class FoamAssessment:
    """Result of checking whether the white foam can actually survive."""

    yolk_contamination_fraction: float
    most_sensitive_evidence_point: float
    """
    The LOWEST published yolk fraction shown to reduce foaming
    (0.022% w/w, Wang & Wang 2009).

    NAMING NOTE - corrected after review
    ------------------------------------
    This field used to be called `threshold`, and that name did real
    damage: it implied a no-effect level below which carryover is
    acceptable. No such level has been established by any study. The
    two published figures (0.022% and 0.5%) are OBSERVATIONS in
    different assays, not limits.

    A reviewer pointed out that the surrounding documentation already
    said "not a universal threshold" while the API went on treating it
    as exactly that. The name is now honest about what the number is.
    """
    sugar_to_white_ratio: float
    ph_estimate: float
    warnings: list[str] = field(default_factory=list)

    @property
    def below_most_sensitive_evidence_point(self) -> bool:
        """
        Is carryover below the lowest published damage observation?

        DELIBERATELY NOT NAMED `foam_will_survive`.

        The old name asserted an outcome the evidence cannot support:
        0.022% is where damage was first MEASURED, not where it begins.
        Below it, the honest position is "no published observation",
        which is not the same as "fine".

        For the operational rule see YOLK_CARRYOVER_REQUIREMENT: zero
        deliberate carryover, because 0.022% of a 35 g white is about
        8 mg - below what a kitchen can see or weigh.
        """
        return (
            self.yolk_contamination_fraction
            < self.most_sensitive_evidence_point
        )

    @property
    def foam_will_survive(self) -> bool:
        """
        DEPRECATED alias, retained so no caller silently changes
        behaviour. Prefer `below_most_sensitive_evidence_point`, which
        does not promise an outcome.
        """
        return self.below_most_sensitive_evidence_point

    def render(self) -> str:
        # "NO OBSERVED DAMAGE" rather than "OK": below the most
        # sensitive published figure there is no evidence either way,
        # and printing "OK" would assert a no-effect level that no
        # study has established.
        status = (
            "NO OBSERVED DAMAGE"
            if self.below_most_sensitive_evidence_point
            else "COLLAPSE RISK"
        )
        lines = [
            f"[{status}] egg white foam",
            f"  yolk contamination : {self.yolk_contamination_fraction * 100:.3f}% w/w",
            f"  lowest published damage observation : "
            f"{self.most_sensitive_evidence_point * 100:.3f}% w/w "
            f"(Wang & Wang 2009)",
            f"  requirement        : {YOLK_CARRYOVER_REQUIREMENT}",
            f"  sugar:white ratio  : {self.sugar_to_white_ratio:.2f}",
            f"  working pH         : ~{self.ph_estimate:.2f}",
        ]
        lines.extend(f"  warning: {w}" for w in self.warnings)
        return "\n".join(lines)


def assess_foam(
    white_g: float,
    sugar_in_foam_g: float,
    yolk_carryover_g: float,
    ph_estimate: float,
) -> FoamAssessment:
    """
    Determine whether the meringue foam is viable.

    yolk_carryover_g models sloppy separation: yolk accidentally left in
    the white. Because lipid is the active foam-killer, even a small
    carryover matters.

    Any non-zero carryover produces a warning, and the warning names
    which published observation (if any) it has reached - 0.022%
    (Wang & Wang 2009) or 0.5% (Li et al. 2021). Amounts below both are
    reported as "no published observation", explicitly NOT as safe: no
    study establishes a no-effect level, and 0.022% of a 35 g white is
    roughly 8 mg, below kitchen detection.

    This function therefore reports evidence, not a verdict. See
    YOLK_CARRYOVER_REQUIREMENT for the operational rule.
    """
    if white_g <= 0:
        raise ValueError("white mass must be positive")
    if yolk_carryover_g < 0:
        raise ValueError("carryover cannot be negative")

    fraction = yolk_carryover_g / white_g
    warnings: list[str] = []

    if yolk_carryover_g > 0:
        detail = (
            f"yolk carryover {fraction * 100:.4f}% w/w "
            f"({yolk_carryover_g:.4f} g). "
        )
        if fraction >= 0.005:
            detail += (
                "At or above the 0.5% level where Li et al. 2021 measured "
                "significant loss of foam capacity and stability. "
            )
        elif fraction >= FOAM_DAMAGE_MOST_SENSITIVE_FRACTION:
            detail += (
                "At or above 0.022%, the LOWEST published level shown to "
                "significantly reduce foaming capacity and speed "
                "(Wang & Wang 2009). Note this is ~8 mg in 35 g of white - "
                "below what a kitchen can see or weigh. "
            )
        else:
            detail += (
                "Below the lowest published damage observation (0.022%, "
                "Wang & Wang 2009), but that is NOT evidence of safety: no "
                "study establishes a no-effect level, and this quantity is "
                "too small to measure in a kitchen anyway. "
            )
        detail += (
            f"Requirement is {YOLK_CARRYOVER_REQUIREMENT}: discard and "
            "re-separate."
        )
        warnings.append(detail)

    ratio = sugar_in_foam_g / white_g if white_g else 0.0
    if ratio > MERINGUE_SUGAR_TO_WHITE_RATIO:
        warnings.append(
            f"sugar:white ratio {ratio:.2f} exceeds the 2:1 structural "
            "optimum; foam will be dense and slow to whip"
        )

    if not (4.0 <= ph_estimate <= 6.0):
        warnings.append(
            f"pH {ph_estimate:.2f} is outside the favourable 4.0-6.0 band; "
            f"overrun peaks near pH {OPTIMAL_FOAM_PH}"
        )

    return FoamAssessment(
        yolk_contamination_fraction=fraction,
        most_sensitive_evidence_point=FOAM_DAMAGE_MOST_SENSITIVE_FRACTION,
        sugar_to_white_ratio=ratio,
        ph_estimate=ph_estimate,
        warnings=warnings,
    )


# --------------------------------------------------------------------------
# Density / layering physics
# --------------------------------------------------------------------------

def foam_density_g_per_ml(overrun_percent: float, liquid_density: float = 1.04) -> float:
    """
    Density of a foam given its overrun.

    Overrun is the volume increase from incorporated air:
        overrun% = (V_foam - V_liquid) / V_liquid * 100

    A foam of overrun O has density  rho_liquid / (1 + O/100).
    At a modest 200% overrun the foam is ~0.35 g/mL - about a third the
    density of the coffee layer, which is what makes stable stratification
    possible rather than accidental.
    """
    if overrun_percent < 0:
        raise ValueError("overrun cannot be negative")
    return liquid_density / (1.0 + overrun_percent / 100.0)


def will_layer_float(upper_density: float, lower_density: float) -> bool:
    """A layer floats only if it is strictly less dense than the one below."""
    return upper_density < lower_density


def sugar_syrup_density_g_per_ml(brix: float) -> float:
    """
    APPROXIMATE density of a pure sucrose solution from its Brix
    (% sugar by mass), using the common linear rule of thumb:

        rho ~= 1.0 + 0.004 * Brix

    LIMITATIONS (flagged after external review)
    -------------------------------------------
    This is an approximation for a pure sucrose-water solution. The real
    base also contains yolk solids and lipids, and the real foam's
    density depends on the overrun a given whisk actually achieves. So
    the layering figures this produces are an ENGINEERING ESTIMATE
    indicating the expected direction and rough magnitude of the density
    gradient - not a measurement of the finished drink.

    Earlier documentation called the resulting stack "thermodynamically
    stable", which overstated a rule-of-thumb calculation. The claim is
    now that layering is EXPECTED to work because the estimated density
    gap is large (roughly 1.15 vs 1.01 vs 0.35 g/mL); confirming it
    requires actually pouring the drink.
    """
    if not (0.0 <= brix <= 60.0):
        raise ValueError("brix outside supported 0-60 range")
    return 1.0 + 0.004 * brix


# --------------------------------------------------------------------------
# The canonical recipe
# --------------------------------------------------------------------------

def build_sepid_o_zarrin() -> Recipe:
    """
    The reference build. One whole egg, nothing discarded.

    Layer 1 (base)  : yolk pasteurized PLAIN at 62 C, sweetened after
    Layer 2 (coffee): double espresso
    Layer 3 (foam)  : white + sugar + salt, Swiss meringue to 71 C
    Layer 4 (garnish): cocoa / cardamom for aroma and visual contrast

    THE SUGAR ASYMMETRY (the key design consequence of review)
    ----------------------------------------------------------
    Sugar is present in both egg layers, but enters at OPPOSITE times,
    because the two components impose opposite constraints:

      YOLK  - sugar added AFTER the heat step.
              Sugar raises Salmonella heat resistance ~10x in yolk
              (Garibaldi 1969: D60 0.40 -> 4.0 min), so heating it
              sweetened would invalidate the plain-yolk safety model.

      WHITE - sugar must be present DURING the heat step.
              Garibaldi Fig. 5 measured plain white heavily coagulating
              by 9 min at 60 C, while +10% sucrose showed no coagulation
              at 27 min. Heating the white plain would scramble it.

    So the white accepts a sugared matrix and compensates with a higher
    temperature (71 C) that survives even a pessimistic sugar-protection
    assumption; the yolk avoids the problem entirely by sequencing.
    """
    r = Recipe("Sepid-o-Zarrin")

    # --- Layer 1: the yolk custard base -----------------------------------
    r.add(
        "egg yolk",
        YOLK_MASS_G,
        "base",
        "one large yolk; separated with zero white carryover tolerance",
    )
    r.add(
        "caster sugar (base)",
        14.0,
        "base",
        "stirred in AFTER pasteurization, off the heat: sugar raises "
        "Salmonella heat resistance ~10x in yolk (Garibaldi 1969), so it "
        "must not be present during the kill step; it still sets the "
        "base density and sweetness",
    )
    r.add(
        "egg white (base diluent)",
        YOLK_DILUENT_WHITE_G,
        "base",
        "added before heating to thin the yolk so it heats evenly and "
        "pours as a layer. Deliberately egg WHITE, not water: Garibaldi "
        "1969 measured its yolk D-values on 'yolk equivalent to the "
        "commercial product (i.e., diluted with egg white to "
        "approximately 43% egg solids)', so diluting with white "
        "reproduces the matrix the model was calibrated on. Taken from "
        "the same egg's white, so nothing is added and nothing wasted",
    )
    r.add(
        "fine salt (base)",
        0.2,
        "base",
        "stirred in AFTER pasteurization, with the sugar: the FORMER 9 CFR "
        "590.570 Table I (superseded 2022-10-31) reclassified yolk with "
        ">=2% salt into a category needing 146 F rather than 142 F, and "
        "Garibaldi 1969 measured "
        "D60 rising 0.40 -> 5.1 min (12.75x) for yolk + 10% NaCl. Salt "
        "is kept out of the kill step for the same reason as sugar; it "
        "still suppresses sulfur notes and sharpens sweetness",
    )

    # --- Layer 2: espresso -------------------------------------------------
    r.add(
        "double espresso",
        30.0,
        "coffee",
        "brewed coffee pH ~4.85-5.13 (NCA). Sits near the pH 4.8 foam "
        "overrun optimum, but note the layers are only in contact at an "
        "interface and egg white is strongly buffered, so the coffee is "
        "NOT assumed to set the foam's pH - the lemon does that",
    )

    # --- Layer 3: the meringue foam ---------------------------------------
    r.add(
        "egg white",
        WHITE_MASS_G - YOLK_DILUENT_WHITE_G,
        "foam",
        "the component normally thrown away; the entire point of the "
        "drink. This is the whole white MINUS the few grams diverted "
        "into the yolk base as its diluent, so the egg is still used "
        "in full",
    )
    r.add(
        "caster sugar (foam)",
        28.0,
        "foam",
        "gives the 0.94:1 sugar:white ratio - under the 2:1 structural "
        "ceiling, added gradually because sucrose delays foam formation "
        "(Hanning 1945)",
    )
    r.add(
        "lemon juice",
        1.0,
        "foam",
        "the actual acidifier for the foam, added directly to the white "
        "where it can overcome albumen's buffering; targets the pH 4.8 "
        "overrun optimum (Hammershoj & Larsen 1999). Final pH is an "
        "estimate until measured with a meter",
    )
    r.add(
        "fine salt (foam)",
        0.1,
        "foam",
        "NaCl enhances egg-white foaming ability and stability "
        "(Raikos et al. 2007)",
    )

    # --- Layer 4: aromatics ------------------------------------------------
    r.add(
        "cocoa powder",
        0.5,
        "garnish",
        "bitter aromatic contrast against the sweet foam",
    )
    r.add(
        "ground cardamom",
        0.1,
        "garnish",
        "classic pairing with coffee zabaione (cf. Food52 Zabaglione al "
        "Caffe, which uses crushed cardamom pods)",
    )

    return r


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

HAZARD_SCOPE = """
WHAT ORGANISM THIS PROJECT'S NUMBERS ARE ABOUT - AND WHAT THEY ARE NOT
======================================================================

Every log10 figure in this repository is for SALMONELLA, and for
nothing else. That is the organism FSIS Appendix III targets, the
organism Garibaldi 1969 measured, and the organism the egg-products
performance standard is written around.

It follows that "5 log10 achieved" must NEVER be read as "all pathogens
eliminated". In particular:

  * Listeria monocytogenes has different thermal resistance from
    Salmonella and can be MORE heat resistant under some conditions in
    liquid egg white (Sampedro et al. 2019, "Thermal Resistance of
    Listeria monocytogenes and Salmonella spp. in Liquid Egg White",
    PMID 31195451). A process validated on Salmonella is not
    automatically adequate for Lm. FSIS added Lm hazard discussion to
    the 2020 egg-products guidance for exactly this reason.

  * Egg-white pH strongly changes Salmonella D-values, and the pH of
    albumen drifts upward with storage age (7.8 fresh, rising to
    9.3-9.4). This project's white model assumes pH 7.8 - the FRESH,
    least favourable case - but the pH of a given egg is not measured.

  * Spore-formers are entirely out of scope. No pasteurization process
    at these temperatures addresses them.

This scope statement exists because a reviewer correctly noted that a
verified Salmonella figure can be silently over-read as a general
safety claim. It is a limitation of the evidence, not a caveat on the
arithmetic.
"""

POST_LETHALITY_CONTROLS = (
    "Add sugar and salt to the yolk base while it is still above 60 C, "
    "immediately after the hold and without transferring vessels, so the "
    "additions are stirred into hot product rather than cooling product.",
    "Use dry, unopened-or-clean-scooped sugar and salt. Dry sugar and "
    "salt do not support growth (water activity far below 0.6), but they "
    "CAN carry viable Salmonella as inert passengers - so a contaminated "
    "scoop transfers organisms directly into pasteurized product.",
    "Use a clean, dry, dedicated spoon for the additions. Never the "
    "spoon or whisk that touched the raw separated egg.",
    "Never return the raw shell, the raw-egg bowl, or unwashed hands to "
    "the pasteurized base. Cross-contamination after lethality is the "
    "dominant remaining hazard for this component.",
    "Serve promptly. If the drink is not consumed within 2 hours, "
    "refrigerate below 5 C; the base is a high-moisture, low-acid, "
    "nutrient-rich medium and lethality confers no lasting protection.",
    "Do not hold the finished base warm (5-60 C) for extended periods. "
    "Pasteurization is not sterilization and it grants no shelf life.",
)
"""
Hygiene controls for the additions made AFTER the yolk kill step.

WHY THIS EXISTS - A REAL GAP, NOT A FORMALITY
---------------------------------------------
A review made a point that had no answer in this project: moving sugar
and salt after the heat step correctly solves the MATRIX problem
(neither protectant is present during lethality), but it introduces a
different hazard that the project had not addressed at all -
RECONTAMINATION.

The logic is uncomfortable but sound. Before the fix, sugar was in the
pan and got pasteurized along with the yolk. After the fix, 14.2 g of
never-heated material is stirred into product whose entire safety claim
rests on a thermal process. Any organism on the spoon, in the sugar, or
on the cook's hands lands in pasteurized product with nothing left to
kill it.

So the fix traded a modelling error for a handling requirement. That is
still the right trade - a modelling error is invisible and a handling
requirement is actionable - but pretending the second hazard does not
exist would have been dishonest.

The former 9 CFR 590.570(b) itself required, verbatim, that
"holding, packaging, facilities and operations shall be such as to
prevent contamination of the product" - i.e. the regulation never
treated the thermal step as the whole of pasteurization either.

SCOPE LIMIT, stated plainly: these are controls, not a validated
sanitation programme. They reduce a hazard; they do not quantify it.
No log reduction is claimed for any item in this tuple.
"""

PREHEAT_BASE_INGREDIENTS = ("egg yolk", "egg white (base diluent)")
"""
The ONLY ingredients permitted in the pan during the yolk kill step.

Named explicitly so a test can assert that nothing else - not sugar, not
salt - has quietly been moved back into the heat step. Both known
solutes that protect Salmonella in yolk are excluded by construction:

    sugar : Garibaldi D60 0.40 -> 4.0 min  (10x)
    salt  : Garibaldi D60 0.40 -> 5.1 min  (12.75x)
"""


def preheat_base_mass_g(recipe: Recipe) -> float:
    """Mass actually present in the pan during the yolk kill step."""
    return sum(
        i.grams
        for i in recipe.ingredients
        if i.layer == "base" and i.name in PREHEAT_BASE_INGREDIENTS
    )


def preheat_salt_percent(recipe: Recipe) -> float:
    """
    Added salt as a percent of the pre-heat yolk matrix.

    Must be 0.0 for the current process, because salt is added after the
    heat step. Retained as a live measurement rather than an assumption
    so that the former 9 CFR 590.570 "plain yolk" categorisation is
    verified from the recipe itself rather than asserted in a comment.
    (That table is a historical benchmark, not current law - see
    thermal_safety.EVIDENCE_REGISTRY.)
    """
    pre = preheat_base_mass_g(recipe)
    if pre <= 0:
        return 0.0
    salt = sum(
        i.grams
        for i in recipe.ingredients
        if i.layer == "base" and "salt" in i.name
        and i.name in PREHEAT_BASE_INGREDIENTS
    )
    return salt / pre * 100.0


def preheat_egg_solids_percent(recipe: Recipe) -> float:
    """
    Egg-solids content of the matrix that is actually pasteurized.

    Compared by test against GARIBALDI_YOLK_SOLIDS_TARGET (43%), the
    composition on which the yolk D-values were measured. This is the
    number that decides whether the "plain yolk" model is being applied
    to a matrix resembling the one it came from.
    """
    yolk = recipe.mass_of("egg yolk")
    white = recipe.mass_of("egg white (base diluent)")
    total = yolk + white
    if total <= 0:
        return 0.0
    solids = yolk * YOLK_SOLIDS_FRACTION + white * WHITE_SOLIDS_FRACTION
    return solids / total * 100.0


def sugar_percent_of_base(recipe: Recipe) -> float:
    """
    Sugar as a percent of the yolk base mass. Reported because the
    denaturation-temperature protection from sugar is concentration
    dependent (Donovan 1977 measured up to +13 C at 54% sucrose).
    """
    base = recipe.layer_mass_g("base")
    if base <= 0:
        return 0.0
    return recipe.mass_of("caster sugar (base)") / base * 100.0


def describe(recipe: Recipe) -> str:
    """Human-readable breakdown of the formulation."""
    lines = [f"{recipe.name} - total {recipe.total_mass_g():.1f} g", ""]
    for layer in ("base", "coffee", "foam", "garnish"):
        items = [i for i in recipe.ingredients if i.layer == layer]
        if not items:
            continue
        lines.append(f"{layer.upper()}  ({recipe.layer_mass_g(layer):.1f} g)")
        for ing in items:
            lines.append(f"  {ing.grams:6.1f} g  {ing.name}")
            if ing.note:
                lines.append(f"           - {ing.note}")
        lines.append("")
    return "\n".join(lines)
