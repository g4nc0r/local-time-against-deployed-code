# Captured output: the small-delay and surcharge stress maps

Run 2026-08-10 on the GPU host (AMD Radeon AI PRO R9700, HIP device 1,
PyTorch 2.13.0/ROCm), `stress_maps.py`, seed 20260811, float64,
`torch.use_deterministic_algorithms(True)`; part A 190 s, part B
354 s wall.  Result artefact `../output/stress_results.json`.  This
file is a regression target: a numeric shift is a manuscript-level
event.  Bitwise ROCm reproducibility was not certified; regression
comparisons use seed + the stated Monte Carlo tolerances (Wilson
intervals per cell; part B rates carry ~2-5 % MC error at the cell
event counts shown).

Ground truth only: all worlds are planted diffusion + one-sided
compound-Poisson Pareto jumps (rate lam per block, sizes
z0 U^(-1/alpha)); no price model enters as an assumption.

Validation before the run (transcripts in `../RUN-LOG.md`): the
vectorised operator scan agrees event-exactly with
`verification/act3-instrument/mc_harness.py` on a common seeded world
(periods 1/5/40); the surcharge machinery reproduces the analytic
diffusive coefficients (see part B baselines below).

## Part A: Theorem 6 bracket maps

Grid: alpha in {1.3, 1.6, 2.0, 2.5, 3.5} x lam in {0.004, 0.012,
0.04} x z0/sigma in {2, 7.5, 20} x check period in {1, 5, 20}, plus a
drift arm (mu/sigma in {0.1, 0.5} at alpha 2.5, lam 0.012, z0 7.5);
141 configuration cells, 32 replicas each, 400,000 blocks; kappa in
{2, 3, 4, 6, 8, 12} x abar in {1, 2, 5, 10, 20, 50}; sigma known
(the estimation pipeline is the spectrometer calibration's surface).  The theorem RHS is
evaluated with the planted integrated tail in Lemma 8's
flat-kernel (leading-order) form, per-event at T(2 kappa sigma
sqrt(a)); epsilon_cens is not added.

Headline: **4,669 of 5,046 drift-admissible (kappa, abar) readings
satisfy |E - pi_J| <= RHS + Wilson.**  All 377 failures are marginal
(median exceedance margin 0.030, max 0.153) and concentrated at
kappa >= 6 (0 failures at kappa <= 4 for z0 >= 7.5; the kappa = 6
failures sit at z0 <= 7.5), i.e. where the doubled cut
2 kappa sigma sqrt(abar) reaches the scale on which the gap-occupation
kernel varies.  This is the flat-kernel form failing, not the
theorem: Lemma 8 states flatness as its leading-order reading
and Corollary 5 prescribes the estimated-kernel form exactly
there.  Degradation map, in one line: **the flat-kernel bracket is
reliable for kappa <= 4 across every planted regime, and at higher
kappa only when the jump scale clears the occupation-variation
scale (z0 >~ 20 sigma).**

Vacuous cells (RHS >= max(0.5, 2 pi_J)): 21 of 5,046, all at
z0 = 2 sigma with kappa = 2 (small-jump regimes at low cut, the
row-8 tick-discreteness corner of the bias budget).

Drift arm: at mu = 0.5 sigma per block, 30 readings violate the
theorem's admission |mu| abar <= (kappa/2) sigma sqrt(abar); the
bracket nevertheless held in all 30 (and in all mu = 0.1 sigma
cells, which are admissible).  No drift-driven failure was reachable
at these grids; the admission boundary is conservative here.

Consistency clause (kappa -> infinity, kappa sqrt(abar) -> 0):
block-quantised delay bounds sigma sqrt(abar) below by sigma, so the
strict joint limit is unreachable in any block world; the clause
manifests as convergence in the resolution ratio.  At alpha 2.5,
lam 0.012, period 1:

| cell | tail mass above doubled cut | \|E - pi_J\| |
|---|---|---|
| kappa 2, abar 2, z0 20 | 0.880 | 0.0013 (m = 210,357; statistically zero) |
| kappa 3, abar 20, z0 20 | 0.820 | 0.0126 |
| kappa 4, abar 10, z0 20 | ~0.75 | 0.0205 |
| kappa 12, abar 1, z0 20 | ~0.30 | 0.1474 (inside its bracket 0.4874) |

E -> pi_J exactly as the retained tail mass -> 1, and every diagonal
cell stays inside its bracket; the deviation at high kappa is the
resolution floor the second bracket term prices.

Tail-read (Hill) bias map, period 1, mu 0, o_ref = 2 z0, delays <= 2
(45 cells, n from 66 to 164,440): the read reproduces the ORDERING
of planted alpha everywhere but carries a systematic finite-o_ref
bias, upward except in the smallest-jump cells: alpha_hat - alpha
ranges +0.35 to +0.65 at z0 = 20 sigma, +0.2 to +0.5 at
z0 = 7.5 sigma, and -0.6 to +0.15 at z0 = 2 sigma (noise-dominated,
n small).  Production tail reads at o_ref = 2 z0 should be quoted
with this bias band, or o_ref pushed deeper where counts allow.
Representative row: planted 2.5 at lam 0.012 reads 2.48 / 2.90 /
3.15 at z0 = 2 / 7.5 / 20 sigma.

## Part B: jump surcharge (Proposition 17)

The Sharp Constant search's policy machinery at rho = 0.05 (exact mint arithmetic,
wandering price, horizon sigma_s sqrt(T) ~ 0.14 S0, 96 replicas,
step 0.004 h): centred renewal policies x in {0.3, 0.5, 0.72} under
one-sided upward jump regimes alpha in {1.6, 2.5, 3.5} x
z0 in {0.1 h, 0.3 h}, jump rate 2 sigma_s^2/h^2, sizes truncated at
20 h (stated; for alpha <= 2 the untruncated E[O_J] diverges, so
truncated readings understate the surcharge).  Beyond-range straddle
landings have L2 = 0 in the isolated class (one-sided holdings
cannot mint a price-containing equal-width range): infinite
log-cost, capped at k = 10 per event and counted.

