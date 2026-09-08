# Sources

Where each number in this project came from.

**A correction to how this file used to open.** It previously claimed
"nothing here is estimated or inferred." That was not true, and an
external review was right to call it out. Some figures *are* derived,
interpolated, or extrapolated — most importantly the egg-white lethality
at our actual sugar concentration, for which no published D-value exists.

Those cases are now labelled where they appear, and audited in full in
[`LIMITATIONS.md`](LIMITATIONS.md). What this file does claim: every
figure is traceable to a named source, and where a figure is derived
rather than measured, that is stated.

---

## 1. Food safety / pasteurization
### FSIS Food Safety Guideline for Egg Products (revised May 2026)

Source of every D-z model in this project.

> ⚠️ **It is guidance, not law — and it says so itself.** An earlier
> version of this entry called it the *"primary regulatory source for
> all lethality maths"*, which overstated its standing. Verified
> against the announcing notice (FR doc **2026-08702**, published
> 2026-05-05), verbatim:
>
> > "The revised guideline represents FSIS' current thinking on these
> > topics and should be considered usable as of its issuance. **The
> > guideline does not create any new legal requirements or have the
> > force and effect of law.**"
>
> That revision was open for public comment until **2026-07-06**, so it
> is not a settled document either. Changes in the May 2026 revision:
> sanitation-SOP support, *Bacillus cereus* as an enzyme-modification
> hazard, a new section on cooking in lieu of pasteurization, and
> readability edits.
>
> **Consequence for this project:** the evidence chain runs *superseded
> regulation → non-binding guidance → our implementation of its models
> → an assumed thermal history.* Guidance, not law, all the way down.
> Status pinned in `thermal_safety.EVIDENCE_REGISTRY`.

This guideline — not the CFR — is where the pasteurization safe harbours
now live. FSIS moved them out of regulation and into guidance in 2020,
and said so explicitly in the preamble to 85 FR 68680:

> "The tables in the appendix of the compliance guideline for
> pasteurization times and temperatures **are not minimum lethalities,
> but rather safe harbors** for plants to follow and be reasonably
> certain that they will be meeting the requirement in 9 CFR 590.570
> ... plants are not required to follow the safe harbors and may use
> alternate procedures, if they have adequate scientific support."

**Table 1 — former CFR pasteurization requirements, reproduced in the
guideline:**

| Product | Time / temperature |
|---|---|
| Whole egg | 140 °F (60.0 °C) / 3.5 min |
| Plain yolk | 142 °F (61.1 °C) / 3.5 min, or 140 °F (60.0 °C) / 6.2 min |
| Sugared whole egg (2–12% sugar) | 142 °F (61.1 °C) / 3.5 min |
| Egg white | 134 °F (56.7 °C) / 3.5 min |

**Appendix III.A — Plain Egg White, pH 7.8 (target 5.7 log₁₀):**

| Temperature | Hold |
|---|---|
| 132.0 °F (55.6 °C) | 32.16 min |
| 133.0 °F (56.1 °C) | 22.56 min |
| 134.0 °F (56.7 °C) | 15.43 min |

**Appendix III.C — Plain Egg Yolk (target 6.2 log₁₀):**

| Temperature | Hold |
|---|---|
| 139.0 °F (59.4 °C) | 17.81 min |
| 142.0 °F (61.1 °C) | 10.48 min |
| 150.0 °F (65.6 °C) | 2.55 min |

**Key quotes:**
- *"In general, FSIS considers a 5 log10 reduction of Salmonella to be
  safe in products that are edible without additional preparation."*
- On egg whites: the former 134 °F / 3.5 min process *"does not achieve
  the same level of lethality as for other liquid egg products and can
  only be used under certain conditions."*

**⚠️ The trap:** anyone copying only the old 134 °F / 3.5 min egg-white
number will *under-process* the white. Our engine independently computes
that process at ~1.3 log₁₀ — far below 5. This is why `thermal_safety.py`
refuses to treat it as sufficient.

### 9 CFR 590.570
> "Pasteurized egg products must be produced to be edible without
> additional preparation to achieve food safety."

