"""
thermal_safety.py
=================
Thermal-lethality (pasteurization) engine for egg-based beverages.

PURPOSE
-------
This module answers ONE question with numbers instead of guesswork:

    "Given a measured time-temperature history of an egg mixture,
     how many log10 reductions of Salmonella did we actually achieve?"

It is used to validate the two egg components of the 'Sepid o Zard'
beverage (see docs/RECIPE.md):

    * yolk base  -> heated by espresso  (target >= 5 log10)
    * white foam -> heated in bain-marie (target >= 5 log10)

SCIENTIFIC BASIS (every constant is sourced, none is invented)
--------------------------------------------------------------
1. First-order thermal inactivation / D-z model.
   D_T = D_ref * 10^((T_ref - T) / z)
   Log reduction over a thermal history = integral of dt / D_T(t).
   This is the standard model FSIS uses to derive its lethality tables
   (FSIS Food Safety Guideline for Egg Products, May 2026, Appendix III).

2. z-value and D-value anchors are REVERSE-DERIVED from the published
   FSIS Appendix III tables rather than taken from a secondary blog.
   Doing it this way means our engine reproduces the regulator's own
   numbers, which is the strongest available validation.

   FSIS Appendix III.A - Plain Egg White, pH 7.8  (target 5.7 log10):
       132.0 F (55.6 C) -> 32.16 min
       133.0 F (56.1 C) -> 22.56 min
       134.0 F (56.7 C) -> 15.43 min

   FSIS Appendix III.C - Plain Egg Yolk           (target 6.2 log10):
       139.0 F (59.4 C) -> 17.81 min
       142.0 F (61.1 C) -> 10.48 min
       150.0 F (65.6 C) ->  2.55 min

   FSIS Table 1 (reproducing the SUPERSEDED regulatory table; these
   are GUIDANCE safe harbours, not law. An earlier version of this
   header said "former regulation safe harbours, still valid" - a
   phrase that contradicted itself AND contradicted the corrected
   block 250 lines below in this same file. See CFR_TABLE_I_F for the
   full provenance and EVIDENCE_REGISTRY for authority status):
       Whole egg   140 F (60.0 C) / 3.5 min
       Plain yolk  142 F (61.1 C) / 3.5 min ; 140 F (60.0 C) / 6.2 min
       Egg white   134 F (56.7 C) / 3.5 min  (note: <5 log10, see below)

3. IMPORTANT REGULATORY NUANCE, verified in the FSIS guideline:
   the historic 134 F / 3.5 min egg-white process does NOT achieve a
   5 log10 reduction. FSIS explicitly says so and supplies the longer
   Appendix III.A times instead. This module therefore refuses to treat
   3.5 min at 56.7 C as sufficient for egg white - a mistake that a
   naive reading of the old regulation would produce.

REFERENCES
----------
- FSIS, "Food Safety Guideline for Egg Products", May 2026,
  Table 1 + Appendix III.A / III.B / III.C.
- 9 CFR 590.570 (pasteurized egg products must be edible without
  further preparation).
- Schuman et al. 1997, in-shell pasteurization 57 C / 75 min,
  as tabulated by Baldwin, "A Practical Guide to Sous Vide Cooking".
- Istituto Nazionale Espresso Italiano (INEI), certified espresso
  parameters: water exit temperature 88 +/- 2 C, TEMPERATURE OF THE
  DRINK IN THE CUP 67 +/- 3 C.

A NOTE ON AN ERROR THIS MODULE EXISTS TO PREVENT
------------------------------------------------
An early draft of this analysis assumed espresso arrives in the cup at
~90 C, because 88-93 C is the number baristas quote. That number is the
BREW WATER temperature at the group head, not the beverage temperature.
The INEI specification puts the drink in the cup at 67 +/- 3 C, and a
hobbyist thermocouple measurement in a ceramic cup read 146 F (63.3 C).
Using 90 C instead of 67 C overstates the mixture temperature by ~15 C
and can flip a lethality verdict from "raw" to "pasteurized" - which is
exactly the kind of silent error that gets people sick. The constant
below is therefore pinned to the published standard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Sequence


# --------------------------------------------------------------------------
# Unit helpers
# --------------------------------------------------------------------------

def f_to_c(fahrenheit: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (fahrenheit - 32.0) * 5.0 / 9.0


def c_to_f(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return celsius * 9.0 / 5.0 + 32.0


# --------------------------------------------------------------------------
# The D-z thermal death model
# --------------------------------------------------------------------------

MAX_CREDITED_LOG = 12.0
"""
Ceiling on reported log10 reduction.

WHY THIS EXISTS
---------------
A D-z model is a local linearization of thermal death kinetics,
calibrated over a narrow temperature window. Extrapolating it far above
that window produces arithmetically valid but physically meaningless
numbers: an early version of this module reported "12020 log10" for a
71 C meringue step, because the egg-white model's z of ~3.5 C was
extrapolated ~14 C beyond its calibration range.

