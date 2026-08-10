// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

/// @notice Minimal read interfaces for the Trader Joe Liquidity Book v2.2
///         (lfj-gg/joe-v2 at commit 067c6cc), covering only the getters the
///         Liquidity Book fork suite asserts against. Signatures transcribed from
///         `src/interfaces/ILBPair.sol` and `src/interfaces/ILBFactory.sol`
///         at that commit.
interface ILBPair {
    function getTokenX() external view returns (address tokenX);
    function getTokenY() external view returns (address tokenY);
    function getBinStep() external view returns (uint16 binStep);
    function getReserves() external view returns (uint128 reserveX, uint128 reserveY);
    function getActiveId() external view returns (uint24 activeId);
    function getBin(uint24 id) external view returns (uint128 binReserveX, uint128 binReserveY);
    function getNextNonEmptyBin(bool swapForY, uint24 id) external view returns (uint24 nextId);
    function getStaticFeeParameters()
        external
        view
        returns (
            uint16 baseFactor,
            uint16 filterPeriod,
            uint16 decayPeriod,
            uint16 reductionFactor,
            uint24 variableFeeControl,
            uint16 protocolShare,
            uint24 maxVolatilityAccumulator
        );
    function getVariableFeeParameters()
        external
        view
        returns (uint24 volatilityAccumulator, uint24 volatilityReference, uint24 idReference, uint40 timeOfLastUpdate);
    function getPriceFromId(uint24 id) external view returns (uint256 price);
    function getIdFromPrice(uint256 price) external view returns (uint24 id);
    function getSwapOut(uint128 amountIn, bool swapForY)
        external
        view
        returns (uint128 amountInLeft, uint128 amountOut, uint128 fee);
    function getLBHooksParameters() external view returns (bytes32 hooksParameters);
}

interface ILBFactory {
    struct LBPairInformation {
        uint16 binStep;
        ILBPair LBPair;
        bool createdByOwner;
        bool ignoredForRouting;
    }

    function getLBPairInformation(address tokenX, address tokenY, uint256 binStep)
        external
        view
        returns (LBPairInformation memory lbPairInformation);
}
