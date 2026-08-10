# Third-party identity anchors

The share-potential identity read on operators other than the paper's
own, on two venue classes. `OUTPUT.md` is the captured result and the
regression target.

These readings support the third-party paragraphs of the paper's
Numerical verification section. They are evidence inside the existing
surfaces rather than a surface of their own: the V3 reading extends the
production anchor beyond the single operator it records, and the
Liquidity Book reading pairs with the fork suite of the sixth surface.

## Contents

| File | What it is |
|---|---|
| `t2_identity.py` | the V3-class identity evaluator, applied per admitted sequence |
| `scan_aero_events.py` | the Aerodrome Slipstream event scan |
| `ws0_probe.py` | the Uniswap V3 event scan and class census |
| `t2_aero_full.json`, `t2_aero.json` | Slipstream results, full era and a 600k-block prefix |
| `t2_univ3.json` | Uniswap V3 results |
| `lb_anchor.py` | the Liquidity Book anchor, scan and identity in one script |
| `lb_avax.json` | Liquidity Book results, 77 admitted sequences |

## Inputs

Everything here reads public chain data. Nothing reads the event lake,
and no census join is performed.

The Liquidity Book anchor streams Avalanche C-Chain logs and needs one
archive-capable endpoint in `RPC_AVAX_ALCHEMY`. The V3 scans read Base
logs over the census era; on a fresh machine they re-derive their
inputs from the chain, which is slow, and the committed result JSONs
are the captured answer.

The raw intermediate scans are not vendored. They are large, they
regenerate from the scripts at the stated eras, and in the Liquidity
Book case the raw stream alone is about 12 MB.

## Anonymisation

Operators appear as `op_NNNN`, on the same convention as the rest of
this tree and as the companion paper. Per-sequence transaction hashes
are deliberately absent: publishing a hash alongside a pseudonym would
defeat the pseudonym, because the sender is recoverable from the
transaction. Pair, pool, factory and position-manager addresses are
public contracts and are published as they are.

## Known limitation

`ws0_probe.py` does not retry a dropped streaming read. A long scan
that loses its connection will end short rather than fail loudly, so
compare the class counts against `t2_univ3.json` before trusting a
fresh run.