There is no such thing as 12000 log10 of reduction. A 12 log10
reduction already means one surviving cell in a trillion, which exceeds
any plausible starting bioburden in a single egg. Reporting anything
beyond that is false precision, so results are capped and the
extrapolation is disclosed rather than hidden.
"""


@dataclass(frozen=True)
class DzModel:
    """
    First-order thermal inactivation model for a pathogen in a matrix.

    Attributes
    ----------
    name : str
        Human-readable matrix name, e.g. "egg white pH 7.8".
    t_ref_c : float
        Reference temperature in Celsius at which d_ref_min applies.
    d_ref_min : float
        Decimal reduction time (minutes) at t_ref_c.
    z_c : float
        z-value in Celsius: the temperature rise that cuts D tenfold.
    source : str
        Provenance string. Required - we never carry an unsourced constant.
    valid_min_c, valid_max_c : float
        The temperature window the model was calibrated over. Results
        outside this window are flagged as extrapolation.
    """

    name: str
    t_ref_c: float
    d_ref_min: float
    z_c: float
    source: str
    valid_min_c: float = 0.0
    valid_max_c: float = 100.0
    is_composition_extrapolation: bool = False
    """
    True when the model itself was derived by extrapolating along a
    dimension OTHER than temperature - in practice, sugar concentration.

    Needed because a model can sit perfectly inside its temperature
    window while still resting on an unmeasured composition. Without
    this flag the pessimistic 44%-sucrose white model would report as
    'MODELLED (in-window)', which would understate the uncertainty in
    exactly the place this project already went wrong once.
    """

    def d_at(self, temp_c: float) -> float:
        """D-value (minutes) at a given temperature."""
        return self.d_ref_min * 10.0 ** ((self.t_ref_c - temp_c) / self.z_c)

    def is_extrapolation(self, temp_c: float) -> bool:
        """
        True if this result should be treated as extrapolated - either
        because temp_c is outside the calibrated window, or because the
        model's composition was itself extrapolated.
        """
        if self.is_composition_extrapolation:
            return True
        return not (self.valid_min_c <= temp_c <= self.valid_max_c)

    def log_reduction_isothermal(self, temp_c: float, minutes: float) -> float:
        """Log10 reduction for a perfectly isothermal hold."""
        if minutes <= 0.0:
            return 0.0
        return minutes / self.d_at(temp_c)

    def minutes_for_target(self, temp_c: float, target_log: float) -> float:
        """Isothermal hold time (minutes) needed to reach target_log."""
        return target_log * self.d_at(temp_c)


# --------------------------------------------------------------------------
# Model calibration from the published FSIS tables
# --------------------------------------------------------------------------

def calibrate_from_two_points(
    name: str,
    temp_a_c: float,
    minutes_a: float,
    temp_b_c: float,
    minutes_b: float,
    target_log: float,
    source: str,
    valid_min_c: float | None = None,
    valid_max_c: float | None = None,
) -> DzModel:
    """
    Derive (z, D) from two published FSIS time-temperature pairs that both
    deliver the same target log reduction.

    Because both rows achieve the same lethality:
        target_log = t_a / D(T_a) = t_b / D(T_b)
    and D(T) = D_ref * 10^((T_ref - T)/z), it follows that
        t_a / t_b = 10^((T_b - T_a) / z)
    so
        z = (T_b - T_a) / log10(t_a / t_b)

    This makes the engine reproduce the regulator's own table instead of
    relying on a hand-copied D-value from a secondary source.
    """
    import math

    if minutes_a <= 0 or minutes_b <= 0:
        raise ValueError("hold times must be positive")
    if temp_a_c == temp_b_c:
        raise ValueError("calibration needs two distinct temperatures")

    ratio = math.log10(minutes_a / minutes_b)
    if ratio == 0.0:
        raise ValueError("times identical at different temperatures: no z")

    z = (temp_b_c - temp_a_c) / ratio

    # Anchor D at temp_a_c using the target log reduction.
    d_ref = minutes_a / target_log

    # Default the validity window to the calibration span itself.
    lo, hi = sorted((temp_a_c, temp_b_c))

    return DzModel(
        name=name,
        t_ref_c=temp_a_c,
        d_ref_min=d_ref,
        z_c=z,
        source=source,
        valid_min_c=lo if valid_min_c is None else valid_min_c,
        valid_max_c=hi if valid_max_c is None else valid_max_c,
    )


# FSIS Appendix III.A - Plain Egg White, pH 7.8, target 5.7 log10.
# Calibrated on the 132.0 F / 32.16 min and 134.0 F / 15.43 min rows.
EGG_WHITE_PH78 = calibrate_from_two_points(
    name="liquid egg white, pH 7.8",
    temp_a_c=f_to_c(132.0),
    minutes_a=32.16,
    temp_b_c=f_to_c(134.0),
    minutes_b=15.43,
    target_log=5.7,
    source=(
        "FSIS Food Safety Guideline for Egg Products (May 2026), "
        "Appendix III.A, Plain Egg White pH 7.8"
    ),
    # FSIS Appendix III.A tabulates egg white from ~127.5 F to 134 F.
    # Beyond ~57 C this model extrapolates, so results get capped and
    # flagged rather than reported as precise.
    valid_min_c=f_to_c(127.5),
    valid_max_c=f_to_c(134.0),
)

# FSIS Appendix III.C - Plain Egg Yolk, target 6.2 log10.
# Calibrated on the 139.0 F / 17.81 min and 150.0 F / 2.55 min rows.
EGG_YOLK_PLAIN = calibrate_from_two_points(
    name="liquid egg yolk, plain",
    temp_a_c=f_to_c(139.0),
    minutes_a=17.81,
    temp_b_c=f_to_c(150.0),
    minutes_b=2.55,
    target_log=6.2,
    source=(
        "FSIS Food Safety Guideline for Egg Products (May 2026), "
        "Appendix III.C, Plain Egg Yolk"
    ),
    # Appendix III.C spans 139 F to 150 F (59.4-65.6 C), which happily
    # brackets the 62 C custard hold this recipe actually uses.
    valid_min_c=f_to_c(139.0),
    valid_max_c=f_to_c(150.0),
)


# --------------------------------------------------------------------------
# HISTORICAL REGULATORY BENCHMARK - *NOT* CURRENT LAW
# --------------------------------------------------------------------------
#
# READ THIS BEFORE CITING ANYTHING BELOW.
#
# An earlier version of this module described the table below as "LAW"
# and as a live "regulatory safe harbour". THAT WAS WRONG, and it was
# wrong in the direction that flattered this project - it dressed a
# superseded table up as the strongest possible evidence.
#
# What was actually verified (eCFR API, boundary-tested):
#
#   * Table I DID exist in 9 CFR 590.570, then titled "Pasteurization of
#     liquid eggs". Our SECTION CITATION was correct. (A reviewer
#     asserted the table lived in 590.575; it did not - 590.575 was
#     "Heat treatment of dried whites", covering spray/pan dried
#     albumen held for 5-7 DAYS. That claim was checked and rejected.)
#
#   * Last day Table I was operative : 2022-10-30
#     First day it was gone          : 2022-10-31
#     Verified by fetching both dates: 'Table I' count 2 -> 0.
#
#   * The amending rule is 85 FR 68680 (Oct 29, 2020), which also
#     retitled the section to "Control of pathogens in pasteurized egg
#     products" and REMOVED 590.575 entirely.
#
#   * Current 9 CFR 590.570, in full, is a PERFORMANCE STANDARD:
#         "Pasteurized egg products must be produced to be edible
#          without additional preparation to achieve food safety..."
#     There are no times, no temperatures, and no product categories.
#
# So where did the safe harbours go? They did not vanish - they moved
# out of regulation and into guidance. FSIS says so in its own words in
# the preamble to 85 FR 68680:
#
#     "The tables in the appendix of the compliance guideline for
#      pasteurization times and temperatures are not minimum
#      lethalities, but rather safe harbors for plants to follow and be
#      reasonably certain that they will be meeting the requirement in
#      9 CFR 590.570 ... plants are not required to follow the safe
#      harbors and may use alternate procedures, if they have adequate
#      scientific support."
#
# That guidance is the FSIS Food Safety Guideline for Egg Products -
# which is ALREADY the source of the D-z models above (Appendix III.A
# and III.C). So the current authority was in this repo all along; only
# the CFR framing was stale.
#
# HOW THE TABLE BELOW MAY THEREFORE BE USED:
#
#   ALLOWED : as a historical benchmark. A process that would have
#             satisfied a 1971-2022 row is a process the regulator once
#             considered adequate for that category. That is meaningful
#             context, and it is independent of our D-z arithmetic.
#
#   FORBIDDEN : calling it current law, a current safe harbour, or
#             "REGULATORY" evidence for the finished drink. The
#             finished sweetened base is not in ANY row (see
#             FINISHED_BASE_NOT_IN_ANY_ROW below), and even the
#             pre-heat phase only *resembles* a row - we are a kitchen,
#             not an FSIS-inspected official plant, so no safe harbour
#             is available to us at all in the legal sense.
#
# Evidence grade for anything derived from this block is
# Evidence.REGULATORY_HISTORICAL, never MEASURED.

CFR_TABLE_I_F = {
    "albumen (without chemicals)": ((134.0, 3.5), (132.0, 6.2)),
    "whole egg": ((140.0, 3.5), None),
    "whole egg blends (<2% nonegg)": ((142.0, 3.5), (140.0, 6.2)),
    "fortified whole egg and blends": ((144.0, 3.5), (142.0, 6.2)),
    "salt whole egg (>=2% salt)": ((146.0, 3.5), (144.0, 6.2)),
    "sugar whole egg (2-12% sugar)": ((142.0, 3.5), (140.0, 6.2)),
    "plain yolk": ((142.0, 3.5), (140.0, 6.2)),
    "sugar yolk (>=2% sugar)": ((146.0, 3.5), (144.0, 6.2)),
    "salt yolk (2-12% salt)": ((146.0, 3.5), (144.0, 6.2)),
}
"""
The FORMER 9 CFR 590.570 Table I, "Pasteurization requirements".
Each value is ((temp_F, minutes), (alternative temp_F, minutes) | None).

PROVENANCE, fully pinned:
    promulgated : 36 FR 9814,  May 28 1971
    last amended: 85 FR 81341, Dec 16 2020
    superseded  : 85 FR 68680, Oct 29 2020 (effective in eCFR
                  2022-10-31; last operative day 2022-10-30)
    text source : eCFR versioner API, title-9 part 590 @ 2021-01-01
                  and @ 2022-10-30, cross-checked against
                  govinfo CFR-2020-title9-vol2-part590.

THIS IS A HISTORICAL BENCHMARK. It is NOT current law. See the long
comment above this dict for the verification trail and for the rules on
what may and may not be claimed from it.

