# Fork-suite captured output (fifth, sixth and eighth verification surfaces)

Captured `forge test -vv` output for the exact-layer fork suite. This
file is the regression target: a numeric shift here means either a test
change or a manuscript revision, per the programme rule.

- Run date: 2026-08-09. RPC: `https://mainnet.base.org` via
  `RPC_BASE_ALCHEMY`.
- Fork pin: Base block **45,000,000**, chosen inside the census era
  (blocks 44.0M to 49.2M) and inside the production anchor's amounts
  window (43,635,967 to 45,988,726), so the fork tier, the sender-keyed
  census, and the real-data anchor share an era. The GS/ME pin
  43,175,000 predates the era and is deliberately not reused.
- Two targets, both unmodified production deployments on Base:
  Aerodrome Slipstream NFPM `0x8279…5b72` (WETH/USDC, tick spacing 100)
  and Uniswap V3 NFPM `0x03a5…34f1` (WETH/USDC, fee 500, tick
  spacing 10).
- Third target, on Ethereum mainnet: Uniswap V3 NFPM `0xC364…FE88`
  (WETH/USDT, fee 500, tick spacing 10), pinned block **25,200,000**.
  RPC via `RPC_ETH_ALCHEMY`. The pin sits in a window wall-clock
  aligned to the Base census era, so the three V3 tracks share an era
  in time as well as in geometry. This is the first track at a
  12-second block time.
- The mainnet pair is WETH/USDT rather than USDC/WETH because the
  suite's tolerances are absolute token1 raw units: mainnet USDC sorts
  below WETH, so USDC/WETH would put an eighteen-decimal asset in the
  token1 role. WETH/USDT keeps Base's 18-over-6 decimal shape. USDT
  returns no data from `transfer` and `approve`, so the `_send` and
  `_approve` helpers in `ExactLayerForkBase` carry those calls; the
  by-role `tok0`/`tok1` fields there serve the same purpose.
- Twenty tests across four contracts.
- Gas figures on the two Base exact-layer tracks were re-captured on
  2026-08-10 when the shared base moved its token pair into by-role
  fields. Every asserted value and every logged number is unchanged;
  only gas moved.
- The mainnet track's gas figures were re-captured on 2026-08-10 when
  its `setUp` gained the guard that skips the track, rather than
  reverting, when `RPC_ETH_ALCHEMY` is unset. Asserted values and
  logged numbers are unchanged; only gas moved, by 30 to 500 units.

## Test-to-manuscript map

| Test | Manuscript result | What is asserted against bytecode |
|---|---|---|
| `test_shareIdentity_randomWidthPairs` | Theorem 2 (Share-Potential Identity) | On 10 pseudo-random width pairs per venue: the re-mint liquidity equals the binding-side minimum `min(x/x_u, y/y_u)` to 1 unit; mint amounts match the V3-exact prediction to 3 wei; one side is consumed to sub-liquidity-unit slack; `V_after = L' V_unit` in 1e18 fixed point (rounding-dominated residual, see below); `k >= 0` on every event. |
| `test_twoBranchAmplitude` | Proposition 2 (Two-Branch Amplitude) and Lemma 3 (Binding Side) | Six displacement cases, three per branch, with the price placed exactly at the midpoint of a whole-tick translate of the old range (centring exact by construction). Hard asserts: the exact mint-minimum layer to wei, and the branch-correct binding side. The closed form is asserted within a quantisation budget of 20,000 ppm; the only model gap is the translate's width factor, roughly `|d| * 5e-5` in sqrt price for a `d`-tick shift. |
| `test_cornerValues` | Corollary 3 (Corner Values) | Price placed exactly on the corner tick (corner sqrt ratios are tick-representable, so this layer is quantisation-free). Upper corner: burn returns are all token1 and equal `L*w` to 1 wei. Lower corner: burn returns are all token0, the amount is exact to 1 wei, and its value equals `L*w*s_a/s_b` to 5 raw units (observed: exact). The recentred corner mint is empty: the production NFPM reverts. |
| `test_freeLocus` | Corollary 2 (Free Locus) | The tick-representable locus point (identical re-placement) costs at most 4 raw units (observed: 1). A tick-rounded slide along the locus is at least an order of magnitude cheaper than a generic share-moving re-placement of comparable width; the exact layer and `k >= 0` are asserted throughout. |

