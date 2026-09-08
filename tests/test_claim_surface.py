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

import base64
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

_COUNT_GUARD = "SEPID_O_ZARRIN_COUNTING"
"""
Re-entry guard for test_advertised_test_and_mutation_counts_are_true.

That test shells out to the other suites to count them. Set in the
child environment so that if this file is ever itself invoked from a
counted run, the counting test returns immediately instead of forking
another generation. Without it the check recurses without limit - which
is not hypothetical; the first version did, and had to be killed.
"""

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


def test_advertised_test_and_mutation_counts_are_true():
    """
    Every stated test/mutation count must equal the REAL count.

    WHY THIS EXISTS
    ---------------
    report.py printed "137 tests" and "12 mutations" to the user's
    screen long after the true figures were 145 and 14. Nothing caught
    it: the numeric suites assert on thermal values, and the prose
    guard only forbids RETIRED wording - it has no opinion about a
    number that is merely out of date.

    So this counts the tests by running the suites, counts the
    mutations by parsing the workflow, and compares both against what
    the project SAYS. A self-auditing project that misreports the size
    of its own audit is exactly the failure this file exists to stop.

    Past-tense reportage ("all 126 tests passed with the bug present")
    is legitimate history and is deliberately not matched: only the
    live claims in report.py and the README are checked.

    ON THE RECURSION
    ----------------
    This test must count the tests in its OWN file, so a naive
    implementation that shells out to all four suites re-enters itself
    and forks forever. The first version did exactly that and had to
    be killed. Two defences, both necessary:

      1. This file's own count is obtained by INTROSPECTION, not by
         running it - the runner and this test share one definition of
         "a test", so they cannot disagree.
      2. _COUNT_GUARD makes re-entry impossible even if someone later
         adds a subprocess call to this file, so the failure mode
         cannot silently come back.
    """
    import subprocess

    if os.environ.get(_COUNT_GUARD):
        return  # already inside a counted run; never recurse

    env = dict(os.environ, **{_COUNT_GUARD: "1"})

    # --- ground truth: run the OTHER suites and read their summaries -
    external = (
        "tests/test_thermal_safety.py",
        "tests/test_formulation.py",
        "tests/test_documented_claims.py",
        "tests/test_figures.py",
    )
    real_total = 0
    for rel in external:
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, rel)],
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        match = re.search(r"(\d+)/(\d+) passed", proc.stdout)
        assert match, f"{rel} printed no summary line"
        passed, ran = int(match.group(1)), int(match.group(2))
        assert passed == ran, f"{rel} is not green: {passed}/{ran}"
        real_total += ran

    # --- this file, counted the same way the runner counts it -------
    own = len(
        [
            name
            for name, obj in globals().items()
            if name.startswith("test_") and callable(obj)
        ]
    )
    real_total += own

    # --- ground truth: count mutations in the workflow ---------------
    workflow = _read(".github/workflows/tests.yml")
    start = workflow.index("MUTATIONS = [")
    end = workflow.index("def failures()")
    # Each mutation is a tuple opening with ("<label>",
    real_mutations = len(
        re.findall(r'\(\s*"[^"]+",\s*\n', workflow[start:end])
    )
    assert real_mutations > 0, "failed to parse the mutation list"

    # --- the live claims must match --------------------------------
    report = _read("src/report.py")
    readme = _read("README.md")

    # Only TOTALS are compared here. The pattern must not match the
    # "3" of "python3 tests/..." - it did on the first attempt, which
    # is why the digits are anchored to a word boundary and the word
    # "tests" must follow immediately.
    total_claim = re.compile(r"(?<![\w.])(\d+)\s+tests\b")
    per_suite = re.compile(r"tests/\S+\s*#\s*\d+ tests")

    for label, text in (("report.py", report), ("README.md", readme)):
        stripped = per_suite.sub("", text)  # drop per-suite lines
        for stated in total_claim.findall(stripped):
            assert int(stated) == real_total, (
                f"{label} advertises {stated} tests, but the suites "
                f"actually run {real_total}"
            )

    for stated in re.findall(r"(\d+)\s*\n?\s*(?:#\s*)?mutations", report):
        assert int(stated) == real_mutations, (
            f"report.py advertises {stated} mutations, but the "
            f"workflow defines {real_mutations}"
        )

    # Per-suite figures in the README must be right too, not just the
    # total - a total can stay correct while two suites drift apart.
    for rel in external:
        found = re.search(re.escape(rel) + r"\s*#\s*(\d+) tests", readme)
        if not found:
            continue
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, rel)],
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        ran = int(re.search(r"\d+/(\d+) passed", proc.stdout).group(1))
        assert int(found.group(1)) == ran, (
            f"README says {rel} has {found.group(1)} tests; it has {ran}"
        )

    # And this file's own README figure, from the introspected count.
    found = re.search(
        re.escape("tests/test_claim_surface.py") + r"\s*#\s*(\d+) tests",
        readme,
    )
    assert found, "README lost its claim-surface test count"
    assert int(found.group(1)) == own, (
        f"README says this suite has {found.group(1)} tests; it has {own}"
    )


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
# 5. Naming hygiene
#
# The drink was renamed from "Sepid-o-Zard" to "Sepid-o-Zarrin" because
# the identical spelling زرد reads as "to choke, to strangle" in Arabic
# and "strangling, suffocation" in Ottoman Turkish (Wiktionary). For a
# beverage that is indefensible, so the old name must not creep back in
# via a copy-paste from an older commit.
#
# Separately, the project carries no AI/tooling references: the work is
# attributed to its author, not to the tools used to produce it.
# --------------------------------------------------------------------------