READ THE YOLK ROWS TOGETHER:

    plain yolk                142 F / 3.5 min   or  140 F / 6.2 min
    sugar yolk (>=2% sugar)   146 F / 3.5 min   or  144 F / 6.2 min
    salt  yolk (2-12% salt)   146 F / 3.5 min   or  144 F / 6.2 min

The regulator penalised BOTH salt and sugar by +4 F (2.2 C). This is an
INDEPENDENT line of support for keeping both out of the kill step -
independent because it is a regulatory judgement rather than a
re-reading of Garibaldi's D-values.

Note equally what the thresholds ARE. The salted category began at 2%
added salt; the sugared category at 2% added sugar. Below those the
product was categorised as PLAIN yolk.

WHAT "PLAIN" MEANT, since this was challenged:
"Plain" contrasts with SUGAR and SALT - i.e. with added NONEGG
ingredients. It does not mean "undiluted yolk". Commercial liquid yolk
is itself white-diluted: Garibaldi's own item (vii) is "yolk equivalent
to the commercial product (i.e., diluted with egg white to
approximately 43% egg solids)". A reviewer proposed reclassifying our
pre-heat base as a "whole egg blend" because it contains 5.2 g of white.
That was checked and REJECTED: at 43.06% egg solids the base sits on
commercial plain yolk (0.06 points away) and 17.4 points away from
whole egg (25.65%). Relabelling it "whole egg blend" would make the
description LESS accurate, not more.
"""

class AuthorityStatus(str, Enum):
    """
    Legal / epistemic status of a cited authority.

    WHY THIS EXISTS
    ---------------
    Four separate rounds of review found the same class of defect: a
    document in this repo describing an authority in the wrong TENSE or
    the wrong CATEGORY - "still valid" for a superseded table, "law,
    not a model" for guidance, "safe harbour" for a kitchen that can
    never have one. Each time the numbers were right and the prose was
    wrong, and each time a green test suite failed to notice because
    the tests only checked numbers.

    Statuses are ordered from most to least binding. Nothing in this
    project reaches CURRENT_LAW.
    """

    CURRENT_LAW = "CURRENT LAW (operative regulation)"
    """An operative regulation imposing a requirement on us. None apply."""

    SUPERSEDED_LAW = "SUPERSEDED LAW (was operative, now removed)"
    """
    A regulation that WAS operative and no longer is. Usable as a
    historical benchmark; never citable in the present tense.
    """

    AGENCY_GUIDANCE = "AGENCY GUIDANCE (not legally binding)"
    """
    Official agency guidance. Carries real weight - it is what a
    regulator says it expects - but explicitly not law. FSIS states
    this of its own egg-products guideline verbatim.
    """

    PEER_REVIEWED = "PEER-REVIEWED MEASUREMENT"
    """A measurement in the primary literature."""


@dataclass(frozen=True)
class Authority:
    """One cited authority, with its status pinned and dated."""

    key: str
    title: str
    status: AuthorityStatus
    citation: str
    note: str = ""
    operative_from: str | None = None
    operative_until: str | None = None

    @property
    def is_citable_in_present_tense(self) -> bool:
        """
        May this authority be described as currently in force?

        False for SUPERSEDED_LAW, which is the trap this registry
        exists to close.
        """
        return self.status is not AuthorityStatus.SUPERSEDED_LAW


EVIDENCE_REGISTRY: dict[str, Authority] = {
    "cfr_590_570_current": Authority(
        key="cfr_590_570_current",
        title="9 CFR 590.570, Control of pathogens in pasteurized egg products",
        status=AuthorityStatus.CURRENT_LAW,
        citation="85 FR 68680 (Oct 29 2020); eCFR, retrieved 2026-09-08",
        note=(
            "A pure PERFORMANCE STANDARD: no times, no temperatures, no "
            "product categories. It states that pasteurized egg products "
            "must be edible without additional preparation. It imposes no "
            "specific process on anyone, and it binds FSIS-inspected "
            "official plants rather than kitchens. Full text in "
            "CFR_590_570_CURRENT_TEXT."
        ),
        operative_from="2022-10-31",
    ),
    "cfr_590_570_table_i": Authority(
        key="cfr_590_570_table_i",
        title="9 CFR 590.570 Table I, Pasteurization requirements",
        status=AuthorityStatus.SUPERSEDED_LAW,
        citation="36 FR 9814 (May 28 1971); removed by 85 FR 68680",
        note=(
            "The prescriptive time/temperature table. Boundary-tested via "
            "the eCFR versioner API: present at 2022-10-30, absent at "
            "2022-10-31. MUST NEVER be described as current law, a "
            "current safe harbour, or 'still valid'. Historical benchmark "
            "only, and only for the pre-heat egg phase - the finished "
            "sweetened base matches no row at all."
        ),
        operative_from="1971-05-28",
        operative_until="2022-10-30",
    ),
    "fsis_egg_guideline": Authority(
        key="fsis_egg_guideline",
        title="FSIS Food Safety Guideline for Egg Products",
        status=AuthorityStatus.AGENCY_GUIDANCE,
        citation="Revised May 2026; FR doc 2026-08702, published 2026-05-05",
        note=(
            "Source of every D-z model in this module (Appendix III.A, "
            "III.C) and of the safe-harbour tables after they left the "
            "CFR. FSIS on the appendix tables, verbatim: 'are not minimum "
            "lethalities, but rather safe harbors for plants to follow'. "
            "And on the guideline itself, verbatim: 'does not create any "
            "new legal requirements or have the force and effect of law'. "
            "The May 2026 revision was open for comment until 2026-07-06, "
            "so even this is not a settled document."
        ),
        operative_from="2026-05-05",
    ),
    "garibaldi_1969": Authority(
        key="garibaldi_1969",
        title="Garibaldi, Straka & Ijichi 1969, Heat Resistance of Salmonella in Various Egg Products",
        status=AuthorityStatus.PEER_REVIEWED,
        citation="Appl Microbiol 17(4):491-496; page scans in data/garibaldi/",
        note=(
            "Primary source for every matrix-specific D-value here. Read "
            "from page scans, not from secondary summaries - which is how "
            "three of this project's own errors were found."
        ),
    ),
    "wang_2009": Authority(
        key="wang_2009",
        title="Wang & Wang 2009, Effects of Yolk Contamination, Shearing, and Heating on Foaming Properties of Fresh Egg White",
        status=AuthorityStatus.PEER_REVIEWED,
        citation="J Food Sci 74(2):C147; PMID 19323729",
        note=(
            "Most sensitive published yolk-carryover observation: 0.022% "
            "w/w significantly reduced foaming capacity and speed."
        ),
    ),
}
"""
SINGLE SOURCE OF TRUTH for the status of every authority this project
cites.

Added after a review observed that the repo had been maintaining two
parallel, inconsistent notions of evidence - an `Evidence` enum for
model grades and an entirely separate, undocumented notion of
"regulatory" status carried only in prose. No other module or document
may assert an authority's status independently; they must defer here.

Tests enforce three invariants:
  1. No authority in this project has CURRENT_LAW status that imposes a
     process requirement on us.
  2. Superseded authorities are never described in the present tense in
     any source file or document.
  3. Every status claim in the prose matches this registry.
"""


CFR_590_570_CURRENT_TEXT = (
    "Pasteurized egg products must be produced to be edible without "
    "additional preparation to achieve food safety and may receive "
    "additional preparation for palatability or aesthetic, epicurean, "
    "gastronomic, or culinary purposes. Pasteurized egg products are "
    "not required to bear a safe-handling instruction or other "
    "labeling that directs that the product must be cooked or "
    "otherwise treated for safety."
)
"""
The ENTIRE current text of 9 CFR 590.570, verbatim from eCFR.

Stored here so that nobody has to take this module's word for the claim
that the prescriptive table is gone. There are no temperatures, no
times, and no product categories in the current rule - it is a pure
performance standard, and compliance is demonstrated per-plant under
HACCP (9 CFR 417.4(a), 417.5(a)).