### Schuman et al. 1997, via Baldwin, *A Practical Guide to Sous Vide Cooking*
In-shell egg pasteurization: **57 °C (135 °F) for ≥ 75 minutes.**
Also: egg white coagulates at ~62 °C (ovotransferrin denaturation);
the custardy "perfect egg" state occurs at 64.5 °C.

---

## 2. Espresso parameters

### Istituto Nazionale Espresso Italiano (INEI) — certified espresso
| Parameter | Value |
|---|---|
| Ground coffee | 7 g ± 0.5 |
| Water exit temperature from unit | **88 °C ± 2** |
| **Temperature of the drink in the cup** | **67 °C ± 3** |
| Entry water pressure | 9 bar ± 1 |
| Percolation time | 25 s ± 2.5 |
| Volume in cup incl. foam | 25 mL ± 2.5 |

**⚠️ The error this prevents.** An early draft of this analysis assumed
espresso reaches the cup at ~90 °C, because 88–95 °C is the number
baristas quote. **That is the brew-water temperature at the group head,
not the beverage temperature.** The drink in the cup is 67 ± 3 °C.
A hobbyist thermocouple reading in a ceramic cup measured 146 °F
(63.3 °C), consistent with the standard.

Using 90 °C instead of 67 °C overstates the mixture temperature by
~15 °C and can flip a lethality verdict from "raw" to "pasteurized."
Two unit tests now lock the correct constant in place.

### Espresso / coffee pH
National Coffee Association: brewed coffee pH **4.85 – 5.13**.
Rune et al. 2023 measured brews at pH 3.97–4.25 across roast levels.
Either way the coffee is acidic and sits near the egg-white foam
optimum, which the recipe exploits deliberately.

---

## 3. Egg white foam chemistry

### Lomakina & Míková 2006, *Czech J. Food Sci.* 24:110–118
Review, "A Study of the Factors Affecting the Foaming Properties of Egg White."

- **The headline figure:** *"One drop of yolk caused a reduction from
  135 to 40 ml in the volume of egg white foam"* (St. John & Flor 1931).
- *"The triglyceride fraction of egg yolk is more detrimental than the
  cholesterol and phospholipids fractions."*
- Foam collapse mechanisms: bubble disproportionation, lamellae rupture,
  and drainage.
- Sugar **delays** foam formation: with 50% sugar, >9 min beating was
  needed to incorporate all liquid vs 3–4 min without, and 32 min to
  reach comparable stiffness vs 16 min (Hanning 1945). → *add sugar
  gradually, not all at once.*
- Water up to 40% can be added without reducing foam stability.
- Pasteurization reduces foaming ability via ovotransferrin denaturation
  at ~53 °C; metal ions and citrate/phosphate salts raise its
  denaturation temperature.
- pH: greatest foaming capacity at neutral/acidic pH; foam stability
  highest at pH 8.6 (native) — but see Hammershøj below.

### Hammershøj & Larsen 1999
Foam **overrun highest at pH 4.8**, lowest at pH 10.7. Drainage
resistance best at pH 7.0 at 30 min, but **on a long-term scale the
pH 4.8 foam was most resistant to drainage** — due to more rigid
interfacial behaviour and smaller bubbles.

This is the single most important formulation input: it means the
acidic espresso *helps* the foam rather than hurting it.

### Li et al. 2021, *Foods* 10:2238
"Comparative Study on Foaming Properties of Egg White with Yolk
Fractions and Their Hydrolysates."

- Simulated industrial egg white = egg white + **0.5% w/w egg yolk**;
  at this level both foam capacity and foam stability dropped
  significantly.

> ⚠️ **Correction.** This 0.5% figure was previously described here as
> "our hard design threshold". That was wrong and it was lax in the
> unsafe direction — see Wang & Wang 2009 below, which measured
> significant damage at **0.022%**, about 23× lower. 0.5% is one
> observation in one simulated industrial system, not a permitted level.
- Critical mechanistic detail: **yolk plasma** (LDL + livetins) caused
  the damage, while **yolk granules** (HDL, phosvitin) *"did not harm
  the foam ability of egg white."* So the culprit is specifically the
  LDL/lipid fraction competing at the air–water interface.