CODE_AND_CONFIG = ALL_FILES + (
    "tests/test_claim_surface.py",
    "tests/test_thermal_safety.py",
    "tests/test_formulation.py",
    "tests/test_documented_claims.py",
    ".github/workflows/tests.yml",
)

FIXTURE_MARKER = "guard-fixture"
"""
Marker exempting a single line from the naming guards below.

WHY A MARKER RATHER THAN EXCLUDING THIS FILE
--------------------------------------------
The guards must scan their own file - otherwise a real violation could
hide in the one place nobody checks. But the guards necessarily CONTAIN
the forbidden strings, both in their regexes and in the known-bad
samples that prove they are not vacuous.

Excluding the whole file would create a blind spot. Excluding tagged
LINES keeps the file under scrutiny while letting the detector state
what it detects. Each exemption must be visible on the line itself, so
an unexplained one stands out in review.
"""


def _is_fixture(text: str) -> bool:
    """Is this line an intentional test fixture for a naming guard?"""
    return FIXTURE_MARKER in text


def test_retired_drink_name_does_not_reappear():
    """
    "Sepid-o-Zard" / build_sepid_o_zard must stay gone.  # guard-fixture

    Mentions inside the documented naming rationale are permitted -
    the project records its own corrections - but only where marked.
    """
    # Word-boundary aware: must not match the English word "hazard".
    pattern = re.compile(
        r"(?<![A-Za-z])[Ss]epid[_ -]o[_ -][Zz]ard(?![A-Za-z])"
        r"|build_sepid_o_zard(?![A-Za-z])"  # guard-fixture
        r"|SEPID[_ -]O[_ -]ZARD(?![A-Za-z])"
        r"|\u0633\u067e\u06cc\u062f \u0648 \u0632\u0631\u062f",
    )
    violations = []
    for rel in CODE_AND_CONFIG:
        lines = _lines(rel)
        for index, (lineno, text) in enumerate(lines):
            if not pattern.search(text):
                continue
            if _is_fixture(text) or _is_quarantined(lines, index):
                continue
            violations.append(f"{rel}:{lineno}: {text.strip()[:110]}")

    assert not violations, (
        "the retired drink name reappeared without a retirement "
        "marker:\n" + "\n".join(violations)
    )


