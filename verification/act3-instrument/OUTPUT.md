# Captured output: the instrument

Two kinds of artefact are captured here. The synthetic harness is the
act's dependency-free reference implementation and sits at the end of
this file. The eleven probes above it are the population read: they are
deterministic, with no RNG except probe 11, but they consume the
sender-keyed operator layer, a per-pool tick cache, and the census
cells, all path-parameterised through the environment and documented in
the header of `common.py`. Query order is fixed by sorted pools and an
explicit `ORDER BY block`, so repeated runs against an unchanged lake
reproduce these numbers exactly.

Probes 1 to 3 are ports of the empirical companion paper's probe
scripts. Their outputs were diffed field by field against that paper's
captured artefacts and match exactly, which is what licences treating
them as this paper's own surface. Everything below is a regression
target: a numeric shift is a manuscript-level event, and an extension
must preserve the walk order rather than reorder it.

## Probe 1: pooled overshoot and actuation (`probe_pooled.py`)

```
322 cells, 139,382 valid events, interior fraction 0.5411,
63,961 trigger firings.
overshoot (width units): q50 0.09, q90 0.23, q99 0.36
normalised tail: q90/q50 2.05, q99/q50 3.80
  (half-normal benchmark 2.44 / 3.82)
delay (blocks): n 56,167, censored 0.1219, q50 529, q90 7,710, q99 17,403
diffusive scaling: med[over^2/delay] short 2.00, long 0.175, ratio 0.088
jump signature (naive): 63 fast-large events, 0.0011 of measured
per-operator median delay: q10 66.5, median 1,505.5, q90 7,643.5
```

Reading: the negative baseline. Pooled overshoots match
diffusion-with-lag almost exactly, and overshoot is roughly
delay-invariant at 0.088, which is the threshold-and-dwell gating
signature of the delay-invariance dichotomy. The naive pooled
inversion is dead, and the manuscript says so.

## Probe 2: fast strata and near-zero delay (`probe_fast.py`)

```
all events tail: q99/q50 3.80 (n 63,882)
fast strata q99/q50: <=50blk 4.34 (2,493 ev), <=100blk 4.33 (3,268 ev),
                     <=300blk 4.72 (16,367 ev)
near-zero-delay ratio (era sigma): <=2blk fraction>3 = 0.0433 (n 1,292),
  q99 6.53; <=5blk 0.039; <=10blk 0.0433  (folded-normal baseline 0.0027)
```

Reading: the positive baseline. Fast strata fatten past the
half-normal benchmark, and the near-zero-delay excess is sixteen times
the folded null even under an era-average scale.

## Probe 3: window-local scale (`probe_localsigma.py`)

```
4,845 near-zero-delay events.
1d trailing sigma: <=2blk median 1.23, q99 11.69, fraction>3 0.2009
                   <=5blk 0.2235, <=10blk 0.2147 (q99 13.4-14.0)
7d trailing sigma: fraction>3 0.18-0.19, q99 11.9-12.3
era sigma        : fraction>3 0.039-0.043 (the conservative variant)
```

Reading: with the scale local and the candidate jump excluded, 18 to
22 per cent of near-zero-delay overshoots exceed three local standard
deviations against a null of 0.27 per cent. The era-average pass was
conservative, because era scale is inflated by the volatility bursts
themselves. This is the first evaluation of the exceedance estimator.

## Probe 4: within-pool fast-versus-slow contrast (`probe_withinpool.py`)

```
50 census pools: 11 host both strata, 7 fast-only, 30 slow-only
(fast = op median delay <=100 blk, slow = >=300 blk, mid excluded).

both-strata pools, 1d sigma, delay<=10blk:
  fast stratum: n 1,010, median 1.31, q90 3.35, q99 8.26, fraction>3 0.1436
  slow stratum: n   940, median 1.11, q90 4.08, q99 10.13, fraction>3 0.1713
  (delay<=2blk: fast 0.0857 / slow 0.2040; era-sigma variants 0.008-0.019)
fast-only pools, fast stratum, <=10blk: n 117, fraction>3 0.2735
per-pool paired (>=15 events each stratum): 3 pools qualify;
  2 show both strata in excess, 0 fast-only, 1 slow-only (n_fast 17).
normalised tails within both-strata pools: fast q99/q50 4.33 (2,800 ev),
  slow 3.22 (15,178 ev).
```

