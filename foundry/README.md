# Fork verification suite

Foundry tests asserting the manuscript's results against unmodified
production deployments. Three tracks carry the exact-layer results: two
on Base at pinned block 45,000,000 (the Aerodrome Slipstream NFPM and
the Uniswap V3 NFPM) and one on Ethereum mainnet at pinned block
25,200,000 (the Uniswap V3 NFPM, WETH/USDT). One track on Avalanche
C-Chain at pinned block 92,430,000 (the WAVAX/USDC bin-step-10 LBPair
v2.2) carries the Appendix B Liquidity Book algebra.

Twenty tests across four contracts. Per exact-layer venue: the
share-potential identity on pseudo-random width pairs, the two-branch
amplitude with the binding side per branch, the corner values with the
price placed exactly on the corner ticks, and the free locus. The
mainnet track pairs WETH with USDT rather than USDC because the
suite's tolerances are absolute token1 raw units and mainnet USDC sorts
below WETH; WETH/USDT keeps Base's 18-over-6 decimal shape. On the
Liquidity Book: the bin price law (bit-exact against the source commit
and in analytic step form), the constant-sum depth with ladder
single-sidedness, the per-bin atom amplitude, the per-traversal loss,
the base and variable fee shape, the live in-bin fee quote with
single-price execution, and the gross-quoted composition fee.
`PROOF_OUTPUT.md` holds the captured output and the test-to-manuscript
maps, and is the regression target.

```bash
forge build

# full suite (Base tracks need RPC_BASE_ALCHEMY, the mainnet track
# RPC_ETH_ALCHEMY, the LB track RPC_AVAX_ALCHEMY; any archive-capable
# RPC per chain is sufficient). RPC_ETH_ALCHEMY is the optional one:
# unset, the mainnet track skips and the rest run 16 passed, 1 skipped.
RPC_BASE_ALCHEMY=https://mainnet.base.org RPC_ETH_ALCHEMY=<mainnet-rpc-url> RPC_AVAX_ALCHEMY=<avalanche-rpc-url> forge test -vv

# one track
RPC_BASE_ALCHEMY=https://mainnet.base.org forge test --match-contract Slipstream -vv
RPC_BASE_ALCHEMY=https://mainnet.base.org forge test --match-contract UniV3 -vv
RPC_ETH_ALCHEMY=<mainnet-rpc-url> forge test --match-contract Mainnet -vv
RPC_AVAX_ALCHEMY=<avalanche-rpc-url> forge test --match-contract LocalTimeLBForkAvalanche -vv
```

`src/MockCLPool.sol`, `src/MockCLPoolV2.sol`, `src/interfaces/` and
`test/helpers/Tick.sol` are shared by copy from the Master Equation
suite, which owns the upstream. `src/joe-v2/` is shared by copy from
`lfj-gg/joe-v2` at commit `067c6cc`, which owns that upstream.
`lib/forge-std` is vendored.