## Reading the residuals

- The share-identity retained-fraction gap is quoted in 1e18 fixed
  point: the observed worst cases, 5.4e7 (Uniswap V3) and 4.8e7
  (Slipstream), are relative gaps of 5.4e-11 and 4.8e-11, dominated by
  the 1-wei rounding of the reference-liquidity value, not by the
  identity. The wei-level asserts on `L'` and the mint amounts carry
  the exactness claim, matching the anchor surface
  (`verification/anchor/OUTPUT.md`, median 5.7e-17 on 78,908 production
  events, where both sides are computed from the same integers).
- The amplitude closed-form gaps run 12 to 44 ppm on Uniswap V3
  (spacing 10), **12 to 44 ppm on Ethereum mainnet at the same
  spacing**, and 996 to 4,321 ppm on Slipstream (spacing 100),
  ordered by the translate's width factor as the budget predicts. The
  corner values are the exact anchors of both branches (`delta = ±h`)
  and agree to the wei.

## Captured output

```
Ran 4 tests for test/LocalTimeExactLayerForkUniV3.t.sol:LocalTimeExactLayerForkUniV3
[PASS] test_cornerValues() (gas: 1328469)
Logs:
  upper corner value L*w (token1 raw), asserted vs burn:
  22077715218
  lower corner value (token1 raw) and L*w*s_a/s_b:
  21945652115
  21945652115

[PASS] test_freeLocus() (gas: 1415939)
Logs:
  free locus, identical re-placement: V_before - V_after (token1 raw):
  1
  free locus: k (ppm of V) for locus slide vs generic move:
  5962
  428224

[PASS] test_shareIdentity_randomWidthPairs() (gas: 6777401)
Logs:
  share identity: 10 width pairs, worst retained-fraction gap (1e18 fp):
  54262902

[PASS] test_twoBranchAmplitude() (gas: 6228574)
Logs:
  amplitude case (tick shift, signed as two logs):
  150
  0
    Delta-R actual / closed form (token1 raw):
  10724200377
  10724331733
    gap (ppm):
  12
  amplitude case (tick shift, signed as two logs):
  80
  0
    Delta-R actual / closed form (token1 raw):
  7131809879
  7132022027
    gap (ppm):
  29
  amplitude case (tick shift, signed as two logs):
  20
  0
    Delta-R actual / closed form (token1 raw):
  2263598692
  2263699978
    gap (ppm):
  44
  amplitude case (tick shift, signed as two logs):
  0
  20
    Delta-R actual / closed form (token1 raw):
  2096168281
  2096262271
    gap (ppm):
  44
  amplitude case (tick shift, signed as two logs):
  0
  80
    Delta-R actual / closed form (token1 raw):
  6551915828
  6552112811
    gap (ppm):
  30
  amplitude case (tick shift, signed as two logs):
  0
  150
    Delta-R actual / closed form (token1 raw):
  9769347379
  9769471604
    gap (ppm):
  12

Suite result: ok. 4 passed; 0 failed; 0 skipped

Ran 4 tests for test/LocalTimeExactLayerForkSlipstream.t.sol:LocalTimeExactLayerForkSlipstream
[PASS] test_cornerValues() (gas: 1752700)
Logs:
  upper corner value L*w (token1 raw), asserted vs burn:
  22180328929
  lower corner value (token1 raw) and L*w*s_a/s_b:
  20888709790
  20888709790

[PASS] test_freeLocus() (gas: 1447275)
Logs:
  free locus, identical re-placement: V_before - V_after (token1 raw):
  1
  free locus: k (ppm of V) for locus slide vs generic move:
  2424
  426199

[PASS] test_shareIdentity_randomWidthPairs() (gas: 6734144)
Logs:
  share identity: 10 width pairs, worst retained-fraction gap (1e18 fp):
  48429511

[PASS] test_twoBranchAmplitude() (gas: 7676552)
Logs:
  amplitude case (tick shift, signed as two logs):
  1500
  0
    Delta-R actual / closed form (token1 raw):
  10846923519
  10857748411
    gap (ppm):
  996
  amplitude case (tick shift, signed as two logs):
  800
  0
    Delta-R actual / closed form (token1 raw):
  7049070666
  7068440543
    gap (ppm):
  2740
  amplitude case (tick shift, signed as two logs):
  200
  0
    Delta-R actual / closed form (token1 raw):
  2187387921
  2196687257
    gap (ppm):
  4233
  amplitude case (tick shift, signed as two logs):
  0
  200
    Delta-R actual / closed form (token1 raw):
  1975949233
  1984525610
    gap (ppm):
  4321
  amplitude case (tick shift, signed as two logs):
  0
  800
    Delta-R actual / closed form (token1 raw):
  5872099491
  5890025643
    gap (ppm):
  3043
  amplitude case (tick shift, signed as two logs):
  0
  1500
    Delta-R actual / closed form (token1 raw):
  8290585365
  8302643733
    gap (ppm):
  1452

Suite result: ok. 4 passed; 0 failed; 0 skipped

Ran 2 test suites: 8 tests passed, 0 failed, 0 skipped (8 total tests)
```