### Wang & Wang 2009, *J Food Sci* 74(2):C147 — the sensitive one

"Effects of Yolk Contamination, Shearing, and Heating on Foaming
Properties of Fresh Egg White." Full text retrieved and read (American
Egg Board final report, Iowa State University, Sept 21 2009).

Verbatim, on contamination:

> "A concentration as low as **0.022% (as-is basis)** of yolk
> contamination caused significant reductions in foaming capacity and
> foaming speed. The neutral lipid fraction of egg yolk caused the
> major detrimental effect on foaming, and phospholipids fraction did
> not give significant foaming reduction at a concentration as high as
> 0.1%."

For 35 g of white, 0.022% is about **8 mg** — well below anything a
cook can see or weigh. This is why the project's operational rule is
**zero deliberate yolk carryover** rather than a numeric tolerance.

Note the mechanism agrees with Li et al.: **neutral lipid** is the
culprit, phospholipid is comparatively harmless.

Verbatim, on heat — directly relevant to the white step:

> "Heat-induced foaming change is a function of temperature and holding
> time. Foaming was significantly reduced at temperature of **55 C for
> 10 min**, whereas it **did not change up to 3 min at heating
> temperature of 62-64 C.** Industrial processing steps (pumping, pipe
> transfer, and storage) did not produce negative effects on foaming of
> the final products and the controlled pasteurization was actually
> beneficial for good foaming performance."

This is a genuinely interesting result: it suggests a *short, hotter*
treatment can be gentler on foam than a *long, cooler* one. It is
recorded as a researched alternative in `LIMITATIONS.md`, **not**
adopted — see the reasoning there.

### Zhang et al. 2025, *Foods* 14:198
Citric acid treatment raised egg-white protein foaminess **from 50% to
178.2%**, increased surface hydrophobicity by 79.8%, and raised free
sulfhydryl content from 5 to 34.8 µmol/g. Optimum at 5 mg/mL CA;
higher concentrations *reduced* foaming again via aggregation.
Confirms that a *modest* acid addition helps and overdoing it hurts.

### Raikos et al. 2007, *Food Research International*
NaCl enhances foaming ability and stability of egg white proteins;
sucrose improves foam stability. Basis for the 0.1 g salt in the foam.

### Meringue structure
Sugar-to-egg-white ratio of **2:1 is optimal** for meringue hardness,
porosity and stability. Our recipe uses 0.94:1 — deliberately under the
ceiling, for a softer drinkable foam rather than a stiff pastry meringue.

---

## 4. Sugar's TWO opposite effects

Sugar does two things at once, and an early version of this project only
accounted for one of them. This section is the corrected picture.

### 4a. 🔴 Sugar protects the PATHOGEN — the error that was missed

### Garibaldi, Straka & Ijichi 1969, *Applied Microbiology* 17(4):491–496
**"Heat Resistance of Salmonella in Various Egg Products"** — the primary
study FSIS itself cites. Measured *S. typhimurium* D-values:

**At 60 °C:**

| Matrix | D-value |
|---|---|
| Whole egg | 0.27 min |
| Whole egg + 10% sucrose | 0.60 min (2.2×) |
| **Plain egg yolk** | **0.40 min** |
| **Egg yolk + 10% sucrose** | **4.0 min (10×)** |
| Egg yolk + 10% NaCl | 5.1 min (12.8×) |

**At 55 °C:**

| Matrix | D-value |
|---|---|
| Egg white pH 9.2 | 0.55 min |
| Egg white pH 9.2 + 10% sucrose | 1.20 min (2.2×) |

z-values across all products: **4.2–5.3 °C**, average 4.6 °C.

The authors' own words:

> "the change in D value in yolk brought about by either 10% sucrose or
> 10% NaCl supplementation is quite dramatic. Such an increase in heat
> resistance (from D to 10 D) indicates that at temperatures where 10¹⁰
> cells/ml are killed in 1 min in yolk, only 10 cells/ml will be killed
> in yolk supplemented with either 10% salt or 10% sucrose."

