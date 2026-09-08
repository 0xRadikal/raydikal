"""
CLAIM-SURFACE AUDIT: tests that read the PROSE, not the numbers.

WHY THIS FILE EXISTS
====================
Four rounds of external review found the same class of defect, and the
existing 126 tests caught none of them:

  round 3  "all three yolk models are in-window at 62 C"   FALSE
  round 4  cross-check figures computed with the wrong ramp
  round 5  "9 CFR 590.570 Table I ... law, not a model"    SUPERSEDED
  round 6  the round-3 claim was STILL PRESENT in a docstring, two
           hundred lines from its own correction, in the same file

Every one of those was a sentence, not a number. The numeric constants
had already been fixed; the prose asserting the retired conclusion had
not. And because the suite only ever asserted on computed values, it
stayed green while the repository contradicted itself.

That is the whole problem. A project whose premise is "verify
everything" cannot leave its most load-bearing claims - the ones a
human actually reads - unverified.

So these tests treat the source files and documents as DATA. They are
deliberately blunt: they grep for retired wording and fail if it
reappears anywhere. Blunt is correct here, because the failure mode
being prevented is a human re-adding a plausible-sounding sentence.

WHAT THIS FILE CANNOT DO
========================
It cannot tell whether a NEW claim is true. It only ensures that claims
already proven false stay dead, and that authority status is described
consistently with EVIDENCE_REGISTRY. Judging new claims still requires
reading the primary source.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from thermal_safety import (  # noqa: E402
    EVIDENCE_REGISTRY,
    AuthorityStatus,
    Evidence,
)

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

SOURCE_FILES = (
    "src/thermal_safety.py",
    "src/formulation.py",
    "src/report.py",
)

DOC_FILES = (
    "README.md",
    "docs/RECIPE.md",
    "docs/SOURCES.md",
    "docs/LIMITATIONS.md",
)

ALL_FILES = SOURCE_FILES + DOC_FILES


def _read(rel: str) -> str:
    with open(os.path.join(REPO, rel), encoding="utf-8") as handle:
        return handle.read()


def _lines(rel: str) -> list[tuple[int, str]]:
    return list(enumerate(_read(rel).splitlines(), start=1))


# --------------------------------------------------------------------------
# 1. Retired claims must stay retired
# --------------------------------------------------------------------------

# Each entry: (regex, human explanation of why it is forbidden).
#
# A line may still MENTION a retired claim - the project documents its
# own errors deliberately - but only if the same line or a nearby line
# marks it as retired. The `_is_quarantined` helper below implements
# that, so honest error-documentation is allowed and bare assertion is
# not.
RETIRED_CLAIMS = (
    (
        r"all three (?:yolk )?models are (?:genuinely )?in-window",
        "The three Garibaldi/FSIS yolk windows intersect only over "
        "59.4-59.5 C, so this is unachievable at any temperature, let "
        "alone 62 C. Retired in round 4.",
    ),
    (
        r"top of the intersection of both evidence windows",
        "The 'intersection' was computed from Fig. 4's axis range "
        "(50-62 C) rather than its plotted data. Retired in round 4.",
    ),
    (
        r"usable overlap\s*:\s*59\.4\s*-\s*62\.0",
        "False overlap. The real three-way intersection is 59.4-59.5 C.",
    ),
    (
        r"former regulation safe harbours, still valid",
        "Self-contradictory: 'former' and 'still valid'. Table I was "
        "removed 2022-10-31.",
    ),
    (
        r"PRIMARY JUSTIFICATION IS NOW REGULATORY",
        "The yolk step's design basis is a matrix-matched MODEL. The "
        "regulatory table is superseded and, being a safe harbour for "
        "inspected plants, was never available to a kitchen anyway.",
    ),
    (
        r"law,\s*not a model",
        "Table I is superseded law; the FSIS guideline that replaced it "
        "states verbatim that it does not have the force of law.",
    ),
    (
        r"which is a legal safe harbour",
        "No safe harbour, current or historical, applies to this "
        "project.",
    ),
    (
        r"strongest class of evidence",
        "Retired: it described a superseded table.",
    ),
    (
        r"hard design (?:limit|threshold)",
        "The 0.5% foam figure was 23x laxer than Wang & Wang 2009's "
        "0.022% observation. Neither is a threshold; the rule is zero "
        "deliberate carryover.",
    ),
    (
        r"0\.5%\s+figure\s+is\s+our\b|our\s+hard\s+design",
        "Claiming the 0.5% observation as 'ours' reinstates it as a "
        "tolerance. It is one literature datapoint, and not the most "
        "sensitive one.",
    ),
    (
        r"Below 0\.5% yolk it still works",
        "Directly contradicted by Wang & Wang 2009. This sentence told "
        "readers a measurable-damage level was safe.",
    ),
)

# Markers that indicate the surrounding text is documenting an error
# rather than asserting it.
QUARANTINE_MARKERS = (
    "retired",
    "do not reinstate",
    "was wrong",
    "wrong",
    "false",
    "withdrawn",
    "superseded",
    "earlier version",
    "earlier draft",
    "an earlier",
    "correction",
    "forbidden",
    "no longer",
    "removed",
    "must never",
    "contradict",
    "overclaim",
    "retract",
    "stale",
    "error",
    "mistake",
    "round 3",
    "round 4",
    "round 5",
    "not current",
    "historical",
    "formerly",
    "former",
    "used to",
    "previously",
    "this claim",
    "that claim",
    "would have",
    "forbidden",
)

QUARANTINE_BEFORE = 14
"""
How many lines ABOVE a hit may supply the retirement marker.

