"""Probe 1 -- pooled overshoot and actuation delay over the census.

Port of the companion paper's `overshoot_probe.py` into this act's own verification surface; logic and iteration order are
unchanged so the output reproduces the captured artefact `overshoot-probe.json` exactly. Deterministic: no RNG.

This is the paper's negative baseline: per-cell-normalised overshoots
match the diffusion-with-lag benchmark on the pooled population, and the
delay-invariance of overshoot (the long/short scaling ratio) is the
policy-gating signature that kills the naive pooled inversion (delay-invariance
dichotomy).

Run:  python3 probe_pooled.py     (writes results/overshoot-probe.json)
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict

import numpy as np

from common import (DB, FAST_DELAY, FAT_MULT, EXPONENTIAL, HALF_NORMAL,
                    LOOKBACK, RESULTS, REBALANCE_SQL, STALE_GUARD,
                    classify_event, connect, crossing_delay,
                    load_cache, load_census_cells, q)


def main():
    cells = load_census_cells()
    print(f"{len(cells)} census-clean cells", flush=True)

    con = connect()
    by_pool = defaultdict(list)
    for s, p, phi in cells:
        by_pool[p].append((s, phi))

    events = []          # per-event records
    interior = 0
    n_total = 0
    for pool, senders in sorted(by_pool.items()):
        cb, ck = load_cache(pool)
        for sender, phi in senders:
            rows = con.execute(REBALANCE_SQL,
                               [sender, pool, STALE_GUARD]).fetchall()
            for blk, plo, phi_u, ft, u, gap in rows:
                if u is None or not math.isfinite(u) or not 0.0 <= u <= 1.0:
                    continue
                n_total += 1
                cls = classify_event(phi, u, plo, phi_u)
                if cls is None:
                    interior += 1
                    continue
                d, line, over_w = cls
                W = phi_u - plo
                delay = (crossing_delay(cb, ck, blk, line, d)
                         if cb is not None else None)
                events.append({"sender": sender, "pool": pool, "phi": phi,
                               "over_w": over_w, "over_t": over_w * W,
                               "delay": delay, "gap": int(gap), "dir": d})
        print(f"  {pool[:10]}: {len(events):,} trigger firings so far",
              flush=True)

    # per-cell normalisation and per-operator medians
    by_cell = defaultdict(list)
    for e in events:
        by_cell[(e["sender"], e["pool"])].append(e)
    norm = []                    # overshoot / cell median
    fast_large = 0
    n_delay = 0
    op_stats = defaultdict(lambda: {"over_w": [], "delay": [], "n": 0})
    for (s, p), evs in by_cell.items():
        med = float(np.median([e["over_w"] for e in evs]))
        for e in evs:
            if med > 0:
                norm.append(e["over_w"] / med)
            if e["delay"] is not None:
                n_delay += 1
                if e["delay"] <= FAST_DELAY and med > 0 \
                        and e["over_w"] > FAT_MULT * med:
                    fast_large += 1
        st = op_stats[s]
        st["over_w"].append(med)
        st["delay"].extend(e["delay"] for e in evs if e["delay"] is not None)
        st["n"] += len(evs)

    norm = np.array(norm)
    delays = np.array([e["delay"] for e in events if e["delay"] is not None])
    overs_t = np.array([e["over_t"] for e in events])

    # diffusive scaling: per-event over_t^2 / delay, compared across delay bins
    sc_short, sc_long = [], []
    for e in events:
        if e["delay"] and e["delay"] > 0 and e["over_t"] > 0:
            v = e["over_t"] ** 2 / e["delay"]
            (sc_short if e["delay"] <= 20 else sc_long).append(v)

    summary = {
        "n_cells": len(by_cell),
        "n_events_valid_u": n_total,
        "interior_fraction": round(interior / n_total, 4) if n_total else None,
        "n_trigger_firings": len(events),
        "overshoot_width_units": {
            "q50": q([e["over_w"] for e in events], .5),
            "q90": q([e["over_w"] for e in events], .9),
            "q99": q([e["over_w"] for e in events], .99)},
        "overshoot_ticks": {"q50": q(overs_t, .5), "q90": q(overs_t, .9),
                            "q99": q(overs_t, .99)},
        "normalised_tail": {
            "q90_q50": round(q(norm, .9) / q(norm, .5), 2) if len(norm) else None,
            "q99_q50": round(q(norm, .99) / q(norm, .5), 2) if len(norm) else None,
            "half_normal_benchmark": HALF_NORMAL,
            "exponential_benchmark": EXPONENTIAL},
        "delay_blocks": {
            "n_measured": int(n_delay),
            "censored_fraction": round(1 - n_delay / len(events), 4)
            if events else None,
            "q50": q(delays, .5), "q90": q(delays, .9), "q99": q(delays, .99)},
        "diffusive_scaling": {
            "median_over2_per_delay_short(<=20blk)": q(sc_short, .5),
            "median_over2_per_delay_long(>20blk)": q(sc_long, .5),
            "long_short_ratio": round(q(sc_long, .5) / q(sc_short, .5), 3)
            if sc_short and sc_long else None},
        "jump_signature": {
            "fast_large_events": int(fast_large),
            "definition": f"delay<={FAST_DELAY} blk & overshoot>"
                          f"{FAT_MULT}x cell median",
            "fraction_of_measured": round(fast_large / n_delay, 4)
            if n_delay else None},
    }

    operators = {s: {"n_firings": st["n"],
                     "median_cell_overshoot_w": round(float(
                         np.median(st["over_w"])), 4),
                     "median_delay_blocks": (float(np.median(st["delay"]))
                                             if st["delay"] else None)}
                 for s, st in op_stats.items()}

    out = {"db": DB, "lookback_blocks": LOOKBACK, "stale_guard": STALE_GUARD,
           "summary": summary, "operators": operators}
    os.makedirs(RESULTS, exist_ok=True)
    with open(RESULTS + "/overshoot-probe.json", "w") as f:
        json.dump(out, f, indent=1)
    print("\n=== probe 1: pooled overshoot / actuation ===")
    print(json.dumps(summary, indent=1))
    dm = sorted(v["median_delay_blocks"] for v in operators.values()
                if v["median_delay_blocks"] is not None)
    if dm:
        print(f"\nper-operator median delay (blocks): "
              f"q10 {dm[len(dm)//10]}, median {dm[len(dm)//2]}, "
              f"q90 {dm[9*len(dm)//10]}")
    print("wrote results/overshoot-probe.json", flush=True)


if __name__ == "__main__":
    main()