Note what this means for a kitchen: the standard is written for
FSIS-inspected official plants. We are not one. No safe harbour, past
or present, is legally available to this recipe. The most this project
can honestly say is that a step RESEMBLES a process the regulator once
accepted for a similar matrix.
"""

FINISHED_BASE_NOT_IN_ANY_ROW = """
The finished sweetened yolk base is not covered by ANY row of the
historical table, and this must never be glossed over.

After the kill step the recipe adds 14 g sugar and 0.2 g salt to 23.2 g
of egg material:

    egg material   23.20 g
    added nonegg   14.20 g
    total          37.40 g   ->  38.0% added nonegg ingredients

The historical categories cap out far below that:

    whole egg blends            < 2%   added nonegg
    fortified whole egg/blends  2-12%  added nonegg (24-38% egg solids)
    sugar yolk                  >= 2%  sugar        (no upper bound
                                       stated, but it is a YOLK row and
                                       assumes a yolk-dominant matrix)

Table I's own footnote handles this case explicitly:

    "Pasteurization of egg products not listed in this table shall be
     in accordance with paragraph (c) of this section."

i.e. unlisted products required separate, plant-specific justification
even under the old rule.

CONSEQUENCE, stated plainly: the historical benchmark can speak to the
PRE-HEAT EGG PHASE only. It says nothing about the finished sweetened
base. Since sugar and salt are added AFTER lethality, they do not
weaken the kill step - but the relevant hazard for the finished base is
RECONTAMINATION from utensils, hands and the added ingredients
themselves, which is a hygiene control and not a thermal one. See
formulation.POST_LETHALITY_CONTROLS.
"""

SALT_CATEGORY_THRESHOLD_PERCENT = 2.0
"""
Added-salt percentage at which the historical 9 CFR 590.570 Table I
reclassified yolk from "plain yolk" into "salt yolk (2-12 percent salt
added)".

The recipe's pre-heat base carries far less than this (see
formulation.preheat_salt_percent). Staying under the threshold is a
DESIGN CONSTRAINT enforced by test, not a coincidence.
"""

SUGAR_CATEGORY_THRESHOLD_PERCENT = 2.0
"""
Added-sugar percentage at which Table I reclassifies yolk as "sugar
yolk". The recipe adds all sugar AFTER the heat step, so the pre-heat
matrix contains 0%.
"""


def meets_historical_cfr_row(
    product: str,
    temp_c: float,
    hold_min: float,
) -> bool:
    """
    Would this hold have satisfied a row of the FORMER 9 CFR 590.570
    Table I (operative 1971 - 2022-10-30)?

    NOT a current-compliance check. The prescriptive table was removed
    effective 2022-10-31 and replaced by a performance standard; see
    CFR_590_570_CURRENT_TEXT. And no safe harbour of any era is legally
    available to a home kitchen, which is not an FSIS-inspected
    official plant.

    What a True result DOES mean: this time/temperature combination is
    one the regulator once considered adequate for that product
    category. That is real, checkable, historical context, arrived at
    independently of this module's D-z arithmetic - which is exactly
    why it is worth computing.

    What a True result does NOT mean: that the finished drink is
    pasteurized, compliant, or safe. In particular the finished
    sweetened base matches NO row at all
    (see FINISHED_BASE_NOT_IN_ANY_ROW).

    Both the primary and the alternative (lower-temperature,
    longer-hold) option are accepted, matching the table's own "or".
    """
    if product not in CFR_TABLE_I_F:
        raise KeyError(
            f"{product!r} is not a row of the historical 9 CFR 590.570 "
            f"Table I; known rows: {sorted(CFR_TABLE_I_F)}"
        )
    for option in CFR_TABLE_I_F[product]:
        if option is None:
            continue
        req_f, req_min = option
        if temp_c >= f_to_c(req_f) - 1e-9 and hold_min >= req_min - 1e-9:
            return True
    return False


def meets_cfr_safe_harbour(*_args, **_kwargs):  # noqa: ANN002, ANN003
    """
    REMOVED. This name asserted a live legal safe harbour that does not
    exist; calling it raises rather than returning a comfortable bool.

    Use meets_historical_cfr_row() and label the result
    Evidence.REGULATORY_HISTORICAL.
    """
    raise NotImplementedError(
        "meets_cfr_safe_harbour() was removed: 9 CFR 590.570 Table I "
        "ceased to be operative on 2022-10-31 (85 FR 68680), so there "
        "is no current safe harbour to meet - and none is available to "
        "a home kitchen in any case. Use meets_historical_cfr_row() "
        "and grade the result Evidence.REGULATORY_HISTORICAL."
    )


# --------------------------------------------------------------------------
# MATRIX-SPECIFIC MODELS: the sugar problem
# --------------------------------------------------------------------------
#
# THE ERROR THIS SECTION EXISTS TO CORRECT
# ----------------------------------------
# An earlier version of this project applied the FSIS *plain* yolk model
# to a yolk base containing 36.6% sugar, and the FSIS *plain* white model
# to a sweetened meringue. That is invalid. Sugar is not inert with
# respect to microbial thermal death - it PROTECTS the pathogen.
#
# Garibaldi, Straka & Ijichi 1969, "Heat Resistance of Salmonella in
# Various Egg Products", Applied Microbiology 17(4):491-496 - the primary
# study FSIS itself cites - measured D-values directly, at 60 C:
#
#     whole egg                     D = 0.27 min
#     whole egg + 10% sucrose       D = 0.60 min   (2.2x)
#     egg yolk                      D = 0.40 min
#     egg yolk + 10% sucrose        D = 4.0  min   (10x !!)
#     egg yolk + 10% NaCl           D = 5.1  min   (12.8x)
#
# and at 55 C:
#     egg white pH 9.2              D = 0.55 min
#     egg white pH 9.2 + 10% sucrose D = 1.2 min   (2.2x)
#
# The authors' own words: "the change in D value in yolk brought about by
# either 10% sucrose or 10% NaCl supplementation is quite dramatic. Such
# an increase in heat resistance (from D to 10 D) indicates that at
# temperatures where 10^10 cells/ml are killed in 1 min in yolk, only
# 10 cells/ml will be killed in yolk supplemented with either 10% salt or
# 10% sucrose."
#
# Reported z-values were tightly grouped, 4.2 to 5.3 C, average 4.6 C.
#
# HOW THE RECIPE WAS CHANGED IN RESPONSE
# --------------------------------------
# The process was redesigned so the pathogen kill happens in the PLAIN
# matrix, and sugar is added AFTERWARDS. This removes the need to model
# a sweetened matrix for the lethality step at all - the safest fix is
# not a better model, it is a process that does not need one.
# The sugared models below are retained to *verify* that decision and to
# quantify what the old process was actually risking.

GARIBALDI_Z_AVERAGE_C = 4.6
"""
Average z-value across all egg products in Garibaldi et al. 1969
(range 4.2-5.3 C). Used only where the paper does not give a
product-specific z.
"""

YOLK_SUGARED_10PCT = DzModel(
    name="egg yolk + 10% sucrose",
    t_ref_c=60.0,
    d_ref_min=4.0,
    z_c=4.8,
    source=(
        "Garibaldi, Straka & Ijichi 1969, Appl Microbiol 17(4):491-496, "
        "D60 = 4.0 min for egg yolk + 10% sucrose (10x plain yolk); "
        "z = 4.8 C from Fig. 4"
    ),
    # WINDOW CORRECTED AFTER READING THE ACTUAL PAGE SCAN (see note at
    # YOLK_PLAIN_GARIBALDI). Fig. 4's sucrose curve carries plotted data
    # from ~55.0 to ~61.5 C, not the 50-62 C previously assumed here.
    valid_min_c=55.0,
    valid_max_c=61.5,
)

YOLK_PLAIN_GARIBALDI = DzModel(
    name="egg yolk, plain (Garibaldi)",
    t_ref_c=60.0,
    d_ref_min=0.40,
    z_c=4.4,
    source=(
        "Garibaldi, Straka & Ijichi 1969, Appl Microbiol 17(4):491-496, "
        "D60 = 0.40 min for plain egg yolk; z = 4.4 C from Fig. 4. "
        "NOTE the paper's 'yolk' is the COMMERCIAL product: 'yolk "
        "equivalent to the commercial product (i.e., diluted with egg "
        "white to approximately 43% egg solids)' (Materials & Methods, "
        "item vii) - NOT pure undiluted yolk"
    ),
    # WINDOW CORRECTED - THIS WAS AN ERROR OF MINE THAT NO REVIEWER FOUND
    # ------------------------------------------------------------------
    # Earlier revisions of this file declared 50-62 C for both Garibaldi
    # yolk models, citing "Fig. 4 spans roughly 50-62 C". That was an
    # assumption written from memory, never checked against the paper.
    #
    # The page scan of p. 493 was then read directly. Fig. 4's axis does
    # run 50-62 C, but the AXIS IS NOT THE DATA. The plotted points are:
    #
    #     yolk (plain)        ~53.0 - 59.5 C   <- this model
    #     yolk + 10% sucrose  ~55.0 - 61.5 C
    #     yolk + 10% NaCl     ~50.0 - 62.5 C
    #
    # Confusing an axis range with a calibration range is exactly the
    # class of error this module exists to prevent, so the true data
    # extent is used instead. Consequence: the recipe's 62 C step is
    # +2.5 C ABOVE this model's real window, and the previously
    # documented claim that "all three yolk models are in-window at
    # 62 C" was false. See YOLK_MODEL_WINDOW_NOTE.
    valid_min_c=53.0,
    valid_max_c=59.5,
)

YOLK_SALTED_10PCT = DzModel(
    name="egg yolk + 10% NaCl",
    t_ref_c=60.0,
    d_ref_min=5.1,
    z_c=4.6,
    source=(
        "Garibaldi, Straka & Ijichi 1969, Appl Microbiol 17(4):491-496, "
        "abstract: 'D = 5.1 min for egg yolk plus 10% NaCl' versus "
        "'D = 0.40 min for egg yolk' - a 12.75x rise in Salmonella heat "
        "resistance from salt alone. z = 4.6 C from Fig. 4"
    ),
    valid_min_c=50.0,
    valid_max_c=62.5,
)
"""
THE MODEL THIS PROJECT SHOULD HAVE HAD FROM THE START.

