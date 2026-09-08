# سپید و زرّین — Sepid-o-Zarrin

**A whole-egg espresso drink. Nothing from the egg is thrown away.**

One large egg. The yolk becomes a pasteurized custard base. The white —
the part your café currently discards — becomes a pasteurized meringue
foam. The espresso goes between them.

> **Read [`LIMITATIONS.md`](LIMITATIONS.md) before trusting any number
> here.** The safety figures are validated *models*, cross-checked
> against multiple published studies — not a lab certification of the
> finished drink. That distinction matters, and this project got it
> wrong once already.

---

## Before anything else: the safety finding

I modelled the two drinks you already order. Both are **raw-egg
beverages**. This isn't a criticism of your café — it's how the classic
recipe works — but you should be choosing it knowingly.

### Zabaione (espresso poured on raw sweetened yolk)

| | |
|---|---|
| Espresso temperature in cup (INEI standard) | 67 °C |
| Mixture after stirring into 18 g yolk base | **51.1 °C** |
| FSIS requirement for yolk | 61.1 °C held 3.5 min |
| Salmonella reduction achieved | **0.01 of 5.0 log₁₀ needed** |

The espresso simply isn't hot enough. The yolk absorbs its heat and the
mixture lands ~10 °C short of the pasteurization threshold.

**Note:** espresso arrives in the cup at **67 ± 3 °C**, not the 88–95 °C
brew temperature baristas quote. That number is the water at the group
head. I initially got this wrong myself; the correction is documented in
`docs/SOURCES.md` because it changes the answer completely.

### Egg-yolk latte — the more interesting case

| | |
|---|---|
| Mixture (30 g espresso + 18 g yolk + 150 g milk at 65 °C) | **61.7 °C** |
| FSIS threshold | 61.1 °C |

This one **does** exceed the threshold temperature. A naive "is it hot
enough?" check would pass it.

But FSIS limits are **time-at-temperature**, not touch-temperature. The
cup only *passes through* 61.7 °C while cooling:

| Cup insulation | Achieved |
|---|---|
| Very well insulated (k=0.03/min) | 1.96 log₁₀ |
| Typical ceramic cup (k=0.08/min) | 0.74 log₁₀ |
| **Required** | **5.00 log₁₀** |

A genuine hold at 61.7 °C would need **7.1 minutes**. An open cup never
provides that.

**This is the trap the whole project exists to catch:** peak temperature
is not the safety criterion. Hold time is.

### Should you worry?

Honest answer: the per-serving risk is low. Roughly 1 in 10,000–20,000
intact shell eggs carries hazardous *Salmonella*. But:

- If you're pregnant, immunocompromised, elderly, or serving children —
  don't drink it raw. The pasteurized version below costs 6 extra minutes.
- Raw egg protein is only **51% digestible vs 91% cooked**
  (Evenepoel 1998). You're absorbing about half the protein you think.
- Raw white contains **~1800 µg avidin** per egg, which binds biotin and
  blocks its absorption. Heat destroys it.

So pasteurizing isn't a compromise — it's better food.

---

## Why the yolk and white must never be whisked together

This is the single most important technical fact, and it's why you can't
just improvise this drink.

> **One drop of yolk cut egg-white foam volume from 135 mL to 40 mL.**
> — St. John & Flor 1931, via Lomakina & Míková 2006

Two studies measured damage, at levels an order of magnitude apart:

| Yolk carryover | In a 35 g white | Finding |
|---|---|---|
| **0.022%** | **~8 mg** | Wang & Wang 2009 — significant loss of foam capacity *and* speed |
| 0.5% | 0.175 g | Li et al. 2021 — significant loss of capacity and stability |

> ⚠️ **An earlier version of this recipe called 0.5% "the threshold".**
> That was 23× too lax. Worse, calling anything a threshold implies a
> safe level below it — and **no study establishes one.** At ~8 mg, the
> more sensitive figure is below what you can see or weigh in a
> kitchen.
>
> **So the rule is not a number: it is zero deliberate yolk carryover.**
> A tolerance you cannot measure is not a control.

**Mechanism:** yolk lipids — specifically the low-density lipoprotein
(LDL) fraction of yolk *plasma* — adsorb to the air–water interface
faster than albumen proteins, but cannot form the cohesive viscoelastic
film that holds a bubble wall together. The lamellae rupture.

Li et al. also found yolk **granules** (HDL, phosvitin) were *not*
damaging — confirming the lipid/LDL fraction as the specific culprit.