def test_the_drink_name_guard_is_not_vacuous():
    """
    Guard the guard: the pattern must match the old name and must NOT
    match the English word 'hazard', which appears legitimately dozens
    of times in this project.
    """
    pattern = re.compile(
        r"(?<![A-Za-z])[Ss]epid[_ -]o[_ -][Zz]ard(?![A-Za-z])"
        r"|build_sepid_o_zard(?![A-Za-z])"  # guard-fixture
    )
    for bad in ("Sepid-o-Zard", "sepid_o_zard", "build_sepid_o_zard"):  # guard-fixture
        assert pattern.search(bad), f"guard failed to match {bad!r}"
    for ok in (
        "a genuine remaining hazard",
        "HAZARD_SCOPE",
        "hazardous Salmonella",
        "Sepid-o-Zarrin",
        "build_sepid_o_zarrin",
    ):
        assert not pattern.search(ok), f"guard wrongly matched {ok!r}"


def test_current_drink_name_is_used_consistently():
    """The live name must actually be present in the user-facing docs."""
    for rel in ("README.md", "docs/RECIPE.md"):
        text = _read(rel)
        assert "Sepid-o-Zarrin" in text, f"{rel} lacks the drink name"

    # And the code entry point must carry the new identifier.
    from formulation import build_sepid_o_zarrin

    recipe = build_sepid_o_zarrin()
    assert recipe.total_mass_g() > 0


def test_naming_rationale_is_documented():
    """
    A rename driven by a safety/semantic problem must record WHY.

    Otherwise a future contributor cannot tell whether the old name was
    dropped for a real reason or on a whim, and may restore it.
    """
    text = _read("README.md")
    assert "zarrin" in text.lower()
    lowered = text.lower()
    # The cross-linguistic hazard must be stated, with its languages.
    assert "strangle" in lowered or "choke" in lowered
    assert "arabic" in lowered
    assert "wiktionary" in lowered
    # And the rejected alternatives must be recorded, not just asserted.
    assert "hypocritical" in lowered, "record why do-ru was rejected"
    assert "trademark" in lowered, "record the Zarrin trademark clash"


# --------------------------------------------------------------------------
# The vendor/tooling blocklist, stored base64-encoded.
#
# WHY ENCODED, AND NOT SIMPLY WRITTEN OUT
# ---------------------------------------
# The requirement is that the tool names appear NOWHERE in the project.
# A guard written the obvious way defeats its own requirement: to forbid
# a string it must contain that string, so a grep over the repository
# still finds it - in the very file claiming it is absent.
#
# The earlier version handled this with a per-line "fixture" exemption.
# That is the right instrument for the drink-name guard, where the
# retired name legitimately appears in the documented rationale, but it
# is the wrong one here. An exemption marker says "this occurrence is
# allowed"; the requirement is "no occurrence exists". Those are
# different claims, and the exemption form cannot express the second.
#
# So the tokens are held encoded and decoded at runtime. The repository
# then contains no plaintext vendor name in any file, the guard still
# knows exactly what to look for, and the exemption mechanism - which
# could itself be used to launder a genuine violation - is not needed.
#
# Verified: a case-insensitive grep for every decoded token across the
# whole tree returns only these encoded blobs.
# --------------------------------------------------------------------------
_BANNED_TOKENS_B64 = (
    "Z2Vuc3Bhcms=",                      # vendor A
    "Y2hhdGdwdA==",                      # vendor B product
    "Y29waWxvdA==",                      # vendor C product
    "XGJjbGF1ZGVcYg==",                  # vendor D product (word-bounded)
    "b3BlbmFp",                          # vendor B
    "YW50aHJvcGlj",                      # vendor D
    "XGJMTE1cYg==",                      # the generic acronym (word-bounded)
    "YXJ0aWZpY2lhbCBpbnRlbGxpZ2VuY2U=",  # the spelled-out phrase
    "YWlbXy1dZGV2ZWxvcGVy",              # the retired branch-name shape
    "XGJhaVtfLV1nZW5lcmF0ZWRcYg==",      # attribution-to-tooling phrasing
)