Chosen because the retired-claim blocks in this repo quote the old
wording under a heading and then explain it. Deliberately not larger:
a wide window would let an unrelated "wrong" elsewhere in a docstring
launder a fresh assertion.
"""

QUARANTINE_AFTER = 4
"""
How many lines BELOW a hit may supply the marker.

Needed because prose often states the bad claim first and refutes it
in the NEXT sentence:

    Garibaldi's curves were recorded as spanning "roughly 50-62 C".
    That is the range of Fig. 4's AXIS, not the extent of the data.

The refutation lands one line later. This was found as a false
positive from this very test file on its first run - the detector
flagged a line whose own next sentence retired the claim. Kept small
so a distant disclaimer cannot excuse a bare assertion.
"""


QUOTED = re.compile("[\"'\u201c\u201d\u2018\u2019]")
"""
Quote characters. A retired claim being DOCUMENTED is almost always
quoted, because the text reports what was once said. A retired claim
being ASSERTED is not.
"""

BANNER = re.compile(
    r"RETIRED (?:JUSTIFICATION|FRAMING|CLAIM)|DO NOT REINSTATE"
    r"|previously claimed|earlier version of th|earlier draft of th"
    r"|An earlier version|justified 62 C as follows",
    re.IGNORECASE,
)
"""
Explicit "what follows is a retired claim" banners.

