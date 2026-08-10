# Captured output: the Ethereum mainnet arm

Run 2026-08-10. This is the eighth verification surface of the
manuscript: the fork track appears in the paper's fork-suite section
and in `foundry/PROOF_OUTPUT.md`, and the third-party identity, the
two-sided floor scatter and the mainnet limitations appear in its
numerical-verification and limitations sections.
Artefacts here: `m2_summary.json`, `m3_results.json`, `discovery.json`,
`m2_pools_uni.json`, `pool_verification.json`. The two stream blobs
(`m2_cells.json.gz`, `m2_ticks.json.gz`, 11 MB) are not vendored; see
`README.md` for how to regenerate them at the pinned window.
Uniswap V3 on two public chains, no population-census join and no data
lake writes. This file is a regression target.

## M1: the fork suite, passed 4/4, full suite 20/20

The exact layer asserted against the unmodified Uniswap V3 NFPM on
Ethereum mainnet, WETH/USDT fee 500, tick spacing 10, pinned block
25,200,000 inside the era pin. Corner ratio agrees to the wei
(19,991,090,753 on both sides), the identical re-placement on the free
locus costs zero raw units where Base costs one, and the amplitude
gaps run 12 to 44 ppm, the same band as the Base Uniswap V3 track at
the same spacing. The exact layer now holds against deployed code on
three V3-class deployments across two chains, plus the Liquidity Book
on a third.

**Pair choice was forced, and the first attempt failed for a reason
worth recording.** Mainnet USDC/WETH fails all four tests, not because
the law fails but because the suite's tolerances are absolute token1
raw units calibrated for a six-decimal token1; mainnet USDC sorts below
WETH, putting the eighteen-decimal asset in the token1 role, and a few
wei of mint rounding then reads as order 1e8 raw units. WETH/USDT
reproduces Base's 18-over-6 decimal shape so the tolerances mean the
same thing on both chains. USDT returns no data from `transfer` and
`approve`, hence the `_send`/`_approve` helpers now in
`ExactLayerForkBase`. Those helpers and the by-role `tok0`/`tok1`
fields are the only changes to the shared base; the Base and Avalanche
captures reproduce to the wei under them, verified before and after.

## M2: the third-party reading

### The pool set had to be discovered, and eight venues excluded

The majors-only pool set produced 2,450 firings over the
era, four cells at the firing bar and **zero** clean identity events.
A discovery pass over all Uniswap V3 pools by topic (24 windows,
72,000 blocks, 8.3 % of the era) found 973 firings across 143 pools,
with the expected majors already at the top: mainnet ALM is not hiding
elsewhere, it is **about thirty times rarer than Base's**
(roughly 11,700 firings era-wide against Base's 364,098).

Of the 55 busiest pools, **47 are in the Uniswap V3 factory and 8 are
not**: they carry V3 event signatures but belong to forks. They are
excluded rather than mixed in, which is the error the Base census made
and had to be qualified for afterwards.

On the 47 verified pools: **8,318 firings, 5,027 priced, 795 cells,
29 cells at the 30-firing bar**.

### The identity holds on a third venue

**22 isolated third-party re-placements, median |k_real - k_pred|
= 7.9e-17, q99 and max 2.0e-14.** Machine precision, matching the Base
readings (345 events at median 1.1e-16 on Uniswap V3 Base, 253 at
1.1e-16 on Slipstream) and the production anchor (5.7e-17 on 78,908
events). The share-potential identity is now evidenced on three venues
across two chains.

### The premise for the floor scatter was wrong

The arm's third objective expected mainnet to make the corrective swap observable and
so turn the Base lower bound into a measurement. Only **32 %** of
mainnet firings carry their swap in the same pool; the rest route it
through an aggregator, so the value chain leaves the pool and cannot
be closed from its logs at all.

The two subpopulations are not noisy versions of each other, they are
identified and unidentified:

| population | share conserving value | median k |
|---|---|---|
| all priced firings | 24 % | **-0.255** (value rising) |
| swap-carrying firings | 81 % | **+2.5e-4** |

So the two-sided measurement does exist on mainnet, on the swap-carrying
fifth to third of the population rather than on all of it. M3 restricts
to it by construction and reports both counts.

## M3: the floor scatter, two-sided

Seven cells clear the bar: 7 pools, 3 operators, 566 swap-carrying
firings, spans 18 to 115 days.

| floor at | cells above 1 | median score | q10 | q90 |
|---|---|---|---|---|
| uniform eta = 1e-4, as the anchor figure | **7 / 7** | 57.6 | 2.35 | 820 |
| the pool's own fee tier | 6 / 7 | 3.52 | 0.47 | 8.20 |

Unlike the Base surface this is a measurement, not a lower bound: the
mark is pre-swap, from the swap's own constant-liquidity arithmetic,
and the fee leg is on the input side. Every cell sits above the uniform
fee-only floor; one sits below its own fee tier and is reported as it
falls. The sample is small and is not a census.

## M3: the clock, declared

The MEV probe found exit delays 1.6x apart in blocks and 9.3x apart in
seconds between the chains, so a delay cut cannot be matched on both
clocks and the choice must be stated rather than defaulted into.

**The cut is matched in wall-clock seconds.** Theorem 6
bounds how far the price can move while the operator is uncorrected,
which is a statement about elapsed time and diffusion, not about the
chain's accounting unit. Base's abar = 10 blocks is 20 seconds, so the
mainnet cut is **1.67 blocks**, against 10 if one matched on blocks
instead. Both are recorded in `m3_results.json` so the choice is
auditable.

The consequence is worth stating plainly: at 12-second blocks a
wall-clock-matched small-delay class is under two blocks wide, so the
mainnet delay-cut equivalence test is **not powered** on this
population and is not attempted here. That is a property of the block
time, not a failure of the instrument.

## Not done, and why

- **The c_tick admission.** `m3_analysis.py` reports the realised
  per-block tick move, which is the numerator the cross-venue admission
  needs, but not the admission: that compares against c_tick from the
  Base census's quantised-walk simulation. The numbers here must not be
  quoted against the cross-venue section's 1.2-9.8 ratios. Porting the simulation is the
  remaining work.
- **The delay-cut equivalence test**, for the power reason above.
- **A mainnet census.** 29 cells at the firing bar will not carry one,
  and the JIT filter the MEV probe showed to be necessary (12.9 % of
  mainnet position events) is not implemented in this pass.

## What the arm bought

The manuscript-relevant results are M1 and the identity: the exact
layer and the share-potential identity now hold on a third deployment
and a second chain, at 12-second blocks and under a different
sequencing regime. The floor scatter is two-sided but small. The
population tiers are blocked by mainnet ALM sparsity, which is a fact
about the venue rather than a gap in the method, and is now measured
rather than assumed.