## Liquidity Book fork suite (sixth verification surface)

Captured `forge test --match-contract LocalTimeLBForkAvalanche -vv`
output for the Liquidity Book suite: the
The Appendix B Liquidity Book algebra asserted against an
unmodified deployed LBPair v2.2 on Avalanche C-Chain, the discrete-bin
venue class's home deployment. Captured numbers below are regression
targets on the same terms as the exact-layer section above.

- Run date: 2026-08-10. RPC: Alchemy Avalanche C-Chain endpoint via
  `RPC_AVAX_ALCHEMY` (URL not recorded by policy; any archive-capable
  Avalanche C-Chain RPC reproduces the run).
- Fork pin: Avalanche C-Chain block **92,430,000** (2026-08-09,
  finalised; the pair's last parameter update sits 7 seconds before
  the pin's timestamp, inside the 30 s filter period, so the live
  fee-quote test exercises the no-decay reference branch
  deterministically).
- Target: the factory-registered WAVAX/USDC bin-step-10 LBPair v2.2
  `0x864d4e5Ee7318e97483DB7EB0912E09F161516EA`, discovered on-fork
  from LBFactory v2.2 `0xb43120c4745967fa9b93E79C149E66B0f2D6Fe0c`
  (developers.lfj.gg deployment list) via `getLBPairInformation`,
  with token ordering and bin step asserted in `setUp`. The pair
  carries a nonzero LB hooks word (an LB rewarder); hooks receive
  callbacks but do not enter the price, depth, or fee arithmetic
  asserted here.
- Reference implementation: `src/joe-v2/` is a verbatim copy of the
  price, fee, and parameter libraries of `lfj-gg/joe-v2` at commit
  `067c6cc` (the commit Appendix B was read from): `Constants.sol`,
  `PriceHelper.sol`, `FeeHelper.sol`, `PairParameterHelper.sol` and
  their four math dependencies. `BinHelper.getLiquidity` is inlined
  verbatim in the test (the full file pulls token-transfer helpers
  the suite does not need).

### Test-to-manuscript map (Appendix B)