**Measured equivalence points** (Discussion), each equal in lethality to
the trusted 140 °F / 3.5 min whole-egg standard:

| Product | 3.5 min at |
|---|---|
| Egg white pH 9.2 | 133.2 °F (56.2 °C) |
| Egg white pH 9.2 + 10% sucrose | 135.9 °F (57.7 °C) |
| Whole egg | 140.0 °F (60.0 °C) |
| Egg yolk | 141.1 °F (60.6 °C) |

**Why this mattered so much here.** The project heated a 36.6%-sugar
yolk and scored it with FSIS's *plain*-yolk model — a matrix mismatch
that overstates lethality. The fix was to change the process: the yolk
is now pasteurized **plain** and sweetened afterwards.

#### ⚠️ Correction: what the paper says about salt in a *buffer*

An earlier draft of this project's code comments paraphrased Garibaldi
as finding that **salt has no protective effect.** That was a
misquotation, and it erred in the *unsafe* direction. The paper's
no-effect finding is qualified — it applies **in a buffer system**,
which is not egg yolk. In yolk, the same paper measures:

| Matrix | D₆₀ | vs plain |
|---|---|---|
| Plain egg yolk | 0.40 min | — |
| Egg yolk + 10% NaCl | **5.1 min** | **12.75×** |

Salt is therefore treated exactly like sugar in this recipe: kept out
of the kill step and stirred in afterwards. The model
`YOLK_SALTED_10PCT` in `src/thermal_safety.py` encodes this, and the
recipe's worst-case in-window cross-check is deliberately run against
it.

#### ⚠️ The yolk Garibaldi actually tested was **not pure yolk**

Item (vii) of the paper's materials list, verbatim:

> "yolk equivalent to the commercial product (i.e., **diluted with egg
> white to approximately 43% egg solids**)"

This matters for how the model may be applied. An earlier draft of this
recipe thinned the yolk with **water**, which moves the heated matrix
*away* from the tested composition while looking like a neutral step.
The diluent is now **5.2 g of egg white**, putting the pan at 43.06%
egg solids — 0.06 points from Garibaldi's figure, and verified by
`test_preheat_matrix_matches_the_solids_garibaldi_measured`.

#### ⚠️ Correction: the Fig. 4 validity windows were read off the axis

This project previously recorded Garibaldi's yolk TDT curves as
spanning "roughly 50–62 °C" and claimed all three yolk models were
in-window at 62 °C. **Both statements were false, and this was our own
error rather than a reviewer's catch.** 50–62 °C is the range of the
figure's *axis*, not the extent of the plotted data. The true extents,
read from the page scans in `data/garibaldi/`, are:

| Model | Data extent |
|---|---|
| Egg yolk, plain | 53.0–59.5 °C |
| Egg yolk + 10% sucrose | 55.0–61.5 °C |
| Egg yolk + 10% NaCl | 50.0–62.5 °C |

Their intersection is only **59.4–59.5 °C**, so a simultaneous
in-window cross-check of all three is impossible at *any* temperature.
Every model result in this project is now printed with its own window
and flagged `in-window` or `EXTRAPOLATED` individually.

---

## 3b. HISTORICAL regulatory benchmark — the former 9 CFR 590.570 Table I

> ### ⚠️ This section previously claimed to be current law. It was wrong.
>
> An earlier version of this file said the table below was **"law, not
> a model ... the strongest class of evidence available to this
> project."** That was a false claim, and it was false in the direction
> that flattered the project.

**Verified provenance** (eCFR versioner API, boundary-tested by
fetching adjacent dates and counting occurrences of "Table I"):

| Event | Date | Citation |
|---|---|---|
| Promulgated | 1971-05-28 | 36 FR 9814 |
| Last amended | 2020-12-16 | 85 FR 81341 |
| **Last operative day** | **2022-10-30** | — |
| **Removed** | **2022-10-31** | 85 FR 68680 |

**What §590.570 says today**, in full — no times, no temperatures, no
product categories:

> "Pasteurized egg products must be produced to be edible without
> additional preparation to achieve food safety and may receive
> additional preparation for palatability or aesthetic, epicurean,
> gastronomic, or culinary purposes..."

