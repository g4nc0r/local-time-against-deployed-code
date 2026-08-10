# Local Time Against Deployed Code

Paper source and verification code for *Local Time Against Deployed
Code: The Exact Cost Law of Concentrated Liquidity Rebalancing, Its Sharp
Floor, and Its Inversion* (K. R. Ryan, 2026).

A concentrated liquidity manager watches a price and acts when a coded
condition fires. Every such condition is a line in price space, and so
is every floor function in the placement arithmetic, every threshold in
the sizing rule, and every range bound at which a holding value changes
slope. Seen from the price process, deployed market code is a locally
finite set of surfaces, and the value that automated liquidity
management surrenders is generated where the price meets them. The
paper studies that object in three movements. It proves an exact
pathwise dissipation identity whose per-event cost is a potential
difference in the position's composition coordinate, computed from the
venue's mint arithmetic rather than assumed as a market friction. It
bounds every band-maintaining policy from below by that cost, with an
absolute constant, and shows that variable width, corrective swaps, and
jump crossings do not evade the form. And it inverts the law, reading
the population of deployed trigger lines as a threshold detector whose
overshoots and actuation delays are observables of the price law,
including the jump measure that diffusive treatments set aside.

| | |
|---|---|
| **Author** | K. R. Ryan, independent researcher |
| **Contact** | [gancor.xyz](https://gancor.xyz) · ORCID [0009-0004-6295-7040](https://orcid.org/0009-0004-6295-7040) · code and reproduction questions via [GitHub Issues](https://github.com/g4nc0r/local-time-against-deployed-code/issues) |
| **Companion papers** | [*The Geometric Siphon* (SSRN 6686798)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6686798) · [*The Hidden Microstructure of Shared Balance Concentrated Liquidity* (SSRN 6745218)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6745218) · [*Operator & Quantisation Microstructure* (SSRN 7166739)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7166739) · [*Operator Fingerprinting* (SSRN 7202340)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7202340) |
| **Code DOI** | [![DOI](https://zenodo.org/badge/1329266037.svg)](https://doi.org/10.5281/zenodo.21871949) - verification code and Lean formalisation |
| **Python** | 3.11 or later; standard library only for the three act harnesses |
| **Foundry** | `forge` ≥ 1.5; Solidity 0.8.26 |
| **Lean** | 4.32.2 via elan; mathlib pinned in `lean/lake-manifest.json` |
| **Licence** | code MIT (`LICENSE`); paper PDF and LaTeX source © K. R. Ryan, all rights reserved |

**Status.** Preprint submitted to SSRN as
[7259078](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7259078);
the SSRN preprint is the citable record, and an immutable archival
snapshot of this repository is on Zenodo at
[10.5281/zenodo.21871949](https://doi.org/10.5281/zenodo.21871949).
The paper's code-availability section names both, so they should be
kept in step.

## Paper

| Title | Where | Status |
|---|---|---|
| Local Time Against Deployed Code: The Exact Cost Law of Concentrated Liquidity Rebalancing, Its Sharp Floor, and Its Inversion | [SSRN 7259078](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7259078); source in `paper/` | Submitted to SSRN |

## Citation

```bibtex
@techreport{ryan2026localtime,
  author      = {Ryan, K. R.},
  title       = {Local Time Against Deployed Code: The Exact Cost Law of
                 Concentrated Liquidity Rebalancing, Its Sharp Floor, and
                 Its Inversion},
  institution = {SSRN},
  number      = {7259078},
  year        = {2026},
  doi         = {10.2139/ssrn.7259078},
  url         = {https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7259078}
}
```

## Eight verification surfaces

The paper's claims are asserted on eight surfaces. Five are
Python, two are Foundry fork suites against unmodified production
bytecode, one is a synthetic calibration run at simulation scale, and
the eighth carries the exact layer and the identity onto a second
chain. They are complementary rather than independent replications;
the paper says so and says why.
Every one carries a captured output that is a regression target: a
numeric shift in any of them is a manuscript-level event.

| # | Surface | Where | What it asserts |
|---|---|---|---|
| 1 | the forward law | [`verification/act1-law/`](./verification/act1-law/) | the amplitude, its corners and monotonicity threshold, the pathwise identity, occupation offsets, the direction split |
| 2 | the floors | [`verification/act2-floor/`](./verification/act2-floor/) | the algebraic layer, then the corridor, renewal, width-uniform and swap-class floors against adversarial policy search |
| 3 | the instrument | [`verification/act3-instrument/`](./verification/act3-instrument/) | the delay law, planted recovery through the full pipeline, the delay-invariance dichotomy, agreement-test size, discreteness |
| 4 | the production anchor | [`verification/anchor/`](./verification/anchor/) | the first two acts on 135,538 recorded rebalances, no synthetic input |
| 5 | the exact layer on chain | [`foundry/`](./foundry/) | four results against two unmodified position managers on Base, pinned at block 45,000,000 |
| 6 | the discrete-bin algebra | [`foundry/`](./foundry/) | the Liquidity Book appendix against an unmodified LBPair on Avalanche, pinned at block 92,430,000 |
| 7 | synthetic calibration | [`calibration/`](./calibration/) | the instrument's bias behaviour and the floors' sharpness on planted ground truth |
| 8 | the Ethereum mainnet arm | [`foundry/`](./foundry/) and [`verification/mainnet/`](./verification/mainnet/) | the same four results against the Uniswap V3 manager on Ethereum at block 25,200,000; 22 third-party identity events at median 7.9e-17; a two-sided floor scatter; and a within-block null showing rebalances are neither backrun nor sandwiched on either chain |

## Quick start

```bash
git submodule update --init --recursive   # forge-std, for the fork suites

# the three dependency-free act harnesses (~45 s total)
cd verification/act1-law        && python3 mc_harness.py
cd ../act2-floor                && python3 verify_floor.py
cd ../act3-instrument           && python3 mc_harness.py
# each ends "all checks passed" and exits nonzero on a failed check

# the fork suites (20 tests; any archive RPC per chain is sufficient)
cd ../../foundry
RPC_BASE_ALCHEMY=https://mainnet.base.org \
RPC_AVAX_ALCHEMY=https://api.avax.network/ext/bc/C/rpc \
RPC_ETH_ALCHEMY=<ethereum-archive-rpc> \
  forge test
# expected: 20 tests passed, 0 failed, 0 skipped
# RPC_ETH_ALCHEMY is optional: without it the Ethereum track skips and the
# Base and Avalanche tracks run 16 passed, 0 failed, 1 skipped
```

The production anchor and the third act's population probes read an
event lake that is not vendored here; see
[`verification/README.md`](./verification/README.md) for their inputs.

## Layout

```
.
├── paper/                  LaTeX source (local-time.tex) and build PDF
├── verification/           the five Python surfaces, plus the third-party anchors
│   ├── act1-law/             seed 29, six checks
│   ├── act2-floor/           seeds 31 and 229, ten checks plus the scoping probe
│   ├── act3-instrument/      seed 37, eight checks, plus eleven population probes
│   ├── anchor/               the production anchor, deterministic
│   ├── mainnet/              the mainnet arm's reading half, surface eight
│   ├── third-party/          identity anchors on third-party operators
│   └── README.md
├── foundry/                fork suites for surfaces five, six and eight
│   ├── src/                  mock pools, venue interfaces, vendored joe-v2
│   ├── test/                 four test contracts and helpers
│   ├── PROOF_OUTPUT.md       captured forge output and the test-to-manuscript maps
│   └── README.md
├── calibration/            the synthetic calibration surface
├── lean/                   Lean 4 formalisation; see lean/README.md
├── CITATION.cff
├── LICENSE
└── README.md
```

## Build

```bash
cd paper
xelatex local-time.tex && xelatex local-time.tex   # two passes for cross-references
```

The source needs the STIX Two Math and TeX Gyre Termes OpenType fonts.
A clean build is 60 pages with no undefined references and no overfull
boxes.

## Foundry suites

Twenty tests across four contracts. Two tracks on Base at block
45,000,000, against the Aerodrome Slipstream and Uniswap V3 position
managers, carry the exact-layer results: the share-potential identity
on pseudo-random width pairs, the two-branch amplitude with the binding
side per branch, the corner values with the price placed exactly on the
corner ticks, and the free locus. A third track on Ethereum mainnet at
block 25,200,000 replays the same four results against the Uniswap V3
manager on the WETH/USDT fee-500 book. One track on Avalanche C-Chain at
block 92,430,000, against the WAVAX/USDC bin-step-ten LBPair v2.2,
carries the discrete-bin algebra of the paper's Appendix B. The Base
pin sits inside both the census era and the production anchor's window,
so the fork tier, the census, and the anchor share an era.

`forge` caches RPC responses under `~/.foundry/cache`, so repeat runs
are fast. Per-track invocations and the full test-to-manuscript maps
are in [`foundry/README.md`](./foundry/README.md) and
[`foundry/PROOF_OUTPUT.md`](./foundry/PROOF_OUTPUT.md).

`foundry/lib/forge-std` is a submodule, as in the sibling repositories; run
`git submodule update --init --recursive` after cloning.

## Shared code

Where code is shared with the companion papers or between surfaces here
it is shared by copy, with the upstream owner named in the copying
file's header. Nothing in this repository is symlinked to anything
outside it. `foundry/src/MockCLPool.sol`,
`foundry/src/MockCLPoolV2.sol`, `foundry/src/interfaces/` and
`foundry/test/helpers/Tick.sol` come from the Master Equation suite,
which owns them; `foundry/src/joe-v2/` is vendored from `lfj-gg/joe-v2`
at commit `067c6cc`.