Diffusive baselines (jump-free columns) calibrate the machinery:
measured c = 3.828 / 2.686 / 2.368 at x = 0.3 / 0.5 / 0.72 against
analytic 3.96 / 2.70 / 2.40 (-3.4 %, -0.5 %, -1.3 %).

Per-event law: the measured premium k(landed) - k(diffusive-
equivalent) matches the placement-potential form
ln(((1-x)h - O)/((1-x)h - O - O_J)) with mean absolute deviation
1.3e-3 to 4.5e-3 per event across all 18 cells (the deviation is the
O(rho) exact-vs-narrow correction, cf. the kernel check in
`../RUN-LOG.md`), and the return point cancels as the proposition
asserts.

Lower bound: r_J >= lam_J E[O_J]/h holds in all 18 cells, with
measured slack factor 1.9 to 7.0 (the bound is loose exactly as the
log form's convexity suggests).  Representative cells (c units of
sigma_s^2/h^2):

| x | alpha | z0/h | c_total | r_J measured | bound | beyond-range events (inside events) | capped-cost rate |
|---|---|---|---|---|---|---|---|
| 0.5 | 3.5 | 0.1 | 2.757 | 0.016 | 0.007 | 0 (67) | 0.000 |
| 0.5 | 2.5 | 0.3 | 4.970 | 0.447 | 0.128 | 83 (479) | 1.206 |
| 0.5 | 1.6 | 0.3 | 6.982 | 0.461 | 0.144 | 225 (524) | 3.270 |
| 0.72 | 1.6 | 0.3 | 6.840 | 0.281 | 0.042 | 240 (228) | 3.488 |

Heavy-tail degradation, stated plainly: at alpha <= 2 with
z0 = 0.3 h the ledger becomes corner-dominated; for the late trigger
x = 0.72 the beyond-range events OUTNUMBER the inside jump firings
(240 vs 228) and the capped corner rate (3.49) exceeds the entire
diffusive floor.  Since each such event's true isolated-class
log-cost is infinite, any jump law with support beyond h(1-x) gives
every band-maintaining isolated-class policy an infinite
log-dissipation rate; the finite numbers above exist only because
of the k = 10 cap and the 20 h truncation, and the value-flux
(g-form) ledger stays finite.  Flagged to the synthesiser as a
possible scope note on Proposition 17's beyond-range clause.

Additivity: r_total exceeds r_diffusive + r_J + r_beyond by 10-25 %
in the jumpier cells; the excess is sub-trigger jump motion adding
quadratic variation to the displacement, which the per-crossing
surcharge does not price.  The surcharge is per-event exact (the
premium rows above); the ADDITIVE decomposition of the total rate is
leading-order only.
