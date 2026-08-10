# Captured output: the spectrometer calibration, robustness draw (census swap)

Run 2026-08-10 on the workstation (stdlib Python, CPU, seed 20260813,
200 s).  `robustness_sweep.py`; artefact `robustness_results.json`.
Closes the first of the three open items left by `OUTPUT.md`.
This file is a regression target: a numeric shift is a
manuscript-level event.

Naming.  The layer this draw reads is the Base sender-keyed operator
layer behind the companion paper's population, and that layer's clean
pool set is multi-venue: predominantly Aerodrome Slipstream, but with
PancakeSwap V3, Uniswap V3 and V3-fork pools in it.  The artefact and
this file therefore say Base sender-keyed, not Aerodrome.

The census is read by path at runtime and is not vendored here; no
cell count, phi table, pool or operator from it appears here or in the
artefact.  What is published is the recovery
curves and the shape of the draw.  The one census statistic this run
would otherwise have exposed, the ratio of median trigger fractions
between the two censuses, is withheld; `GATED_VERBOSE=1` prints it
locally.

## What the draw asks

The production sweep drew per-operator trigger-line distances from the
UniV3-Base census.  This re-runs the identical experiment, same seed,
same two planted worlds, same twelve pools each, same cadence mix,
same inversion, with the geometry draw taken instead from the Base
sender-keyed layer.  Cells are therefore paired: same price paths,
only the phi draw differs.

## Result: the curves do not move

**Bracket coverage is 1.00 in all 104 cells of all four sweeps**, as
in production.

**The census swap is a null.**  Against the production draw, across
26 paired cells: median absolute bias shift 0.0022, maximum 0.0133
(W1, k = 2); median absolute Wilson-width shift 0.0001, maximum
0.0010.  Bias stays in the production band, W1 -0.191 to -0.214 and
W2 -0.078 to -0.100, and the Hill reads stay at W1 2.73-2.78 and
W2 3.68-3.84 against planted 2.5 and 3.5, including the same
short-era breakdown (W2 at era 100k, 5.21 +- 2.24).

**The matched variant is degenerate.**  Rescaling W_REF so the two
draws' median trigger distances coincide leaves W_REF unchanged: the
two censuses agree on median trigger fraction to the resolution their
artefacts record it at.  The variant collapses onto the first and was
not re-run.  This is the substance of the null, and its limitation:
the two operator populations have near-identical trigger-fraction
distributions, so the swap tests that the instrument does not depend
on which census supplied the draw, not that it tolerates a different
geometry.

## The sensitivity arm the null needs

Because the venue swap moves the geometry so little, the same draw was
re-run with W_REF halved and doubled, a factor of four in trigger-line
distance, far beyond any census-to-census difference.  Paired against
production: |d bias| median 0.0341 (max 0.0547) at half, 0.0171 (max
0.0280) at double; |d Wilson| median 0.0008 and 0.0013.  Bracket
coverage stays 1.00 throughout.

Two readings follow.  First, the census swap sits an order of
magnitude below the instrument's own sensitivity to trigger-line
location, so the null is a real null and not an insensitive test.
Second, the sensitivity is signed and interpretable: closer trigger
lines improve the bias (W2 -0.034 to -0.047 at half W_REF against
-0.078 to -0.100 at production) because more straddle mass clears the
resolution cut, and the Hill read's known upward finite-o_ref bias
falls monotonically with trigger distance (W1 alpha_hat 2.89 at half,
2.76 at production, 2.64 at double, planted 2.5).  Neither effect
touches coverage.

## Status

The robustness draw is executed and its answer is a null: the
production calibration curves are a property of the instrument, not
of the census that supplied the geometry.  Still open from
`OUTPUT.md`: the re-run on a cadence-recovering census layer, the
self-consistent resolution-floor correction, and the tick-quantised
world variant.  Manuscript integration remains a separate authorised
pass.

## Census paths

Neither census artefact is vendored in this repository.  Both sweeps
resolve them from environment variables, `LT_CENSUS_UNIV3` and
`LT_CENSUS_SENDER`, falling back to default filenames beside the
scripts.  The draw is unaffected by where the artefact sits, so the
captured numbers above are independent of the path.
