# Captured output: the third-party identity anchors

Captured 2026-08-10. Two readings of the share-potential identity on
operators other than the paper's own, one on the V3 class and one on
the Liquidity Book. Both are deterministic reads of public chain data
at a fixed era, with no RNG. This file is a regression target: a
numeric shift is a manuscript-level event.

Operators appear under stable `op_NNNN` pseudonyms rather than
addresses, and per-sequence transaction hashes are not published, since
a hash reveals its own sender. Every reported quantity is the one
computed from the identified data. Pool, pair, factory and
position-manager addresses are not obscured, being public contracts.

## The V3 class: isolated third-party re-placements

Every same-transaction re-placement on the census pools of both Base
deployments over the census era, blocks 44,000,000 to 49,200,000,
reconstructed from public burn and mint events with the transaction
sender attached, author and infrastructure addresses excluded. A
sequence is admitted only when it survives the anchor's own event
discipline, which is the isolated interior case the identity is stated
for.

| | Aerodrome Slipstream | Uniswap V3 |
|---|---|---|
| firings sampled | 125,980 | (full era scan) |
| clean isolated interior | **253** | **345** |
| distinct operators | 10 | 8 |
| single-sided limit placements | **2,385** | **33,008** |
| same-range | 88,889 | 71,291 |
| top-up | 95,334 | 235,985 |
| multi-position | 50,040 | 92,949 |
| degenerate | 7,755 | 32,909 |
| identity error, median | **1.11e-16** | **1.11e-16** |
| recovered price self-consistency, median | **1.61e-11** | **2.53e-14** |

Artefacts `t2_aero_full.json`, `t2_aero.json` and `t2_univ3.json`. The
identity holds at the same machine precision as the production anchor
on both venues. The single-sided placements satisfy the identity
trivially, one share being zero on each side, and are reported as a
class rather than folded into the clean count.

The price self-consistency column is the agreement between the two
independent recoveries of the price at the mint, one from each token
leg. It is a check on the reconstruction rather than on the identity,
and its spread between the venues is a tick-spacing effect, spacing 100
on Slipstream against 10 on Uniswap V3.

## The Liquidity Book: third-party bin-level anchor

Avalanche C-Chain, blocks 89,430,000 to 92,430,000, the three million
blocks ending at the fork pin of the sixth surface. Events are
`WithdrawnFromBins` and `DepositedToBins`, with topic hashes computed
from the source ABI rather than assumed. Of 10,100 pairs seen, 10,071
are registered to the v2.2 factory and 29 are excluded as
other-factory deployments.

Isolation follows the same standard as the V3 class. A candidate is a
withdraw and a deposit on the same pair within fifty blocks, admitted
only when both transactions share a sender, neither contains a swap on
the pair, and a closed-interval log query returns exactly those two
transactions, so no third party mutated the touched bins between them.

Of 95 window candidates: 5 rejected on sender mismatch, 13 on
interleaving, 0 on a swap in the transaction, 0 on a missing receipt.
**77 isolated sequences admitted**, across 9 pairs and 21 distinct
senders, none of them the anchor's operator.

| check | n | median | q99 | max |
|---|---|---|---|---|
| burn identity | **1,406** | 6.14e-18 | 1.11e-06 | 1.11e-06 |
| mint identity | 1,225 | **7.03e-22** | 6.40e-21 | **1.04e-20** |
| composition fee | 48 | 0.0 | 0.0 | 0.0 |

The burn identity is exact on the integer form in all **1,406** bin
legs, with zero inexact legs; the residual column reports the
real-valued reading, whose upper tail is the reserve-ratio rounding of
the floor pair. Sidedness holds in all 1,260 applicable legs and the
fresh-bin share rule in all 100. The composition fee and its protocol
split are predicted exactly on all 48 events. Artefact `lb_avax.json`.

### Deployed code against source commit

The Avalanche v2.2 deployment predates joe-v2 commit `7e5b0b4`, which
fixed the composition-fee calculation and is an ancestor of `067c6cc`,
the commit the appendix was read from. In the final-shares identity the
deployed code divides by the original bin liquidity where the later
commit divides by that liquidity plus the net fee. The anchor asserts
the deployed law and reports the commit-form difference separately.

| quantity | n | median | q99 | max |
|---|---|---|---|---|
| commit-form gap | 48 | 5.16e-06 | 5.49e-03 | **5.49e-03** |

Under the deployed law the final-shares identity is exact on all 48
composition-fee events. An earlier run asserted the commit form and
reported a mint-identity tail with maximum 5.49e-03; that tail is
precisely this column and carried no information about the identity.
The tail is not share discretisation, since the bins concerned carry
share supplies of order 1e29 and the mint floor bounds its own
truncation at order 1e-30, twenty-seven orders below.

The general point is worth recording. Reading an identity from a
repository commit and asserting it against a production deployment can
measure the version gap rather than the law. Where a deployment
predates the source read, the deployed form is the object of study and
the commit form is a second, separately reported quantity.

## Scope

No population or census claim is made from either reading. The V3
class carries its census elsewhere; the Liquidity Book has none, and
that remains the named next demonstration.