Reading: the contrast replicates, the fast-stratum excess of 0.1436
being fifty-three times the folded baseline against a pre-specified
tenfold criterion, and the signal is pool-common. The slow stratum's
own near-zero-delay events in the same pools carry excess of the same
order, 0.1713, which is what the forward map predicts if the excess is
a property of the pool's price law rather than of the fast operators.
The slow stratum's small-delay events are in fact slightly more
jump-loaded, which is jump enrichment operating: heavier policy filters
thin the diffusive branch super-polynomially at small delay, so a
filtered operator's rare fast firings are nearly pure jump. Pool-level
selection is real, fast-only pools running hotter at 0.2735 on small
counts, so population aggregates keep the pool-census framing and
per-pool claims stay clean. Two cautions: eleven both-strata pools with
event mass concentrated, 587 of the 940 slow near-zero events sitting
in one pool, and only three pools clearing the paired threshold. This
is why the design reads cross-stratum agreement rather than subtracting
one stratum from the other.

## Probe 5: per-pool tail functionals and the geometry census (`probe_perpool.py`)

```
4,793 scored events across 33 pools (delay<=10blk, 1d sigma; the count
matches probe 3's 1d <=10 cell exactly, the intended cross-check).
population: fraction>3 = 0.2147, Wilson95 [0.2033, 0.2265]
  -> jump-share estimate 0.213
16 pools with n>=30: fraction>3 spans 0.0581 [0.0349, 0.0951]
  to 0.5224 [0.4049, 0.6375]; 17 small pools combined 0.4513 (n 113)
agreement tests (fast vs slow, Fisher exact, >=5 events/stratum):
  6 pools; p = 0.0268, 0.0305, 0.0574, 0.1804, 0.2096, 1.0
  -> 2 nominal rejections, 0 after Bonferroni (0.05/6)
geometry census: k=1 in 24 of 50 pools; k>=2 in 26; k>=3 in 19
  (max 58 distinct scales in one pool)
```

Reading: per-pool tail readings differ far beyond binomial noise, so
the per-pool functional is a real object and cross-pool pooling is
forbidden. Pool-commonality holds broadly under multiplicity
correction, the two low-p cells being localisation flags rather than
refutations. The geometry-count conditionality of multiscale
identification is confirmed binding: the multiscale probe exists in
under two fifths of pools.

## Probe 6: tick-stream jump validation, realised against bipower (`probe_jumpvalidation.py`)

```
39 pools with usable tick streams (dense per-block displacements,
trailing 1d scale, candidate excluded).
RV/BV inflation: median of pool medians 1.198
jump rate beyond 3-cut (BV): pool median 0.334, q90 0.600
jump sizes: per-pool q50 spans ~4.7 to 32.5 sigma (quiet pools at the
  top: one-tick quanta over tiny sigma)
cross-pool validation vs probe 5 fraction>3: Spearman -0.035 (16 pools)
coverage note: swaps_topN.parquet holds 2/50 census pools and blocks
  24.0M-36.5M vs the census era 44.0M-49.2M, zero overlap; the tick
  cache is the tick-stream source.
```

Reading: three findings. The realised-variance scale is inflated about
twenty per cent by within-window jumps, so every captured excess number
is conservative, and the manuscript's estimator is bipower for that
reason. The tick stream is heavy-tailed against trailing-window
diffusion in every pool at the same order as the firing-based excess,
so the firing-based signal reads the price law rather than operator
artefacts. The cross-pool rank validation fails, and is reported as a
disagreement rather than dropped: the per-block detector is
discreteness-dominated in quiet pools and ranks quantisation, not jump
mass. That failure is what put the tick-discreteness admission into the
bias budget as its eighth row; a crossing-conditioned validator is the
open item.

## Probe 7: era-half replication, the (F1) certification (`probe_erahalf.py`)

