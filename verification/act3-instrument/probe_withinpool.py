"""Probe 4 -- the within-pool fast-versus-slow contrast .

The fast-stratum jump excess (probes 2-3) could in principle be a
selection artefact: fast operators choose pools, so the stratum is not
a random sample of pools (the selection objection). The defensible design is the
within-pool contrast, and this probe runs its empirical half, pre-
specified as follows before the first run.

Strata by per-operator median actuation delay (probe 1 output):
FAST <= 100 blocks, SLOW >= 300 blocks, mid excluded. A pool "hosts
both strata" if it carries at least one census cell from each. Within
those pools, near-zero-delay events (0 < delay <= {2,5,10} blocks) are
scored as overshoot / (sigma_local * sqrt(delay)) with the 1-day
trailing window ending strictly before the crossing (probe 3's
methodology; era sigma reported side-by-side), separately for the fast
and slow strata. Two questions, in order:

  1. REPLICATION. Does the fast-stratum excess mass beyond the 3-sigma
     cut survive with the pool set held to both-strata pools?
     Pre-specified criterion: fraction > 3 at least ten times the
     folded-normal baseline 0.0027 with n >= 100 (1d sigma, <=10 blk).
  2. POOL-COMMONALITY. Do the slow stratum's own near-zero-delay
     events in the SAME pools show excess of the same order? The jump
     component is pool-common; policy offsets are operator-specific.
     A pool-common signal appearing in both strata is what the
     forward map predicts; excess confined to the fast stratum within
     the same pools would point at operator-level artefacts instead.

Side outputs: fast-stratum stats in fast-only pools (the complement,
for the selection direction); a per-pool paired contrast over pools
with >= 15 scored events in each stratum; per-cell-normalised tail
ratios (probe 2's statistic) for each stratum within both-strata pools.

A failed contrast is a reportable finding that re-scopes v0 to
single-stratum tail functionals with a selection caveat.

Reads probe 1's output from results/ (run probe_pooled.py first).
Deterministic: no RNG.

Run:  python3 probe_withinpool.py  (writes results/withinpool-contrast.json)
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict

import numpy as np

from common import (FOLDED_NORMAL, RESULTS, local_sigma, connect,
                    load_cache, load_census_cells, q)
from probe_fast import collect_events, tail

FAST_MAX = 100          # blocks, per-operator median delay
SLOW_MIN = 300
DELAY_BINS = [2, 5, 10]
TRAIL_1D = 43_200       # blocks; probe 3's primary window
MIN_PAIRED = 15         # events per stratum for the per-pool pairing
BASELINE = 0.0027       # folded-normal fraction beyond 3


def stats(rs):
    if len(rs) < 30:
        return {"n": len(rs)}
    a = np.array(rs)
    return {"n": len(rs), "median": round(q(rs, .5), 2),
            "q90": round(q(rs, .9), 2), "q99": round(q(rs, .99), 2),
            "fraction_ratio>3": round(float(np.mean(a > 3.0)), 4)}


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
    by_pool = defaultdict(list)
    for s, p, phi in cells:
        by_pool[p].append((s, phi))

    pool_strata = {p: {stratum[s] for s, _ in senders if s in stratum}
                   for p, senders in by_pool.items()}
    both_pools = {p for p, st in pool_strata.items() if st == {"fast", "slow"}}
    fastonly_pools = {p for p, st in pool_strata.items() if st == {"fast"}}

    con = connect()
    events, _ = collect_events(con, by_pool)

    # score near-zero-delay events against 1d-trailing local sigma and
    # era sigma; cache the tick arrays per pool once
    caches = {}
    scored = []              # (pool, stratum, delay, r_1d, r_era)
    from common import pool_sigma
    for e in events:
        d = e["delay"]
        if d is None or d <= 0 or d > max(DELAY_BINS):
            continue
        st = stratum.get(e["sender"])
        if st is None:
            continue
        pool = e["pool"]
        if pool not in caches:
            cb, ck = load_cache(pool)
            caches[pool] = (cb, ck, pool_sigma(cb, ck))
        cb, ck, sg_era = caches[pool]
        if cb is None:
            continue
        sg_1d = local_sigma(cb, ck, e["block"] - d, TRAIL_1D)
        r_1d = (e["over_t"] / (sg_1d * math.sqrt(d))
                if sg_1d and sg_1d > 0 else None)
        r_era = (e["over_t"] / (sg_era * math.sqrt(d))
                 if sg_era and sg_era > 0 else None)
        scored.append({"pool": pool, "stratum": st, "delay": d,
                       "r_1d": r_1d, "r_era": r_era})

    def bin_stats(pool_set, st, key):
        out = {}
        for db_ in DELAY_BINS:
            rs = [x[key] for x in scored
                  if x["pool"] in pool_set and x["stratum"] == st
                  and x["delay"] <= db_ and x[key] is not None]
            out[f"delay<={db_}blk"] = stats(rs)
        return out

    result = {
        "design": {
            "fast_max_blocks": FAST_MAX, "slow_min_blocks": SLOW_MIN,
            "sigma": "1d trailing, ending at crossing (probe 3); era side-by-side",
            "baseline_fraction>3": BASELINE,
            "criterion_replication": ">=10x baseline, n>=100, 1d, <=10blk",
        },
        "pool_census": {
            "n_pools": len(by_pool),
            "n_both_strata": len(both_pools),
            "n_fast_only": len(fastonly_pools),
            "n_slow_only": sum(1 for st in pool_strata.values()
                               if st == {"slow"})},
        "both_strata_pools": {
            "fast_1d": bin_stats(both_pools, "fast", "r_1d"),
            "slow_1d": bin_stats(both_pools, "slow", "r_1d"),
            "fast_era": bin_stats(both_pools, "fast", "r_era"),
            "slow_era": bin_stats(both_pools, "slow", "r_era")},
        "fast_only_pools": {
            "fast_1d": bin_stats(fastonly_pools, "fast", "r_1d")},
    }

    # per-pool paired contrast (<=10 blk, 1d sigma)
    per_pool = defaultdict(lambda: {"fast": [], "slow": []})
    for x in scored:
        if x["pool"] in both_pools and x["r_1d"] is not None:
            per_pool[x["pool"]][x["stratum"]].append(x["r_1d"])
    paired = []
    for p, d in sorted(per_pool.items()):
        if len(d["fast"]) >= MIN_PAIRED and len(d["slow"]) >= MIN_PAIRED:
            ff = float(np.mean(np.array(d["fast"]) > 3.0))
            fs = float(np.mean(np.array(d["slow"]) > 3.0))
            paired.append({"pool": p, "n_fast": len(d["fast"]),
                           "n_slow": len(d["slow"]),
                           "frac3_fast": round(ff, 4),
                           "frac3_slow": round(fs, 4)})
    result["per_pool_paired"] = {
        "min_events_per_stratum": MIN_PAIRED,
        "n_pools": len(paired),
        "n_both_excess": sum(1 for r in paired
                             if r["frac3_fast"] > BASELINE * 10
                             and r["frac3_slow"] > BASELINE * 10),
        "n_fast_only_excess": sum(1 for r in paired
                                  if r["frac3_fast"] > BASELINE * 10
                                  >= r["frac3_slow"]),
        "n_slow_only_excess": sum(1 for r in paired
                                  if r["frac3_slow"] > BASELINE * 10
                                  >= r["frac3_fast"]),
        "pools": paired}

    # probe 2's per-cell-normalised tail statistic, within both-strata pools
    fast_ops = {s for s, st in stratum.items() if st == "fast"}
    slow_ops = {s for s, st in stratum.items() if st == "slow"}
    result["normalised_tail_both_strata_pools"] = {
        "fast": tail([e for e in events if e["pool"] in both_pools
                      and e["sender"] in fast_ops]),
        "slow": tail([e for e in events if e["pool"] in both_pools
                      and e["sender"] in slow_ops])}

    os.makedirs(RESULTS, exist_ok=True)
    with open(RESULTS + "/withinpool-contrast.json", "w") as f:
        json.dump(result, f, indent=1)
    print("=== probe 4: within-pool fast-vs-slow contrast ===")
    print(json.dumps(result, indent=1))
    print("wrote results/withinpool-contrast.json", flush=True)


if __name__ == "__main__":
    main()
