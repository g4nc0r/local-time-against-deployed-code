#!/usr/bin/env python3
"""Tier M3: the block-time readings, and the two-sided floor scatter.

Reads M2's stream (`m2_cells.json.gz`, `m2_ticks.json.gz`) and produces:

  1. THE FLOOR SCATTER, two-sided, ON THE SWAP-CARRYING SUBPOPULATION.
     M2 priced each firing at the pre-swap mark with the fee leg on the
     input side, so where the corrective swap is in the same pool this
     is a measurement and not the lower bound Base is confined to.

     The restriction is forced by the data, not chosen. Only about a
     fifth of mainnet firings carry their swap in the pool; the rest
     route it through an aggregator, so the value chain leaves the pool
     and cannot be closed from its logs. The two subpopulations are
     starkly different: across all priced firings the median k is
     -0.255, value RISING by a quarter, and only 24 % conserve value;
     restricted to swap-carrying firings, 81 % conserve and the median
     k is +2.5e-4, a sane rebalance cost. The first population is not
     noisy, it is unidentified. Both counts are reported. Same floor as
     fig:anchor: eta (1 - rho)^2 sigma^2 / w^2, reported at the uniform
     eta = 1e-4 anchor and at the pool's own fee tier.

  2. THE PER-BLOCK MOVE SCALE, which is NOT yet the c_tick admission.
     The cross-venue admission compares each pool's local scale against
     c_tick, the scale a one-tick-quantised walk would show at the same
     cadence, and that null comes from the Base census's simulation. What is
     computed here is only the realised per-block tick move, the
     numerator of that comparison. It is reported because it is the
     input the admission needs and because it shows the expected
     direction, but it MUST NOT be quoted against the cross-venue
     section's 1.2-9.8 ratios: those are a different statistic. Porting
     the Base census's c_tick simulation is the remaining work here.

  3. THE CLOCK. The MEV probe found exit delays 1.6x apart in blocks and
     9.3x apart in seconds between the two chains, so a delay cut cannot
     be matched on both clocks at once and the choice has to be declared.
     THIS SCRIPT DECLARES IT: the cut is matched in WALL-CLOCK SECONDS,
     not blocks, because Theorem 6's content is that the price
     cannot move far while the operator is not yet corrected, and that
     is a statement about elapsed time and diffusion, not about the
     chain's accounting unit. The block-matched cut is reported
     alongside so the choice can be audited, not hidden.

Ungated: Uniswap V3 mainnet only.

Run:  python3 m3_analysis.py
"""
import gzip
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CELLS = os.path.join(HERE, "m2_cells.json.gz")
TICKS = os.path.join(HERE, "m2_ticks.json.gz")
OUT = os.path.join(HERE, "m3_results.json")

BLOCK_SECONDS = 12.0
SECONDS_PER_YEAR = 365.25 * 86400
ETA_ANCHOR = 1e-4
BUCKET_SECONDS = 300.0
BUCKET_BLOCKS = int(BUCKET_SECONDS / BLOCK_SECONDS)   # 25 blocks
FIRING_BAR = 30
MIN_DAYS = 7
RHO_LO, RHO_HI = 1e-4, 0.5
CONSERVE_TOL = 0.05
CONSERVE_MIN_SHARE = 0.95

# Base comparators, from the captured surfaces (not recomputed here).
BASE_ABAR_BLOCKS = 10          # the paper's delay cut on Base
BASE_BLOCK_SECONDS = 2.0
def _load_pools():
    """Labels and fee tiers for the M2 pool set, from the discovery
    pass's factory verification when present."""
    vf = os.path.join(HERE, "pool_verification.json")
    pf = os.path.join(HERE, "m2_pools_uni.json")
    if os.path.exists(vf) and os.path.exists(pf):
        keep = set(json.load(open(pf)))
        return {v["pool"]: (f"{v['token0'][:8]}/{v['token1'][:8]}",
                            v["fee"])
                for v in json.load(open(vf))["verified"]
                if v["pool"] in keep}
    return {
        "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640": ("USDC/WETH", 500),
        "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8": ("USDC/WETH", 3000),
        "0x11b815efb8f581194ae79006d24e0d814b7697f6": ("WETH/USDT", 500),
        "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36": ("WETH/USDT", 3000),
        "0xcbcdf9626bc03e24f779434178a73a0b4bad62ed": ("WBTC/WETH", 3000),
        "0x99ac8ca7087fa4a2a1fb6357269965a2014abc35": ("WBTC/USDC", 3000),
    }


