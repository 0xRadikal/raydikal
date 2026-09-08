# Limitations and evidence grading

This document exists because an external review found that this
project's documentation was **asserting model output as if it were
laboratory proof**. That criticism was correct. This file is the
honest counterweight to the rest of the docs.

Read this before trusting any number in `RECIPE.md`.

---

## The one-sentence version

**We have validated a mathematical model. We have not validated the
drink.** Those are different things, and conflating them is how
plausible-looking food-safety numbers get people hurt.

---

## Evidence grades used throughout

| Grade | Meaning |
|---|---|
| `MEASURED` | Directly measured in a peer-reviewed study on a closely matching matrix |
| `MODELLED (in-window)` | Computed from a published model, inside its calibration range |
| `MODELLED (extrapolated)` | Computed outside the calibration range — indicative only |
| `MATRIX MISMATCH` | Model's food matrix differs in a way known to change the result — a red flag, not a caveat |
| `UNSUPPORTED` | No adequate source |

Only the first two would survive a food-safety audit. The code enforces
this: `SafetyVerdict.is_defensible` is `False` for the rest, and every
printed result states its grade.

---

## Claim-by-claim audit

### Food safety

| Claim | Grade | Notes |
|---|---|---|
| Sugar raises *Salmonella* heat resistance ~10× in yolk | **MEASURED** | Garibaldi 1969: D₆₀ 0.40 → 4.0 min |
| Sugar raises it ~2.2× in egg white | **MEASURED** | Garibaldi 1969: D₅₅ 0.55 → 1.20 min |
| Plain white coagulates at 60 °C; sugared white does not | **MEASURED** | Garibaldi 1969, Fig. 5 (photographic) |
| Espresso in cup is 67 ± 3 °C | **MEASURED** | INEI certified-espresso specification |
| Zabaione as served is a raw-egg drink | **MODELLED (in-window)** | Energy balance + FSIS III.C |
| Yolk latte reaches ~61.7 °C but lacks hold time | **MODELLED (in-window)** | Peak temp is not the criterion |
| Yolk step (62 °C/10 min plain) would have met the FORMER 9 CFR 590.570 Table I plain-yolk row | **REGULATORY (historical, superseded)** | ⚠️ Table removed 2022-10-31. Not current law, and no safe harbour applies to a kitchen at all |
| Finished sweetened base matches any regulatory category | **UNSUPPORTED** | ⚠️ 38.0% added nonegg vs caps of <2% / 2–12%. No row covers it |
| Real product follows the modelled thermal curve | **UNSUPPORTED** | ⚠️ No thermocouple data. `is_process_measured` is False everywhere |
| Any pathogen other than *Salmonella* is addressed | **UNSUPPORTED** | ⚠️ *Listeria* can be MORE heat resistant in egg white (PMID 31195451) |
| Yolk step ≥ 5 log₁₀ | **MODELLED (in-window)** | Weakest *in-window* model (yolk + 10% NaCl) gives 5.37 log₁₀. ⚠️ Only +0.37 margin |
| Salt raises *Salmonella* heat resistance 12.75× in yolk | **MEASURED** | Garibaldi 1969: D₆₀ 0.40 → 5.1 min. ⚠️ We once misquoted this — see #9 |
| Garibaldi tested yolk diluted with white to ~43% egg solids | **MEASURED** | Paper's materials list, item (vii). Our pan: 43.06% |
| White step (71 °C) ≥ 5 log₁₀ at 47.5% sugar | **MODELLED (extrapolated)** | ⚠️ Weakest safety claim. **No** safe harbour exists for this matrix |
| Old 134 °F/3.5 min white process ≈ 1.3 log₁₀ | **MODELLED (in-window)** | Independently reproduces FSIS's own warning |

### Formulation and physics

| Claim | Grade | Notes |
|---|---|---|
| 0.022% yolk degrades white foam | **MEASURED** | Wang & Wang 2009 — the *more sensitive* observation, ~8 mg in 35 g |
| 0.5% yolk degrades white foam | **MEASURED** | Li et al. 2021. ⚠️ Was wrongly encoded as "the threshold" — 23× too lax |
| A safe level of yolk carryover exists | **UNSUPPORTED** | ⚠️ No study establishes a no-effect level. Rule is zero carryover |
| One drop of yolk: 135 mL → 40 mL foam | **MEASURED** | St. John & Flor 1931, via Lomakina & Míková 2006 |
| Foam overrun peaks near pH 4.8 | **MEASURED** | Hammershøj & Larsen 1999 |
| Sucrose raises egg-protein denaturation up to ~13 °C at 54% | **MEASURED** | Donovan 1977 — but see interpolation caveat below |
| Layers stratify (1.15 / 1.01 / 0.35 g/mL) | **ESTIMATE** | ⚠️ Rule-of-thumb density formula, not measurement |
| Foam final pH ≈ 4.8 | **UNSUPPORTED** | ⚠️ Not measured. See below |