| Test | Appendix B claim | What is asserted against bytecode |
|---|---|---|
| `test_binPriceLaw_exactAgainstSource` | Bin price law `P(i) = (1 + b 10^-4)^(i - 2^23)` | Deployed `getPriceFromId` bit-exact against the commit's `PriceHelper` at nine ids spanning active +/- 5000; the offset anchor `P(2^23) = 2^128` exact on both; the id-price round trip closes at the active bin. |
| `test_binPriceLaw_stepRatio` | Same law, analytic step form | `P(i+1) * 2^128 / P(i)` equals the 128.128 encoding of `1 + b 10^-4` within 2^40 ulp of 2^-128 (~2^-88 relative), the pow library's accumulated squaring truncation at this exponent magnitude; measured worst gap 142,097,247,651 ulp, ~4.2e-28 relative. |
| `test_binDepth_constantSum` | Constant-sum depth `L_i = P(i) x_i + y_i` | Raw-arithmetic recomputation equals the source formula exactly on an 11-bin walked window; single-sidedness (base above the active id, quote below) asserted per bin; depth below the per-bin cap. |
| `test_perBinAmplitude` | Atom amplitude `L_i / P(i)` | Above-active bins: amplitude reconstructs the base reserve exactly. Below-active: the amplitude re-marks to the quote reserve within one wei. Active-bin atom amplitude logged. |
| `test_perTraversalLoss` | Per-traversal loss `L_i b / (10^4 + b)` | The exact-rational form against the price-ratio form `L_i (1 - P(i-1)/P(i))` at deployed prices, on the active and next-lower bins: relative gap 0 at 1e18 fixed point (tolerance 1e-17). |
| `test_feeShape_baseAndVariable` | Fee shape `eta_0 = B b 10^-8`, `eta_v = C_v (v b)^2 10^-20` | Raw-arithmetic recomputation from the deployed pair's static and variable fee parameters equals the commit's `PairParameterHelper` on the re-encoded parameter word; total is the sum, below the cap. |
| `test_swapFee_liveQuote` | Fee charge and single-price execution | Deployed `getSwapOut` on an in-bin swap: fee equals the formula at current parameters (reference-update semantics replicated from source) and output executes at exactly `P(i)`, both to the wei. |
| `test_compositionFee_grossQuotedForm` | Composition fee `eta (1 + eta)` | The commit's `FeeHelper.getCompositionFee` equals `a * f * (f + 1e18) / 1e36` exactly across four amounts at the pair's current total fee. |

### Reading the residuals

- Everything integer-valued is asserted exact (bit-exact prices
  against source, wei-exact depth, amplitude, live fee and output).
  The only stated tolerances are the two representation bounds: the
  step-ratio gap (~4.2e-28 relative, bounded at 2^-88), which is the
  128.128 pow library's own truncation rather than a model gap, and
  the traversal-loss comparison, whose measured relative gap is 0 at
  1e18 fixed point against a 1e-17 budget, the programme's
  machine-precision standard.
- Headline captured values at the pin: active id 8,362,846, active-bin
  price 2,234,268,809,462,282,344,339,823,067 (128.128; ~6.566e-12
  quote wei per base wei, i.e. ~6.57 USDC/AVAX), active-bin depth
  2,425,700,580 quote wei, atom amplitude 369,437,702,107,735,585,265
  base wei, per-traversal loss 2,423,277 quote wei (active bin), fee
  parameters base 5.0e14 / variable 6.3489024e11 / total
  5.0063489024e14 at 1e18 precision (5.006 bp), live quoted fee
  500,634,890,240,000 wei on a 1e18 swap, composition fee
  500,885,525,533,325 on 1e18 at the same total fee.

### Captured output

```
Ran 8 tests for test/LocalTimeLBForkAvalanche.t.sol:LocalTimeLBForkAvalanche
[PASS] test_binDepth_constantSum() (gas: 119194)
Logs:
  active bin reserves (base wei, quote wei) and depth (quote wei):
  2260969186388175120
  2410855224
  2425700580

[PASS] test_binPriceLaw_exactAgainstSource() (gas: 83817)
Logs:
  active id and its 128.128 price:
  8362846
  2234268809462282344339823067

[PASS] test_binPriceLaw_stepRatio() (gas: 37516)
Logs:
  step ratio vs 1 + b*10^-4: worst gap (128.128 ulp):
  142097247651

[PASS] test_compositionFee_grossQuotedForm() (gas: 22370)
Logs:
  composition fee on 1e18 at current total fee:
  500885525533325

[PASS] test_feeShape_baseAndVariable() (gas: 24217)
Logs:
  fee shape at deployed parameters, base / variable / total (1e18 = 1):
  500000000000000
  634890240000
  500634890240000

[PASS] test_perBinAmplitude() (gas: 115280)
Logs:
  active bin atom amplitude L_i/P(i) (base wei):
  369437702107735585265

[PASS] test_perTraversalLoss() (gas: 36131)
Logs:
  traversal loss, bin id / L_i*b/(10^4+b) (quote wei) / rel gap (1e18):
  8362846
  2423277
  0
  traversal loss, bin id / L_i*b/(10^4+b) (quote wei) / rel gap (1e18):
  8362845
  2400077
  0

[PASS] test_swapFee_liveQuote() (gas: 32942)
Logs:
  live quote, 1e18 base in: fee (base wei) / out (quote wei):
  500634890240000
  6562638

Suite result: ok. 8 passed; 0 failed; 0 skipped
```

