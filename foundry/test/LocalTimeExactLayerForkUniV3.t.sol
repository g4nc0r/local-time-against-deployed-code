// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {ExactLayerForkBase} from "./ExactLayerForkBase.sol";
import {INfpmUniV3, IFactoryUniV3} from "../src/interfaces/UniswapV3.sol";
import {IUniswapV3Pool, IERC20} from "../src/interfaces/Slipstream.sol";

/// @title LocalTimeExactLayerForkUniV3
/// @notice Exact-layer fork suite against the unmodified Uniswap V3 NFPM on
///         Base, WETH/USDC fee-500 pool (tick spacing 10), pinned block
///         45,000,000 (inside the census era). Sibling of the Slipstream
///         contract; only the NFPM pool key differs. See ExactLayerForkBase
///         for the four asserted results.
contract LocalTimeExactLayerForkUniV3 is ExactLayerForkBase {
    address constant NFPM = 0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1;
    address constant FACTORY = 0x33128a8fC17869897dcE68Ed026d694621f6FDfD;
    uint24 constant FEE = 500;
    int24 constant TICK_SPACING = 10;

    INfpmUniV3 nfpm = INfpmUniV3(NFPM);

    function setUp() public {
        vm.createSelectFork("base", FORK_BLOCK);
        pool = IUniswapV3Pool(IFactoryUniV3(FACTORY).getPool(WETH, USDC, FEE));
        require(address(pool) != address(0), "no Uniswap V3 pool");
        require(pool.token0() == WETH && pool.token1() == USDC, "unexpected ordering");
        spacing = TICK_SPACING;
        _commonSetup();
        IERC20(WETH).approve(NFPM, type(uint256).max);
        IERC20(USDC).approve(NFPM, type(uint256).max);
    }

    function _mintPos(int24 lo, int24 hi, uint256 a0, uint256 a1)
        internal
        override
        returns (uint256 tokenId, uint128 liq, uint256 used0, uint256 used1)
    {
        (tokenId, liq, used0, used1) = nfpm.mint(
            INfpmUniV3.MintParams({
                token0: WETH,
                token1: USDC,
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
                token0: WETH,
                token1: USDC,
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
