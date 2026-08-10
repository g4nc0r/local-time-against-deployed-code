"""Probe 7 -- era-half replication of the per-pool readings.

The stated certification of (F1) era homogeneity . Splits the census era at its midpoint
block and recomputes each pool's small-delay exceedance reading in
both halves; under (F1) the two halves estimate one per-pool
functional and should disagree no more than binomial noise allows.
Scoring identical to probe 5 (delay <= 10 blk, 1d trailing sigma,
candidate excluded, cut at 3 local scales); Fisher exact per pool,
familywise correction over the tested pools.

Reads the same external inputs as probes 2-5. Deterministic: no RNG.

Run:  python3 probe_erahalf.py   (writes results/erahalf-replication.json)
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict

import numpy as np

from common import RESULTS, connect, load_cache, load_census_cells, local_sigma
from probe_fast import collect_events
from probe_perpool import fisher_exact_2s, wilson

DELAY_MAX = 10
TRAIL_1D = 43_200
CUT = 3.0
MIN_HALF_N = 30
ERA_LO, ERA_HI = 43_990_000, 49_195_202
MID = (ERA_LO + ERA_HI) // 2                 # 46,592,601


def main():
    cells = load_census_cells()
    by_pool = defaultdict(list)
    for s, p, phi in cells:
        by_pool[p].append((s, phi))

    con = connect()
    events, _ = collect_events(con, by_pool)

    caches = {}
    scored = defaultdict(list)               # pool -> (ratio, block)
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
        scored[pool].append((e["over_t"] / (sg * math.sqrt(d)), e["block"]))

    pools_out, pvals = {}, []
    pop = {"h1": [], "h2": []}
    for pool in sorted(scored):
        h1 = [r for r, b in scored[pool] if b < MID]
        h2 = [r for r, b in scored[pool] if b >= MID]
        pop["h1"].extend(h1)
        pop["h2"].extend(h2)
        if len(h1) < MIN_HALF_N or len(h2) < MIN_HALF_N:
            continue
        k1 = sum(1 for r in h1 if r > CUT)
        k2 = sum(1 for r in h2 if r > CUT)
        pval = fisher_exact_2s(k1, len(h1) - k1, k2, len(h2) - k2)
        pools_out[pool] = {
            "n_h1": len(h1), "n_h2": len(h2),
            "frac3_h1": round(k1 / len(h1), 4),
            "frac3_h2": round(k2 / len(h2), 4),
            "wilson_h1": wilson(k1, len(h1)),
            "wilson_h2": wilson(k2, len(h2)),
            "fisher_p": round(pval, 4)}
        pvals.append(pval)

    def frac(rs):
        return round(sum(1 for r in rs if r > CUT) / len(rs), 4) if rs else None

    n_tested = len(pvals)
    nominal = sum(1 for p in pvals if p < 0.05)
    famwise = sum(1 for p in pvals if p < 0.05 / max(n_tested, 1))
    out = {"mid_block": MID,
           "population": {"n_h1": len(pop["h1"]), "n_h2": len(pop["h2"]),
                          "frac3_h1": frac(pop["h1"]),
                          "frac3_h2": frac(pop["h2"])},
           "pools_tested": n_tested,
           "rejections_nominal_0.05": nominal,
           "rejections_familywise": famwise,
           "pools": pools_out}
    os.makedirs(RESULTS, exist_ok=True)
    with open(RESULTS + "/erahalf-replication.json", "w") as f:
        json.dump(out, f, indent=1)
    print("=== probe 7: era-half replication (F1 certification) ===")
    print(json.dumps({k: v for k, v in out.items() if k != "pools"}, indent=1))
    for pool, e in out["pools"].items():
        print(f"  {pool[:10]}..  h1 {e['frac3_h1']} (n {e['n_h1']})  "
              f"h2 {e['frac3_h2']} (n {e['n_h2']})  p {e['fisher_p']}")
    print("wrote results/erahalf-replication.json", flush=True)


if __name__ == "__main__":
    main()