```
census era split at block 46,592,601.
population: h1 fraction>3 = 0.2250 (n 2,329)
            h2 fraction>3 = 0.2050 (n 2,464)
6 pools with n>=30 in both halves; Fisher two-sided per pool:
  p = 0.8072, 0.0075, 0.4456, 0.0004, 0.0004, 0.5130
  -> 3 nominal rejections, 3 after Bonferroni (0.05/6)
```

Reading: the population-level reading replicates across era halves;
the per-pool functional does not, in half the testable pools. (F1) is
certified as a per-pool admission criterion rather than a blanket
property. Three pools carry significant half-to-half drift, a jump
regime or a policy change inside the era, and their per-pool readings
are per-half statements. The manuscript's era discipline is confirmed
binding at finer-than-era scale.

## Probe 8: (F4) exceedance-shape invariance (`probe_shapeinvariance.py`)

```
both-strata pools with exceedances in both strata: 5.
fast exceedances n 50: q50 3.90, q90 6.48, q99 12.40
slow exceedances n 35: q50 3.94, q90 6.49, q99 24.59
two-sample KS: D = 0.1714, p = 0.54
```

Reading: the refutable implication of (F4) survives its first run,
with no shape difference between cadence strata; the two lower
quantiles are nearly identical and the q99 gap is one order statistic
at these counts. Power is limited by eighty-five total exceedances. The
test is specified and captured, and is cheap to rerun as the census
grows.

## Probe 9: bipower rerun of the scale columns (`probe_bipower.py`)

```
population (1d trailing BV vs captured RV), fraction>3:
  <=2blk 0.2768 vs 0.2009 | <=5blk 0.3040 vs 0.2235
  <=10blk 0.2992 vs 0.2147
7d BV: 0.2496 / 0.2635 / 0.2643 (RV 0.1931 / 0.1829 / 0.1809)
per-pool (1d, <=10blk, n>=30): BV >= RV in 13 of 16 pools;
BV span 0.0000-0.6000 (RV captured span 0.0581-0.5224; pool sets
differ slightly with estimator-specific sigma availability)
```

Reading: the designated bipower estimator raises every population
cell, to 25 or 30 per cent against realised variance's 18 to 22, in
the direction and roughly the magnitude that the measured inflation of
1.198 predicts. The captured realised-variance columns are confirmed
conservative, so the manuscript's statement about estimator choice
rests on a run rather than a prediction.

## Probe 10: independent-provenance cross-check (`probe_provenance.py`)

```
6 census pools shared with the position-manager extension parquets; 5
checkable (555,020 shared census-era blocks).
per-pool exact match 0.85-0.96; within one tick 0.91-0.99
(closing-tick convention verified: opening-tick recomparison is
strictly worse, 0.63 exact on the largest pool).
one outlier: 0x85fb468a max |diff| = 701,671 ticks (corrupted row
or scale artefact in one source; flagged, not diagnosed here).
```

Reading: two independent indexing paths agree within one tick on 91 to
99 per cent of half a million shared blocks, which answers the
tick-stream provenance question with no systematic bias. Residuals
concentrate at tick-boundary rounding. The single gross outlier is a
data-quality flag carried back to the indexer, not a finding here.

## Probe 11: per-pool c_tick from real trade sizes (`probe_ctick_real.py`)

```
6 census pools with swap-level trade data; bulk move law per pool
(99.5 % tail cut), compound-Poisson null at the harness grid:
  fine-trade pools (bulk cut 4-6 ticks):   c_tick = 8, 8
  mid (cut 20 ticks):                      c_tick = 32
  coarse (cut 31-421 ticks):               c_tick > 32 (never
    reaches 2x baseline on the grid)
spurious rate declines monotonically with the scale ratio in every
pool (the harness's monotonicity, reproduced on real trade laws).
```

Reading: the synthetic c_tick of sixteen is mid-range, conservative
for fine-trade pools and not conservative for chunky-trade pools. The
bias budget's eighth-row admission is therefore genuinely per-pool
wherever swap-level data exists, and pools with coarse trade laws
admit no small-delay reading at production scales. Coverage is capped
at the six extension-covered pools; extending it needs swap-level
indexing for the remaining census pools.

## The synthetic harness: `mc_harness.py`

`python3 mc_harness.py`, seed 37, run 2026-08-10, 1.5 s on the
reference machine. Standard library only, no on-chain data, per-check
independent seeding so that an edit to one check never shifts
another's draws.