Stored verbatim in the code as `CFR_590_570_CURRENT_TEXT`, with a test
asserting it contains no temperatures — so this claim is checkable
rather than trusted.

**A reviewer's correction, and its own correction.** A reviewer flagged
this staleness — correctly — but attributed Table I to **§590.575**.
That was checked and rejected: §590.575 was *"Heat treatment of dried
whites"*, covering spray/pan-dried albumen held at 125–130 °F for
**5–7 days**. Table I was in §590.570, exactly as this repo had cited.
Our section number was right; our *tense* was wrong.

**The historical table** (rows relevant here):

| Liquid egg product | Temp / hold | Alt. temp / hold |
|---|---|---|
| Albumen (without chemicals) | 134 °F / 3.5 min | 132 °F / 6.2 min |
| Whole egg | 140 °F / 3.5 min | — |
| Whole egg blends (<2% added nonegg) | 142 °F / 3.5 min | 140 °F / 6.2 min |
| Fortified whole egg/blends (24–38% solids, 2–12% nonegg) | 144 °F / 3.5 min | 142 °F / 6.2 min |
| **Plain yolk** | **142 °F / 3.5 min** | **140 °F / 6.2 min** |
| Sugar yolk (≥2% sugar) | 146 °F / 3.5 min | 144 °F / 6.2 min |
| Salt yolk (2–12% salt) | 146 °F / 3.5 min | 144 °F / 6.2 min |

Table I's own footnote: *"Pasteurization of egg products not listed in
this table shall be in accordance with paragraph (c) of this section."*

### What may and may not be claimed from this

**Allowed** — the yolk step (62 °C / 10 min) *would have* satisfied both
plain-yolk rows, and falls **0.22 °C short** of the salt/sugar yolk row.
That shortfall quantifies the cost of letting either protectant into
the kill step. Computed by `meets_historical_cfr_row()`.

**Not allowed** — calling any of this a current safe harbour. Beyond
the table's removal, safe harbours apply to **FSIS-inspected official
plants**; a home kitchen has none, of any era.

### Was "plain yolk" the right row? Yes — and this was challenged

A reviewer argued our pre-heat base (18 g yolk + 5.2 g white) should be
reclassified as a *"whole egg blend"*. Rejected on arithmetic:

| Matrix | Egg solids |
|---|---|
| Pure yolk | 52.0% |
| **Our pre-heat base** | **43.06%** |
| Garibaldi's tested yolk | ~43% |
| Whole egg | 25.65% |

Our base is **0.06 points** from commercial plain yolk and **17.41
points** from whole egg. "Plain" contrasts with *sugar* and *salt* —
added **nonegg** ingredients — not with dilution by white. Commercial
liquid yolk is itself white-diluted, which is exactly what Garibaldi's
item (vii) describes. The proposed relabel would have made the
description less accurate.

### But the FINISHED base matches no row at all — this part was right

After the kill step we add 14 g sugar + 0.2 g salt to 23.2 g of egg:

```
egg material   23.20 g
added nonegg   14.20 g   ->  38.0% of the finished base
```

Category caps are <2% (blends) and 2–12% (fortified). **Nothing covers
38%.** So the benchmark speaks to the **pre-heat egg phase only**.

Because sugar and salt arrive *after* lethality they cannot weaken the
kill step — but the finished base's dominant hazard is
**recontamination**, a hygiene control rather than a thermal one. The
former §590.570(b) required exactly this too: *"holding, packaging,
facilities and operations shall be such as to prevent contamination of
the product."* See `formulation.POST_LETHALITY_CONTROLS`.

**And the asymmetry, honestly:** there is a historical benchmark for the
yolk step but **none for the white step**, because no row covers a
47.5%-sugar meringue. The white remains a modelled extrapolation.

## 3c. Hazard scope — *Salmonella* only

### Sampedro et al. 2019, *J Food Prot*, PMID 31195451

"Thermal Resistance of *Listeria monocytogenes* and *Salmonella* spp.
in Liquid Egg White."