A reviewer objected that the recipe's "plain yolk" step is not really
plain, because water AND SALT are in the pan during the kill step. That
objection was checked against the primary source rather than accepted or
dismissed - and the source is harsher than the reviewer argued.

Garibaldi's abstract measures, IN THE YOLK MATRIX ITSELF:

    egg yolk                D60 = 0.40 min
    egg yolk + 10% NaCl     D60 = 5.10 min      <- 12.75x
    egg yolk + 10% sucrose  D60 = 4.00 min      <- 10x

and comments (p. 494):

    "the change in D value in yolk brought about by either 10% sucrose
     or 10% NaCl supplementation is quite dramatic ... This, to our
     knowledge, is the first time that such stabilization to heat of
     bacterial vegetative cells by sodium chloride has been observed."

A PREVIOUS REVISION OF THIS PROJECT MISREPRESENTED THIS.
It quoted the paper as saying "salt has no protective effect on
Salmonella". The actual sentence is:

    "Results of experiments in our laboratory indicate that salt has no
     protective effect on salmonella heated in A BUFFER SYSTEM."

In a buffer - not in yolk. In yolk the same paper measured 12.75x. The
earlier partial quotation removed the qualifier that reversed its
meaning, and it erred in the UNSAFE direction. It is corrected here and
in docs/SOURCES.md.
"""

WHITE_SUGARED_10PCT = DzModel(
    name="egg white pH 9.2 + 10% sucrose",
    t_ref_c=55.0,
    d_ref_min=1.2,
    z_c=4.3,
    source=(
        "Garibaldi, Straka & Ijichi 1969, Appl Microbiol 17(4):491-496, "
        "D55 = 1.2 min for egg white pH 9.2 + 10% sucrose (2.2x plain); "
        "z = 4.3 C from Fig. 2"
    ),
    # Garibaldi's egg-white TDT curves span roughly 48-60 C (Fig. 2).
    valid_min_c=48.0,
    valid_max_c=60.0,
)

WHITE_PLAIN_GARIBALDI = DzModel(
    name="egg white pH 9.2, plain (Garibaldi)",
    t_ref_c=55.0,
    d_ref_min=0.55,
    z_c=4.2,
    source=(
        "Garibaldi, Straka & Ijichi 1969, Appl Microbiol 17(4):491-496, "
        "D55 = 0.55 min for egg white pH 9.2; z = 4.2 C from Fig. 2"
    ),
    valid_min_c=48.0,
    valid_max_c=60.0,
)

# Garibaldi's own published equivalence points. These are DIRECTLY
# STATED in the paper's Discussion as processes equivalent in lethality
# to the long-trusted 140 F / 3.5 min whole-egg standard. They are the
# strongest evidence available for a sweetened matrix, because they are
# read off measured TDT curves rather than extrapolated by us.
GARIBALDI_EQUIVALENCE_POINTS_F = {
    "egg white pH 9.2": 133.2,
    "egg white pH 9.2 + 10% sucrose": 135.9,
    "egg yolk": 141.1,
    "whole egg": 140.0,
}
"""
Garibaldi 1969, Discussion: "for a holding time of 3.5 min it is
necessary to maintain pH 9.2 egg white at a temperature of not less
than 133.2 F; similarly for yolk, 3.5 min at 141.1 F, for egg white
pH 9.2 plus 10% sucrose, 3.5 min at 135.9 F".

135.9 F = 57.7 C. This is the anchor for the sweetened-white step:
a MEASURED equivalence, not an extrapolation.
"""

GARIBALDI_REFERENCE_HOLD_MIN = 3.5
"""Holding time to which the equivalence temperatures above apply."""

GARIBALDI_YOLK_DATA_EXTENT_C = {
    "egg yolk, plain (Garibaldi)": (53.0, 59.5),
    "egg yolk + 10% sucrose": (55.0, 61.5),
    "egg yolk + 10% NaCl": (50.0, 62.5),
}
"""
Temperature extent of the ACTUAL PLOTTED DATA POINTS in Garibaldi 1969
Fig. 4, read off the page scan (PMC377728, p. 493).

Recorded separately from the axis range because the two were once
confused in this project, with the axis (50-62 C) mistaken for the
calibration range. Kept here so a test can assert the models' windows
match the source rather than a remembered approximation.
"""

YOLK_MODEL_WINDOW_NOTE = """
WHY THE "THREE INDEPENDENT MODELS, ALL IN-WINDOW" CLAIM WAS RETIRED

The recipe's 62 C yolk hold was once justified by saying three
independent models agreed AND all three were inside their calibration
windows. After Fig. 4's real data extents were read from the page scan,
the second half of that claim collapsed:

    FSIS Appendix III.C plain yolk : 59.4 - 65.6 C   62 C in-window
    Garibaldi plain yolk           : 53.0 - 59.5 C   62 C is +2.5 C out
    Garibaldi yolk + 10% sucrose   : 55.0 - 61.5 C   62 C is +0.5 C out

The intersection of all three windows is 59.4-59.5 C - a 0.1 C slot.
There is NO practical temperature at which all three are simultaneously
in-window, so no amount of retuning the target could have rescued the
claim. It was not a tuning problem; it was a false statement.

What replaced it is NARROWER, not stronger. An earlier version of this
note claimed the replacement was "stronger, not weaker" because the
yolk step was "justified primarily by 9 CFR 590.570 Table I, which is a
legal safe harbour". That second overclaim had to be retired too:
Table I ceased to be operative on 2022-10-31, and no safe harbour of
any era is available to a home kitchen.

