"""Probe 6 -- direct jump detection on the tick stream (the validation
leg), with the bipower-versus-realised scale comparison.

Pre-specified before the first run.

The original plan named `Datasets/aerodrome/swaps_topN.parquet` as the
validation source; a coverage check this session found only 2 of the
50 census pools in it, so the per-pool tick cache (the indexed tick
stream for exactly these pools) is the source, and the parquet serves
as an independent-provenance cross-check on the overlapping pools
(run separately, recorded alongside).

Detection. Per pool: collapse the cache to one tick per block (last
sample); form displacements d_j between consecutive present blocks
with gap g_j <= 2 blocks (dense samples). At each dense sample,
trailing 1-day local scale over [b_j - 43200, b_j), two estimators:
  RV  sqrt(sum d^2 / span)                (probe 3's estimator)
  BV  sqrt((pi/2) * sum |d_i||d_{i-1}| / span)   (bipower; jump-robust)
admission >= 30 window samples spanning >= half the window. A dense
sample is a JUMP if |d_j| > 3 * sigma * sqrt(g_j), scored under each
estimator. Per pool: dense-sample count, jump rates (per dense sample
and per 10k blocks), jump sizes in sigma units (q50, q99), and the
median RV/BV ratio (the within-window jump inflation of RV; bias
budget, conservative direction).

Validation. Across pools scored by probe 5 (firing-based fraction>3,
n >= 30): Spearman rank correlation with the tick-stream jump rate
(BV-based), computed here with no scipy dependency. Agreement of
ranks (and same-order magnitudes) is the acceptance criterion;
disagreement is reportable and localises to pools.

Reads probe 5's output from results/. Deterministic: no RNG.

Run:  python3 probe_jumpvalidation.py (writes results/jump-validation.json)
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

from common import RESULTS, load_cache, load_census_cells, q

TRAIL = 43_200
MIN_SAMPLES = 30
GAP_MAX = 2
CUT = 3.0


def per_block(cb, ck):
    """Last tick per block."""
    keep = np.r_[cb[1:] != cb[:-1], True]
    return cb[keep], ck[keep].astype(float)


def rolling_scales(b, t):
    """Trailing-window RV and BV local scales at index j, summing
    displacements ending strictly before b[j] (the candidate displacement
    ending at b[j] is excluded, mirroring probe 3's local_sigma); NaN
    where admission fails."""
    n = len(b)
    d = np.diff(t)                      # d[i] ends at block b[i+1]
    # padded prefixes: P[m] = sum over displacements ending at index <= m-1
    P2 = np.r_[0.0, np.cumsum(np.r_[0.0, d * d])]
    PP = np.r_[0.0, np.cumsum(np.r_[0.0, 0.0,
                                    np.abs(d[1:]) * np.abs(d[:-1])])]
    lo = np.searchsorted(b, b - TRAIL)
    idx = np.arange(n)
    s2 = P2[idx] - P2[lo]               # ends in [lo, j-1]
    sp = PP[idx] - PP[lo]
    prev = b[np.maximum(idx - 1, 0)]
    span = (prev - b[lo]).astype(float)
    cnt = idx - lo
    rv = np.full(n, np.nan)
    bv = np.full(n, np.nan)
    ok = (cnt >= MIN_SAMPLES) & (span >= TRAIL / 2)
    with np.errstate(invalid="ignore", divide="ignore"):
        rv[ok] = np.sqrt(s2[ok] / span[ok])
        bv[ok] = np.sqrt((math.pi / 2) * sp[ok] / span[ok])
    return rv, bv


def spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean()
    ry -= ry.mean()
    den = math.sqrt(float((rx * rx).sum() * (ry * ry).sum()))
    return float((rx * ry).sum() / den) if den > 0 else None


def main():
    cells = load_census_cells()
    pools = sorted({p for _, p, _ in cells})

    out_pools = {}
    for pool in pools:
        cb, ck = load_cache(pool)
        if cb is None or len(cb) < 200:
            continue
        b, t = per_block(cb, ck)
        rv, bv = rolling_scales(b, t)
        d = np.diff(t)
        g = np.diff(b).astype(float)
        dense = g <= GAP_MAX
        # scale at the displacement's end block, window ending before it
        rv_e, bv_e = rv[1:], bv[1:]
        ok_rv = dense & np.isfinite(rv_e) & (rv_e > 0)
        ok_bv = dense & np.isfinite(bv_e) & (bv_e > 0)
        z_rv = np.abs(d[ok_rv]) / (rv_e[ok_rv] * np.sqrt(g[ok_rv]))
        z_bv = np.abs(d[ok_bv]) / (bv_e[ok_bv] * np.sqrt(g[ok_bv]))
        if len(z_rv) < 500:
            continue
        span_blocks = float(b[-1] - b[0])
        jr = z_rv[z_rv > CUT]
        jb = z_bv[z_bv > CUT]
        ratio = rv_e[ok_bv & ok_rv] / bv_e[ok_bv & ok_rv] \
            if (ok_bv & ok_rv).any() else np.array([])
        out_pools[pool] = {
            "n_dense": int(len(z_rv)),
            "jump_rate_RV": round(float(np.mean(z_rv > CUT)), 5),
            "jump_rate_BV": round(float(np.mean(z_bv > CUT)), 5),
            "jumps_per_10k_blocks_BV": round(
                float((z_bv > CUT).sum()) / span_blocks * 1e4, 2),
            "jump_sigma_q50_BV": round(q(jb.tolist(), .5), 2)
            if len(jb) else None,
            "jump_sigma_q99_BV": round(q(jb.tolist(), .99), 2)
            if len(jb) else None,
            "rv_over_bv_median": round(float(np.median(ratio)), 3)
            if len(ratio) else None}

    perpool = json.load(open(RESULTS + "/perpool-tails.json"))
    fire = {p: v["fraction>3"] for p, v in perpool["pools"].items()}
    common = sorted(set(fire) & set(out_pools))
    rho = None
    if len(common) >= 5:
        rho = spearman(np.array([fire[p] for p in common]),
                       np.array([out_pools[p]["jump_rate_BV"]
                                 for p in common]))

    rates = [v["jump_rate_BV"] for v in out_pools.values()]
    ratios = [v["rv_over_bv_median"] for v in out_pools.values()
              if v["rv_over_bv_median"] is not None]
    out = {
        "design": {"gap_max_blocks": GAP_MAX, "trail_blocks": TRAIL,
                   "cut": CUT, "note": "tick cache is the source; "
                   "swaps_topN.parquet covers 2/50 census pools "
                   "(coverage check 2026-08-09)"},
        "n_pools": len(out_pools),
        "population": {
            "jump_rate_BV_q50": round(q(rates, .5), 5) if rates else None,
            "jump_rate_BV_q90": round(q(rates, .9), 5) if rates else None,
            "rv_over_bv_median_of_medians": round(q(ratios, .5), 3)
            if ratios else None},
        "validation": {
            "n_pools_common": len(common),
            "spearman_fire_vs_tick_BV": round(rho, 3)
            if rho is not None else None},
        "pools": out_pools,
    }
    os.makedirs(RESULTS, exist_ok=True)
    with open(RESULTS + "/jump-validation.json", "w") as f:
        json.dump(out, f, indent=1)
    print("=== probe 6: tick-stream jump validation ===")
    print(json.dumps({k: v for k, v in out.items() if k != "pools"},
                     indent=1))
    print("wrote results/jump-validation.json", flush=True)


if __name__ == "__main__":
    main()
