#!/usr/bin/env python3
"""MEV probe, Base side of readings A and B, from the local layer.

The mainnet probe reads firing position and exit delay by streaming.
On Base both are already on disk: `univ3-layer.db` holds the
operator-keyed `rebalances` table (with the previous range and the
firing tick) and `swap_ticks`, the per-block last Swap tick. So the
Base half of A and B needs no stream, and can therefore run over the
FULL census era rather than the short window the streamed readings C
and D use.

Definitions are the streamed probe's, and the streamed probe's are the
Base census's: firing position u in the previous range, and exit delay as
blocks since the tick was last inside that range, capped at the
20,000-block lookback.

Ungated: Uniswap V3 Base only. Read-only on the lake.

Run:  python3 base_local_ab.py
"""
from __future__ import annotations

import json
import os

import duckdb
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
# The Uniswap V3 Base layer is not vendored here; point UNIV3_LAYER_DB at it.
DB = os.environ.get("UNIV3_LAYER_DB",
                    os.path.join(HERE, "univ3-layer.db"))
OUT = os.path.join(HERE, "mev_probe_base_local_ab.json")
LOOKBACK = 20_000
BLOCK_SECONDS = 2.0
POOLS = {
    "0xd0b53d9277642d899df5c87a3966a349a798f224": "WETH/USDC 500",
    "0x6c561b446416e1a00e8e93e221854d6ea4171372": "WETH/USDC 3000",
    "0x8c7080564b5a792a33ef2fd473fba6364d5495e5": "WETH/cbBTC 3000",
}


def q(v, p):
    return float(np.quantile(v, p)) if len(v) else float("nan")


def main():
    con = duckdb.connect(DB, read_only=True)
    out = {"block_seconds": BLOCK_SECONDS, "lookback": LOOKBACK,
           "source": "univ3-layer.db (rebalances, swap_ticks)",
           "per_pool": {}}
    all_u, all_d = [], []
    for pool, label in POOLS.items():
        rows = con.execute("""
            SELECT block, firing_tick, prev_lower, prev_upper
            FROM rebalances
            WHERE pool = ? AND prev_lower IS NOT NULL
              AND firing_tick IS NOT NULL AND prev_upper > prev_lower
            ORDER BY block
        """, [pool]).fetchall()
        cache = con.execute("""
            SELECT block, tick FROM swap_ticks WHERE pool = ?
            ORDER BY block
        """, [pool]).fetchnumpy()
        cb, ck = cache["block"].astype(np.int64), \
            cache["tick"].astype(np.int64)
        us, ds = [], []
        for blk, ft, plo, phi_u in rows:
            us.append((ft - plo) / (phi_u - plo))
            hi = int(np.searchsorted(cb, blk))
            lo = max(0, int(np.searchsorted(cb, blk - LOOKBACK)))
            if hi <= lo:
                continue
            w = ck[lo:hi]
            inside = (w >= plo) & (w <= phi_u)
            nz = np.nonzero(inside)[0]
            if len(nz):
                ds.append(int(blk - cb[lo + nz[-1]]))
        all_u += us
        all_d += ds
        out["per_pool"][label] = {
            "n_firings": len(rows), "n_delay": len(ds),
            "interior_fraction": round(
                float(np.mean([(0 < u < 1) for u in us])), 4) if us else None,
            "u_q50": round(q(us, .5), 4),
            "delay_mass_at_0": round(
                float(np.mean([d == 0 for d in ds])), 4) if ds else None,
            "delay_q50": q(ds, .5), "delay_q90": q(ds, .9),
        }
    con.close()
    out["A_firing_position"] = {
        "n": len(all_u),
        "interior_fraction": round(
            float(np.mean([(0 < u < 1) for u in all_u])), 4),
        "q10": round(q(all_u, .10), 4), "q50": round(q(all_u, .50), 4),
        "q90": round(q(all_u, .90), 4),
    }
    out["B_exit_delay_blocks"] = {
        "n": len(all_d),
        "_note": "delay >= 1 BY CONSTRUCTION: the tick cache carries "
                 "one entry per block and the search takes blocks "
                 "strictly before the firing, so a same-block "
                 "correction is not observable here. The mass-at-zero "
                 "question of the spec's 5.1 is answered by reading C, "
                 "which orders by log index inside the block. The same "
                 "construction is used on both chains, so the "
                 "distributions remain comparable above zero.",
        "mass_at_0_structural_zero": round(
            float(np.mean([d == 0 for d in all_d])), 4),
        "mass_le_1": round(float(np.mean([d <= 1 for d in all_d])), 4),
        "q50": q(all_d, .5), "q90": q(all_d, .9),
        "q50_seconds": q(all_d, .5) * BLOCK_SECONDS,
        "q90_seconds": q(all_d, .9) * BLOCK_SECONDS,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print(json.dumps(out, indent=1))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