The yolk step's actual design basis is the FSIS Appendix III.C plain
egg yolk model, which IS in-window at 62 C (59.4-65.6 C) and IS
matrix-matched to plain, white-diluted yolk. One honest in-window
model, not three. The Garibaldi curves are retained as CROSS-CHECKS
only, each labelled individually with whether it interpolates or
extrapolates at the process temperature - two of the three
extrapolate, and that is disclosed rather than averaged away.

Two overclaims in sequence, both in the same direction, is the pattern
worth remembering: when a claim collapses, the replacement deserves the
same scrutiny as the original rather than inheriting its confidence.
""".strip()


# --------------------------------------------------------------------------
# The concentration gap, and a deliberately pessimistic model
# --------------------------------------------------------------------------
#
# Garibaldi tested 10% sucrose. Our meringue foam is ~44% sugar by mass
# of the foam layer. Protection therefore probably EXCEEDS the measured
# 2.2x, which means Garibaldi's sugared-white model is NOT conservative
# at our concentration. Ignoring that gap would repeat the original sin
# of this project in a subtler form.
#
# There is no published D-value for Salmonella in a 44% sucrose egg
# white. Rather than interpolate and pretend, we build an intentionally
# PESSIMISTIC model and require the process to pass against it:
#
#   assume every additional 10% sucrose multiplies D by the same 2.18x
#   that Garibaldi measured for the first 10%, compounding.
#
# This is almost certainly harsher than reality - real protection
# saturates rather than compounding geometrically (Mattick et al. 2001
# found sucrose protection is temperature-dependent and even DETRIMENTAL
# below ~60 C). Using it means a passing process is safe under an
# assumption we expect to be wrong in the safe direction.
#
# WHAT THIS TEST CHANGED IN THE RECIPE
# ------------------------------------
# Under this pessimistic model a 60 C / 5 min white hold yields only
# ~5.05 log10 - a +0.05 margin, which is not a margin at all. The
# earlier "60 C fallback" was therefore REMOVED from the recipe.
# A 71 C hold needs just 0.02 min for 5 log10 even pessimistically, so
# the Swiss-meringue temperature survives the harshest assumption.

SUCROSE_PROTECTION_PER_10PCT = 2.18
"""
Measured D-value multiplier for the first 10% sucrose in egg white:
Garibaldi D55 rises 0.55 -> 1.20 min. Used as the compounding base for
the pessimistic model below.
"""


def pessimistic_sugared_white(sugar_percent: float) -> DzModel:
    """
    Build a deliberately harsh model for egg white at high sugar.

    Extrapolates Garibaldi's measured 2.18x-per-10%-sucrose protection
    geometrically. Intended for stress-testing a process, NOT for
    claiming a lethality figure.

    Raises for concentrations above 60%, where sucrose approaches
    saturation and the geometric assumption becomes meaningless.
    """
    if not (0.0 <= sugar_percent <= 60.0):
        raise ValueError("sugar_percent must be between 0 and 60")

    factor = SUCROSE_PROTECTION_PER_10PCT ** (sugar_percent / 10.0)
    return DzModel(
        name=f"egg white + {sugar_percent:.1f}% sucrose (pessimistic)",
        t_ref_c=55.0,
        d_ref_min=0.55 * factor,
        z_c=4.3,
        source=(
            "PESSIMISTIC EXTRAPOLATION from Garibaldi 1969 "
            f"(D55 0.55 -> 1.20 min for 10% sucrose), compounding "
            f"{SUCROSE_PROTECTION_PER_10PCT}x per 10% sucrose to "
            f"{sugar_percent:.1f}%. Not a measured value; used only to "
            "stress-test that a process holds under a harsher-than-"
            "expected assumption"
        ),
        valid_min_c=48.0,
        valid_max_c=75.0,
        # The sugar concentration is extrapolated, so results must never
        # be graded as in-window however comfortable the temperature is.
        is_composition_extrapolation=True,
    )


# --------------------------------------------------------------------------
# Non-isothermal (real world) lethality integration
# --------------------------------------------------------------------------

@dataclass
class ThermalHistory:
    """
    A measured or modelled temperature-versus-time curve.

    times_min and temps_c must be the same length and times must be
    non-decreasing. This represents what actually happens in a cup or a
    bain-marie, where temperature is never constant.
    """

    times_min: Sequence[float]
    temps_c: Sequence[float]
    label: str = "history"
    provenance: str = "ASSUMED"
    """
    Where this curve came from. One of:

        "ASSUMED"   - a design intent. Nobody measured it. This is the
                      default precisely because it is the honest
                      default, and because a silent default should be
                      the weakest claim rather than the strongest.
        "MEASURED"  - recorded from a real batch with a calibrated
                      instrument. Requires `instrument` to be set.
        "SIMULATED" - output of a physical model (e.g. Newton cooling)
                      rather than a hand-written intent.

    WHY THIS FIELD EXISTS
    ---------------------
    A review observed that SafetyVerdict.is_defensible returned True
    for a thermal history labelled "PURELY ASSUMED, no thermocouple".
    That was checked and reproduced - it was true. The class docstring
    said "measured or modelled" and then never recorded which, so
    every downstream property silently treated an aspiration as data.

    That is the same error class as the retired `is_lab_grade`: a name
    promising more than the inputs support.
    """
    instrument: str | None = None
    """
    Instrument identification and calibration state, required when
    provenance == "MEASURED". Free text, e.g.
    "type-K thermocouple, ice-point checked 2026-09-01, +/-0.5 C".
    """

    _VALID_PROVENANCE = ("ASSUMED", "MEASURED", "SIMULATED")

    def __post_init__(self) -> None:
        if len(self.times_min) != len(self.temps_c):
            raise ValueError("times and temps must have equal length")
        if len(self.times_min) < 2:
            raise ValueError("need at least two samples")
        for earlier, later in zip(self.times_min, self.times_min[1:]):
            if later < earlier:
                raise ValueError("times must be non-decreasing")
        if self.provenance not in self._VALID_PROVENANCE:
            raise ValueError(
                f"provenance must be one of {self._VALID_PROVENANCE}, "
                f"got {self.provenance!r}"
            )
        if self.provenance == "MEASURED" and not self.instrument:
            raise ValueError(
                "provenance='MEASURED' requires `instrument` naming the "
                "device and its calibration state. Claiming a curve was "
                "measured without saying what measured it is the kind "
                "of unfalsifiable claim this module exists to prevent."
            )

    @property
    def is_measured(self) -> bool:
        """True only for a real, instrumented temperature record."""
        return self.provenance == "MEASURED"

    def peak_c(self) -> float:
        return max(self.temps_c)

    def duration_min(self) -> float:
        return self.times_min[-1] - self.times_min[0]


SUBDIVISION_STEPS = 512
"""
Number of sub-intervals used per segment when integrating lethality.

WHY THIS EXISTS - A REAL NUMERICAL BUG, CAUGHT IN REVIEW
--------------------------------------------------------
The first version of this integrator applied the trapezoidal rule
directly to the caller's segment endpoints. That is wrong whenever a
segment spans a wide temperature range, because the lethal rate 1/D(T)
is EXPONENTIAL in temperature. A straight line drawn between the rate
at 20 C and the rate at 64 C sits far above the true curve, so the
trapezoid credits lethality that never happened.

Measured on this project's own yolk step (20 -> 64 C ramp over 1.5 min,
then a 5 min hold at 64 C), against the FSIS plain-yolk model:

    endpoints only (old behaviour) : 8.52 log10
    converged (fine subdivision)  : 7.57 log10
    OVERSTATEMENT                 : 0.95 log10

An external reviewer independently derived ~7.57 by hand and flagged
that the documented 8.52 could not be right. They were correct.

The error direction is what makes this serious: it OVERSTATES safety.
A 0.95 log10 phantom margin is the kind of thing that turns a marginal
process into an apparently comfortable one.

