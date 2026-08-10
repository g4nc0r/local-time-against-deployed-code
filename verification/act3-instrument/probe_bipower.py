"""Probe 9 -- the bipower rerun of the captured sigma columns.

The manuscript's estimator
section designates a jump-robust bipower trailing scale; the
captured probe 3/5 columns used the RV-flavoured trailing sigma of
common.local_sigma (probe 6 measured the RV/BV inflation at a
median 1.198, so the captured excesses are conservative). This
probe recomputes the probe-3 population cells and the probe-5
per-pool readings with a bipower local scale,

    sigma_BV^2 = (pi/2) * sum |dt_i||dt_{i-1}| / span,

same window, same guards, and prints the RV-captured numbers
alongside. common.py is untouched (it is the captured surface).

Reads probe 1's output for the strata (run probe_pooled.py first)
and the captured probe 3/5 artefacts for the side-by-side.
Deterministic: no RNG.

Run:  python3 probe_bipower.py   (writes results/bipower-rerun.json)
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict

import numpy as np

from common import (MIN_SAMPLES, RESULTS, connect, load_cache,
                    load_census_cells, q)
from probe_fast import collect_events
from probe_perpool import wilson

DELAY_BINS = [2, 5, 10]
TRAILS = {"1d": 43_200, "7d": 302_400}
CUT = 3.0
MIN_POOL_N = 30


def local_sigma_bv(cb, ck, end_block, trail):
    """Bipower per-block tick scale over [end_block - trail, end_block)."""
    hi = int(np.searchsorted(cb, end_block))
    lo = int(np.searchsorted(cb, end_block - trail))
    if hi - lo < MIN_SAMPLES:
        return None
    span = float(cb[hi - 1] - cb[lo])
    if span < trail / 2:
        return None
    dt = np.abs(np.diff(ck[lo:hi].astype(float)))
    if len(dt) < 2:
        return None
    return math.sqrt((math.pi / 2) * float(np.sum(dt[1:] * dt[:-1])) / span)


def stats(rs):
    if len(rs) < 100:
        return {"n": len(rs)}
    a = np.array(rs)
    return {"n": len(rs), "median": round(q(rs, .5), 2),
            "q99": round(q(rs, .99), 2),
            "fraction_ratio>3": round(float(np.mean(a > CUT)), 4)}


def main():
    cells = load_census_cells()
    by_pool = defaultdict(list)
    for s, p, phi in cells:
        by_pool[p].append((s, phi))

    con = connect()
    events, _ = collect_events(con, by_pool)

    caches = {}
    ratios = {t: defaultdict(list) for t in TRAILS}
    perpool = defaultdict(list)
    for e in events:
        d = e["delay"]
        if d is None or d <= 0 or d > max(DELAY_BINS):
            continue
        pool = e["pool"]
        if pool not in caches:
            caches[pool] = load_cache(pool)
        cb, ck = caches[pool]
        if cb is None:
            continue
        crossing = e["block"] - d
        for label, trail in TRAILS.items():
            sg = local_sigma_bv(cb, ck, crossing, trail)
            if sg is None or sg <= 0:
                continue
            r = e["over_t"] / (sg * math.sqrt(d))
            for db_ in DELAY_BINS:
                if d <= db_:
                    ratios[label][db_].append(r)
            if label == "1d" and d <= 10:
                perpool[pool].append(r)

    pools_out = {}
    for pool, rs in sorted(perpool.items()):
        if len(rs) < MIN_POOL_N:
            continue
        k = sum(1 for r in rs if r > CUT)
        pools_out[pool] = {"n": len(rs),
                           "fraction>3": round(k / len(rs), 4),
                           "wilson95": wilson(k, len(rs))}

    captured3 = json.load(open(RESULTS + "/overshoot-localsigma.json"))
    captured5 = json.load(open(RESULTS + "/perpool-tails.json"))
    rv_pop = captured3["tests"]
    rv_pools = {p: v["fraction>3"] for p, v in captured5["pools"].items()}

    out = {"population_bipower": {label: {f"delay<={db_}blk": stats(rs[db_])
                                          for db_ in DELAY_BINS}
                                  for label, rs in ratios.items()},
           "population_rv_captured": {label: rv_pop[label]
                                      for label in TRAILS},
           "perpool_bipower": pools_out,
           "perpool_rv_captured": rv_pools}
    frs = [v["fraction>3"] for v in pools_out.values()]
    if frs:
        out["perpool_bipower_span"] = [min(frs), max(frs)]
    os.makedirs(RESULTS, exist_ok=True)
    with open(RESULTS + "/bipower-rerun.json", "w") as f:
        json.dump(out, f, indent=1)
    print("=== probe 9: bipower rerun of the sigma columns ===")
    print(json.dumps({k: v for k, v in out.items()
                      if not k.startswith("perpool_")}, indent=1))
    print("per-pool fraction>3, bipower vs captured RV:")
    for pool, e in pools_out.items():
        rv = rv_pools.get(pool)
        print(f"  {pool[:10]}..  BV {e['fraction>3']} (n {e['n']})  "
              f"RV {rv}")
    if frs:
        print(f"per-pool BV span {min(frs):.4f} to {max(frs):.4f}")
    print("wrote results/bipower-rerun.json", flush=True)


if __name__ == "__main__":
    main()
