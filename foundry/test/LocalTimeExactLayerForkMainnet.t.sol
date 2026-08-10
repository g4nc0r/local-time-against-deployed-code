// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {ExactLayerForkBase} from "./ExactLayerForkBase.sol";
import {INfpmUniV3, IFactoryUniV3} from "../src/interfaces/UniswapV3.sol";
import {IUniswapV3Pool, IERC20} from "../src/interfaces/Slipstream.sol";

/// @title LocalTimeExactLayerForkMainnet
/// @notice Exact-layer fork suite against the unmodified Uniswap V3 NFPM on
///         Ethereum mainnet, WETH/USDT fee-500 pool (tick spacing 10),
///         pinned block 25,200,000. Third deployment of the V3 class and the
///         first at a 12-second block time. Sibling of the Base contracts;
///         the NFPM pool key and the chain differ. See ExactLayerForkBase
///         for the four asserted results.
///
///         The pair is WETH/USDT, not USDC/WETH: the base contract's
///         tolerances are absolute token1 raw units, and mainnet USDC sorts
///         below WETH, so USDC/WETH would put an eighteen-decimal asset in
///         the token1 role. WETH/USDT keeps Base's 18-over-6 decimal shape.
///         USDT returns no data from transfer and approve, so the base's
///         _send and _approve helpers carry those calls.
contract LocalTimeExactLayerForkMainnet is ExactLayerForkBase {
    uint256 constant MAINNET_FORK_BLOCK = 25_200_000;

    address constant NFPM = 0xC36442b4a4522E871399CD717aBDD847Ab11FE88;
    address constant FACTORY = 0x1F98431c8aD98523631AE4a59f267346ea31F984;
    address constant M_WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address constant M_USDT = 0xdAC17F958D2ee523a2206206994597C13D831ec7;
    uint24 constant FEE = 500;
    int24 constant TICK_SPACING = 10;

    INfpmUniV3 nfpm = INfpmUniV3(NFPM);

    function setUp() public {
        // The Ethereum track is the optional one. The Base and Avalanche
        // tracks run against public endpoints; this needs an archive node.
        // Without RPC_ETH_ALCHEMY the contract skips rather than reverting in
        // setUp, so the run the README documents is sixteen green tests and
        // not fifteen plus a failure.
        if (bytes(vm.envOr("RPC_ETH_ALCHEMY", string(""))).length == 0) {
            vm.skip(true);
            return;
        }
        vm.createSelectFork("ethereum", MAINNET_FORK_BLOCK);
        pool = IUniswapV3Pool(IFactoryUniV3(FACTORY).getPool(M_WETH, M_USDT, FEE));
        require(address(pool) != address(0), "no Uniswap V3 pool");
        require(pool.token0() == M_WETH && pool.token1() == M_USDT, "unexpected ordering");
        spacing = TICK_SPACING;
        tok0 = M_WETH;
        tok1 = M_USDT;
        _commonSetup();
        _approve(M_WETH, NFPM, type(uint256).max);
        _approve(M_USDT, NFPM, type(uint256).max);
    }

    function _mintPos(int24 lo, int24 hi, uint256 a0, uint256 a1)
        internal
        override
        returns (uint256 tokenId, uint128 liq, uint256 used0, uint256 used1)
    {
        (tokenId, liq, used0, used1) = nfpm.mint(
            INfpmUniV3.MintParams({
                token0: M_WETH,
                token1: M_USDT,
                fee: FEE,
                tickLower: lo,
                tickUpper: hi,
                amount0Desired: a0,
                amount1Desired: a1,
                amount0Min: 0,
                amount1Min: 0,
                recipient: address(this),
                deadline: block.timestamp
            })
        );
        lastTokenId = tokenId;
    }

    function _burnAll(uint256 tokenId, uint128 liq) internal override returns (uint256 x, uint256 y) {
        (x, y) = nfpm.decreaseLiquidity(
            INfpmUniV3.DecreaseLiquidityParams({
                tokenId: tokenId,
                liquidity: liq,
                amount0Min: 0,
                amount1Min: 0,
                deadline: block.timestamp
            })
        );
        nfpm.collect(
            INfpmUniV3.CollectParams({
                tokenId: tokenId,
                recipient: address(this),
                amount0Max: type(uint128).max,
                amount1Max: type(uint128).max
            })
        );
    }

    function _mintExpectRevert(int24 lo, int24 hi, uint256 a0, uint256 a1) internal override {
        vm.expectRevert();
        nfpm.mint(
            INfpmUniV3.MintParams({
                token0: M_WETH,
                token1: M_USDT,
                fee: FEE,
                tickLower: lo,
                tickUpper: hi,
                amount0Desired: a0,
                amount1Desired: a1,
                amount0Min: 0,
                amount1Min: 0,
                recipient: address(this),
                deadline: block.timestamp
            })
        );
    }
}