512 steps per segment is far past convergence for the ramps used here
(the value is stable to 4 decimal places beyond ~256), while staying
cheap enough for a test suite.
"""


def _lethal_rate(model: DzModel, temp_c: float, floor_c: float) -> float:
    """Instantaneous lethal rate 1/D(T), or zero below the floor."""
    if temp_c < floor_c:
        return 0.0
    return 1.0 / model.d_at(temp_c)


def accumulated_log_reduction(
    history: ThermalHistory,
    model: DzModel,
    floor_c: float = 50.0,
    steps_per_segment: int = SUBDIVISION_STEPS,
) -> float:
    """
    Integrate lethality over a non-isothermal thermal history.

    Each caller-supplied segment is subdivided and integrated with the
    trapezoidal rule on the instantaneous lethal rate 1/D(T), assuming
    the temperature varies LINEARLY within the segment.

    Subdivision is essential, not an optimisation: 1/D(T) is exponential
    in T, so integrating a wide segment from its endpoints alone
    materially overstates lethality. See SUBDIVISION_STEPS.

    Parameters
    ----------
    floor_c : float
        Temperatures below this contribute no credited lethality.
        50 C is used because most food pathogens stop multiplying by
        ~50 C and crediting lethality below that is not defensible
        (Baldwin; FDA Food Code danger-zone discussion). Being
        conservative here can only under-claim safety, never over-claim.
    steps_per_segment : int
        Sub-intervals per segment. Exposed so tests can demonstrate
        convergence; production callers should use the default.
    """
    if steps_per_segment < 1:
        raise ValueError("steps_per_segment must be at least 1")

    total = 0.0
    pairs = list(zip(history.times_min, history.temps_c))

    for (t0, temp0), (t1, temp1) in zip(pairs, pairs[1:]):
        dt = t1 - t0
        if dt <= 0.0:
            continue

        # An isothermal segment needs no subdivision: the rate is
        # constant, so the trapezoid is already exact.
        if temp0 == temp1:
            total += _lethal_rate(model, temp0, floor_c) * dt
            continue

        n = steps_per_segment
        h = dt / n
        prev_rate = _lethal_rate(model, temp0, floor_c)
        for i in range(1, n + 1):
            temp = temp0 + (temp1 - temp0) * (i / n)
            rate = _lethal_rate(model, temp, floor_c)
            total += 0.5 * (prev_rate + rate) * h
            prev_rate = rate

    # Cap the reported figure. See MAX_CREDITED_LOG for the reasoning:
    # extrapolating a D-z model far past its calibration window yields
    # arithmetically large but physically meaningless log values.
    return min(total, MAX_CREDITED_LOG)


# --------------------------------------------------------------------------
# Newtonian cooling: what an espresso shot actually does to a yolk
# --------------------------------------------------------------------------

def newtonian_mix_then_cool(
    t_start_c: float,
    t_ambient_c: float,
    cooling_constant_per_min: float,
    total_min: float,
    steps: int = 2000,
    label: str = "newtonian",
) -> ThermalHistory:
    """
    Model a hot mass placed in a cup and losing heat to the room.

    T(t) = T_amb + (T_start - T_amb) * exp(-k t)

    This is Newton's law of cooling. It is the correct first-order model
    for a small liquid volume in a ceramic cup, and it is deliberately
    used here to show that an espresso shot CANNOT pasteurize a yolk:
    the mixture cools through the lethal window far too quickly.
    """
    import math

    if steps < 2:
        raise ValueError("need at least 2 steps")

    times = [total_min * i / (steps - 1) for i in range(steps)]
    temps = [
        t_ambient_c + (t_start_c - t_ambient_c) * math.exp(-cooling_constant_per_min * t)
        for t in times
    ]
    return ThermalHistory(times_min=times, temps_c=temps, label=label)


def equilibrium_mix_temperature(
    masses_g: Iterable[float],
    temps_c: Iterable[float],
    specific_heats: Iterable[float] | None = None,
) -> float:
    """
    Mixing temperature from an energy balance:
        T_mix = sum(m_i c_i T_i) / sum(m_i c_i)

    Used to compute what temperature a 30 g espresso shot at ~90 C
    reaches when stirred into a ~18 g room-temperature yolk-sugar base.
    Ignoring vessel heat capacity makes the result an UPPER bound on the
    mixture temperature, which is the conservative direction for a
    safety argument (a real cup would be cooler still).
    """
    masses = list(masses_g)
    temps = list(temps_c)
    if len(masses) != len(temps):
        raise ValueError("masses and temps must align")
    if not masses:
        raise ValueError("need at least one component")

    if specific_heats is None:
        heats = [1.0] * len(masses)
    else:
        heats = list(specific_heats)
        if len(heats) != len(masses):
            raise ValueError("specific heats must align")

    numerator = sum(m * c * t for m, c, t in zip(masses, heats, temps))
    denominator = sum(m * c for m, c in zip(masses, heats))
    if denominator <= 0:
        raise ValueError("total heat capacity must be positive")
    return numerator / denominator


# --------------------------------------------------------------------------
# Verdicts
# --------------------------------------------------------------------------

TARGET_LOG_DEFAULT = 5.0
"""
FSIS: "In general, FSIS considers a 5 log10 reduction of Salmonella to be
safe in products that are edible without additional preparation."
"""

ESPRESSO_IN_CUP_C = 67.0
"""
Temperature of the drink in the cup, per the Istituto Nazionale Espresso
Italiano certified-espresso specification: 67 +/- 3 C.