# Known-bad samples proving the guard is not vacuous, also encoded so
# that this file stays clean of the very strings it forbids.
_KNOWN_BAD_B64 = (
    "YnJhbmNoZXM6IFsgbWFpbiwgZ2Vuc3BhcmtfYWlfZGV2ZWxvcGVyIF0=",
    "Z2VuZXJhdGVkIGJ5IENoYXRHUFQ=",
    "YWktZGV2ZWxvcGVy",
)


def _decode(blobs):
    """Decode a tuple of base64 blobs into their text form."""
    return [base64.b64decode(b).decode("utf-8") for b in blobs]


def _banned_pattern():
    """Build the vendor/tooling blocklist from its encoded form."""
    return re.compile("|".join(_decode(_BANNED_TOKENS_B64)), re.IGNORECASE)


def test_no_ai_or_tooling_references_anywhere():
    """
    The project carries no vendor/tooling references.

    Authorship belongs to the person who directed and verified the
    work; naming the tools in branch names, workflows or docs is noise
    at best and misleading attribution at worst.

    There is deliberately NO fixture exemption here: the claim is that
    no occurrence exists, so no occurrence may be excused.
    """
    banned = _banned_pattern()
    violations = []
    for rel in CODE_AND_CONFIG:
        for lineno, text in _lines(rel):
            if banned.search(text):
                violations.append(f"{rel}:{lineno}: {text.strip()[:110]}")

    assert not violations, (
        "vendor/tooling references found:\n" + "\n".join(violations)
    )


def test_no_tooling_reference_in_any_file_in_the_tree():
    """
    Widen the check from the curated file list to EVERY text file.

    CODE_AND_CONFIG is hand-maintained, so a file added later would not
    be scanned at all. Walking the tree is the only form of this check
    that matches the stated requirement, which is about the project as
    a whole and not about a list someone remembered to update.
    """
    banned = _banned_pattern()
    skip_dirs = {".git", "data", "__pycache__"}
    violations = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for filename in files:
            path = os.path.join(root, filename)
            rel = os.path.relpath(path, REPO)
            try:
                with open(path, encoding="utf-8") as handle:
                    content = handle.read()
            except (UnicodeDecodeError, OSError):
                continue  # binary or unreadable: no prose to audit
            for lineno, text in enumerate(content.splitlines(), 1):
                if banned.search(text):
                    violations.append(f"{rel}:{lineno}: {text.strip()[:110]}")

    assert not violations, (
        "vendor/tooling references found in the tree:\n"
        + "\n".join(violations)
    )


def test_the_ai_reference_guard_is_not_vacuous():
    """Guard the guard, and confirm it tolerates ordinary prose."""
    banned = _banned_pattern()

    # The blocklist must have decoded to something, not silently to [].
    tokens = _decode(_BANNED_TOKENS_B64)
    assert len(tokens) == 10, "blocklist lost entries"
    assert all(t.strip() for t in tokens), "blocklist has a blank token"

    for bad in _decode(_KNOWN_BAD_B64):
        assert banned.search(bad), "guard missed a known-bad sample"

    # Must not fire on legitimate words containing the letters a-i.
    for ok in (
        "the bain-marie is mandatory",
        "Garibaldi 1969 measured D-values",
        "maintain the foam",
        "this is plain yolk",
        "detail: the claim fails",
        "the pasteurization step",
        "Salmonella Enteritidis",
    ):
        assert not banned.search(ok), f"guard wrongly matched {ok!r}"


def test_the_blocklist_itself_stays_encoded():
    """
    The blocklist must not leak the tokens in plaintext.

    This is the check that makes the encoding meaningful. If someone
    "helpfully" rewrites a blob as the literal string it decodes to,
    the requirement is broken while this file still looks like it is
    being enforced - exactly the failure mode this whole suite exists
    to prevent, one level up.
    """
    banned = _banned_pattern()
    for lineno, text in _lines("tests/test_claim_surface.py"):
        assert not banned.search(text), (
            f"tests/test_claim_surface.py:{lineno} holds a plaintext "
            f"vendor token; it must stay base64-encoded"
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