```
[1] delay-law mixture reproduces the overshoot density (Owen-T identity): max rel err over 7 points = 6.33e-15
[2] flat-entry kernel and delay law (exact sampler): n = 49415, KS: overshoot 0.0049, delay 0.0037, folded ratio 0.0043
[3] planted jump-share inside the small-delay bracket (bipower pipeline): m = 4500, w_hat = 0.336, truth = 0.540, bracket [0.248, 0.557] (floor factor 0.52)
[3b] Hill recovery of planted alpha from exceedance sizes: alpha_hat = 2.711 (planted 2.5), n_exceed = 224
[4] penetration delay-invariance vs lag diffusive scaling: penetration med[O^2/a] long/short = 0.033 (<0.35), lag = 2.317 (in [0.5, 3])
[5] penetration filter jump-enriches the small-delay sample: jump share <=2blk: penetration 0.847 (n 932), plain 0.541 (n 5039)
[6] Fisher agreement test holds nominal size on common-p nulls: rejection rates at 0.05: (100,100): 0.045, (30,500): 0.043
[7] discreteness sweep delivers c_tick (spurious <= 2x baseline): spurious rates 1:0.5210, 2:0.2642, 4:0.0697, 8:0.0158, 16:0.0051, 32:0.0011; c_tick = 16
[8] Cox checking shifts jump-share level, not tail shape: w_share: cox 0.605 (n 4473) vs poisson 0.521 (n 3700); alpha_hat: cox 2.796 (n_exc 281) vs poisson 2.866 (n_exc 159)
(1.5 s)
all checks passed
```

Reading of each line.

1. The integral identity behind the flat-entry delay law holds to
   machine precision under smooth quadrature, the substitution
   a = sin^2(theta) killing both endpoint singularities. The delay law
   marginalises exactly to the overshoot density of the first act.
2. The joint delay-and-overshoot law is confirmed by exact Lévy
   first-passage sampling with no path discretisation. All three
   Kolmogorov-Smirnov statistics sit at the sampling floor at
   n = 49,415.
3. The full pipeline, threshold operator, trailing bipower scale with
   candidate exclusion, and the exceedance and jump-share estimators,
   recovers the planted jump share inside the small-delay bracket. The
   realised-variance variant fails this check by design: the planted
   world's jump variance share, about seventy-seven per cent, inflates
   it roughly twofold, which is the bias budget's third row made
   visible and the reason the manuscript's estimator is bipower.
4. The delay-invariance dichotomy in one world. The penetration
   operator's overshoot is delay-invariant at a ratio of 0.033, the
   synthetic analogue of the population's 0.088, while the lag
   operator scales diffusively at 2.3. Long-delay survivors are
   meander-conditioned, which is why the diffusive ratio sits near two
   rather than one. A dwell-in-time rule under dense checking clusters
   the actuation time at the dwell value instead of spreading it, so
   the population figure mixes operator clusters and the per-operator
   scan needs the penetration form.
5. Jump enrichment quantified: 85 per cent of the penetration
   operator's two-block firings are jump crossings against 54 per cent
   for the plain operator. The gap to a hundred is real rather than
   estimation error, because a diffusive crossing followed by a second
   jump inside the delay window fires the filter carrying a diffusive
   crossing label.
6. The agreement test is honest at the stratum counts probe 5 works
   with: empirical size 0.043 to 0.045 at a nominal 0.05.
7. The discreteness admission constant. Under a trade-quantum null,
   compound-Poisson counts with signed geometric moves averaging two
   ticks, a rounded diffusion being unable to reproduce the pathology,
   spurious exceedance falls monotonically and crosses twice baseline
   at a scale ratio of sixteen. That constant belongs to this
   trade-size model and scales with the per-trade move distribution,
   so per-pool application either measures that distribution, as probe
   11 does, or uses sixteen conservatively.
8. The (F4) split. Cox checking, densified for two blocks after any
   jump, raises the small-delay jump share from 0.521 to 0.605 while
   the recovered tail index moves by 0.07, inside noise. Levels are
   check-weighted and shapes are clean, which is what (F4) asserts.