This is NOT the brew temperature (88 +/- 2 C at the group head). See the
module docstring for why conflating the two is dangerous here.
"""

ESPRESSO_IN_CUP_TOLERANCE_C = 3.0
"""INEI tolerance on the in-cup temperature."""

ESPRESSO_SHOT_MASS_G = 30.0
"""
Mass of a double espresso used throughout the recipe calculations.
INEI specifies 25 +/- 2.5 mL for a single; cafe doubles are commonly
~30 g of beverage. Using a larger shot mass carries MORE heat into the
mixture, so 30 g is the conservative choice when the goal is to show
that even a generous shot cannot pasteurize a yolk.
"""

YOLK_SPECIFIC_HEAT = 0.85
"""
Approximate specific heat of egg yolk relative to water (water = 1.0).
Yolk is ~50% water with high lipid and protein solids, so its specific
heat is lower than water's. Using a relative scale is valid here because
equilibrium_mix_temperature only depends on ratios of m*c.
"""


class Evidence(str, Enum):
    """
    Evidence grade for a claim. Added after external review found that
    this project's documentation was asserting model output as if it were
    laboratory proof.

    The distinction is not pedantic. A green unit test proves the
    ARITHMETIC is right. It says nothing about whether a real cup of this
    drink achieves the modelled lethality. Conflating the two is how
    plausible-looking food-safety numbers become dangerous.
    """

    MEASURED = "MEASURED"
    """
    Directly measured in a peer-reviewed study, in a matrix closely
    matching ours. Strongest grade available without our own lab work.
    """

    MODELLED_IN_WINDOW = "MODELLED (in-window)"
    """
    Computed from a published model, at conditions INSIDE that model's
    calibration range. Defensible interpolation.
    """

    MODELLED_EXTRAPOLATED = "MODELLED (extrapolated)"
    """
    Computed outside the model's calibration range. Indicative only.
    Must never be presented as a proven figure.
    """

    MATRIX_MISMATCH = "MATRIX MISMATCH"
    """
    The model's food matrix differs from ours in a way known to affect
    the result (e.g. plain-yolk model applied to sugared yolk). This
    grade is a red flag, not a caveat.
    """

    REGULATORY_HISTORICAL = "REGULATORY (historical, superseded)"
    """
    The process would have satisfied a row of a regulation that WAS in
    force but no longer is - here, 9 CFR 590.570 Table I, operative
    1971 to 2022-10-30.

    Added after a review pointed out a real taxonomy hole: the docs
    were printing an evidence grade called "REGULATORY" that did not
    exist in this enum, because the regulatory check lived in a
    completely separate function. Two parallel evidence systems, one
    of which was undocumented, is exactly how an overclaim survives.

    Deliberately NOT ranked above MEASURED. A superseded rule is
    strong context, not proof, and it is not law today. It is also not
    available to a home kitchen in any legal sense, since safe
    harbours apply to FSIS-inspected official plants.
    """

    UNSUPPORTED = "UNSUPPORTED"
    """No adequate source. Must be removed or explicitly labelled a guess."""

    @property
    def is_current_law(self) -> bool:
        """
        True only for a CURRENTLY operative regulatory requirement.

        Always False for every member of this enum, and that is the
        point: nothing this project computes is current-law compliance.
        The property exists so the claim can be asserted by test rather
        than trusted to prose - if a future edit adds a grade that
        returns True here, a test will demand justification.
        """
        return False

    @property
    def is_model_supported(self) -> bool:
        """
        True when a published model backs the figure at conditions it was
        actually calibrated for.

        NAMING NOTE (corrected after review)
        ------------------------------------
        This property used to be called `is_lab_grade`, which was wrong.
        A model evaluated inside its calibration window is well founded,
        but it is still a MODEL - it is not a measurement of our finished
        product. Calling that "lab grade" asserted more than the evidence
        deserved, in a project whose whole point is not doing that.

        Use `is_lab_validated` for the genuinely stronger claim.
        """
        return self in (Evidence.MEASURED, Evidence.MODELLED_IN_WINDOW)

    @property
    def is_lab_validated(self) -> bool:
        """
        True ONLY for figures measured in a laboratory on a matching
        matrix. Nothing this project computes from a model qualifies.

        Kept deliberately strict so the distinction between "our maths is
        sound" and "someone measured this" can never blur again.
        """
        return self is Evidence.MEASURED


@dataclass
class SafetyVerdict:
    """Structured, printable outcome of a lethality assessment."""

    component: str
    achieved_log: float
    target_log: float
    peak_c: float
    duration_min: float
    model_source: str
    evidence: Evidence = Evidence.MODELLED_IN_WINDOW
    notes: list[str] = field(default_factory=list)
    history_provenance: str = "ASSUMED"
    """
    Provenance of the thermal history this verdict was computed from,
    copied through from ThermalHistory.provenance so that a verdict
    cannot be inspected in isolation and mistaken for measured fact.
    """

    @property
    def is_safe(self) -> bool:
        """
        Whether the modelled lethality meets the target.

        NOTE: this is a statement about the MODEL, not a laboratory
        certification of the finished drink. Check `evidence` to see how
        much weight the number deserves.
        """
        return self.achieved_log >= self.target_log

    @property
    def is_model_defensible(self) -> bool:
        """
        LEVEL 1 - MATHEMATICAL. Meets the target AND rests on a model
        evaluated at conditions it was calibrated for.

        Says nothing about whether the real process ever reached these
        temperatures. Renamed from `is_defensible`, which was too broad
        a word for a claim this narrow.
        """
        return self.is_safe and self.evidence.is_model_supported

    @property
    def is_process_measured(self) -> bool:
        """
        LEVEL 2 - PROCESS. The thermal history is a real instrumented
        record, not a design intent.

        WHY THIS EXISTS
        ---------------
        A review found that `is_defensible` returned True for a history
        explicitly labelled "PURELY ASSUMED, no thermocouple". That was
        reproduced and confirmed. Model correctness and process
        measurement are different questions, and collapsing them let an
        aspiration inherit a model's credibility.

        False everywhere in this project today: we have no thermocouple
        data. That is a gap in the evidence, and it is now visible in
        the type system rather than only in prose.
        """
        return self.is_safe and self.history_provenance == "MEASURED"

    @property
    def is_lab_validated(self) -> bool:
        """
        LEVEL 3 - MICROBIOLOGICAL. Requires all of: target met,
        laboratory-grade evidence for the matrix, AND a measured
        thermal history.

        Always False for computed results. A microbiological challenge
        study on the finished formulation is the only thing that could
        make this True, and none has been done.
        """
        return (
            self.is_safe
            and self.evidence.is_lab_validated
            and self.history_provenance == "MEASURED"
        )

    @property
    def is_defensible(self) -> bool:
        """
        DEPRECATED alias of `is_model_defensible`, retained so that no
        caller silently gets a different answer than before. Prefer the
        explicit name: this one invited exactly the over-reading that
        review caught.
        """
        return self.is_model_defensible

    @property
    def margin_log(self) -> float:
        return self.achieved_log - self.target_log

    @property
    def was_capped(self) -> bool:
        """True if the raw integral hit the MAX_CREDITED_LOG ceiling."""
        return self.achieved_log >= MAX_CREDITED_LOG

    def render(self) -> str:
        status = "PASS" if self.is_safe else "FAIL"
        if self.was_capped:
            achieved = f">= {MAX_CREDITED_LOG:.0f} log10 (capped)"
            margin = "very large"
        else:
            achieved = f"{self.achieved_log:.2f} log10"
            margin = f"{self.margin_log:+.2f} log10"

        lines = [
            f"[{status}] {self.component}",
            f"  evidence grade   : {self.evidence.value}",
            f"  peak temperature : {self.peak_c:.1f} C",
            f"  process duration : {self.duration_min:.1f} min",
            f"  achieved         : {achieved}",
            f"  required         : {self.target_log:.2f} log10",
            f"  margin           : {margin}",
            f"  model source     : {self.model_source}",
        ]
        lines.extend(f"  note: {n}" for n in self.notes)
        return "\n".join(lines)


def assess(
    component: str,
    history: ThermalHistory,
    model: DzModel,
    target_log: float = TARGET_LOG_DEFAULT,
    notes: Sequence[str] | None = None,
    matrix_matches_model: bool = True,
) -> SafetyVerdict:
    """
    Run a full lethality assessment on a thermal history.

    Parameters
    ----------
    matrix_matches_model : bool
        Set False when the food being assessed differs from the model's
        matrix in a way known to change thermal death - above all, added
        sugar or salt. Garibaldi et al. 1969 measured a 10-fold rise in
        yolk D-value from only 10% sucrose, so this flag exists to make
        that mismatch loud rather than invisible.
    """
    achieved = accumulated_log_reduction(history, model)
    collected = list(notes or [])
    peak = history.peak_c()

    # Grade the evidence. Order matters: a matrix mismatch is the most
    # serious problem, because no amount of correct arithmetic fixes it.
    if not matrix_matches_model:
        grade = Evidence.MATRIX_MISMATCH
        collected.append(
            "the assessed food does not match this model's matrix; added "
            "sugar/salt raises Salmonella heat resistance (Garibaldi et "
            "al. 1969 measured 10x for yolk + 10% sucrose), so this "
            "figure OVERSTATES lethality and must not be relied on"
        )
    elif model.is_extrapolation(peak):
        grade = Evidence.MODELLED_EXTRAPOLATED
        direction = "above" if peak > model.valid_max_c else "below"
        collected.append(
            f"peak {peak:.1f} C is {direction} this model's calibrated "
            f"window ({model.valid_min_c:.1f}-{model.valid_max_c:.1f} C); "
            "treat the figure as indicative only, not as a proven value"
        )
    else:
        grade = Evidence.MODELLED_IN_WINDOW

    if history.provenance != "MEASURED":
        collected.append(
            f"thermal history provenance is {history.provenance}: this is "
            "a design intent, not an instrumented record. The lethality "
            "figure is what the process SHOULD achieve if the stated "
            "time/temperature is actually held"
        )

    return SafetyVerdict(
        component=component,
        achieved_log=achieved,
        target_log=target_log,
        peak_c=peak,
        duration_min=history.duration_min(),
        model_source=model.source,
        evidence=grade,
        notes=collected,
        history_provenance=history.provenance,
    )