**Design consequence:** architectural separation. The yolk and white
each get their own vessel, their own sugar, their own heat treatment,
and meet only as visible layers in the glass. This is not a garnish
decision — it's the only way both functions survive.

---

## The recipe

**Total: 126.9 g — one serving. Equipment: thermometer (mandatory),
two bowls, small whisk or milk frother, saucepan for a bain-marie.**

### ⚠️ The sugar rule — read this first

Sugar goes into **both** egg layers, but at **opposite times**. This is
not fussiness; getting it backwards breaks either safety or texture.

| | When sugar goes in | Why |
|---|---|---|
| **Yolk** | **AFTER** heating | Sugar makes *Salmonella* ~10× harder to kill in yolk (Garibaldi 1969: D₆₀ 0.40 → 4.0 min) |
| **White** | **DURING** heating | Plain white coagulates at 60 °C in minutes; sugared white doesn't (Garibaldi Fig. 5) |

An earlier version of this recipe sweetened the yolk *before* heating and
then scored it with a plain-yolk safety model. That was a real error,
corrected here. See [`LIMITATIONS.md`](LIMITATIONS.md).

**The same rule applies to salt,** for two independent reasons found in
Round 4:

- Garibaldi measured D₆₀ for yolk + 10% NaCl at **5.1 min vs 0.40 min
  plain — 12.75× protection.** An earlier draft of `SOURCES.md`
  mistakenly said salt had "no protective effect"; the source says no
  effect *in a buffer system*, which is not egg yolk.
- The **former 9 CFR 590.570 Table I** (superseded 2022-10-31)
  reclassified yolk at ≥2% salt into a category requiring 146 °F rather
  than 142 °F.

### Layer 1 — Yolk base (37.4 g)

| Amount | Ingredient | Why |
|---|---|---|
| 18 g | egg yolk (1 large) | — |
| 5.2 g | **egg white** (from the same egg) | thins the plain yolk so it heats evenly and pours as a layer. Deliberately white, **not water** — see the note below |
| 0.2 g | fine salt | **added after heating** — see the sugar rule |
| 14 g | caster sugar | **added after heating** — see the sugar rule |

> **Why the diluent is egg white rather than water.** Garibaldi measured
> its yolk D-values not on pure yolk but on "yolk equivalent to the
> commercial product (i.e., **diluted with egg white to approximately
> 43% egg solids**)". Thinning with water would push the matrix *away*
> from the composition the model was calibrated on while looking like a
> neutral step. 5.2 g of white puts the pan at **43.06% egg solids** —
> 0.06 points from Garibaldi's figure. It also comes from the same egg,
> so nothing extra is added and nothing is wasted.

1. Separate the egg **carefully**. Zero tolerance for white in the yolk
   bowl, and — far more important — **zero yolk in the white bowl.**
   If you break the yolk into the white, stop and start over. You cannot
   fish it out; see the carryover evidence above — the rule is zero
   deliberate carryover, not a tolerance.
2. Whisk the yolk with the **5.2 g of egg white only**. **No sugar and
   no salt yet** — both protect *Salmonella* in yolk, and keeping them
   out is what keeps this base legally "plain yolk".
3. Set over a bain-marie. Whisk **constantly**. Bring to **62 °C and
   hold for 10 minutes.**

> **A plain yolk is more delicate than a sweetened one.** Without sugar's
> protein-stabilising effect you have less margin before it sets, so
> whisk continuously and watch the thermometer. Holding at 62 °C rather
> than higher buys back 3 °C of headroom below the setting point.

4. **Result — matrix-matched model: 7.93 log₁₀** *Salmonella* reduction
   against a 5.00 target, on the FSIS Appendix III.C plain-yolk model,
   evaluated inside its calibration window (59.4–65.6 °C).

   **Historical cross-check.** The step would also have satisfied both
   plain-yolk rows of the *former* 9 CFR 590.570 Table I:

   | Former CFR row | Requirement | Us |
   |---|---|---|
   | plain yolk | 142 °F (61.1 °C) / 3.5 min | **would PASS** |
   | plain yolk | 140 °F (60.0 °C) / 6.2 min | **would PASS** |
   | salt yolk (2–12% salt) | 144 °F (62.2 °C) / 6.2 min | **would FAIL by 0.22 °C** |
   | sugar yolk (≥2% sugar) | 144 °F (62.2 °C) / 6.2 min | **would FAIL by 0.22 °C** |

   Those last two rows are the concrete price of adding either
   protectant early — and we qualify for the plain-yolk row **only**
   because the pan holds nothing but yolk and egg white (0.00% salt,
   0.00% sugar).