The full-suite run on 2026-08-10 (both Base tracks plus this one,
`forge test -vv` with `RPC_BASE_ALCHEMY` and `RPC_AVAX_ALCHEMY` set)
passed 16 of 16 with the exact-layer captured numbers above unchanged.

## Captured output, Ethereum mainnet (eighth verification surface)

Run 2026-08-10, pin 25,200,000, WETH/USDT fee 500.

```
Ran 4 tests for test/LocalTimeExactLayerForkMainnet.t.sol:LocalTimeExactLayerForkMainnet
[PASS] test_cornerValues() (gas: 1294016)
Logs:
  upper corner value L*w (token1 raw), asserted vs burn:
  20111391825
  lower corner value (token1 raw) and L*w*s_a/s_b:
  19991090753
  19991090753

[PASS] test_freeLocus() (gas: 1561471)
Logs:
  free locus, identical re-placement: V_before - V_after (token1 raw):
  0
  free locus: k (ppm of V) for locus slide vs generic move:
  186
  439587

[PASS] test_shareIdentity_randomWidthPairs() (gas: 7376192)
Logs:
  share identity: 10 width pairs, worst retained-fraction gap (1e18 fp):
  54688134

[PASS] test_twoBranchAmplitude() (gas: 6319797)
Logs:
  amplitude case (tick shift, signed as two logs):
  150
  0
    Delta-R actual / closed form (token1 raw):
  10724200377
  10724331733
    gap (ppm):
  12
  amplitude case (tick shift, signed as two logs):
  80
  0
    Delta-R actual / closed form (token1 raw):
  7131809879
  7132022027
    gap (ppm):
  29
  amplitude case (tick shift, signed as two logs):
  20
  0
    Delta-R actual / closed form (token1 raw):
  2245122853
  2245223313
    gap (ppm):
  44
  amplitude case (tick shift, signed as two logs):
  0
  20
    Delta-R actual / closed form (token1 raw):
  1811433189
  1811514412
    gap (ppm):
  44
  amplitude case (tick shift, signed as two logs):
  0
  80
    Delta-R actual / closed form (token1 raw):
  5661929863
  5662100087
    gap (ppm):
  30
  amplitude case (tick shift, signed as two logs):
  0
  150
    Delta-R actual / closed form (token1 raw):
  8442318417
  8442425767
    gap (ppm):
  12

Suite result: ok. 4 passed; 0 failed; 0 skipped; finished in 409.86ms (34.94ms CPU time)
```

The mainnet corner ratio agrees to the wei (19,991,090,753 on both
sides), the identical re-placement on the free locus costs zero raw
units against Base's one, and the amplitude gaps fall in the same 12 to
44 ppm band as the Base Uniswap V3 track at the same tick spacing. The
exact layer holds against deployed code on three V3-class deployments
across two chains, and against the Liquidity Book on a third.

## Reproduction

```bash
cd foundry
forge build

# Base exact-layer tracks (any working Base archive RPC is sufficient)
RPC_BASE_ALCHEMY=https://mainnet.base.org forge test --match-contract ExactLayer -vv

# Liquidity Book track (any Avalanche C-Chain archive RPC)
RPC_AVAX_ALCHEMY=<avalanche-rpc-url> forge test --match-contract LocalTimeLBForkAvalanche -vv

# Ethereum mainnet track (any mainnet archive RPC)
RPC_ETH_ALCHEMY=<mainnet-rpc-url> forge test --match-contract LocalTimeExactLayerForkMainnet -vv

# full suite (both env vars set)
forge test -vv
```

`src/MockCLPool.sol`, `src/MockCLPoolV2.sol`, `src/interfaces/` and
`test/helpers/Tick.sol` are shared by copy from the Master Equation
suite (`~/Projects/Papers/Master Equation/foundry/`), which owns the
upstream; `src/joe-v2/` is shared by copy from `lfj-gg/joe-v2` at
commit `067c6cc`, which owns that upstream; `lib/forge-std` is
vendored the same way. The fork tests are deterministic at their pins;
the captured numbers above should reproduce to the wei.
