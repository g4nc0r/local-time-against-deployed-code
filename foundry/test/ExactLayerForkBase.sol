// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {Test, console} from "forge-std/Test.sol";
import {MockCLPoolV2} from "../src/MockCLPoolV2.sol";
import {IUniswapV3Pool, IERC20} from "../src/interfaces/Slipstream.sol";
import {TickHelpers} from "./helpers/Tick.sol";

/// @title ExactLayerForkBase
/// @notice Shared body of the exact-layer fork suite: the four exact-layer
///         results of the manuscript asserted against unmodified production
///         bytecode on Base. Two concrete children instantiate it: Aerodrome Slipstream
///         and Uniswap V3, both at the same pinned block inside the census
///         era (blocks 44.0M-49.2M).
///
/// The four results and how each is asserted on chain:
///
///  1. Share-Potential Identity (Theorem thm:share). Its integer content is
///     the binding-side mint minimum: an isolated re-placement of withdrawn
///     holdings (x, y) into a new range mints L' = min(x/x_u, y/y_u), the
///     binding side is consumed to sub-liquidity-unit slack, and the
///     retained value fraction is min(omega/omega') branch-wise. Asserted
///     on pseudo-random width pairs against actual NFPM mint returns.
///
///  2. Two-Branch Amplitude (Proposition prop:amplitude). The recentred new
///     range is realised as a whole-tick translate of the old range with the
///     price placed exactly at the translate's midpoint by a limit swap, so
///     the centring is exact and the only model gap is the translate's
///     width factor (bounded and logged). The binding side per branch
///     (Lemma lem:binding) and the wei-exact mint-minimum layer are hard
///     asserts; agreement with the closed form eq:branches is asserted at a
///     stated quantisation tolerance.
///
///  3. Corner Values (Corollary cor:corners). The price is placed exactly on
///     the range corner tick (corner sqrt ratios are tick-representable, so
///     no quantisation): burn returns are asserted all-token1 with value
///     L*w at the upper corner and all-token0 with value L*w*s_a/s_b at the
///     lower corner, and the recentred corner mint is asserted empty
///     (reverts) on the production NFPM.
///
///  4. Free Locus (Corollary cor:free). The tick-representable point of the
///     locus (the identical re-placement) is asserted free to mint
///     rounding; a tick-rounded slide along the locus is asserted an order
///     of magnitude cheaper than a generic share-moving re-placement of
///     comparable width, with the exact layer asserted throughout and
///     k >= 0 asserted on every re-placement.
///
/// Predictions come from MockCLPoolV2 (exact V3 TickMath, shared by copy
/// from the Master Equation suite, which owns the upstream) synced to the
/// live pool's slot0. Mint-side rounding differs from the predictor's
/// floor-rounding by at most a few wei; tolerances are set accordingly and
/// every residual is logged for PROOF_OUTPUT.md capture.
abstract contract ExactLayerForkBase is Test {
    uint256 internal constant Q96 = 2 ** 96;

    /// @dev Pinned inside the census era 44.0M-49.2M and inside the
    ///      production anchor's amounts window (43,635,967-45,988,726), so
    ///      the fork tier, the census, and the anchor share an era, per the
    ///      programme convention. The Geometric Siphon and Master Equation
    ///      pin 43,175,000, which predates this era and is not reused.
    uint256 internal constant FORK_BLOCK = 45_000_000;

    address internal constant WETH = 0x4200000000000000000000000000000000000006;
    address internal constant USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;

    /// @dev The two pool tokens by role, defaulting to the Base pair. A
    ///      venue suite whose token ordering or decimals differ overrides
    ///      them in setUp before _commonSetup.
    address internal tok0 = WETH;
    address internal tok1 = USDC;
    uint256 internal deal0 = 3_000_000 ether;
    uint256 internal deal1 = 1e16;

    IUniswapV3Pool internal pool;
    int24 internal spacing;
    MockCLPoolV2 internal predictor;

    // ---- venue hooks --------------------------------------------------------

    function _mintPos(int24 lo, int24 hi, uint256 a0, uint256 a1)
        internal
        virtual
        returns (uint256 tokenId, uint128 liq, uint256 used0, uint256 used1);

    function _burnAll(uint256 tokenId, uint128 liq) internal virtual returns (uint256 x, uint256 y);

    function _mintExpectRevert(int24 lo, int24 hi, uint256 a0, uint256 a1) internal virtual;

    // ---- common setup body --------------------------------------------------

    function _commonSetup() internal {
        predictor = new MockCLPoolV2(0);
        deal(tok0, address(this), deal0);
        deal(tok1, address(this), deal1);
    }

    // ---- plumbing -----------------------------------------------------------

    /// @dev V3-style exact-input swap callback; Slipstream retains the
    ///      Uniswap V3 callback selector.
    function uniswapV3SwapCallback(int256 d0, int256 d1, bytes calldata) external {
        require(msg.sender == address(pool), "callback: not pool");
        if (d0 > 0) _send(tok0, msg.sender, uint256(d0));
        if (d1 > 0) _send(tok1, msg.sender, uint256(d1));
    }

    /// @dev transfer for tokens that return no data, such as USDT.
    function _send(address token, address to, uint256 amount) internal {
        (bool ok, bytes memory ret) =
            token.call(abi.encodeWithSelector(IERC20.transfer.selector, to, amount));
        require(ok && (ret.length == 0 || abi.decode(ret, (bool))), "transfer failed");
    }

    /// @dev approve for tokens that return no data, such as USDT.
    function _approve(address token, address spender, uint256 amount) internal {
        (bool ok, bytes memory ret) =
            token.call(abi.encodeWithSelector(IERC20.approve.selector, spender, amount));
        require(ok && (ret.length == 0 || abi.decode(ret, (bool))), "approve failed");
    }

    /// @dev Move the pool price exactly to `target` with a price-limited
    ///      exact-input swap; the swap stops at the limit, so slot0 lands on
    ///      the target with no residual.
    function _placePrice(uint160 target) internal {
        (uint160 cur,) = pool.slot0();
        if (cur == target) return;
        bool zeroForOne = target < cur;
        pool.swap(address(this), zeroForOne, int256(1) << 110, target, "");
        (uint160 got,) = pool.slot0();
        require(got == target, "price placement inexact");
    }

    function _nearest(int24 t) internal view returns (int24) {
        return TickHelpers.nearest(t, spacing);
    }

    function _sqrtAt(int24 t) internal view returns (uint160) {
        return predictor.getSqrtRatioAtTick(t);
    }

    /// @dev Floor mulDiv; magnitudes in this suite stay far below 2^256.
    function _mulDiv(uint256 a, uint256 b, uint256 den) internal pure returns (uint256) {
        return (a * b) / den;
    }

    /// @dev Value of a holding (a0, a1) in token1 raw units at sqrt price s.
    function _val(uint256 a0, uint256 a1, uint160 s) internal pure returns (uint256) {
        return _mulDiv(_mulDiv(a0, s, Q96), s, Q96) + a1;
    }

    /// @dev Exact-layer prediction for re-minting holdings (x, y) into
    ///      [lo, hi] at the pool's current price: binding-side minimum
    ///      liquidity and its per-range amounts, V3-exact tick math.
    function _predict(uint256 x, uint256 y, int24 lo, int24 hi)
        internal
        returns (uint128 liqP, uint256 p0, uint256 p1)
    {
        (uint160 s, int24 t) = pool.slot0();
        predictor.setSqrtPriceX96(s, t);
        liqP = predictor.getLiquidityForAmounts(x, y, lo, hi);
        (p0, p1) = predictor.getAmountsForLiquidity(liqP, lo, hi);
    }

    /// @dev Re-mint holdings (x, y) into [lo, hi] and assert the exact layer:
    ///      L' is the binding-side minimum and the amounts match the V3-exact
    ///      prediction to mint rounding. Returns actuals.
    function _remintAsserted(uint256 x, uint256 y, int24 lo, int24 hi)
        internal
        returns (uint128 liq2, uint256 m0, uint256 m1)
    {
        (uint128 liqP, uint256 p0, uint256 p1) = _predict(x, y, lo, hi);
        (, liq2, m0, m1) = _mintPos(lo, hi, x, y);
        assertApproxEqAbs(uint256(liq2), uint256(liqP), 1, "L' = min(x/x_u, y/y_u)");
        assertApproxEqAbs(m0, p0, 3, "mint amount0 matches exact layer");
        assertApproxEqAbs(m1, p1, 3, "mint amount1 matches exact layer");
    }

    /// @dev Slack on each side of the re-mint; the binding side's slack is
    ///      below one liquidity unit's amount (plus wei rounding).
    function _bindingSlackOk(uint256 held, uint256 minted, uint128 liq2) internal pure returns (bool) {
        return held - minted <= held / uint256(liq2) + 4;
    }

    // =========================================================================
    // Test 1: Share-Potential Identity on pseudo-random width pairs.
    // =========================================================================
    function test_shareIdentity_randomWidthPairs() public {
        (uint160 s0, int24 t0) = pool.slot0();
        bytes32 seed = keccak256("local-time-e3-tier1");
        uint256 worstRetGapE18 = 0;

        for (uint256 i = 0; i < 10; i++) {
            bytes32 r = keccak256(abi.encode(seed, i));
            // half-widths 3-40 spacings; centre offsets up to half the width
            int24 w1 = int24(int256(3 + uint256(uint8(r[0])) % 38)) * spacing;
            int24 w2 = int24(int256(3 + uint256(uint8(r[1])) % 38)) * spacing;
            int24 o1 = int24(int256((uint256(r) >> 16) % uint256(int256(w1)))) - w1 / 2;
            int24 o2 = int24(int256((uint256(r) >> 120) % uint256(int256(w2)))) - w2 / 2;

            (int24 lo1, int24 hi1) = _rangeAround(t0, w1, o1);
            (int24 lo2, int24 hi2) = _rangeAround(t0, w2, o2);

            (uint256 tokenId, uint128 liq,,) = _mintPos(lo1, hi1, 5 ether, 12_500e6);
            (uint256 x, uint256 y) = _burnAll(tokenId, liq);
            (uint128 liq2, uint256 m0, uint256 m1) = _remintAsserted(x, y, lo2, hi2);

            // exactly one side binds (both only on the free locus)
            assertTrue(
                _bindingSlackOk(x, m0, liq2) || _bindingSlackOk(y, m1, liq2),
                "one side consumed to sub-unit slack"
            );

            // value form of the identity: retained fraction equals the
            // binding-side share ratio; both sides in 1e18 fixed point
            uint256 vb = _val(x, y, s0);
            uint256 va = _val(m0, m1, s0);
            assertLe(va, vb + 2, "k >= 0 (no free value)");
            (uint256 q0, uint256 q1) = predictor.getAmountsForLiquidity(uint128(1e18), lo2, hi2);
            uint256 fA = _mulDiv(va, 1e18, vb);
            uint256 fB = _mulDiv(_mulDiv(uint256(liq2), _val(q0, q1, s0), 1e18), 1e18, vb);
            uint256 gap = fA > fB ? fA - fB : fB - fA;
            if (gap > worstRetGapE18) worstRetGapE18 = gap;
            assertLe(gap, 5e9, "V_after = L' * V_unit (identity, value form)");
        }
        console.log("share identity: 10 width pairs, worst retained-fraction gap (1e18 fp):");
        console.log(worstRetGapE18);
    }

    function _rangeAround(int24 t0, int24 w, int24 off) internal view returns (int24 lo, int24 hi) {
        lo = _nearest(t0 + off - w);
        hi = _nearest(t0 + off + w);
        if (lo >= t0 - 1) lo -= spacing;
        if (hi <= t0 + 1) hi += spacing;
    }

    // =========================================================================
    // Test 2: Two-Branch Amplitude, both branches, exact centring.
    // =========================================================================
    function test_twoBranchAmplitude() public {
        int24 W = 20 * spacing; // half-width in ticks
        int24[6] memory shifts = [int24(15), int24(8), int24(2), int24(-2), int24(-8), int24(-15)];

        for (uint256 j = 0; j < shifts.length; j++) {
            uint256 snap = vm.snapshotState();
            (, int24 t0) = pool.slot0();
            int24 lo1 = _nearest(t0 - W);
            int24 hi1 = lo1 + 2 * W;
            int24 d = shifts[j] * spacing;
            int24 lo2 = lo1 + d;
            int24 hi2 = hi1 + d;

            uint256 sa = _sqrtAt(lo1);
            uint256 sb = _sqrtAt(hi1);
            // exact centring: the price goes to the translate's midpoint
            uint160 sStar = uint160((uint256(_sqrtAt(lo2)) + uint256(_sqrtAt(hi2))) / 2);
            _placePrice(sStar);

            (uint256 tokenId, uint128 liq,,) = _mintPos(lo1, hi1, 5 ether, 12_500e6);
            (uint256 x, uint256 y) = _burnAll(tokenId, liq);
            (uint128 liq2, uint256 m0, uint256 m1) = _remintAsserted(x, y, lo2, hi2);

            // Lemma lem:binding: token0 binds on the up branch, token1 down
            if (d > 0) {
                assertTrue(_bindingSlackOk(x, m0, liq2), "token0 binds on the up branch");
            } else {
                assertTrue(_bindingSlackOk(y, m1, liq2), "token1 binds on the down branch");
            }

            // closed form eq:branches at the exact (L, sbar, h, delta)
            uint256 sbar = (sa + sb) / 2;
            uint256 h = (sb - sa) / 2;
            uint256 drClosed;
            if (d > 0) {
                uint256 del = uint256(sStar) - sbar;
                drClosed = _mulDiv(_mulDiv(liq, del, Q96), 2 * sbar + h + del, sbar + h);
            } else {
                uint256 m = sbar - uint256(sStar);
                drClosed = _mulDiv(
                    _mulDiv(_mulDiv(liq, m, Q96), sbar - m, sbar + h), 2 * sbar + h - m, sbar + h - m
                );
            }
            uint256 drActual = _val(x, y, sStar) - _val(m0, m1, sStar);
            uint256 gapPpm = drClosed > drActual
                ? _mulDiv(drClosed - drActual, 1e6, drClosed)
                : _mulDiv(drActual - drClosed, 1e6, drClosed);

            console.log("amplitude case (tick shift, signed as two logs):");
            console.log(d > 0 ? uint256(int256(d)) : 0);
            console.log(d < 0 ? uint256(int256(-d)) : 0);
            console.log("  Delta-R actual / closed form (token1 raw):");
            console.log(drActual);
            console.log(drClosed);
            console.log("  gap (ppm):");
            console.log(gapPpm);
            // quantisation budget: the translate's width factor, ~|d|*5e-5
            assertLe(gapPpm, 20_000, "closed form within quantisation budget");

            vm.revertToState(snap);
        }
    }

    // =========================================================================
    // Test 3: Corner Values, price placed exactly on the corner ticks.
    // =========================================================================
    function test_cornerValues() public {
        int24 W = 6 * spacing;

        // upper corner: delta = +h
        uint256 snap = vm.snapshotState();
        (, int24 t0) = pool.slot0();
        int24 lo1 = _nearest(t0 - W);
        int24 hi1 = lo1 + 2 * W;
        (uint256 tokenId, uint128 liq,,) = _mintPos(lo1, hi1, 5 ether, 12_500e6);
        uint256 sa = _sqrtAt(lo1);
        uint256 sb = _sqrtAt(hi1);
        uint256 lw = _mulDiv(liq, sb - sa, Q96); // L * w

        _placePrice(uint160(sb));
        (uint256 x, uint256 y) = _burnAll(tokenId, liq);
        assertEq(x, 0, "upper corner: token0 side empty");
        assertApproxEqAbs(y, lw, 1, "Delta-R(h) = V(s_b) = L*w");
        // the recentred corner mint is empty: production NFPM reverts
        _mintExpectRevert(hi1 - W, hi1 + W, 0, y);
        console.log("upper corner value L*w (token1 raw), asserted vs burn:");
        console.log(y);
        vm.revertToState(snap);

        // lower corner: delta = -h
        (, t0) = pool.slot0();
        lo1 = _nearest(t0 - W);
        hi1 = lo1 + 2 * W;
        (tokenId, liq,,) = _mintPos(lo1, hi1, 5 ether, 12_500e6);
        sa = _sqrtAt(lo1);
        sb = _sqrtAt(hi1);
        lw = _mulDiv(liq, sb - sa, Q96);

        _placePrice(uint160(sa));
        (x, y) = _burnAll(tokenId, liq);
        assertEq(y, 0, "lower corner: token1 side empty");
        uint256 a0exp = (uint256(liq) << 96) * (sb - sa) / sb / sa;
        assertApproxEqAbs(x, a0exp, 1, "lower corner amount0 exact");
        // corner asymmetry: x * s_a^2 = L*w*s_a/s_b
        uint256 vDown = _val(x, 0, uint160(sa));
        uint256 rhs = _mulDiv(lw, sa, sb);
        assertApproxEqAbs(vDown, rhs, 5, "Delta-R(-h) = L*w*s_a/s_b (corner ratio)");
        _mintExpectRevert(lo1 - W, lo1 + W, x, 0);
        console.log("lower corner value (token1 raw) and L*w*s_a/s_b:");
        console.log(vDown);
        console.log(rhs);
    }

    // =========================================================================
    // Test 4: Free Locus.
    // =========================================================================
    function test_freeLocus() public {
        (uint160 s0, int24 t0) = pool.slot0();
        int24 W = 15 * spacing;
        int24 lo1 = _nearest(t0 - W);
        int24 hi1 = _nearest(t0 + W);

        // (a) the tick-representable locus point: identical re-placement
        (uint256 tokenId, uint128 liq,,) = _mintPos(lo1, hi1, 5 ether, 12_500e6);
        (uint256 x, uint256 y) = _burnAll(tokenId, liq);
        (uint128 liq2, uint256 m0, uint256 m1) = _remintAsserted(x, y, lo1, hi1);
        uint256 vb = _val(x, y, s0);
        uint256 va = _val(m0, m1, s0);
        assertLe(va, vb + 2, "k >= 0");
        assertLe(vb - va, 4, "identical re-placement free to mint rounding");
        console.log("free locus, identical re-placement: V_before - V_after (token1 raw):");
        console.log(vb - va);

        // withdraw again for the sliding cases
        (uint256 x2, uint256 y2) = _burnAll(lastTokenId, liq2);
        uint256 vb2 = _val(x2, y2, s0);

        // (b) near-locus slide: double both tick distances from the price
        uint256 snap = vm.snapshotState();
        int24 lo3 = _nearest(t0 - 2 * (t0 - lo1));
        int24 hi3 = _nearest(t0 + 2 * (hi1 - t0));
        (, uint256 n0, uint256 n1) = _remintAsserted(x2, y2, lo3, hi3);
        uint256 kSlidePpm = _mulDiv(vb2 - _val(n0, n1, s0), 1e6, vb2);
        vm.revertToState(snap);

        // (c) generic share-moving re-placement of comparable width
        int24 lo4 = _nearest(t0 - 25 * spacing);
        int24 hi4 = _nearest(t0 + 3 * spacing);
        if (hi4 <= t0 + 1) hi4 += spacing;
        (, uint256 g0, uint256 g1) = _remintAsserted(x2, y2, lo4, hi4);
        uint256 kGenPpm = _mulDiv(vb2 - _val(g0, g1, s0), 1e6, vb2);

        console.log("free locus: k (ppm of V) for locus slide vs generic move:");
        console.log(kSlidePpm);
        console.log(kGenPpm);
        assertGe(kGenPpm, 10 * kSlidePpm + 10, "locus slide an order cheaper than generic move");
    }

    /// @dev Venue children record the most recent _mintPos tokenId here so
    ///      test 4 can burn a position minted through _remintAsserted.
    uint256 internal lastTokenId;
}
