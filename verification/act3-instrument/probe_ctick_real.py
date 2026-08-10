"""Probe 11 -- per-pool c_tick from real trade-size distributions.

The harness's discreteness
sweep (check 7) delivered c_tick = 16 under a synthetic
trade-quantum null (+-geometric(1/2) moves, two-tick mean). This
probe removes the synthetic-model caveat: for census pools with
per-swap tick data in the lake's swap-extension parquets, the null is
rebuilt from the pool's OWN empirical per-swap tick-move
distribution (bulk, jump tail beyond the 99.5th percentile of
|move| excluded, since the null is diffusion-from-trades), the
compound walk is simulated at the harness grid of
sigma * sqrt(a-bar) / spacing, and the pool's own c_tick is the
grid value where the spurious exceedance rate falls to twice the
folded baseline. The pool's actual scale ratio then gives a
per-pool admission verdict.

Deterministic: seed 41, per-pool independent substreams.

Run:  python3 probe_ctick_real.py   (~2-4 min;
      writes results/ctick-real.json)
"""
from __future__ import annotations

import json
import math
import os

import duckdb
import numpy as np

from common import RESULTS, load_cache, load_census_cells, pool_sigma

def _lake():
    """Resolve the event lake and its file naming.

    The lake is a private dataset of recorded position-manager events. It is
    not vendored here, and neither is its file naming: point LAKE_DIR at the
    directory and LAKE_LAYOUT at a JSON file naming the members, or place
    `lake-layout.json` under verification/. Absent either, the surfaces that
    read the lake cannot run; the captured OUTPUT.md files are the answer
    they produced.
    """
    d = os.environ.get("LAKE_DIR")
    here = os.path.dirname(os.path.abspath(__file__))
    lay = os.environ.get("LAKE_LAYOUT") or os.path.join(here, "..", "lake-layout.json")
    if not d or not os.path.exists(lay):
        raise SystemExit(
            "missing input: the position-manager event lake\n"
            "  set LAKE_DIR to the lake directory, and LAKE_LAYOUT to a JSON\n"
            "  naming its members (db, amounts, swap_extensions); see\n"
            "  verification/README.md.")
    with open(lay) as f:
        return d, json.load(f)


LAKE, _L = _lake()
EXT = [os.path.join(LAKE, f) for f in _L["swap_extensions"]
       if os.path.exists(os.path.join(LAKE, f))]

SEED = 41
ABAR = 10
GRID = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0)
BASE3 = 0.0027
BD = 120_000
MIN_SWAPS = 2_000
TAIL_CUT = 0.995


def scan_two_sided(xr, half):
    """check7's every-block two-sided detector, verbatim logic."""
    events = []
    anchor = xr[0]
    up, dn = anchor + half, anchor - half
    crossed, side = None, 0
    for i, x in enumerate(xr):
        if crossed is None:
            if x > up:
                crossed, side = i, 1
            elif x < dn:
                crossed, side = i, -1
            else:
                continue
        elif (side > 0 and x <= up) or (side < 0 and x >= dn):
            crossed = None
            continue
        events.append((i - crossed + 1, (x - up) if side > 0 else (dn - x)))
        anchor = x
        up, dn = anchor + half, anchor - half
        crossed = None
    return events


def simulate(rng, moves, nu):
    """Compound walk: Poisson(nu) draws per block from the empirical
    bulk move law; returns the per-block path."""
    counts = rng.poisson(nu, BD)
    total = int(counts.sum())
    draws = moves[rng.integers(0, len(moves), total)]
    ends = np.cumsum(counts)
    sums = np.zeros(BD)
    np.add.at(sums, np.repeat(np.arange(BD), counts), draws)
    return np.cumsum(sums)


def pool_ctick(rng, moves, nu_real):
    ej2 = float(np.mean(moves.astype(float) ** 2))
    if ej2 <= 0:
        return None, None
    rates = []
    for v in GRID:
        sigma = v / math.sqrt(ABAR)
        nu = sigma * sigma / ej2
        half = max(2.0, round(7.5 * sigma)) + 0.5
        xr = simulate(rng, moves, nu)
        rr = [o / (sigma * math.sqrt(a))
              for a, o in scan_two_sided(xr, half) if a <= ABAR]
        rates.append(sum(1 for r in rr if r > 3.0) / len(rr)
                     if len(rr) >= 200 else None)
    c_tick = next((v for v, r in zip(GRID, rates)
                   if r is not None and r <= 2 * BASE3), None)
    return c_tick, rates


def main():
    census_pools = sorted({p for _, p, _ in load_census_cells()})
    con = duckdb.connect()
    con.execute("PRAGMA memory_limit='4GB'")
    files = ",".join(f"'{f}'" for f in EXT)

    out = {"pools": {}, "grid": list(GRID),
           "synthetic_harness_c_tick": 16}
    cticks = []
    for i, pool in enumerate(census_pools):
        rows = con.execute(f"""
            SELECT tick FROM read_parquet([{files}])
            WHERE pool = '{pool}' ORDER BY block, log_index
        """).fetchall()
        if len(rows) < MIN_SWAPS:
            continue
        ticks = np.array([r[0] for r in rows], dtype=np.int64)
        mv = np.diff(ticks)
        mv = mv[mv != 0]
        if len(mv) < MIN_SWAPS:
            continue
        cut = np.quantile(np.abs(mv), TAIL_CUT)
        bulk = mv[np.abs(mv) <= cut]
        rng = np.random.default_rng(SEED * 100_000 + i)
        c_tick, rates = pool_ctick(rng, bulk, None)
        cb, ck = load_cache(pool)
        sg = pool_sigma(cb, ck) if cb is not None else None
        ratio = sg * math.sqrt(ABAR) if sg else None   # spacing = 1 tick
        entry = {"n_swap_moves": int(len(mv)),
                 "bulk_cut_ticks": float(cut),
                 "mean_abs_move": round(float(np.mean(np.abs(bulk))), 2),
                 "E_J2": round(float(np.mean(bulk.astype(float) ** 2)), 1),
                 "c_tick": c_tick,
                 "spurious_rates": [None if r is None else round(r, 4)
                                    for r in rates]}
        if ratio is not None and c_tick is not None:
            entry["scale_ratio_sigma_sqrt_abar"] = round(ratio, 1)
            entry["admitted"] = bool(ratio >= c_tick)
        out["pools"][pool] = entry
        if c_tick is not None:
            cticks.append(c_tick)

    if cticks:
        out["summary"] = {
            "pools_evaluated": len(cticks),
            "c_tick_min": min(cticks), "c_tick_max": max(cticks),
            "c_tick_median": float(np.median(cticks)),
            "synthetic_16_conservative_for":
                sum(1 for c in cticks if c <= 16)}
    os.makedirs(RESULTS, exist_ok=True)
    with open(RESULTS + "/ctick-real.json", "w") as f:
        json.dump(out, f, indent=1)
    print("=== probe 11: per-pool c_tick from real trade sizes ===")
    if "summary" in out:
        print(json.dumps(out["summary"], indent=1))
    for pool, e in out["pools"].items():
        print(f"  {pool[:10]}..  c_tick {e['c_tick']}  "
              f"E[J^2] {e['E_J2']}  moves {e['n_swap_moves']}  "
              f"ratio {e.get('scale_ratio_sigma_sqrt_abar')}  "
              f"admitted {e.get('admitted')}")
    print("wrote results/ctick-real.json", flush=True)


if __name__ == "__main__":
    main()