Every log₁₀ figure in this project targets ***Salmonella***. That is the
organism FSIS Appendix III addresses and the one Garibaldi measured. But
*Listeria monocytogenes* has different thermal resistance and can be
**more** heat resistant under some conditions in liquid egg white — so a
Salmonella-validated process is not automatically adequate for Lm. FSIS
added Lm hazard discussion to the 2020 egg-products guidance for this
reason.

Consequence: **"5 log₁₀ achieved" must never be read as "all pathogens
eliminated."** Spore-formers are entirely out of scope at these
temperatures. See `formulation.HAZARD_SCOPE`.

### Mattick et al. 2001, *Appl Environ Microbiol* 67(9):4128–4136
Important nuance that keeps this from being oversimplified: sucrose
protection is **temperature-dependent**. Below ~65 °C, reduced water
activity was *detrimental* to *Salmonella* survival; above ~70 °C it was
protective. Sucrose at 55 °C was significantly detrimental (P = 0.04),
neutral at 60 °C, and protective at 74 °C (P = 0.003).

So the literature is not a simple "sugar always protects." Garibaldi's
direct egg-matrix measurements are the right basis for our conditions,
and Mattick suggests our pessimistic assumption is likely conservative.

### 4b. Sugar protects the egg PROTEIN — the effect we exploit

### Donovan 1977, via Renzetti et al. 2020, *Food Hydrocolloids*
> "High sucrose concentrations can raise the denaturation temperature of
> egg white protein up to about **13 °C (in 54% sucrose w/w)**."

Mechanism: preferential hydration / preferential exclusion — sugar is
excluded from the protein surface, which thermodynamically favours the
compact folded state.

⚠️ **Interpolation caveat.** This figure is for **54%** sucrose. An
earlier draft used it to justify heating a **36.6%** sugar yolk, which
was never rigorously established. That is now moot for safety, since the
yolk is heated plain — but it means the plain yolk is genuinely less
forgiving than the original write-up implied. Lowering the target to
62 °C recovers 3 °C of headroom below the setting point.

### Garibaldi 1969, Fig. 5 — measured, photographic
The same paper documents this effect directly, which is why the **white**
must keep its sugar during heating:

| At 60 °C | Plain egg white | White + 10% sucrose |
|---|---|---|
| 2 min | turbid | — |
| 9 min | **heavy coagulation** | — |
| 21 min | — | only slightly turbid |
| 27 min | — | **no coagulation** |

This is the asymmetry at the heart of the recipe: the yolk must be
sweetened *after* heating for safety, while the white must be sweetened
*during* heating for texture.

### Wang et al. 2025, *PMC12191903*
Confirms sugars enhance thermal stability of ovalbumin and lysozyme,
with reduced ΔH consistent with the preferential-exclusion mechanism.

### Egg protein denaturation temperatures (DSC)
| Protein | T_denat |
|---|---|
| Ovotransferrin (conalbumin) | 61–65 °C |
| Lysozyme | ~67–75 °C |
| Ovalbumin | ~84 °C |

Ovotransferrin is the heat-sensitive bottleneck — which is exactly why
white sets before yolk despite yolk needing a higher *pasteurization*
temperature.

---

## 5. Nutrition — why not wasting the white matters

### Evenepoel et al. 1998, *J Nutr* (PMID 9772141)
True ileal digestibility measured by stable isotope techniques in
humans: **cooked egg protein 90.9 ± 0.8%, raw egg protein 51.3 ± 9.8%.**

So cooking nearly **doubles** the protein you actually absorb. After
ingesting 25 g of raw egg protein, almost 50% is malabsorbed over 24 h.
This means gently pasteurizing the white is not a nutritional
compromise — it is a nutritional *improvement*.

### Avidin / biotin
Avidin is ~0.05% of egg-white protein, roughly **1800 µg per egg**.
It binds 4 mol biotin per mol with very high affinity, blocking
absorption. **Heat denatures avidin**, eliminating the anti-nutrient.
Documented case report: biotin deficiency from consuming 5–8 raw egg
whites daily for 16 months.

