"""Probe 3 -- the near-zero-delay jump test with window-local sigma.

Port of the companion paper's `overshoot_localsigma.py` into this act's
verification surface; logic and iteration order unchanged, reproduces
the captured artefact (`overshoot-localsigma.json`, 2026-08-09)
exactly. Deterministic.

Scores every near-zero-delay event against sigma measured in a trailing
window ending strictly before the crossing block (candidate jump and
firing move excluded), so the null is "local pre-crossing diffusion
produced this overshoot". This is the methodology the manuscript's jump-robust
scale estimator formalises, and its excess-mass numbers are the
first evaluation of the exceedance estimator.

Run:  python3 probe_localsigma.py  (writes results/overshoot-localsigma.json)
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict

import numpy as np

from common import (FOLDED_NORMAL, RESULTS, STALE_GUARD, classify_event,
                    connect, crossing_delay, load_cache, load_census_cells,
                    local_sigma, pool_sigma, q)

DELAY_BINS = [2, 5, 10]
TRAILS = {"1d": 43_200, "7d": 302_400}

LOCALSIGMA_SQL = """
    SELECT block, prev_lower, prev_upper, u
    FROM rebalances
    WHERE sender = ? AND pool = ? AND firing_tick IS NOT NULL
      AND tick_gap_blocks <= ? AND u IS NOT NULL
      AND prev_upper > prev_lower
    ORDER BY block"""


def main():
    cells = load_census_cells()
    by_pool = defaultdict(list)
    for s, p, phi in cells:
        by_pool[p].append((s, phi))

    con = connect()

    # ratios[trail_label][delay_bin] -> list; era kept for the side-by-side
    ratios = {t: defaultdict(list) for t in TRAILS}
    ratios["era"] = defaultdict(list)
    n_events, n_sigma_miss = 0, 0
    for pool, senders in sorted(by_pool.items()):
        cb, ck = load_cache(pool)
        if cb is None:
            continue
        sg_era = pool_sigma(cb, ck)
        for sender, phi in senders:
            rows = con.execute(LOCALSIGMA_SQL,
                               [sender, pool, STALE_GUARD]).fetchall()
            for blk, plo, phi_u, u in rows:
                if u is None or not math.isfinite(u) or not 0.0 <= u <= 1.0:
                    continue
                cls = classify_event(phi, u, plo, phi_u)
                if cls is None:
                    continue
                d, line, over_w = cls
                W = phi_u - plo
                delay = crossing_delay(cb, ck, blk, line, d)
                if delay is None or delay <= 0 or delay > max(DELAY_BINS):
                    continue
                n_events += 1
                over_t = over_w * W
                crossing = blk - delay
                for label, trail in TRAILS.items():
                    sg = local_sigma(cb, ck, crossing, trail)
                    if sg is None or sg <= 0:
                        n_sigma_miss += 1
                        continue
                    r = over_t / (sg * math.sqrt(delay))
                    for db_ in DELAY_BINS:
                        if delay <= db_:
                            ratios[label][db_].append(r)
                if sg_era and sg_era > 0:
                    r = over_t / (sg_era * math.sqrt(delay))
                    for db_ in DELAY_BINS:
                        if delay <= db_:
                            ratios["era"][db_].append(r)

    def stats(rs):
        if len(rs) < 100:
            return {"n": len(rs)}
        a = np.array(rs)
        return {"n": len(rs), "median": round(q(rs, .5), 2),
                "q90": round(q(rs, .9), 2), "q99": round(q(rs, .99), 2),
                "fraction_ratio>3": round(float(np.mean(a > 3.0)), 4)}

    out = {"benchmark_folded_normal": FOLDED_NORMAL,
           "benchmark_fraction>3": 0.0027,
           "n_near_zero_delay_events": n_events,
           "tests": {label: {f"delay<={db_}blk": stats(rs[db_])
                             for db_ in DELAY_BINS}
                     for label, rs in ratios.items()}}
    os.makedirs(RESULTS, exist_ok=True)
    with open(RESULTS + "/overshoot-localsigma.json", "w") as f:
        json.dump(out, f, indent=1)
    print("=== probe 3: window-local sigma ===")
    print(json.dumps(out, indent=1))
    print("wrote results/overshoot-localsigma.json", flush=True)


if __name__ == "__main__":
    main()