> ⚠️ **Correction: this is a historical benchmark, not current law.**
> An earlier version of this file called it a *"safe harbour ... law,
> needing no calibration window ... the strongest evidence in this
> project."* Verified against the eCFR API: **Table I was removed on
> 2022-10-31** (85 FR 68680). Today §590.570 is a bare performance
> standard with no times or temperatures at all.
>
> The safe harbours moved into the *FSIS Food Safety Guideline for Egg
> Products* — already the source of the model above. And safe harbours
> apply to FSIS-inspected plants; **a home kitchen has none, of any
> era.** What the table still tells us is real but modest: 62 °C /
> 10 min is a process the regulator once accepted for plain yolk.

> ⚠️ **And the finished sweetened base matches no row at all.** Once
> the 14 g sugar and 0.2 g salt go in, the base is **38.0% added nonegg
> ingredients**, against category caps of <2% and 2–12%. Because they
> arrive *after* lethality they cannot weaken the kill step — but the
> remaining hazard becomes **recontamination**, which is a hygiene
> problem, not a thermal one. See step 6.

5. **Secondary — model cross-checks.** Computed on the specified history
   (1.5 min ramp from 20 °C, then a 10 min hold). These models do **not**
   share a validity window:

   | Model | Result | Data window |
   |---|---|---|
   | FSIS III.C plain yolk (design basis) | 7.93 log₁₀ | in-window 59.4–65.6 °C |
   | Garibaldi 1969 plain yolk | ≥ 12 log₁₀ | **extrapolated** 53.0–59.5 °C |
   | Garibaldi 1969 yolk + 10% sucrose | 6.57 log₁₀ | **extrapolated** 55.0–61.5 °C |
   | Garibaldi 1969 yolk + 10% NaCl | **5.37 log₁₀** | in-window 50.0–62.5 °C |

   **Judge the step by its weakest *in-window* model: 5.37 log₁₀** against
   a 5.00 target — and note that this worst case assumes 10% salt, about
   twelve times more than the drink ever contains, and none of it during
   heating.

> **Correction.** An earlier version of this file claimed these models
> were "all in-window at 62 °C" and that Garibaldi's curves "span roughly
> 50–62 °C". Both were **false, and they were our own error, not a
> reviewer's catch.** The 50–62 °C figure was read off the *axis* of
> Fig. 4 rather than the extent of the plotted data. The true extents are
> in the table above; their intersection is only 59.4–59.5 °C, so a
> simultaneous in-window cross-check is impossible at *any* temperature.

> **Why 62 °C and not 64 °C?** An earlier version specified 64 °C / 5 min.
> At 64 °C every Garibaldi curve extrapolates, while 62 °C already clears
> the former CFR plain-yolk row (a historical benchmark, not law — see
> above) and leaves 3 °C below the plain-yolk setting
> point instead of 1 °C.
>
> **On the sugared row, precisely:** it shows the step stays above target
> under the only sweetened matrix with a published D-value (10% sucrose).
> It does **not** validate the recipe's finished ~37% sugar level.
> Adding sugar early is a real error with a partial cushion — not
> harmless. Follow the sequence.

6. Take off the heat, **now whisk in the 14 g sugar and the 0.2 g salt**
   until dissolved.

   > ### ⚠️ This step is where the drink is most likely to be spoiled
   >
   > Moving the sugar and salt after heating fixed a real safety problem
   > (they protect *Salmonella* during the kill step). But it created a
   > different one that this project originally failed to address:
   > **14.2 g of never-heated material now goes into product whose
   > entire safety claim rests on the heat step you just finished.**
   >
   > Dry sugar and salt can't support growth — but they *can* carry
   > organisms as inert passengers, and so can a spoon. Nothing after
   > this point will kill anything.
   >
   > - Add them while the base is **still above 60 °C**, straight after
   >   the hold, without changing vessels.
   > - Use a **clean, dry, dedicated spoon.** Never the one that touched
   >   the raw separated egg.
   > - Never return the **shell, the raw-egg bowl, or unwashed hands**
   >   to the pasteurized base.
   > - **Serve promptly.** Beyond 2 hours, refrigerate below 5 °C. This
   >   is a high-moisture, low-acid, nutrient-rich liquid, and
   >   pasteurization grants it **no shelf life whatsoever.**
   > - Don't hold it warm (5–60 °C). Pasteurization is not
   >   sterilization.
   >
   > No log reduction is claimed for any of the above. These controls
   > reduce a hazard; they don't quantify it.