Relevant here because the user's motivation is not wasting a nutritious
ingredient — and raw white is precisely the form in which that nutrition
is *least* available.

---

## 6. Culinary precedent

This drink is not unprecedented. The yolk/white split is an established
technique, which is reassuring rather than limiting.

### Tom & Jerry (1820s)
Wikipedia / What's Cooking America / Vintage American Cocktails:
> "Separate eggs. Beat egg whites until stiff. Mix egg yolks with
> powdered sugar. Put a spoonful of yolk mixture in cup, fold in some
> egg white, then add hot milk."

Bar-Vademecum's analysis gives per-egg masses: **egg white 40 g,
egg yolk 20 g.** Exactly the architecture used here: yolks sweetened,
whites whipped separately, hot liquid added.

### The Fizz family
| Drink | Egg component |
|---|---|
| Silver Fizz | egg white |
| Golden Fizz | egg yolk |
| Royal Fizz | whole egg |

Sepid-o-Zard applies "Royal Fizz" logic to espresso, with the two egg
halves kept structurally separate and each given its own designed
lethality step — unlike the classic fizzes, which use the egg raw.

> An earlier draft called it "the food-safe member of this family."
> That phrasing is withdrawn: it describes the finished drink, and the
> finished drink has **not** been validated. Only the model has. The
> defensible claim is *"designed with a pasteurization step for each
> egg component"*, not *"food-safe"*.

### Coffee zabaglione
Miscela d'Oro: 3 egg yolks, 50 g sugar, 40 g hot espresso, cocoa to
garnish. Food52's *Zabaglione al Caffè* adds crushed cardamom pods —
the precedent for the cardamom in our garnish.

### Swiss meringue
Standard pastry technique: whisk whites + sugar over a bain-marie to
**71 °C (160 °F)**, which simultaneously dissolves the sugar and
pasteurizes the whites. Callebaut's professional version targets 60 °C.
Both clear the FSIS 5-log₁₀ bar per our engine.

---

## 7. Deliberately excluded

Things considered and rejected, so the reasoning is auditable:

- **Enzymatic lipid hydrolysis (lipase / phospholipase A₂)** to rescue
  yolk-contaminated foam. Li et al. 2021 shows it works and raises
  foaminess above plain egg white. Excluded: requires food-grade
  enzymes, pH-stat control and a 2 h 45 °C incubation. Not achievable
  in a café, and physical separation solves the same problem for free.
- **Copper ions (Cu²⁺)** to stabilize foam via the copper–ovotransferrin
  complex. Documented as the most effective cation tested. Excluded on
  toxicity grounds — deliberately adding copper salts to a drink is
  unsafe, and this is exactly the sort of "clever" idea that must be
  rejected rather than tried.
- **Raw-egg service.** Excluded: the entire safety analysis exists to
  avoid it.
- **Whisking yolk and white together.** Excluded: 18 g of yolk in 35 g
  of white is **51.4% w/w — about 2,300× the most sensitive published
  damage level** (0.022%, Wang & Wang 2009) and ~100× the Li et al.
  level. The foam is destroyed. This is the single most common way this
  drink fails.
- **Sweetening the yolk before pasteurizing.** Excluded after review:
  Garibaldi 1969 measured a 10× rise in *Salmonella* heat resistance
  from 10% sucrose in yolk. The step is designed to survive this mistake
  (6.57 log₁₀ on Garibaldi's 10%-sucrose model, which does NOT extend to
  the finished ~37% sugar level), but the process sequences
  sugar afterwards so the safety basis is valid rather than lucky.
- **A 60 °C egg-white hold.** Excluded: clears 5 log₁₀ on paper, but by
  only ~1.3× versus ~141× for 71 °C / 3 min, and 60 °C is exactly where
  Garibaldi photographed plain white coagulating. Too thin a margin at
  too unforgiving a temperature to recommend.
- **Interpolating a D-value for 44%-sucrose egg white.** No published
  measurement exists. Rather than invent one, the step is stress-tested
  against a deliberately pessimistic compounding extrapolation and
  labelled `MODELLED (extrapolated)`. See [`LIMITATIONS.md`](LIMITATIONS.md).
