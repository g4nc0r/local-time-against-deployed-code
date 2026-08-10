// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {Test, console} from "forge-std/Test.sol";
import {ILBPair, ILBFactory} from "../src/interfaces/LiquidityBook.sol";
import {Constants} from "../src/joe-v2/Constants.sol";
import {PriceHelper} from "../src/joe-v2/PriceHelper.sol";
import {FeeHelper} from "../src/joe-v2/FeeHelper.sol";
import {PairParameterHelper} from "../src/joe-v2/PairParameterHelper.sol";
import {Uint256x256Math} from "../src/joe-v2/math/Uint256x256Math.sol";

/// @title LocalTimeLBForkAvalanche
/// @notice Liquidity Book fork suite: the discrete-bin algebra of Appendix B
///         (app:lb) asserted against an unmodified deployed
///         LBPair v2.2 on Avalanche C-Chain, the venue class's home
///         deployment, at a pinned block. The reference implementation is the
///         source the appendix was read from (lfj-gg/joe-v2, commit 067c6cc),
///         shared by copy under src/joe-v2/; the deployed pair is the
///         factory-registered WAVAX/USDC bin-step-10 pair.
///
/// The asserted results and their tolerances:
///
///  1. Bin price law. P(i) = (1 + b*10^-4)^(i - 2^23) as a 128.128-binary
///     fixed-point number: the deployed getPriceFromId is asserted bit-exact
///     against the commit's PriceHelper across a spread of ids, the id
///     offset anchor P(2^23) = 2^128 is asserted exact, and the id-price
///     round trip closes at the active bin.
///
///  2. Step ratio. P(i+1)*2^128/P(i) is asserted equal to the 128.128
///     encoding of 1 + b*10^-4 within a stated representation tolerance
///     (the pow library's accumulated squaring truncation, 2^-88 relative
///     at this exponent magnitude); the residual is measured and logged.
///
///  3. Constant-sum depth. L_i = P(i) x_i + y_i (128.128 quote units) from
///     getBin reserves, recomputed by raw arithmetic, with the ladder's
///     single-sidedness (bins above the active id all base, below all
///     quote) asserted on a walked window of non-empty bins.
///
///  4. Per-bin amplitude. L_i/P(i): asserted to reconstruct the base
///     reserve exactly on above-active bins and to re-mark to the quote
///     reserve within one wei on below-active bins; the active-bin atom
///     amplitude is logged.
///
///  5. Per-traversal loss. L_i * b/(10^4 + b), exact in the two contract
///     constants, asserted against the price-ratio form
///     L_i (1 - P(i-1)/P(i)) evaluated at deployed prices, at a stated
///     1e-17 relative tolerance (residual logged).
///
///  6. Fee shape. Base fee B*b*10^-8 and variable fee C_v (upsilon*b)^2
///     * 10^-20 recomputed by raw arithmetic from the deployed pair's
///     static and variable fee parameters, asserted equal to the commit's
///     PairParameterHelper on the re-encoded parameter word.
///
///  7. Live fee quote. The deployed pair's getSwapOut fee on an in-bin swap
///     asserted equal to the fee predicted from the appendix formula at the
///     pair's current parameters (with the reference-update semantics
///     replicated from source), and the swap output asserted to execute at
///     exactly the active bin price.
///
///  8. Composition fee. The gross-quoted form eta*(1 + eta): the commit's
///     FeeHelper.getCompositionFee asserted equal to
///     a * f * (f + 1e18) / 1e36 across amounts at the pair's current
///     total fee.
///
/// The pair carries a nonzero LB hooks word (an LB rewarder); hooks receive
/// callbacks but do not enter the price, depth, or fee arithmetic asserted
/// here, and getSwapOut does not consult them.
contract LocalTimeLBForkAvalanche is Test {
    using Uint256x256Math for uint256;

    /// @dev Avalanche C-Chain, 2026-08-09, finalised well before capture;
    ///      chosen as a recent block with the pair active (last parameter
    ///      update 7 seconds before the pin, inside the filter period, so
    ///      the fee-quote replication exercises the no-decay branch).
    uint256 internal constant FORK_BLOCK = 92_430_000;

    /// @dev LBFactory v2.2 on Avalanche (developers.lfj.gg deployment list),
    ///      the deployment lineage of commit 067c6cc.
    address internal constant LB_FACTORY = 0xb43120c4745967fa9b93E79C149E66B0f2D6Fe0c;
    address internal constant WAVAX = 0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7;
    address internal constant USDC = 0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E;
    uint16 internal constant BIN_STEP = 10;

    /// @dev 2^23, the id offset of the price law.
    uint24 internal constant ID_OFFSET = 8_388_608;

    ILBPair internal pair;
    uint24 internal active;

    function setUp() public {
        vm.createSelectFork("avalanche", FORK_BLOCK);
        pair = ILBFactory(LB_FACTORY).getLBPairInformation(WAVAX, USDC, BIN_STEP).LBPair;
        require(address(pair) != address(0), "no LB pair");
        require(pair.getTokenX() == WAVAX && pair.getTokenY() == USDC, "unexpected token ordering");
        require(pair.getBinStep() == BIN_STEP, "unexpected bin step");
        active = pair.getActiveId();
    }

    // ---- shared helpers -----------------------------------------------------

    /// @dev Verbatim body of BinHelper.getLiquidity (joe-v2 067c6cc): the
    ///      constant-sum depth L = price * x + y in 128.128 quote units.
    ///      BinHelper.sol is not copied wholesale because it imports the
    ///      token-transfer helpers; this fifteen-line function is its only
    ///      part the suite needs.
    function _binLiquidity(uint256 x, uint256 y, uint256 price) internal pure returns (uint256 liquidity) {
        if (x > 0) {
            unchecked {
                liquidity = price * x;
                require(liquidity / x == price, "liquidity overflow");
            }
        }
        if (y > 0) {
            unchecked {
                y <<= Constants.SCALE_OFFSET;
                liquidity += y;
                require(liquidity >= y, "liquidity overflow");
            }
        }
    }

    /// @dev The surveyed bin window: five non-empty bins below the active id,
    ///      the active bin, five above, walked with getNextNonEmptyBin.
    function _binWindow() internal view returns (uint24[11] memory ids) {
        uint24 id = active;
        for (uint256 i = 0; i < 5; i++) {
            id = pair.getNextNonEmptyBin(true, id); // descending
            ids[4 - i] = id;
        }
        ids[5] = active;
        id = active;
        for (uint256 i = 0; i < 5; i++) {
            id = pair.getNextNonEmptyBin(false, id); // ascending
            ids[6 + i] = id;
        }
    }

    /// @dev Re-encode the deployed pair's fee parameters into the packed
    ///      word the commit's helpers operate on. The id reference is set
    ///      through updateIdReference (there is no direct setter), then the
    ///      true active id is written last.
    function _packedParams() internal view returns (bytes32 p) {
        (
            uint16 baseFactor,
            uint16 filterPeriod,
            uint16 decayPeriod,
            uint16 reductionFactor,
            uint24 variableFeeControl,
            uint16 protocolShare,
            uint24 maxVolAcc
        ) = pair.getStaticFeeParameters();
        (uint24 volAcc, uint24 volRef, uint24 idRef, uint40 tLast) = pair.getVariableFeeParameters();

        p = PairParameterHelper.setStaticFeeParameters(
            bytes32(0), baseFactor, filterPeriod, decayPeriod, reductionFactor, variableFeeControl, protocolShare, maxVolAcc
        );
        p = PairParameterHelper.setActiveId(p, idRef);
        p = PairParameterHelper.updateIdReference(p);
        p = PairParameterHelper.setVolatilityReference(p, volRef);
        p = PairParameterHelper.setVolatilityAccumulator(p, volAcc);
        p = PairParameterHelper.updateTimeOfLastUpdate(p, tLast);
        p = PairParameterHelper.setActiveId(p, active);
    }

    // =========================================================================
    // Test 1: bin price law, bit-exact against the commit's PriceHelper.
    // =========================================================================
    function test_binPriceLaw_exactAgainstSource() public view {
        // the id offset anchor: exponent zero, price exactly one in 128.128
        assertEq(PriceHelper.getPriceFromId(ID_OFFSET, BIN_STEP), Constants.SCALE, "P(2^23) = 2^128");
        assertEq(pair.getPriceFromId(ID_OFFSET), Constants.SCALE, "deployed P(2^23) = 2^128");

        int256[9] memory offsets = [int256(0), 1, -1, 10, -10, 100, -100, 5000, -5000];
        for (uint256 i = 0; i < offsets.length; i++) {
            uint24 id = uint24(uint256(int256(uint256(active)) + offsets[i]));
            assertEq(
                pair.getPriceFromId(id),
                PriceHelper.getPriceFromId(id, BIN_STEP),
                "deployed price bit-exact against commit source"
            );
        }

        // id-price round trip closes at the active bin
        assertEq(pair.getIdFromPrice(pair.getPriceFromId(active)), active, "round trip id -> price -> id");

        console.log("active id and its 128.128 price:");
        console.log(active);
        console.log(pair.getPriceFromId(active));
    }

    // =========================================================================
    // Test 2: adjacent-bin price ratio equals 1 + b*10^-4 in 128.128.
    // =========================================================================
    function test_binPriceLaw_stepRatio() public view {
        // the 128.128 encoding of 1 + b/10^4 (PriceHelper.getBase)
        uint256 base = Constants.SCALE + (uint256(BIN_STEP) << Constants.SCALE_OFFSET) / 10_000;

        int256[5] memory offsets = [int256(-100), -1, 0, 1, 100];
        uint256 worstGap = 0;
        for (uint256 i = 0; i < offsets.length; i++) {
            uint24 id = uint24(uint256(int256(uint256(active)) + offsets[i]));
            uint256 pLo = pair.getPriceFromId(id);
            uint256 pHi = pair.getPriceFromId(id + 1);
            uint256 ratio = pHi.mulDivRoundDown(Constants.SCALE, pLo);
            uint256 gap = ratio > base ? ratio - base : base - ratio;
            if (gap > worstGap) worstGap = gap;
        }
        console.log("step ratio vs 1 + b*10^-4: worst gap (128.128 ulp):");
        console.log(worstGap);
        // representation tolerance: the pow library truncates each of its
        // repeated squarings, and at this pair's exponent magnitude
        // (|i - 2^23| ~ 2.6e4) the accumulated error reaches order 1e11 ulp
        // of 2^-128, i.e. ~4e-28 relative (measured 142,097,247,651 ulp at
        // the pin). The bound 2^40 ulp = 2^-88 ~ 3e-27 relative states the
        // representation's accuracy class with sevenfold headroom.
        assertLe(worstGap, 1 << 40, "P(i+1)/P(i) = 1 + b*10^-4 within pow truncation");
    }

    // =========================================================================
    // Test 3: constant-sum depth and ladder single-sidedness.
    // =========================================================================
    function test_binDepth_constantSum() public view {
        uint24[11] memory ids = _binWindow();
        for (uint256 i = 0; i < ids.length; i++) {
            uint24 id = ids[i];
            (uint128 x, uint128 y) = pair.getBin(id);
            uint256 price = pair.getPriceFromId(id);

            // single-sidedness (BinHelper.verifyAmounts): base above, quote below
            if (id > active) assertEq(y, 0, "bin above active holds only base");
            if (id < active) assertEq(x, 0, "bin below active holds only quote");

            // L_i = P(i) x_i + y_i, raw arithmetic vs the source formula
            uint256 li = _binLiquidity(x, y, price);
            uint256 raw = price * uint256(x) + (uint256(y) << Constants.SCALE_OFFSET);
            assertEq(li, raw, "L_i = P(i) x_i + y_i");
            assertLe(li, Constants.MAX_LIQUIDITY_PER_BIN, "depth below the per-bin cap");
        }

        (uint128 ax, uint128 ay) = pair.getBin(active);
        uint256 la = _binLiquidity(ax, ay, pair.getPriceFromId(active));
        console.log("active bin reserves (base wei, quote wei) and depth (quote wei):");
        console.log(ax);
        console.log(ay);
        console.log(la >> Constants.SCALE_OFFSET);
    }

    // =========================================================================
    // Test 4: per-bin amplitude L_i / P(i).
    // =========================================================================
    function test_perBinAmplitude() public view {
        uint24[11] memory ids = _binWindow();
        for (uint256 i = 0; i < ids.length; i++) {
            uint24 id = ids[i];
            (uint128 x, uint128 y) = pair.getBin(id);
            uint256 price = pair.getPriceFromId(id);
            uint256 amp = _binLiquidity(x, y, price) / price; // base wei

            if (id > active) {
                // all base: the atom amplitude is the base reserve itself
                assertEq(amp, uint256(x), "amplitude reconstructs base reserve exactly");
            } else if (id < active) {
                // all quote: the amplitude re-marks to the quote reserve
                uint256 remark = amp.mulShiftRoundDown(price, Constants.SCALE_OFFSET);
                assertLe(remark, uint256(y), "re-marked amplitude bounded by quote reserve");
                assertLe(uint256(y) - remark, 1, "re-marked amplitude within one wei");
            }
        }

        (uint128 ax2, uint128 ay2) = pair.getBin(active);
        uint256 pa = pair.getPriceFromId(active);
        console.log("active bin atom amplitude L_i/P(i) (base wei):");
        console.log(_binLiquidity(ax2, ay2, pa) / pa);
    }

    // =========================================================================
    // Test 5: per-traversal loss L_i * b / (10^4 + b).
    // =========================================================================
    function test_perTraversalLoss() public view {
        uint24[2] memory ids = [active, pair.getNextNonEmptyBin(true, active)];
        uint256 worstRelE18 = 0;
        for (uint256 i = 0; i < ids.length; i++) {
            uint24 id = ids[i];
            (uint128 x, uint128 y) = pair.getBin(id);
            uint256 price = pair.getPriceFromId(id);
            uint256 li = _binLiquidity(x, y, price);

            // exact in the two contract constants
            uint256 lossExact = li.mulDivRoundDown(BIN_STEP, 10_000 + uint256(BIN_STEP));
            // price-ratio form at deployed prices: L_i (1 - P(i-1)/P(i))
            uint256 lossPrice = li - li.mulDivRoundDown(pair.getPriceFromId(id - 1), price);

            uint256 gap = lossExact > lossPrice ? lossExact - lossPrice : lossPrice - lossExact;
            uint256 relE18 = gap.mulDivRoundDown(1e18, lossExact);
            if (relE18 > worstRelE18) worstRelE18 = relE18;

            console.log("traversal loss, bin id / L_i*b/(10^4+b) (quote wei) / rel gap (1e18):");
            console.log(id);
            console.log(lossExact >> Constants.SCALE_OFFSET);
            console.log(relE18);
        }
        // machine-precision standard: 1e-17 relative
        assertLe(worstRelE18, 10, "loss forms agree to 1e-17 relative");
    }

    // =========================================================================
    // Test 6: fee shape, base and variable, against the commit's helpers.
    // =========================================================================
    function test_feeShape_baseAndVariable() public view {
        (uint16 baseFactor,,,, uint24 variableFeeControl,,) = pair.getStaticFeeParameters();
        (uint24 volAcc,,,) = pair.getVariableFeeParameters();
        bytes32 p = _packedParams();

        // eta_0 = B * b * 10^-8, in the contracts' 1e18 fee precision
        uint256 baseFee = PairParameterHelper.getBaseFee(p, BIN_STEP);
        assertEq(baseFee, uint256(baseFactor) * BIN_STEP * 1e10, "base fee B*b*10^-8");

        // eta_v = C_v * (upsilon*b)^2 * 10^-20, rounded up in the source
        uint256 varFee = PairParameterHelper.getVariableFee(p, BIN_STEP);
        uint256 prod = uint256(volAcc) * BIN_STEP;
        assertEq(varFee, (prod * prod * uint256(variableFeeControl) + 99) / 100, "variable fee C_v*(vb)^2*10^-20");

        uint256 total = PairParameterHelper.getTotalFee(p, BIN_STEP);
        assertEq(total, baseFee + varFee, "total fee is the sum");
        assertLe(total, Constants.MAX_FEE, "below the fee cap");

        console.log("fee shape at deployed parameters, base / variable / total (1e18 = 1):");
        console.log(baseFee);
        console.log(varFee);
        console.log(total);
    }

    // =========================================================================
    // Test 7: live fee quote and single-price execution.
    // =========================================================================
    function test_swapFee_liveQuote() public view {
        // replicate the view-path parameter updates from LBPair.getSwapOut
        bytes32 p = PairParameterHelper.updateReferences(_packedParams(), block.timestamp);
        p = PairParameterHelper.updateVolatilityAccumulator(p, active);
        uint128 totalFee = PairParameterHelper.getTotalFee(p, BIN_STEP);

        // an in-bin swap: 1 WAVAX for USDC, far below the active bin's quote depth
        uint128 amountIn = 1e18;
        uint128 predictedFee = FeeHelper.getFeeAmountFrom(amountIn, totalFee);
        uint256 price = pair.getPriceFromId(active);
        uint256 predictedOut = uint256(amountIn - predictedFee).mulShiftRoundDown(price, Constants.SCALE_OFFSET);

        (uint128 left, uint128 out, uint128 fee) = pair.getSwapOut(amountIn, true);
        assertEq(left, 0, "swap fills inside the active bin");
        assertEq(fee, predictedFee, "deployed fee equals the formula at current parameters");
        assertEq(out, predictedOut, "the bin trades at exactly P(i)");

        console.log("live quote, 1e18 base in: fee (base wei) / out (quote wei):");
        console.log(fee);
        console.log(out);
    }

    // =========================================================================
    // Test 8: composition fee, the gross-quoted form eta*(1 + eta).
    // =========================================================================
    function test_compositionFee_grossQuotedForm() public view {
        bytes32 p = PairParameterHelper.updateReferences(_packedParams(), block.timestamp);
        p = PairParameterHelper.updateVolatilityAccumulator(p, active);
        uint128 f = PairParameterHelper.getTotalFee(p, BIN_STEP);

        uint128[4] memory amounts = [uint128(1e12), 1e15, 1e18, 5e20];
        for (uint256 i = 0; i < amounts.length; i++) {
            uint256 expected = uint256(amounts[i]) * f * (uint256(f) + Constants.PRECISION) / Constants.SQUARED_PRECISION;
            assertEq(
                uint256(FeeHelper.getCompositionFee(amounts[i], f)),
                expected,
                "composition fee is a*eta*(1+eta), gross-quoted"
            );
        }
        console.log("composition fee on 1e18 at current total fee:");
        console.log(FeeHelper.getCompositionFee(1e18, f));
    }
}