7. Pour into the serving glass. Let it settle.

### Layer 2 — Espresso (30 g)

8. Pull a double espresso, 30 g. Pour gently over the base — down the
   side of the glass or over the back of a spoon.

> Brewed coffee is pH ~4.85–5.13 (NCA), near the pH 4.8 optimum where
> egg-white foam overrun peaks (Hammershøj & Larsen 1999).
>
> **But don't over-read that.** Egg white is strongly buffered and the
> layers only touch at an interface, so the coffee does *not* set the
> foam's pH — the lemon juice does. An earlier draft got this wrong.
### Layer 3 — Meringue foam (58.9 g)

| Amount | Ingredient | Why |
|---|---|---|
| 29.8 g | egg white | the part normally thrown away — the point of the drink. This is the whole white (35 g) *minus* the 5.2 g diverted into the yolk base |
| 28 g | caster sugar | 0.94:1 ratio, under the 2:1 structural ceiling |
| 1 g | lemon juice | the actual acidifier — targets the 4.8 overrun optimum |
| 0.1 g | fine salt | NaCl enhances foaming ability and stability |

9. Combine white + lemon + salt in a **scrupulously clean, dry,
   grease-free** bowl. Any fat residue is the same problem as yolk.

10. Set over the bain-marie. Whisk continuously and add the sugar
    **gradually, in 3–4 additions.** Unlike the yolk, the white **needs**
    its sugar during heating or it will coagulate.

> **Don't dump the sugar in at once.** With 50% sugar present from the
> start, Hanning (1945) measured >9 minutes of beating to incorporate
> the liquid versus 3–4 minutes without, and 32 minutes to reach
> comparable stiffness versus 16. Sugar delays foam formation; adding it
> in stages lets the protein film establish first.

11. Bring to **71 °C**, hold **3 minutes**, then remove from heat and
    whip to soft, glossy peaks.

> ### ⚠️ Why 71 °C, and why this is the weakest claim in the project
>
> The white can't be pasteurized plain — it would scramble. So it must
> be heated **sweetened**, and sugar protects the pathogen. Our foam is
> **47.5% sugar**; Garibaldi measured only **10%**. No published
> *Salmonella* D-value exists for egg white this sweet, and unlike the
> yolk step there is **no regulatory benchmark, current or historical,**
> for it either.
>
> Rather than interpolate and pretend, the step was stress-tested
> against a deliberately harsh model (compounding Garibaldi's measured
> 2.18×-per-10% protection up to 47.5%). Result: **5 log₁₀ needs only
> ~0.02 min at 71 °C** — an enormous margin even under that assumption.
>
> Evidence grade: `MODELLED (extrapolated)`. To be explicit, because it
> matters: this step is **not validated, not laboratory-confirmed, and
> not a measurement.** A large margin under a harsh assumption is
> reassurance, not proof. Full disclosure in
> [`LIMITATIONS.md`](LIMITATIONS.md).

12. Spoon the foam over the coffee. At ~200% overrun the foam is
    ~**0.35 g/mL** against the espresso's ~1.01 g/mL, so it should float
    securely.

### Layer 4 — Garnish (0.6 g)

13. Dust with **0.5 g cocoa** and **0.1 g ground cardamom**.
    (Cardamom follows the coffee-zabaglione precedent — Food52's
    *Zabaglione al Caffè* uses crushed cardamom pods.)

---

## Why it should stay in layers

A density gradient does the work, not a careful pour:

| Layer | Estimated density |
|---|---|
| Yolk base (~37 Brix syrup) | ~1.15 g/mL |
| Espresso | ~1.01 g/mL |
| Meringue foam (200% overrun) | ~0.35 g/mL |

`1.15 > 1.01 > 0.35` — the gap is large, so stratification is **expected**
to be robust rather than luck.

> **These are estimates, not measurements.** They come from the standard
> rule of thumb `ρ ≈ 1.0 + 0.004 × Brix`, which describes pure sucrose
> solutions; the real base also has yolk solids and lipids, and the real
> foam's density depends on the overrun your whisk achieves. An earlier
> draft called this "thermodynamically stable," which overstated a
> back-of-envelope calculation.

---

## How to drink it

