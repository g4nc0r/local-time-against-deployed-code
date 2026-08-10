# Surface 8: the Ethereum mainnet arm

The eighth verification surface. It carries the exact layer and the
third-party identity onto a second chain, at a twelve-second block and
under a different sequencing regime, and it measures whether the event
leg the paper prices is an artefact of extraction.

The surface has two halves. The **fork track** lives in
[`../../foundry/`](../../foundry/) with the other three tracks
(`LocalTimeExactLayerForkMainnet.t.sol`, pinned at block 25,200,000 on
the WETH/USDT fee-500 book) and is captured in
`foundry/PROOF_OUTPUT.md`. The **on-chain reading** is here.

`OUTPUT.md` and `OUTPUT-mev.md` are the captured outputs and are
regression targets: a numeric shift in either is a manuscript-level
event.

## What each script does

| script | what it produces |
|---|---|
| `discover_pools.py` | scans Uniswap V3 pools by event topic over sampled windows of the era, to establish where mainnet position activity actually is. Output `discovery.json` |
| `m2_stream.py` | streams position and swap events for the verified pool set over the era, prices each firing at the pre-swap mark with the fee leg on the input side, and writes the cell and tick blobs plus `m2_summary.json` |
| `m3_analysis.py` | reads M2's blobs and produces the two-sided floor scatter, the block-time readings and the clock declaration. Output `m3_results.json` |
| `mev_probe.py` | one code path over matched pairs and a matched wall-clock window on both chains: interior fractions, exit delays, adjacency ratios against a within-block null, JIT and same-range shares. Outputs `mev_probe_ethereum.json`, `mev_probe_base.json` |
| `base_local_ab.py` | the A/B check behind the probe's ordering convention. Conflating a JIT position with a same-range re-mint reverses the answer; the ordering of mint and burn inside the block is what separates them |

`pool_verification.json` records which of the busiest pools are in the
Uniswap V3 factory. Eight of the fifty-five carry V3 event signatures
without factory membership and are excluded rather than mixed in.

## Running them

The scripts read the public SQD portal (`portal.sqd.dev`) and need no
key and no archive node. They are not deterministic in the sense the
`act1`–`act3` harnesses are: they read a live public dataset, and their
outputs are pinned by block window rather than by seed.

```bash
python3 discover_pools.py          # optional; the pool set is vendored
python3 m2_stream.py               # writes m2_cells.json.gz + m2_ticks.json.gz
python3 m3_analysis.py             # reads them, writes m3_results.json
python3 mev_probe.py --chain ethereum
python3 mev_probe.py --chain base
```

The two stream blobs are **not vendored**: `m2_ticks.json.gz` alone is
11 MB, against a repository whose whole first commit is under four. Run
`m2_stream.py` at the pinned window to regenerate them before
`m3_analysis.py`. Everything else needed to check the captured numbers
is in this folder.

## What this surface establishes, and what it does not

It establishes that the exact layer and the share-potential identity
hold on a third V3-class deployment and a second chain, that the
realised event cost can be measured rather than bounded where the
corrective swap stays in the pool, and that rebalance firings are
neither backrun nor sandwiched against a within-block null on either
chain.

It does not establish a mainnet population read. Active liquidity
management on mainnet fires about thirty times less often than on
Base, so twenty-nine cells clear the firing bar and no census is
available. Two readings deliberately absent: the mainnet discreteness
admission is not computed here, so nothing in `m3_results.json` should
be quoted against the admission constants in the paper; and the
cross-chain delay-cut equivalence test is not powered at a
twelve-second block and is not attempted.