---

## The weakest points, stated plainly

### 1. ⚠️ The white's safety claim is an extrapolation

This is the most important limitation in the project.

The white **cannot** be pasteurized plain — it would coagulate
(Garibaldi Fig. 5). So it must be heated sweetened, and sugar protects
the pathogen. Our foam is **47.5% sugar**, while Garibaldi measured
only **10%**. There is no published *Salmonella* D-value for egg white
at ~48% sucrose, **and no regulatory benchmark — current or historical
— covers it either.** The yolk step at least resembles a row of a
former regulation (see finding #11); the white step resembles nothing.

To be explicit, since a large margin can read as proof: the 71 °C / 3 min
white step is **not validated, not laboratory-confirmed, and not a
measurement of our finished product.**

**What we did instead of guessing:** built a deliberately pessimistic
model that compounds Garibaldi's measured 2.18×-per-10% protection
geometrically up to 47.5%, and required the process to pass against it.
At 71 °C it needs only ~0.02 min for 5 log₁₀, so it passes with an
enormous margin.

**What this still is not:** a measurement. The compounding assumption is
almost certainly harsher than reality — Mattick et al. 2001 found
sucrose protection is temperature-dependent and even *detrimental*
below ~60 °C — but "probably conservative" is not "verified."

**This directly changed the recipe.** Under this model a 60 °C hold
needs **7.68 min** for 5 log₁₀, so the old "60 °C / 10 min" fallback
cleared the bar by only about **1.3×** — and a 5-minute hold **fails
outright** at 3.30 log₁₀. Compare roughly **141×** for 71 °C / 3 min.
Since 60 °C is also where Garibaldi photographed plain white coagulating
within 9 minutes, it is an unforgiving target to hit by hand for such a
thin margin. The fallback was **removed**, not footnoted.

> These numbers were previously quoted as 5.7 min / 1.8× / 150×. Both
> the foam sugar rising to 47.5% and the integrator bug fix (finding #5)
> pushed them in the *less* favourable direction.

### 2. ⚠️ Foam pH is not measured

The docs previously implied espresso's pH (~4.9–5.1) would put the foam
near the pH 4.8 overrun optimum. **That reasoning was wrong.** Egg white
is a strongly buffered protein system, and the layers only touch at an
interface. You cannot compute a mixture's pH from its components' pH on
paper.

The lemon juice is now described as *the* acidifier, added directly to
the white. The target pH remains an **estimate until measured with a
meter**.

### 3. ⚠️ The 54% → 36.6% sugar interpolation

Donovan 1977 measured ~+13 °C denaturation shift at **54%** sucrose.
Earlier docs leaned on that to justify heating a **36.6%** sugar yolk at
64 °C. That interpolation was never rigorously established.

This is now moot for safety, because the yolk is heated **plain** and
sweetened afterwards. But it means the plain yolk is genuinely more
delicate — continuous whisking and accurate temperature control matter
more than they did in the original write-up. Lowering the target to
62 °C recovers 3 °C of headroom below the setting point, which offsets
most of that cost.

### 4. ⚠️ "Thermodynamically stable" was overstated

The layering figures come from `ρ ≈ 1.0 + 0.004 × Brix`, a rule of thumb
for *pure sucrose solutions*. The real base contains yolk solids and
lipids; the real foam's density depends on the overrun your whisk
actually achieves.

The honest claim: the estimated density gap is **large** (roughly
1.15 vs 1.01 vs 0.35 g/mL), so stratification is *expected to work*.
Confirming it requires pouring the drink.

---

---

## Corrections from the second review round

A reviewer challenged two published figures ("8.52" and "9.79 log₁₀"),
saying they couldn't be reproduced from the code. Investigating found
something worse than a typo.

### 5. 🔴 A numerical bug was overstating lethality — now fixed

The figures **were** exactly what the code emitted. The code was wrong.

The integrator applied the trapezoidal rule directly to the caller's
segment endpoints. But the lethal rate `1/D(T)` is **exponential** in
temperature, so a straight line drawn from the rate at 20 °C to the rate
at the hold temperature sits far above the true curve — crediting
lethality that never happened.

Measured on this project's own yolk step:

| Method | Result |
|---|---|
| Endpoints only (old) | 8.52 log₁₀ |
| Converged (fine subdivision) | **7.57 log₁₀** |
| **Phantom margin** | **0.95 log₁₀** |

The reviewer independently derived ~7.57 by hand. They were right.

**The direction is what made this serious: it overstated safety.** The
integrator now subdivides each segment (512 steps) and a test asserts
the default has actually converged. A mutation test confirmed that
merely fixing the constant wasn't enough — reverting it still passed
every other test, so an explicit convergence guard was added.

**Lesson recorded:** "docs machine-verified against code output" is
necessary but *not sufficient*. Docs and code can be wrong together.
`tests/test_documented_claims.py` now also checks the physics against
hand-derivable closed forms that bypass the shared integrator.

### 6. ⚠️ "Three independent models" was overstated at 64 °C

The docs described the yolk step as confirmed by three independent
models. At the old 64 °C target that wasn't true: Garibaldi's yolk TDT
curves (Fig. 4) span roughly **50–62 °C**, so two of the three were
extrapolating.

**Fix:** the target was lowered to **62 °C**. The reasoning given at the
time was that this sat inside the overlap of both evidence windows — see
finding **#8 below**, which shows that overlap was itself computed from a
misread figure. The decision survives on other grounds (it matches the
former CFR plain-yolk row — see finding #11 for why that is a historical
benchmark and not law — and leaves 3 °C below the setting point), but
the original justification for it was wrong.

The honest trade-off is that the *headline number got smaller* (7.93
instead of 8.52) and the hold got longer (10 min instead of 5). A
weaker, well-founded claim beats a stronger, inflated one.

### 7. ⚠️ `is_lab_grade` was semantically wrong — renamed

The code had a property treating `MODELLED (in-window)` as equivalent to
laboratory evidence. A model evaluated inside its calibration window is
well founded, but it is **not a measurement of our finished product**.

Renamed to `is_model_supported`, with a separate, strictly-stricter
`is_lab_validated` that only `MEASURED` satisfies. A test now asserts
that **no computed recipe step** claims lab validation.

### 8. ⚠️ We read the model validity windows off a figure's **axis**

**This one was not caught by any reviewer. We found it ourselves, and it
had been propagating through the docs, the code and a passing test.**

Garibaldi's yolk TDT curves were recorded in this project as spanning
"roughly 50–62 °C". That is the range of **Fig. 4's axis**, not the
extent of the plotted data. Reading the actual curves from the page
scans now committed in `data/garibaldi/` gives:

| Model | Recorded (wrong) | True data extent |
|---|---|---|
| Egg yolk, plain | 50.0–62.0 °C | **53.0–59.5 °C** |
| Egg yolk + 10% sucrose | 50.0–62.0 °C | **55.0–61.5 °C** |
| Egg yolk + 10% NaCl | — | **50.0–62.5 °C** |

**Consequences.** The claim that all three yolk models were "in-window at
62 °C" — printed in the report, in `RECIPE.md`, and asserted by a test
named `test_all_three_yolk_models_are_in_window_at_the_recipe_temperature`
— was **false**. Worse, it is *unachievable*: the three windows intersect
only over 59.4–59.5 °C, so no target temperature could ever have
satisfied it. The test passed only because it was checking the same
wrong constants the claim was derived from.

**Fix.** Windows corrected to the true extents; the false test deleted
and replaced with six tests that check each model's window individually,
including one asserting that **no temperature exists** at which all three
are in-window. Every model figure is now printed with its own window and
an explicit `in-window` / `EXTRAPOLATED` flag. The justification for the
yolk step was moved to the CFR benchmark, which has no calibration
window and so cannot fail this way — though **that move introduced its
own overclaim**, corrected in finding #11: the benchmark was presented
as current law when the table had already been superseded.

**The lesson worth keeping:** an axis range is not a data extent, and a
test written from the same misreading as the claim cannot catch it.

### 9. ⚠️ We misquoted the source on salt, in the unsafe direction

An earlier code comment paraphrased Garibaldi as finding that **"salt has
no protective effect."** The paper's no-effect finding is qualified: it
applies **in a buffer system.** In egg yolk, the same paper measures
D₆₀ rising from 0.40 min to **5.1 min — 12.75× protection.**

This error pointed the wrong way. It made a salted kill step look
harmless when it is in fact slightly *worse* than a sugared one.

**Fix.** Salt is now added **after** the heat step, alongside the sugar.
A `YOLK_SALTED_10PCT` model was added, and the recipe's worst-case
in-window cross-check is deliberately run against it — yielding
**5.37 log₁₀** against a 5.00 target. That margin is only **0.37 log₁₀**,
which is thin, and it is reported as the governing figure rather than the
more flattering 7.93 from the plain-yolk model.

### 10. ⚠️ Documented log₁₀ figures were computed with the wrong ramp

Also self-caught. The cross-check table in `formulation.py` quoted
8.08 / 6.65 / 5.44 log₁₀ — values produced by a **4.0 min** ramp, while
the specified process and the whole test suite use **1.5 min.** The
correct figures are **7.93 / 6.57 / 5.37**, so the drift *inflated* the
apparent safety of the step.

**Fix.** `YOLK_RAMP_MINUTES` is now a single named constant consumed by
the recipe, the report and the tests; the figures live in a
machine-readable `YOLK_STEP_CROSS_CHECKS` dict; and
`test_docstring_cross_checks_match_the_real_process` recomputes all of
them from the live constants and fails if the prose, the dict or the
integrator disagree. The same pass caught a stale "1.8×" in the report
where the code computed 1.3×.

### 11. 🔴 We claimed a regulatory safe harbour that no longer exists

**This was the most serious error in the project, and it was in the part
we were proudest of.**

The yolk step's primary justification was labelled *"REGULATORY — law,
not a model"* and described as "the strongest class of evidence
available to this project." Verified against the eCFR versioner API,
boundary-tested on adjacent dates:

| Fact | Value |
|---|---|
| Table I promulgated | 1971-05-28 (36 FR 9814) |
| **Last operative day** | **2022-10-30** |
| **Removed** | **2022-10-31** (85 FR 68680) |
| Current §590.570 | a bare performance standard |

So a superseded table was being presented as live law — an overclaim
about the *nature* of the evidence rather than its value.

**A reviewer raised this and was right in substance but wrong in
attribution**, placing Table I in §590.575. Checked and rejected:
§590.575 was *"Heat treatment of dried whites"* (spray/pan-dried
albumen held 5–7 **days**). Our section citation had been correct all
along; our **tense** had not.

**What survived the correction.** The safe harbours did not disappear —
FSIS moved them into the *Food Safety Guideline for Egg Products*,
which was already this repo's model source. FSIS's own words:

> "The tables in the appendix of the compliance guideline for
> pasteurization times and temperatures **are not minimum lethalities,
> but rather safe harbors** for plants to follow."

**Fix.** `meets_cfr_safe_harbour()` now *raises* instead of returning a
comfortable bool; it is replaced by `meets_historical_cfr_row()`. Added
`Evidence.REGULATORY_HISTORICAL` — which also closed a real hole, since
the docs had been printing a `REGULATORY` grade that **did not exist in
the enum**. Two parallel evidence systems, one undocumented, is exactly
how an overclaim survives review. Also added `Evidence.is_current_law`,
`False` for every member, with a test that keeps it so.

**And a limit that applies regardless of dates:** safe harbours apply
to FSIS-inspected official plants. A home kitchen has none, of any era.

### 12. 🔴 The finished sweetened base matches no regulatory category

Valid reviewer finding, verified by arithmetic. After the kill step:

```
egg material   23.20 g
added nonegg   14.20 g   ->  38.0% of the finished base
```

Historical caps were **<2%** (whole egg blends) and **2–12%**
(fortified). Nothing covers 38%. Table I's own footnote sent unlisted
products to paragraph (c) for separate justification.

The benchmark therefore speaks to the **pre-heat egg phase only** — a
scope limit now stated in `FINISHED_BASE_NOT_IN_ANY_ROW`.

**What was *not* accepted.** The reviewer also proposed reclassifying
the pre-heat base as a *"whole egg blend"* because it contains 5.2 g of
white. Rejected on numbers: at **43.06%** egg solids it is 0.06 points
from commercial plain yolk and **17.41 points** from whole egg
(25.65%). "Plain" contrasts with *sugar* and *salt* — added **nonegg**
ingredients — not with dilution by white; commercial liquid yolk is
itself white-diluted. That relabel would have made the description
*less* accurate.

### 13. 🔴 Our own fix created a new hazard: recontamination

Moving sugar and salt after the kill step correctly solved the *matrix*
problem. It also introduced a hazard the project had not addressed at
all: **14.2 g of never-heated material is now stirred into product
whose entire safety claim rests on a thermal process.**

Dry sugar and salt cannot support growth (water activity far below
0.6), but they can carry viable *Salmonella* as inert passengers — and
a contaminated spoon transfers organisms straight into pasteurized
product.

The former §590.570(b) required this too, verbatim: *"holding,
packaging, facilities and operations shall be such as to prevent
contamination of the product."*

**Fix.** Added `POST_LETHALITY_CONTROLS` — six controls, now printed in
the report. **No log reduction is claimed for any of them:** they reduce
a hazard, they do not quantify it. This is a genuine remaining weakness,
not a solved problem.

### 14. 🔴 `is_defensible` blessed thermal curves nobody measured

Reproduced exactly as the reviewer described: `is_defensible` returned
`True` for a `ThermalHistory` labelled *"PURELY ASSUMED, no
thermocouple"*. The class docstring said "measured or modelled" and
then **never recorded which**, so every downstream property treated an
aspiration as data.

Same error class as the retired `is_lab_grade`: a name promising more
than the inputs support.

**Fix — three levels, now structural rather than promised:**

| Level | Question | Property | Status |
|---|---|---|---|
| 1. Mathematical | Is the model right? | `is_model_defensible` | ✅ yes |
| 2. Process | Did the product follow the curve? | `is_process_measured` | ❌ **no** |
| 3. Microbiological | Does the finished matrix achieve it? | `is_lab_validated` | ❌ **no** |

`ThermalHistory` now carries `provenance` (`ASSUMED` / `MEASURED` /
`SIMULATED`), **defaults to the weakest claim**, and refuses
`MEASURED` unless a calibrated instrument is named. Verdicts carry the
provenance forward so they cannot be read in isolation and mistaken for
measurement.

### 15. ✅ A researched alternative we deliberately did *not* adopt

Wang & Wang 2009 reports something genuinely useful for the white step:

> "Foaming was significantly reduced at temperature of **55 C for 10
> min**, whereas it **did not change up to 3 min at heating temperature
> of 62-64 C.**"

That suggests a *short, hotter* pulse may be gentler on foam than a
*long, cooler* one — and hints at a redesign: pasteurize the white
**plain**, cool it, then add sugar and whip. That would eliminate the
47.5%-sugar extrapolation entirely.

**We did not adopt it, and the reason matters.** Garibaldi Fig. 5
photographed *plain* egg white going turbid in 2 min and heavily
coagulating by 9 min at 60 °C. A 62–64 °C plain-white hold is therefore
squeezed between coagulation on one side and insufficient lethality on
the other, and Wang & Wang measured **foam functionality, not microbial
lethality** — the two studies do not compose into a validated process.

Adopting it would trade a *disclosed, modelled* risk for an
*undisclosed, unmodelled* one. Documented as a research direction
requiring three simultaneous proofs — lethality, foam function, and
post-treatment contamination control — not as a fix.

### 16. 🔴 Retired claims survived inside the source code

**The most uncomfortable finding so far, because it means a correction
is not the same thing as a fix.**

After finding #8 corrected the window constants, the *sentence*
asserting the retired conclusion was still in `formulation.py`:

> "62 C is the top of the intersection of both evidence windows...
>  At 62 C all three models are genuinely in-window."

It sat roughly 80 lines from its own correction, inside the same
docstring. Two source files also disagreed about one physical fact —
`formulation.py` said the intersection was 59.4–62.0 °C while
`thermal_safety.py` said 59.4–59.5 °C.

Four further live-tense violations were found by our own sweep after
the reviewer's list was exhausted: `formulation.py:724` and `:914`,
`README.md:282`, `docs/RECIPE.md:146`.

**Why the tests missed it.** All 126 tests passed with every one of
these present, because the suite asserted only on **numbers**. Every
defect in rounds 3–6 was a **sentence**.

**Fix.** `tests/test_claim_surface.py` reads the source files and
documents as data and fails if retired wording reappears. It is
registered in CI, and the CI mutation battery now includes four
**prose** mutations, so the guard is proven rather than assumed.

**Two holes in the guard itself**, both found by mutation-testing the
test — and both worth recording because they are the same shape as the
bug it exists to prevent:

- **Marker laundering** — a hit adjacent to an existing retirement note
  inherited that note's protection. Fixed by requiring the hit *line*
  to read as reportage (quoted, or carrying its own marker).
- **Self-quarantine** — the forbidden phrase *"former regulation safe
  harbours, still valid"* contains the word "former", which was itself
  a quarantine marker. The phrase **excused itself**, and a verbatim
  round-6 defect passed the guard. Fixed by stripping the matched
  phrase before looking for markers.

### 17. 🔴 Fixing one overclaim produced another

When the "three models in-window" claim collapsed, the replacement text
read:

> "What replaced it is stronger, not weaker. The yolk step is now
>  justified primarily by 9 CFR 590.570 Table I, which is a legal safe
>  harbour..."

That table had been superseded for two years. The new claim inherited
the old one's confidence instead of being independently checked.

**The lesson, stated plainly: when a claim collapses, its replacement
deserves the same scrutiny as the original.** Two overclaims in
sequence, both in the same flattering direction, is not bad luck.

### 18. ⚠️ Even the *current* authority is guidance, not law

Verified while checking a citation, and it narrows the whole project.

The FSIS *Food Safety Guideline for Egg Products* — the source of every
D-z model here and of the safe-harbour tables after they left the CFR —
says of itself, verbatim:

> "The revised guideline represents FSIS' current thinking on these
> topics and should be considered usable as of its issuance. **The
> guideline does not create any new legal requirements or have the
> force and effect of law.**"

Its May 2026 revision (FR doc 2026-08702) was open for public comment
until **2026-07-06**, so it is not even a settled document.

So the evidence chain is: *superseded* regulation → *non-binding*
guidance → *our* implementation of the models in that guidance →
*assumed* thermal history. It is guidance, not law, all the way down.
Recorded in `EVIDENCE_REGISTRY`, which is now the single source of
truth for the status of every authority cited.

---

## What the tests do and do not prove

**They prove:** that this *software* correctly implements the published
D-z kinetics — the integrator agrees with a closed-form analytical
solution, the models reproduce FSIS table rows they were never
calibrated on, matrix mismatches are detected, out-of-window
extrapolation is flagged rather than hidden, and retired claims cannot
silently return.

**They do not prove:**

- that a real cup of this drink achieves the modelled log reduction —
  no microbiological challenge study was performed;
- that the real process follows the modelled thermal curve — no
  thermocouple data exists, and every `ThermalHistory` here carries
  `provenance="ASSUMED"`;
- that **D-z is the best physical model** for every matrix used here.
  Reproducing published values shows the implementation is faithful to
  those values; it does not adjudicate the underlying kinetics. An
  earlier phrasing — *"a mathematical model has been validated"* —
  blurred these two, and has been narrowed to *"the implementation has
  been checked against published values and exact mathematics."*

A green test suite is a statement about code, not about food.

---

## What would actually close these gaps

1. **Inoculated pack / challenge study** on the finished foam at its real
   sugar concentration. This is the only thing that upgrades the white's
   claim from extrapolated to measured.
2. **pH meter** reading of the finished foam and of the interface.
3. **Densitometer or simple mass/volume** measurement of each real layer.
4. **Thermocouple logging** inside the actual bain-marie, since all
   claims are time-at-temperature and heat transfer in a home pan is not
   uniform.

Items 2–4 are achievable in a good café. Item 1 needs a lab.

---

## Practical risk statement

For a healthy adult, the residual risk here is low and the process is a
clear improvement over the raw-egg drinks it replaces — that comparison
is the honest baseline, and it is documented with numbers.

But **if you are pregnant, immunocompromised, elderly, or serving
children**, "modelled as safe" is not the standard you should accept.
Use commercially pasteurized eggs, which carry an actual validated
process behind them.

A thermometer is not optional. Every safety claim in this project is
time-at-temperature, and the egg-yolk-latte finding shows precisely how
misleading "it feels hot enough" can be.
