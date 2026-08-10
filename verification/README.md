# Verification harnesses

Five of the paper's eight verification surfaces live here. The other
three are the Foundry fork suites in [`../foundry/`](../foundry/)
(surfaces five and six, and the mainnet track of surface eight), the
synthetic calibration surface in
[`../calibration/`](../calibration/) (surface seven), and the reading
half of the mainnet arm in [`mainnet/`](./mainnet/) (surface eight).

Each act of the paper ships its own reference implementation at a
fixed seed. Those three are standard-library Python with no
dependencies, no network access, and no on-chain input, so they run
anywhere Python 3 runs. The fourth surface, the production anchor,
evaluates the first two acts against an operator's recorded rebalance
history and therefore needs the event lake; it is reproducible where
the lake is, not everywhere.

Every folder carries an `OUTPUT.md` holding the captured run. Those
captures are the regression targets: a numeric shift in any of them is
a manuscript-level event, because the paper's §Numerical verification
quotes them directly.

| Folder | Surface | Seed | Inputs | Runtime |
|---|---|---|---|---|
| [`act1-law/`](./act1-law/) | the forward law | 29 | none | ~16 s |
| [`act2-floor/`](./act2-floor/) | the floors | 31, 229 | none | ~26 s, ~30 s |
| [`act3-instrument/`](./act3-instrument/) | the instrument | 37 | none (harness); event lake (probes) | ~2 s |
| [`anchor/`](./anchor/) | the production anchor | none, deterministic | event lake | ~2 min |
| [`mainnet/`](./mainnet/) | the Ethereum mainnet arm | none, pinned by block window | public SQD portal | minutes to hours |
| [`third-party/`](./third-party/) | third-party identity anchors | none, deterministic | public chain logs | minutes to hours |

## Quick start

```bash
cd act1-law        && python3 mc_harness.py     # 6 checks, ends "all checks passed"
cd ../act2-floor   && python3 verify_floor.py   # 10 checks, ends "all checks passed"
cd ../act3-instrument && python3 mc_harness.py  # 8 checks, ends "all checks passed"
```

Each script exits nonzero on a failed check and prints the failing
line, so the three are usable as a regression gate without reading the
captured output.

## act1-law: the forward law

`mc_harness.py` (seed 29) runs six checks against the first act. The
two-branch amplitude is checked against the venue's mint-minimum
arithmetic over twenty thousand random parameter draws with both
branches evaluated; the corner values and the down-branch monotonicity
threshold follow from the same sweep. The pathwise dissipation
identity is asserted on a simulated path with 250 impulses, where it
holds to machine precision rather than to discretisation error,
because the holding value is piecewise quadratic in the square-root
price coordinate. The last two checks exercise the occupation-offset
bound together with the monitoring dichotomy, near-continuous
monitoring concentrating the firing offset and coarse monitoring
restoring uniformity, and the scale-function direction split.

## act2-floor: the floors

Two artefacts. `verify_floor.py` (seed 31) is the reference harness,
ten checks in about twenty-six seconds. It asserts the algebraic layer
first, the placement-family potential identity, the share-potential
identity, and the free locus, then the floor layer, the corridor
constants, the centred Monte Carlo sweep, the renewal grid, the
widen-slide adversaries against the width-uniform floor, the clock and
drift bounds, and the swap class with its edge-hugging limit and
return-point policies. A policy measured below its class floor fails
the run rather than being reported.

`probe_bound.py` (seed 229) is the scoping probe that preceded it. It
simulates the centred fixed-width family at four triggers, matches the
exact coefficient within three per cent, then grid-searches the full
three-parameter renewal family analytically. It is kept because the
paper quotes its minimum and because the two artefacts reach the same
constant by different routes.

## act3-instrument: the instrument

`mc_harness.py` (seed 37) runs eight checks against the third act, each
with an independently seeded generator so that a later edit to one
check never shifts another's draws. It asserts the delay-law mixture,
confirms the joint flat-entry law by exact Lévy first-passage sampling
with no path discretisation, recovers a planted jump share and a
planted Pareto tail index through the full estimation pipeline,
separates a penetration operator from a lag operator by the
delay-invariance dichotomy, measures jump enrichment, holds the
agreement test at nominal size, and runs the discreteness and
jump-checking sweeps.

The lake-reading surfaces resolve their inputs through two variables:
`LAKE_DIR`, the directory of recorded position-manager events, and
`LAKE_LAYOUT`, a JSON file naming the members that directory holds.
Neither the lake nor its file naming is published, so those surfaces
do not run from a clean clone; each one's captured `OUTPUT.md` is the
answer it produced, and every surface that does not read the lake runs
anywhere.

The `probe_*.py` scripts in the same folder are the population read.
They are deterministic but not dependency-free: they consume the
sender-keyed operator layer, a per-pool tick cache, and the census
cells, all path-parameterised through the environment and none of them
copied into this tree. `common.py` carries the loaders and estimators
they share and documents the three inputs. Their captured artefacts
are under `results/`.

Operators are identified in those artefacts by a stable pseudonym,
`op_NNNN`, rather than by address. The same convention holds in the
mainnet arm's `m3_results.json`. Every reported number is the
identified one; only the key differs, and the mapping is held back.
Pool, token and position-manager addresses are not obscured anywhere:
they are public contracts and identify nobody.

## anchor: the production anchor

`anchor.py` evaluates the first two acts against 135,538 recorded
rebalances from a production position manager, with no synthetic
input. It has no RNG. Three evaluations run: the share-potential
identity per event against the same event's amounts, the realised
dissipation rate per pool against the swap-mediated floor with the
local volatility and the execution cost measured from the pool's own
streams, and the deployed trigger and correction convention against
the renewal-family optimum.

The captured output records the standing caveats, chief among them
that the amounts window covers the first fifty-three days of the era,
that gas is excluded from the realised rate and reported separately,
that the volatility is five-minute realised rather than bipower, and
that the execution-cost anchor is uniform across pools where the true
fee tiers differ.

## third-party: the identity on other operators

`third-party/` holds two readings of the share-potential identity on
third-party operators, one across both Base V3 deployments over the
census era and one on the Liquidity Book on Avalanche. They are
evidence inside the existing surfaces rather than a surface of their
own: the V3 reading extends the production anchor beyond the single
operator it records, and the Liquidity Book reading pairs with the
fork suite that carries the discrete-bin algebra.

Both read public chain logs only, with no lake and no census join.
Operators carry `op_NNNN` pseudonyms and per-sequence transaction
hashes are withheld, since a hash would recover the sender the
pseudonym hides. See that folder's `README.md` for inputs and its
`OUTPUT.md` for the captured numbers.

## Provenance

The three act harnesses were written against the three source
manuscripts that the paper consolidates and keep their original seeds
and draw orders, so their captured numbers are unchanged by the
consolidation. Where code is shared with
[`../calibration/`](../calibration/) it is shared by copy with the
owner named in the copying file's header, per the programme's rule
against symlinking between surfaces.
