# Captured output: the MEV probe

Run 2026-08-10. `mev_probe.py --chain ethereum` and
`--chain base`, one code path over one wall-clock era; artefacts
`mev_probe_ethereum.json`, `mev_probe_base.json`. Its readings are
quoted in the manuscript's numerical-verification section, in the
paragraph on whether the event leg is somebody else's revenue.
Uniswap V3 on two public chains, no population-census join and no data
lake writes. This file is a regression target.

The probe was written to answer one question before any census-scale
mainnet work is chartered: is the instrument reading the same object on
a chain with proposer-builder separation and an extraction industry as
it reads on Base, which has neither? Four readings, on three matched
pool pairs, over 120 days ending inside the census era.

Windows: Base blocks 44,000,000-49,200,000 (120.4 days, 2.000 s), main-
net blocks 24,763,430-25,626,973 (119.9 days, 12 s). Pairs are
WETH/USDC at 500 and 3000 and the BTC/WETH 3000 book, whose Base leg is
cbBTC and whose mainnet leg is WBTC.

## The four readings

| | Base | Mainnet |
|---|---|---|
| position events | 2,002,351 | 42,150 |
| trigger firings | 189,207 | 1,086 |
| A interior fraction | 0.4291 | 0.2186 |
| A firing position u, q10 / q50 / q90 | -0.09 / 0.522 / 1.102 | -0.031 / 1.350 / 2.425 |
| B exit delay, median blocks | 213 | 331 |
| B exit delay, median seconds | 426 | 3,972 |
| B exit delay, q90 seconds | 7,114 | 139,188 |
| B share re-placed within one block | 0.1046 | 0.1273 |
| C own corrective swap share | 0.180 | 0.218 |
| C backrun, observed / null | 0.969 | 0.518 |
| C frontrun, observed / null | 0.966 | 1.406 |
| C sandwich, observed / null | 0.808 | 0.771 |
| D JIT share of position events | 0.0024 | 0.1288 |
| D same-range re-mint share | 0.1789 | 0.0424 |

## What it says

**Rebalances are not being backrun or sandwiched, on either chain.**
Every adjacency ratio against the within-block null is at or below one:
Base 0.969 and 0.808, mainnet 0.518 and 0.771. Raw shares alone would
have suggested otherwise (mainnet's raw frontrun share is 0.39), which
is why the null is the reading and the raw share is not. The
extraction industry is not, on this evidence, operating on the
rebalance boundary of these books. For the manuscript this is the
useful direction: the dissipation the paper prices is not an artefact
of somebody taking the other side of it.

**Mainnet firings are placed late in their block.** The one ratio above
the null anywhere is mainnet's frontrun at 1.406, with backrun
correspondingly at 0.518. Rebalances there sit after most of the
block's swaps, which reads as low-priority ordering rather than
extraction, and has a convenient consequence: the mint executes near
the block's closing price, which is what the tick-cache convention
(last Swap tick per block) already assumes.

**JIT liquidity is a mainnet problem and only a mainnet problem**,
0.24 % of Base position events against 12.88 % of mainnet's, a factor
of 54. Any mainnet census must classify and exclude it, and report the
count, or its population is inflated by positions that exist for one
block. The mirror image is that same-range re-minting, which is fee
compounding, is four times commoner on Base (17.9 % against 4.2 %):
each chain contaminates the census in its own way, and the ordering of
the mint and the burn inside the block is what separates the two. That
distinction is not cosmetic; conflating them reverses the answer,
which is exactly what an earlier run of this probe did before the
ordering was used.

**The two chains' clocks disagree about which clock to use.** Median
exit delay is 213 Base blocks against 331 mainnet blocks, a factor of
1.6, but 426 seconds against 3,972 seconds, a factor of 9.3. The q90
gap is wider still, two hours against thirty-eight. A delay-cut
equivalence test that matches abar/6 in blocks would look approximately
matched on the block clock while comparing populations whose actual
behaviour differs by an order of magnitude in time. **Tier M3 must
state which clock it matches on, and defend it, before the test is
run.** The threat is real, and it is not the one anticipated:
it comes from operator cadence, not from atomic backrunning, which the
adjacency null has just ruled out.

**Overshoot is fatter on mainnet, not truncated.** The median firing
sits at u = 1.35, a third of a range-width beyond the old range's far
edge, against 0.522 on Base, which is the range's midpoint; interior
firings are 21.9 % against 42.9 %. Mainnet operators let price run well
past their range before re-placing. This **contradicts** the prediction
that efficient backrunning would correct faster and truncate overshoot. The
observed direction is the opposite and the adjacency null supplies the
reason: there is no extra correction to truncate anything, so what the
gap measures is how long operators wait, which at 12-second blocks and
mainnet gas is a great deal longer.

## Consequences

For the mainnet arm: M1 and M2 are unaffected. M3 needs the clock
decision above, and needs a JIT filter before any mainnet census.
Nothing here argues against running the arm; the extraction confound
that would have argued against it has been measured and is absent.

For the manuscript, nothing yet: this is probe-level evidence on three
pairs, and no sentence should cite it until the arm proper runs.

## Method notes

Reading B's delay is at least one block by construction on both
chains: the tick cache holds one entry per block and is searched
strictly before the firing block, so a same-block correction cannot
appear in it. Reading C, which orders by log index inside the block, is
where the same-block question is settled. The two chains use the same
construction, so the distributions remain comparable above zero.

Reading C's null conditions on the block's own external swap count s: a
firing inserted at a uniformly random position among the s + 1 gaps has
P(before) = P(after) = s/(s+1) and P(both) = (s-1)/(s+1). Summing over
firings gives the expected counts quoted. Excess over the null is
placement; agreement is ambient traffic.

`base_local_ab.py` computes A and B from the local layer instead of the
stream. It is retained as a cross-check but is **not** the comparison
basis: the layer's `rebalances` table includes same-range re-mints,
which are interior by construction and are not trigger firings, so it
reads interior fraction 0.582 where the streamed trigger-firing
definition reads 0.429. The streamed number is the comparable one.
