"""Probe 8 -- (F4)'s refutable implication: exceedance shape across
cadence strata.

Under the exclusion
restriction (F4), checking responds to activity but not to the size
of the individual jump, so conditioning on the recovered cadence
stratum may shift the LEVEL of the exceedance rate (check
weighting) but not the SHAPE of the exceedance distribution. The
test: within both-strata pools, compare the distribution of
exceedance sizes (scored ratio r given r > 3, delay <= 10 blk, 1d
sigma, candidate excluded) between fast and slow strata by
two-sample Kolmogorov--Smirnov and by tail-quantile ratios. A
significant shape difference refutes (F4); a level difference does
not.

Reads probe 1's output for the operator delay medians (run
probe_pooled.py first). Deterministic: no RNG.

Run:  python3 probe_shapeinvariance.py
      (writes results/shape-invariance.json)
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict

import numpy as np

from common import RESULTS, connect, load_cache, load_census_cells, local_sigma, q
from probe_fast import collect_events

DELAY_MAX = 10
TRAIL_1D = 43_200
CUT = 3.0
FAST_MAX, SLOW_MIN = 100, 300
MIN_EXC = 30                      # minimum exceedances per stratum


def ks_2samp(a, b):
    """Two-sample KS statistic and asymptotic p (stdlib arithmetic)."""
    a, b = np.sort(a), np.sort(b)
    na, nb = len(a), len(b)
    allv = np.concatenate([a, b])
    cda = np.searchsorted(a, allv, side="right") / na
    cdb = np.searchsorted(b, allv, side="right") / nb
    d = float(np.max(np.abs(cda - cdb)))
    ne = na * nb / (na + nb)
    lam = (math.sqrt(ne) + 0.12 + 0.11 / math.sqrt(ne)) * d
    p = 2 * sum((-1) ** (j - 1) * math.exp(-2 * j * j * lam * lam)
                for j in range(1, 101))
    return d, min(max(p, 0.0), 1.0)


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

    con = connect()
    events, _ = collect_events(con, by_pool)

    caches = {}
    scored = defaultdict(list)               # pool -> (ratio, stratum)
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
        st = stratum.get(e["sender"])
        if st is None:
            continue
        sg = local_sigma(cb, ck, e["block"] - d, TRAIL_1D)
        if not sg or sg <= 0:
            continue
        scored[pool].append((e["over_t"] / (sg * math.sqrt(d)), st))

    # both-strata pools only, so the pool tail is common by design
    exc = {"fast": [], "slow": []}
    pools_used = []
    for pool, rs in sorted(scored.items()):
        f = [r for r, st in rs if st == "fast" and r > CUT]
        s_ = [r for r, st in rs if st == "slow" and r > CUT]
        if f and s_:
            pools_used.append(pool)
            exc["fast"].extend(f)
            exc["slow"].extend(s_)

    def shape(rs):
        if len(rs) < MIN_EXC:
            return {"n": len(rs)}
        return {"n": len(rs), "q50": round(q(rs, .5), 2),
                "q90": round(q(rs, .9), 2), "q99": round(q(rs, .99), 2),
                "q90_over_q50": round(q(rs, .9) / q(rs, .5), 3),
                "q99_over_q50": round(q(rs, .99) / q(rs, .5), 3)}

    out = {"pools_with_both_strata_exceedances": len(pools_used),
           "fast": shape(exc["fast"]), "slow": shape(exc["slow"])}
    if len(exc["fast"]) >= MIN_EXC and len(exc["slow"]) >= MIN_EXC:
        d, p = ks_2samp(np.array(exc["fast"]), np.array(exc["slow"]))
        out["ks"] = {"D": round(d, 4), "p": round(p, 4),
                     "verdict": "shape difference NOT detected (F4 stands)"
                     if p >= 0.05 else "shape difference detected (F4 refuted"
                     " at 0.05)"}
    os.makedirs(RESULTS, exist_ok=True)
    with open(RESULTS + "/shape-invariance.json", "w") as f:
        json.dump(out, f, indent=1)
    print("=== probe 8: (F4) exceedance-shape invariance ===")
    print(json.dumps(out, indent=1))
    print("wrote results/shape-invariance.json", flush=True)


if __name__ == "__main__":
    main()