Only these may open a multi-line quotation on a retired claim's
behalf. Deliberately a short, specific list rather than reusing
QUARANTINE_MARKERS: the broad marker list is fine for establishing
that a REGION discusses errors, but far too loose to license an
unquoted assertion.
"""


def _is_quarantined(lines: list[tuple[int, str]], hit_index: int) -> bool:
    """
    Is this occurrence marked as a retired/erroneous claim?

    MARKER LAUNDERING - why this is stricter than it first looks
    -----------------------------------------------------------
    The first version of this helper accepted any retirement marker
    anywhere in the surrounding window. Testing it against a
    deliberately reinstated claim exposed the hole immediately: text
    injected ADJACENT to an existing retirement note inherited that
    note's protection, so the guard blessed the very sentence it was
    written to forbid.

    That is worth dwelling on, because it is the same shape as the bug
    this whole file exists to prevent - a check that looks rigorous
    while quietly approving the thing it targets.

    A hit is therefore quarantined only if BOTH hold:

      1. a retirement marker appears in the window, AND
      2. the hit line itself reads as reportage rather than assertion -
         it is quoted, or it carries a retirement marker of its own.

    Condition 2 breaks the laundering: a bare assertion sitting beside
    somebody else's disclaimer fails it.
    """
    start = max(0, hit_index - QUARANTINE_BEFORE)
    stop = min(len(lines), hit_index + 1 + QUARANTINE_AFTER)
    context = " ".join(text.lower() for _, text in lines[start:stop])
    if not any(marker in context for marker in QUARANTINE_MARKERS):
        return False

    hit_line = lines[hit_index][1]
    if QUOTED.search(hit_line):
        return True

    # SELF-QUARANTINE, found by mutation testing this very file.
    #
    # The forbidden phrase "former regulation safe harbours, still
    # valid" CONTAINS the word "former", which is itself a quarantine
    # marker. So the phrase excused itself and the guard passed a
    # verbatim reinstatement of a round-6 defect.
    #
    # Fix: strip the matched phrase out of the line before looking for
    # on-line markers, so a claim can never launder itself with its own
    # wording. Only text OUTSIDE the match may quarantine it.
    residue = hit_line
    for pattern, _why in RETIRED_CLAIMS:
        residue = re.sub(pattern, " ", residue, flags=re.IGNORECASE)
    lowered = residue.lower()
    if any(marker in lowered for marker in QUARANTINE_MARKERS):
        return True

    # A retired claim quoted across SEVERAL lines only carries its
    # opening quote on the first one. Walk back to the nearest
    # explicit retirement banner and accept the hit if an unclosed
    # quotation was opened between there and here.
    #
    # Verified necessary: this project's own retired-claim blocks
    # reproduce the old wording as an indented multi-line quotation,
    # and the stricter per-line rule above flagged two of them as
    # fresh assertions. The banner requirement keeps this narrow -
    # arbitrary nearby prose cannot open a quotation on a claim's
    # behalf.
    for index in range(hit_index - 1, start - 1, -1):
        text = lines[index][1]
        if BANNER.search(text):
            span = "\n".join(t for _, t in lines[index : hit_index + 1])
            if len(QUOTED.findall(span)) % 2 == 1:
                return True
            break

    return False


def test_no_file_asserts_a_retired_claim():
    """
    The load-bearing test of this file.

    Any retired wording must be accompanied by an explicit marker that
    it is retired. Bare re-assertion fails.
    """
    violations: list[str] = []

    for rel in ALL_FILES:
        lines = _lines(rel)
        for pattern, why in RETIRED_CLAIMS:
            regex = re.compile(pattern, re.IGNORECASE)
            for index, (lineno, text) in enumerate(lines):
                if not regex.search(text):
                    continue
                if _is_quarantined(lines, index):
                    continue
                violations.append(
                    f"{rel}:{lineno}\n"
                    f"    text : {text.strip()[:110]}\n"
                    f"    why  : {why}"
                )

    assert not violations, (
        "retired claims re-asserted without a retirement marker:\n\n"
        + "\n\n".join(violations)
    )


def test_the_retired_claim_detector_actually_detects():
    """
    Guard the guard.

    A pattern list that matches nothing would make the test above
    vacuous - exactly the failure mode that let a stale mutation
    pattern silently pass in an earlier round. So verify the regexes
    fire against known-bad text.
    """
    samples = {
        r"all three (?:yolk )?models are (?:genuinely )?in-window":
            "At 62 C all three models are genuinely in-window, so",
        r"law,\s*not a model":
            "This is law, not a model.",
        r"hard design (?:limit|threshold)":
            "Treated here as a hard design limit, not a soft target.",
        r"which is a legal safe harbour":
            "Table I, which is a legal safe harbour for plain yolk",
    }
    for pattern, sample in samples.items():
        assert re.search(pattern, sample, re.IGNORECASE), (
            f"pattern {pattern!r} failed to match its own known-bad "
            f"sample - the retired-claim test would be vacuous"
        )

    # And every pattern in the live list must be a compilable regex.
    for pattern, why in RETIRED_CLAIMS:
        re.compile(pattern)
        assert len(why) > 30, f"pattern {pattern!r} lacks an explanation"


# --------------------------------------------------------------------------
# 2. Authority status must be described consistently
# --------------------------------------------------------------------------


def test_superseded_authorities_are_never_present_tense():
    """
    A superseded authority may not be described as currently binding.

    This is the round-5 defect generalised: it is not enough to fix the
    one sentence that said 'law, not a model'; every mention of the
    table must carry its tense correctly.
    """
    table = EVIDENCE_REGISTRY["cfr_590_570_table_i"]
    assert table.status is AuthorityStatus.SUPERSEDED_LAW
    assert table.is_citable_in_present_tense is False

    # Present-tense verbs that would wrongly imply the table is live.
    bad = re.compile(
        r"Table I\s+(?:is|remains|provides|requires|gives|applies)\b"
        r"|590\.570\s+Table I\s+(?:reclassifies|requires|specifies)\b"
        r"|(?:current|live|operative)\s+safe\s+harbou?r\s+for\s+plain",
        re.IGNORECASE,
    )
    violations = []
    for rel in ALL_FILES:
        lines = _lines(rel)
        for index, (lineno, text) in enumerate(lines):
            if bad.search(text) and not _is_quarantined(lines, index):
                violations.append(f"{rel}:{lineno}: {text.strip()[:110]}")

    assert not violations, (
        "superseded Table I described in the present tense:\n"
        + "\n".join(violations)
    )


def test_registry_is_the_only_authority_on_status():
    """
    Every authority carries a pinned status, citation and note.

    Prevents a half-populated registry entry from looking authoritative
    while actually asserting nothing.
    """
    assert EVIDENCE_REGISTRY, "registry must not be empty"
    for key, authority in EVIDENCE_REGISTRY.items():
        assert authority.key == key, f"{key}: key mismatch"
        assert isinstance(authority.status, AuthorityStatus)
        assert len(authority.citation) > 15, f"{key}: citation too thin"
        assert len(authority.note) > 40, f"{key}: note too thin"

    # The superseded entry must record when it stopped applying.
    table = EVIDENCE_REGISTRY["cfr_590_570_table_i"]
    assert table.operative_until == "2022-10-30"
    assert table.operative_from == "1971-05-28"


def test_no_current_law_imposes_a_process_requirement_on_us():
    """
    The only CURRENT_LAW entry is a performance standard.

    It contains no times or temperatures, so nothing in this project
    can claim to satisfy a numeric legal requirement.
    """
    from thermal_safety import CFR_590_570_CURRENT_TEXT

    current = [
        a
        for a in EVIDENCE_REGISTRY.values()
        if a.status is AuthorityStatus.CURRENT_LAW
    ]
    assert len(current) == 1, "expected exactly one current-law entry"

    for token in ("142", "140", "146", "3.5", "6.2", "Table"):
        assert token not in CFR_590_570_CURRENT_TEXT, (
            f"current 590.570 text must not contain {token!r}"
        )

    # And no Evidence grade may claim current-law status.
    for member in Evidence:
        assert member.is_current_law is False


def test_fsis_guideline_is_graded_as_guidance_not_law():
    """
    The current authority for our models is GUIDANCE.

    FSIS says so verbatim: the guideline 'does not create any new legal
    requirements or have the force and effect of law'. Since every D-z
    model here comes from it, that limit propagates to every figure.
    """
    guideline = EVIDENCE_REGISTRY["fsis_egg_guideline"]
    assert guideline.status is AuthorityStatus.AGENCY_GUIDANCE
    assert "force and effect of law" in guideline.note
    assert "safe harbors" in guideline.note


# --------------------------------------------------------------------------
# 3. No finished-product validation claims
# --------------------------------------------------------------------------


def test_no_document_claims_the_finished_drink_is_validated():
    """
    Level 1 is achieved; Levels 2 and 3 are not.

    So no document may call the finished drink validated, proven, or
    laboratory-confirmed.
    """
    bad = re.compile(
        r"(?:the\s+)?(?:drink|beverage|product|recipe)\s+is\s+"
        r"(?:validated|proven|verified|certified|food-safe|lab-validated)"
        r"|laboratory[- ]validated\s+(?:drink|beverage|product)"
        r"|proven\s+safe\s+to\s+drink",
        re.IGNORECASE,
    )
    violations = []
    for rel in ALL_FILES:
        lines = _lines(rel)
        for index, (lineno, text) in enumerate(lines):
            if bad.search(text) and not _is_quarantined(lines, index):
                violations.append(f"{rel}:{lineno}: {text.strip()[:110]}")

    assert not violations, (
        "finished-product validation claimed:\n" + "\n".join(violations)
    )


def test_limitations_states_the_three_levels_explicitly():
    """The honest summary must be present, not merely implied."""
    text = _read("docs/LIMITATIONS.md")
    assert "is_process_measured" in text
    assert "is_lab_validated" in text
    lowered = text.lower()
    assert "no thermocouple" in lowered or "thermocouple" in lowered
    assert "challenge study" in lowered


def test_report_prints_what_is_not_established():
    """
    The report is what a reader sees first, so the gaps must be in it.
    """
    text = _read("src/report.py")
    assert "NOT ESTABLISHED" in text
    assert "has not" in text.lower()


# --------------------------------------------------------------------------
# 4. Cross-file numeric agreement on the disputed windows
# --------------------------------------------------------------------------


def test_no_file_repeats_the_axis_derived_window():
    """
    '50-62 C' as a Garibaldi DATA range must not reappear.

    That figure is the Fig. 4 axis, and mistaking it for the data
    extent is the original sin of round 4.
    """
    bad = re.compile(
        r"Garibaldi[^\n]{0,60}(?:50\s*[-–]\s*62|50\.0\s*[-–]\s*62\.0)"
        r"|(?:50\s*[-–]\s*62|50\.0\s*[-–]\s*62\.0)[^\n]{0,40}Fig\.?\s*4",
        re.IGNORECASE,
    )
    violations = []
    for rel in ALL_FILES:
        lines = _lines(rel)
        for index, (lineno, text) in enumerate(lines):
            if bad.search(text) and not _is_quarantined(lines, index):
                violations.append(f"{rel}:{lineno}: {text.strip()[:110]}")

    assert not violations, (
        "axis-derived Garibaldi window re-asserted as data:\n"
        + "\n".join(violations)
    )


def test_window_intersection_is_stated_consistently():
    """
    The three-way intersection is 59.4-59.5 C everywhere it appears.

    A round-6 finding was that formulation.py said 59.4-62.0 while
    thermal_safety.py said 59.4-59.5 - two source files disagreeing on
    one physical fact.
    """
    from thermal_safety import (
        EGG_YOLK_PLAIN,
        YOLK_PLAIN_GARIBALDI,
        YOLK_SALTED_10PCT,
        YOLK_SUGARED_10PCT,
    )

    models = (
        EGG_YOLK_PLAIN,
        YOLK_PLAIN_GARIBALDI,
        YOLK_SUGARED_10PCT,
        YOLK_SALTED_10PCT,
    )
    lo = max(m.valid_min_c for m in models)
    hi = min(m.valid_max_c for m in models)

    # Computed from the live constants, not transcribed.
    assert abs(lo - 59.44444444444444) < 0.01, f"lo drifted to {lo}"
    assert abs(hi - 59.5) < 0.01, f"hi drifted to {hi}"
    assert hi - lo < 0.2, "intersection should be a sliver, not a range"

    # 62 C - the process temperature - must NOT be inside it.
    from formulation import YOLK_CUSTARD_TARGET_C

    assert not (lo <= YOLK_CUSTARD_TARGET_C <= hi), (
        "if the process temperature is inside the full intersection, the "
        "retired 'all three in-window' claim would be true and this "
        "whole guard needs revisiting"
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
