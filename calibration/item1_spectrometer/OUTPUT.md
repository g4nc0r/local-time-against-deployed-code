# Captured output: the spectrometer calibration (production)

Run 2026-08-10 (stdlib Python, CPU, seed 20260813, 62 s; toy
validation seed 20260812).  `production_sweep.py` with the
census-derived geometry draw; artefact `production_results.json`.
This file is a regression target: a numeric shift is a
manuscript-level event.

The geometry draw samples, at runtime, the 495 clean line-recovery
cells of the operator-keyed Uniswap V3 census on Base reported in the
manuscript.  That census artefact is not vendored here (see
`production_sweep.py` for the path variable).  The census numbers flow
through the draw and are not restated here; this capture publishes
recovery curves and the draw's parameterisation shape only.  Draw shape: per-operator trigger-line distance
phi_i x W_REF with phi_i sampled uniformly from the clean cells and
W_REF = 75 local scales (census median trigger distance lands near
22 sigma); cadence/filter mix is a stated calibration assumption
(60 % every-block plain, 20 % period 5, 10 % period 20 dwell 3,
10 % penetration 0.3 w), flagged for re-run if a future census layer
recovers cadence.  Sender-keyed robustness draw: deferred, noted
as open; executed later and captured in `ROBUSTNESS.md`.

Pipeline is the paper's actual inversion (Appendix G): trailing
bipower local scale with candidate exclusion (43,200-block window),
admission 0 < t_act <= abar with cr >= trail, kappa = 3 exceedance,
folded-normal baseline subtraction, Wilson intervals, Hill tail read
at o_ref = 2 z0 on the <= 2-block subsample, within-component
agreement replication.  Operator scan validated event-exactly
against the third act's harness under `verification/act3-instrument/`
(see `../RUN-LOG.md`).

## Toy validation (pre-production gate)

`config_toy.json` (synthetic mix, planted alpha 2.5): 6/6 pools
recover the planted jump share inside the Theorem 6 bracket;
within-component agreement p = 1.00 in every pool; per-component
exceedance spread visible (the multiscale signal of
Proposition 15); Hill mean 2.94 (documented upward finite-o_ref
kernel bias, cf. the stress maps' bias map).

## Production calibration curves

Two planted worlds, 12 pools each, 32 census-drawn operators per
pool, era 800,000 blocks; anchor cell k = 32, era 800k, abar = 10.
W1: alpha 2.5, z0 7.5 sigma, lam 0.012.  W2: alpha 3.5, z0 20 sigma,
lam 0.004.  Full tables in `production_results.json`; the shape:

**Bracket coverage is 1.00 in every cell of every sweep** (120
pool-inversions per world across the three sweeps).

**Bias (the resolution floor), pi_J_hat minus planted labels**: flat
in population size and era length, moving only with the delay cut,
exactly as Theorem 6 prices it: W1 bias -0.19 to -0.21
(z0 = 7.5 sigma sits close to the 3 sigma sqrt(a) cut, so much of
the straddle mass is below resolution), W2 bias -0.075 to -0.096
(z0 = 20 sigma clears the cut).  The bias is the instrument's known
resolution, not noise: it is bracket-covered everywhere and
tail-correctable (a self-consistent floor correction using the
recovered tail is future work, noted).

**Variance (the statistical width)**: mean Wilson half-width falls
from 0.011-0.013 at k = 2 to 0.002-0.003 at k = 32 (population
curve), and from 0.009-0.011 at era 100k to 0.002-0.003 at era 800k;
RMSE is bias-dominated throughout (RMSE ~ |bias| to within 0.005).

**Power curve (the F1-adjacent number)**: precision is
admitted-event-limited, not operator-limited; the invariant is the
Wilson curve in m, half-width ~ 1.96 sqrt(E(1-E)/m)/(1-base), so a
+-0.02 statistical read needs roughly m >= 2,000 admitted
small-delay events per pool-era, and the operators-needed conversion
is m / (per-operator admitted events).  Under this draw's dense
cadence mix a single census-drawn operator typically clears it
(k = 2 already gives +-0.013); at production firing rates (census
firing bar, order 10^2 firings per cell-era) the same invariant
implies order 10^1-10^2 operators or pooled-era accumulation, which
is the honest reading of the census's per-pool geometry counts.

**Tail read**: W1 alpha_hat 2.75-2.77 +- 0.07 (planted 2.5, the
+0.2-0.3 finite-o_ref bias of the stress maps); W2 alpha_hat
3.69 +- 0.28 (planted 3.5).  Breakdown regime, reported honestly:
short eras with sparse heavy tails (W2 at era 100k) give
alpha_hat 5.3 +- 2.2, the read is not usable below ~400k blocks at
lam = 0.004; W1's denser jumps stay usable from 200k.

**Delay-cut curve**: tightening abar from 30 to 2 improves the bias
(-0.214 -> -0.191 in W1; -0.096 -> -0.075 in W2) at negligible
width cost under this cadence mix, confirming the small-delay
design; the effect is modest here because the mix is
dense-check-dominated.

## Status

The spectrometer calibration is executed: harness built,
toy-validated, census draw wired (UniV3-Base), production curves
captured.  Open, gated on nothing structural: (i) the census-swap
robustness draw, executed 2026-08-10 and captured in `ROBUSTNESS.md`
(a null; the draw the programme called Aerodrome-side reads a
multi-venue Base layer, and that file carries the naming correction);
(ii) re-run on a cadence-recovering census layer;
(iii) the self-consistent resolution-floor correction; (iv) a
tick-quantised world variant (budget row 8) if the manuscript
integration wants it.  Manuscript integration remains a separate
authorised pass.
