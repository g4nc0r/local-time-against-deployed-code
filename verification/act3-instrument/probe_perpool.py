"""Probe 5 -- per-pool tail functionals with uncertainty, the agreement
test, and the geometry census (the per-pool leg; first evaluation of the bias budget).

Pre-specified before the first run.

Estimates. Near-zero-delay events (0 < delay <= 10 blocks), ALL census
operators (any operator's small-delay firings read the pool tail; the
stratum enters only the agreement test, by design), scored
as overshoot / (sigma_1d * sqrt(delay)) with probe 3's 1-day trailing
window. Per pool: the exceedance estimate E-hat = fraction beyond 3,
a 95 % Wilson interval, the clipped jump-share estimate
w-hat_J = max(0, (E-hat - 0.0027) / (1 - 0.0027)), and exceedance
size quantiles in sigma units. Pools with n >= 30 are reported
individually; smaller pools aggregate into "small_pools_combined".

Agreement test . Per pool with >= 5 scored events in each
stratum (fast = op median delay <= 100 blk, slow = >= 300 blk):
two-sided Fisher exact test on the beyond-3 counts, stdlib
implementation (hypergeometric enumeration). Under the pool-common
null the strata share one exceedance probability; small p localises a
violated hypothesis to the cell (overidentification).

Geometry census (the binding constraint on multiscale identification). Per pool: census cells,
their phi, per-cell trigger scale = phi * median(W) in ticks (median
over the cell's trigger firings), the count k of distinct scales
(rounded to 2 significant figures), and the max/min scale ratio.

Reads probe 1's output from results/. Deterministic: no RNG.

Run:  python3 probe_perpool.py   (writes results/perpool-tails.json)
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict

import numpy as np

from common import (RESULTS, connect, load_cache, load_census_cells,
                    local_sigma, q)
from probe_fast import collect_events

DELAY_MAX = 10
TRAIL_1D = 43_200
CUT = 3.0
BASELINE = 0.0027
MIN_POOL_N = 30
MIN_STRATUM_N = 5
FAST_MAX, SLOW_MIN = 100, 300
Z95 = 1.959963984540054


def wilson(k, n, z=Z95):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def fisher_exact_2s(a, b, c, d):
    """Two-sided Fisher exact p for table [[a, b], [c, d]] by point-mass
    enumeration (sum of tables with probability <= observed)."""
    n = a + b + c + d
    r1, c1 = a + b, a + c
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)

    def logp(x):
        return (math.lgamma(r1 + 1) - math.lgamma(x + 1)
                - math.lgamma(r1 - x + 1)
                + math.lgamma(n - r1 + 1) - math.lgamma(c1 - x + 1)
                - math.lgamma(n - r1 - c1 + x + 1)
                - math.lgamma(n + 1) + math.lgamma(c1 + 1)
                + math.lgamma(n - c1 + 1))
    obs = logp(a)
    tot = 0.0
    for x in range(lo, hi + 1):
        lp = logp(x)
        if lp <= obs + 1e-9:
            tot += math.exp(lp)
    return min(1.0, tot)


def main():
    probe = json.load(open(RESULTS + "/overshoot-probe.json"))
    op_delay = {s: v["median_delay_blocks"]
                for s, v in probe["operators"].items()}
    stratum = {}
    for s, d in op_delay.items():
        if d is None:
            continue
        if d <= FAST_MAX:
            stratum[s] = "fast"
        elif d >= SLOW_MIN:
            stratum[s] = "slow"

    cells = load_census_cells()
    cell_phi = {}
    by_pool = defaultdict(list)
    for s, p, phi in cells:
        by_pool[p].append((s, phi))
        cell_phi[(s, p)] = phi

    con = connect()
    events, _ = collect_events(con, by_pool)

    # score near-zero-delay events with 1d trailing sigma
    caches = {}
    scored = defaultdict(list)          # pool -> (ratio, stratum_or_None)
    for e in events:
        d = e["delay"]
        if d is None or d <= 0 or d > DELAY_MAX:
            continue
        pool = e["pool"]
        if pool not in caches:
            caches[pool] = load_cache(pool)
        cb, ck = caches[pool]
        if cb is None:
            continue
        sg = local_sigma(cb, ck, e["block"] - d, TRAIL_1D)
        if not sg or sg <= 0:
            continue
        scored[pool].append((e["over_t"] / (sg * math.sqrt(d)),
                             stratum.get(e["sender"])))

    # per-cell trigger scales for the geometry census
    cell_W = defaultdict(list)
    for e in events:
        if e["over_w"] > 0:
            cell_W[(e["sender"], e["pool"])].append(e["over_t"] / e["over_w"])

    def pool_geometry(pool):
        scales = []
        phis = []
        for s, phi in by_pool[pool]:
            ws = cell_W.get((s, pool))
            if not ws:
                continue
            scale = phi * float(np.median(ws))
            if scale > 0:
                scales.append(scale)
                phis.append(phi)
        if not scales:
            return {"n_cells_with_scale": 0}
        sig2 = sorted({float(f"{x:.2g}") for x in scales})
        return {"n_cells_with_scale": len(scales),
                "k_distinct_scales": len(sig2),
                "phi_values": sorted(set(phis)),
                "scale_ticks_min": round(min(scales), 1),
                "scale_ticks_max": round(max(scales), 1),
                "scale_span_ratio": round(max(scales) / min(scales), 2)}

    pools_out = {}
    small_rs = []
    agreements = []
    for pool in sorted(scored):
        rs = np.array([r for r, _ in scored[pool]])
        n = len(rs)
        exc = rs[rs > CUT]
        if n < MIN_POOL_N:
            small_rs.extend(rs.tolist())
            continue
        k = int((rs > CUT).sum())
        ehat = k / n
        entry = {
            "n": n, "fraction>3": round(ehat, 4),
            "wilson95": wilson(k, n),
            "jump_share_est": round(max(0.0, (ehat - BASELINE)
                                        / (1 - BASELINE)), 4),
            "exceedance_sigma_q50": round(q(exc.tolist(), .5), 2)
            if len(exc) else None,
            "exceedance_sigma_q90": round(q(exc.tolist(), .9), 2)
            if len(exc) else None,
            "geometry": pool_geometry(pool)}
        # agreement test
        f = [r for r, st in scored[pool] if st == "fast"]
        s_ = [r for r, st in scored[pool] if st == "slow"]
        if len(f) >= MIN_STRATUM_N and len(s_) >= MIN_STRATUM_N:
            a = sum(1 for r in f if r > CUT)
            c = sum(1 for r in s_ if r > CUT)
            pval = fisher_exact_2s(a, len(f) - a, c, len(s_) - c)
            entry["agreement"] = {
                "n_fast": len(f), "n_slow": len(s_),
                "frac3_fast": round(a / len(f), 4),
                "frac3_slow": round(c / len(s_), 4),
                "fisher_p": round(pval, 4)}
            agreements.append(pval)
        pools_out[pool] = entry

    small = {}
    if small_rs:
        rs = np.array(small_rs)
        k = int((rs > CUT).sum())
        small = {"n": len(rs), "n_pools": len(scored) - len(pools_out),
                 "fraction>3": round(k / len(rs), 4),
                 "wilson95": wilson(k, len(rs))}

    all_rs = np.array([r for v in scored.values() for r, _ in v])
    k_all = int((all_rs > CUT).sum())

    # geometry census across all pools: the distribution of k
    kdist = defaultdict(int)
    for pool in by_pool:
        g = pool_geometry(pool)
        kdist[g.get("k_distinct_scales", 0)] += 1

    out = {
        "design": {"delay_max_blocks": DELAY_MAX, "cut": CUT,
                   "sigma": "1d trailing (probe 3)", "baseline": BASELINE,
                   "min_pool_n": MIN_POOL_N,
                   "strata": {"fast_max": FAST_MAX, "slow_min": SLOW_MIN}},
        "population": {"n_events_scored": int(len(all_rs)),
                       "n_pools_scored": len(scored),
                       "fraction>3": round(k_all / len(all_rs), 4),
                       "wilson95": wilson(k_all, len(all_rs))},
        "pools": pools_out,
        "small_pools_combined": small,
        "agreement_summary": {
            "n_pools_tested": len(agreements),
            "n_reject_at_0.05": sum(1 for p in agreements if p < 0.05),
            "p_values": [round(p, 4) for p in sorted(agreements)]},
        "geometry_k_distribution": dict(sorted(kdist.items())),
    }
    os.makedirs(RESULTS, exist_ok=True)
    with open(RESULTS + "/perpool-tails.json", "w") as f:
        json.dump(out, f, indent=1)
    print("=== probe 5: per-pool tail functionals ===")
    print(json.dumps(out, indent=1))
    print("wrote results/perpool-tails.json", flush=True)


if __name__ == "__main__":
    main()
