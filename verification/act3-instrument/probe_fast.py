"""Probe 2 -- the conditioned rerun: fast strata and near-zero delay.

Port of the companion paper's `overshoot_fast.py` into this act's
verification surface; logic and iteration order unchanged, reproduces the captured
artefact (`overshoot-fast.json`, 2026-08-09) exactly. Deterministic.

The paper's positive baseline: fast-operator strata fatten past the
half-normal benchmark, and near-zero-delay overshoot ratios against
sigma sqrt(delay) carry mass far beyond the folded-normal null; the
identification these numbers seed is the small-delay identification theorem.

Reads probe 1's output from this surface's own results/ (run
probe_pooled.py first).

Run:  python3 probe_fast.py      (writes results/overshoot-fast.json)
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict

import numpy as np

from common import (FOLDED_NORMAL, HALF_NORMAL, RESULTS, REBALANCE_SQL,
                    STALE_GUARD, classify_event, connect, crossing_delay,
                    load_cache, load_census_cells, pool_sigma, q)

OP_THRESHOLDS = [50, 100, 300]      # per-operator median delay strata, blocks
DELAY_BINS = [2, 5, 10]             # near-zero-delay event bins, blocks

FAST_SQL = """
    SELECT block, prev_lower, prev_upper, u
    FROM rebalances
    WHERE sender = ? AND pool = ? AND firing_tick IS NOT NULL
      AND tick_gap_blocks <= ? AND u IS NOT NULL
      AND prev_upper > prev_lower
    ORDER BY block"""


def collect_events(con, by_pool):
    """Trigger firings with delays plus per-pool era sigma; the shared
    event walk of probes 2-4."""
    events, sigmas = [], {}
    for pool, senders in sorted(by_pool.items()):
        cb, ck = load_cache(pool)
        sigmas[pool] = pool_sigma(cb, ck)
        for sender, phi in senders:
            rows = con.execute(FAST_SQL,
                               [sender, pool, STALE_GUARD]).fetchall()
            for blk, plo, phi_u, u in rows:
                if u is None or not math.isfinite(u) or not 0.0 <= u <= 1.0:
                    continue
                cls = classify_event(phi, u, plo, phi_u)
                if cls is None:
                    continue
                d, line, over_w = cls
                W = phi_u - plo
                delay = (crossing_delay(cb, ck, blk, line, d)
                         if cb is not None else None)
                events.append({"sender": sender, "pool": pool,
                               "over_w": over_w, "over_t": over_w * W,
                               "delay": delay, "block": blk,
                               "line": line, "dir": d})
    return events, sigmas


def tail(evs):
    """Per-cell-normalised tail ratios over an event subset."""
    by_cell = defaultdict(list)
    for e in evs:
        by_cell[(e["sender"], e["pool"])].append(e["over_w"])
    norm = []
    for vals in by_cell.values():
        med = float(np.median(vals))
        if med > 0:
            norm.extend(v / med for v in vals)
    if len(norm) < 200:
        return None
    return {"n_cells": len(by_cell), "n_events": len(norm),
            "q90_q50": round(q(norm, .9) / q(norm, .5), 2),
            "q99_q50": round(q(norm, .99) / q(norm, .5), 2)}


def main():
    probe = json.load(open(RESULTS + "/overshoot-probe.json"))
    op_delay = {s: v["median_delay_blocks"]
                for s, v in probe["operators"].items()}

    cells = load_census_cells()
    by_pool = defaultdict(list)
    for s, p, phi in cells:
        by_pool[p].append((s, phi))

    con = connect()
    events, sigmas = collect_events(con, by_pool)

    strata = {}
    for thr in OP_THRESHOLDS:
        fast_ops = {s for s, d in op_delay.items()
                    if d is not None and d <= thr}
        strata[f"op_median_delay<={thr}blk"] = {
            "n_operators": len(fast_ops),
            "tail": tail([e for e in events if e["sender"] in fast_ops])}

    # near-zero-delay jump test, all operators
    delay_tests = {}
    for db_ in DELAY_BINS:
        ratios = []
        for e in events:
            sg = sigmas.get(e["pool"])
            if (e["delay"] is not None and 0 < e["delay"] <= db_
                    and sg and sg > 0):
                ratios.append(e["over_t"] / (sg * math.sqrt(e["delay"])))
        if len(ratios) < 100:
            delay_tests[f"delay<={db_}blk"] = {"n": len(ratios)}
            continue
        delay_tests[f"delay<={db_}blk"] = {
            "n": len(ratios),
            "ratio_median": round(q(ratios, .5), 2),
            "ratio_q90": round(q(ratios, .9), 2),
            "ratio_q99": round(q(ratios, .99), 2),
            "fraction_ratio>3": round(float(np.mean(
                np.array(ratios) > 3.0)), 4)}

    out = {"benchmarks": {"half_normal_tail": HALF_NORMAL,
                          "folded_normal_ratio": FOLDED_NORMAL},
           "all_events_tail": tail(events),
           "fast_operator_strata": strata,
           "near_zero_delay_jump_test": delay_tests,
           "n_events": len(events),
           "pools_with_sigma": sum(1 for v in sigmas.values() if v)}
    os.makedirs(RESULTS, exist_ok=True)
    with open(RESULTS + "/overshoot-fast.json", "w") as f:
        json.dump(out, f, indent=1)
    print("=== probe 2: fast strata / near-zero delay ===")
    print(json.dumps(out, indent=1))
    print("wrote results/overshoot-fast.json", flush=True)


if __name__ == "__main__":
    main()
