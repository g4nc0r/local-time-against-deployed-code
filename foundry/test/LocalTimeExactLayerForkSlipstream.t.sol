// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {ExactLayerForkBase} from "./ExactLayerForkBase.sol";
import {
    INonfungiblePositionManager,
    IUniswapV3Pool,
    IUniswapV3Factory,
    IERC20
} from "../src/interfaces/Slipstream.sol";

/// @title LocalTimeExactLayerForkSlipstream
/// @notice Exact-layer fork suite against the unmodified Aerodrome Slipstream
///         NFPM on Base, WETH/USDC tickSpacing-100 pool, pinned block
///         45,000,000 (inside the census era). See ExactLayerForkBase for
///         the four asserted results.
contract LocalTimeExactLayerForkSlipstream is ExactLayerForkBase {
    address constant NFPM = 0x827922686190790b37229fd06084350E74485b72;
    address constant FACTORY = 0x5e7BB104d84c7CB9B682AaC2F3d509f5F406809A;
    int24 constant TICK_SPACING = 100;

    INonfungiblePositionManager nfpm = INonfungiblePositionManager(NFPM);

    function setUp() public {
        vm.createSelectFork("base", FORK_BLOCK);
        pool = IUniswapV3Pool(IUniswapV3Factory(FACTORY).getPool(WETH, USDC, TICK_SPACING));
        require(address(pool) != address(0), "no Slipstream pool");
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
            INonfungiblePositionManager.MintParams({
                token0: WETH,
                token1: USDC,
                tickSpacing: TICK_SPACING,
                tickLower: lo,
                tickUpper: hi,
                amount0Desired: a0,
                amount1Desired: a1,
                amount0Min: 0,
                amount1Min: 0,
                recipient: address(this),
                deadline: block.timestamp,
                sqrtPriceX96: 0
            })
        );
        lastTokenId = tokenId;
    }

    function _burnAll(uint256 tokenId, uint128 liq) internal override returns (uint256 x, uint256 y) {
        (x, y) = nfpm.decreaseLiquidity(
            INonfungiblePositionManager.DecreaseLiquidityParams({
                tokenId: tokenId,
                liquidity: liq,
                amount0Min: 0,
                amount1Min: 0,
                deadline: block.timestamp
            })
        );
        nfpm.collect(
            INonfungiblePositionManager.CollectParams({
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
            INonfungiblePositionManager.MintParams({
                token0: WETH,
                token1: USDC,
                tickSpacing: TICK_SPACING,
                tickLower: lo,
                tickUpper: hi,
                amount0Desired: a0,
                amount1Desired: a1,
                amount0Min: 0,
                amount1Min: 0,
                recipient: address(this),
                deadline: block.timestamp,
                sqrtPriceX96: 0
            })
        );
    }
}