POOLS = _load_pools()


def tsqrt(t):
    return 1.0001 ** (t / 2.0)


def median(v):
    v = sorted(v)
    if not v:
        return float("nan")
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def q(v, p):
    v = sorted(v)
    return v[min(int(p * len(v)), len(v) - 1)] if v else float("nan")


def pool_sigma(tk, blk_lo, blk_hi):
    """Annualised sqrt-price volatility, 300-second buckets, matching the
    Base reading's convention at this chain's block time."""
    sel = [(b, t) for b, t in tk if blk_lo <= b <= blk_hi]
    if len(sel) < 50:
        return None
    buckets = {}
    for b, t in sel:
        buckets[b // BUCKET_BLOCKS] = (b, t)
    keys = sorted(buckets)
    if len(keys) < 50:
        return None
    sps = [tsqrt(buckets[k][1]) for k in keys]
    span = buckets[keys[-1]][0] - buckets[keys[0]][0]
    if span <= 0:
        return None
    rv = sum((sps[i] - sps[i - 1]) ** 2 for i in range(1, len(sps)))
    s2 = rv / (span * BLOCK_SECONDS)
    return {"sigma_s_ann": math.sqrt(s2 * SECONDS_PER_YEAR),
            "sbar": sum(sps) / len(sps), "n_buckets": len(sps)}


def ctick_ratio(tk, blk_lo, blk_hi):
    """The block-aggregated move law against its own discreteness null.

    The Base reading compared each pool's local scale to c_tick, the
    scale a one-tick-quantised random walk would show at the same
    cadence, and every pool came in below it. Here: the ratio of the
    realised per-block sqrt-price move to one tick at the pool's own
    price, which is the same comparison in the same units."""
    sel = [(b, t) for b, t in tk if blk_lo <= b <= blk_hi]
    if len(sel) < 100:
        return None
    moves = []
    for i in range(1, len(sel)):
        db = sel[i][0] - sel[i - 1][0]
        if db <= 0 or db > 50:
            continue
        moves.append(abs(sel[i][1] - sel[i - 1][1]) / math.sqrt(db))
    if len(moves) < 100:
        return None
    return {"median_tick_move_per_sqrt_block": median(moves),
            "q90": q(moves, .9), "n": len(moves)}


def main():
    cells = json.load(gzip.open(CELLS, "rt"))
    ticks = {p: [tuple(x) for x in v]
             for p, v in json.load(gzip.open(TICKS, "rt")).items()}
    for p in ticks:
        ticks[p].sort()
    out = {"block_seconds": BLOCK_SECONDS,
           "clock_decision": {
               "matched_on": "wall-clock seconds",
               "why": "Theorem 6 bounds how far the price can move "
                      "while the operator is uncorrected, which is a "
                      "statement about elapsed time and diffusion, not "
                      "about the chain's accounting unit",
               "base_cut_blocks": BASE_ABAR_BLOCKS,
               "base_cut_seconds": BASE_ABAR_BLOCKS * BASE_BLOCK_SECONDS,
               "mainnet_cut_blocks_wallclock_matched":
                   BASE_ABAR_BLOCKS * BASE_BLOCK_SECONDS / BLOCK_SECONDS,
               "mainnet_cut_blocks_if_matched_on_blocks":
                   BASE_ABAR_BLOCKS,
               "note": "the two differ by 6x; the block-matched value is "
                       "reported so the choice is auditable"},
           "cells": [], "per_pool": {}}

    # ---- 1. the floor scatter -------------------------------------------
    rows = []
    for key, c in cells.items():
        pool, op = key.split("|")
        # swap-carrying firings only: the value chain closes on those
        ks = [k for k, sw in zip(c["k"], c["sw"]) if sw]
        blks_sw = [b for b, sw in zip(c["blk"], c["sw"]) if sw]
        us_sw = [u for u, sw in zip(c["u"], c["sw"]) if sw]
        n_all = len(c["k"])
        if len(ks) < FIRING_BAR or pool not in ticks:
            continue
        blk_lo, blk_hi = min(blks_sw), max(blks_sw)
        span_years = (blk_hi - blk_lo) * BLOCK_SECONDS / SECONDS_PER_YEAR
        if span_years * 365.25 < MIN_DAYS:
            continue
        sig = pool_sigma(ticks[pool], blk_lo, blk_hi)
        if sig is None:
            continue
        u, sbar = median(us_sw), sig["sbar"]
        rho, w = u / sbar, 2 * u
        if not (RHO_LO < rho < RHO_HI):
            continue
        kept = [k for k in ks if abs(k) <= CONSERVE_TOL]
        if len(kept) < CONSERVE_MIN_SHARE * len(ks) or len(kept) < FIRING_BAR:
            continue
        mean_k = sum(kept) / len(kept)
        r_hat = mean_k * len(ks) / span_years
        base = (1 - rho) ** 2 * sig["sigma_s_ann"] ** 2 / w ** 2
        fee = POOLS.get(pool, ("?", 500))[1]
        rows.append({
            "pool": POOLS.get(pool, (pool,))[0], "pool_addr": pool,
            "operator": op, "n_firings_swap": len(ks),
            "n_firings_all": n_all, "n_conserved": len(kept),
            "swap_share": round(sum(c["sw"]) / len(c["sw"]), 4),
            "fee_share_of_value": round(median(c["fee"]), 6),
            "days": round(span_years * 365.25, 1), "rho": round(rho, 5),
            "mean_k": mean_k, "r_hat_pct": 100 * r_hat,
            "floor_anchor_pct": 100 * ETA_ANCHOR * base,
            "floor_own_pct": 100 * (fee / 1e6) * base,
            "score_anchor": r_hat / (ETA_ANCHOR * base),
            "score_own": r_hat / ((fee / 1e6) * base),
        })
    rows.sort(key=lambda r: -r["n_firings_swap"])
    out["cells"] = rows
    if rows:
        sa = [r["score_anchor"] for r in rows]
        so = [r["score_own"] for r in rows]
        out["scatter_summary"] = {
            "n_cells": len(rows),
            "n_pools": len(set(r["pool_addr"] for r in rows)),
            "n_operators": len(set(r["operator"] for r in rows)),
            "firings_swap_carrying": sum(r["n_firings_swap"] for r in rows),
            "firings_all_in_those_cells": sum(r["n_firings_all"] for r in rows),
            "median_swap_share": round(median(
                [r["swap_share"] for r in rows]), 4),
            "anchor_eta": {"above_1": sum(1 for x in sa if x > 1),
                           "median": round(median(sa), 2),
                           "q10": round(q(sa, .1), 2),
                           "q90": round(q(sa, .9), 2)},
            "own_fee": {"above_1": sum(1 for x in so if x > 1),
                        "median": round(median(so), 2),
                        "q10": round(q(so, .1), 2),
                        "q90": round(q(so, .9), 2)},
            "two_sided": True,
            "population": "swap-carrying firings only; see the module "
                          "docstring for why the rest are unidentified",
            "note": "priced at the pre-swap mark with the fee leg on the "
                    "input side, so this is a measurement, not the lower "
                    "bound the Base surface is confined to",
        }

    # ---- 2. the c_tick admission ----------------------------------------
    for pool, tk in ticks.items():
        r = ctick_ratio(tk, min(b for b, _ in tk), max(b for b, _ in tk))
        if r:
            out["per_pool"][POOLS.get(pool, (pool,))[0] + " " + pool[:8]] = r

    json.dump(out, open(OUT, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "cells"},
                     indent=1))
    print(f"\n{len(rows)} cells; wrote {OUT}")


if __name__ == "__main__":
    main()