Don't stir it. Pull the spoon down through all three layers and eat
upward — cold sweet custard, bitter coffee, warm airy foam. The
composition changes as you go.

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Foam won't whip | Yolk or grease contamination | Start over with a new egg and a degreased bowl. Do **not** assume a small smear is tolerable — damage is measured down to 0.022% (~8 mg), below what you can see. |
| Foam whips then collapses | Sugar added too fast, or under-whipped | Add sugar in 3–4 stages; whip to glossy soft peaks. |
| Base curdled / grainy | Exceeded ~65 °C, or not whisked enough | Keep to 62 °C and whisk constantly. Remember the yolk is heated **plain** now, so it's less forgiving than a sweetened one. |
| Layers merged | Base too thin, or espresso poured too hard | Keep base sugar at 14 g; pour over the back of a spoon. |
| Foam tastes eggy | Under-acidified | The lemon isn't optional; it also helps the foam. |

---

## ❌ The 60 °C fallback was withdrawn

An earlier version of this recipe offered "60 °C for 10 minutes" as a
gentler egg-white option. **It has been removed.**

Against a plain-white model it looked comfortably safe. Once our foam's
actual **47.5% sugar** is accounted for with a pessimistic model, the
picture changes:

| At 60 °C | Value |
|---|---|
| Time needed for 5 log₁₀ | **7.68 min** |
| A 5-minute hold | 3.30 log₁₀ — **fails**, at 0.65× the required time |
| A 10-minute hold | 6.55 log₁₀ — passes, but only **1.3×** the requirement |

Compare 71 °C, where 5 log₁₀ needs **0.02 min** — roughly **141×** margin
on a 3-minute hold. And 60 °C is precisely where Garibaldi photographed
plain white coagulating within 9 minutes, so it's an unforgiving
temperature to be aiming at by hand.

A process that depends on hitting a 10-minute hold accurately, to land
1.3× above the limit — and which outright **fails** at 5 minutes — is not
one to recommend to a home cook. **71 °C is the only white process
specified.** If you can't hold it reliably, use commercially pasteurized
egg white rather than dropping the temperature.

> These figures moved between drafts (they were once quoted as 5.7 min
> and 1.8×). Two corrections are responsible: the foam sugar rose to
> 47.5% when the white was re-split, and a numerical bug in the
> integrator was fixed — it had been overstating lethality by using
> endpoint-only trapezoids on an exponential rate. Both pushed these
> numbers in the *less* favourable direction, which is why the fallback
> went from "thin" to "withdrawn".

---

## Do not do these

- **Don't** whisk yolk and white together "to save a bowl." That's the
  one thing guaranteed to fail.
- **Don't** trust the old 134 °F / 3.5 min egg-white figure from the
  superseded regulation. It yields only ~1.3 log₁₀. FSIS explicitly
  states it doesn't reach the lethality of other liquid egg products.
- **Don't** add copper salts. Cu²⁺ genuinely is the most effective
  foam-stabilizing cation in the literature — and deliberately dosing a
  drink with copper is unsafe. Rejected on toxicity grounds.
- **Don't** skip the thermometer. Every safety claim here is
  time-at-temperature. Without measurement you have no process, and the
  yolk latte result above shows exactly how misleading "it feels hot"
  can be.
- **Don't** sweeten the yolk before heating. Sugar makes *Salmonella*
  ~10× harder to kill in yolk. The step is designed to tolerate this
  mistake, but don't spend the safety margin on carelessness.

---

## ⚠️ What this recipe has and has not proven

The numbers here come from **validated models**, cross-checked against
multiple independent published studies. They are **not** the result of a
microbiological challenge study on the finished drink.

A green test suite proves the arithmetic is right. It says nothing about
whether your cup hit the modelled lethality.

**If you are pregnant, immunocompromised, elderly, or serving children:**
use commercially pasteurized eggs, which have an actual validated
process behind them. "Modelled as safe" is not the standard you should
accept.

Full honest audit: [`LIMITATIONS.md`](LIMITATIONS.md).

---

## Reproduce the analysis

```bash
python3 src/report.py                   # full report with evidence grades
python3 tests/test_thermal_safety.py    # 52 safety tests
python3 tests/test_formulation.py       # 31 formulation tests
python3 tests/test_documented_claims.py # 15 doc-drift tests
```

The thermal model is validated by **reproducing FSIS's own published
tables from rows it was not calibrated on**:

| Check | Predicted | FSIS published |
|---|---|---|
| Egg white, 133 °F | 22.28 min | 22.56 min |
| Egg yolk, 142 °F | 10.48 min | 10.48 min |

Full citations in [`SOURCES.md`](SOURCES.md).
