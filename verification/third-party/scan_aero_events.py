#!/usr/bin/env python3
"""Tier 2, Aerodrome side: streaming identity evaluation on sampled
era windows over the census pools.

The census pools carry ~28 Mint/Burn events per block era-wide, so
nothing is collected; each block's (tx, pool) groups are evaluated
inline (t2_eval.identity_of, the anchor's event discipline) and only
aggregates survive. Sampling: WINDOWS windows of WIDTH blocks evenly
spaced across the census era; coverage is reported alongside the
numbers. Slipstream shares Uniswap V3's event signatures, so the WS0
scanner's decoding carries over unchanged.

Output: t2_aero.json + printed summary (captured in aero_scan.log).

Run detached:
  systemd-run --user --unit=t2-aero-scan \
    --property=WorkingDirectory="$PWD" \
    bash -lc 'python3 scan_aero_events.py > aero_scan.log 2>&1'
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "third-party"))
import ws0_probe as w  # noqa: E402
import t2_eval  # noqa: E402

OUT = os.path.join(
    HERE, "t2_aero_full.json" if os.environ.get("AERO_FULL") else "t2_aero.json"
)
PAIRS = os.path.join(HERE, "aero_census_pairs.json")

AERO_NFPM = "0x827922686190790b37229fd06084350e74485b72"
# AERO_FULL=1 switches from sampled windows to the full era (separate
# checkpoint), for the definitive interior-clean population.
FULL = bool(os.environ.get("AERO_FULL"))
WINDOWS = 1 if FULL else 30
WIDTH = (0 if FULL else 20_000)


def main():
    if os.path.exists(OUT):
        print("checkpoint exists; nothing to do")
        return
    pools = [r["pool"].lower() for r in json.load(open(PAIRS))
             if r.get("pair") != "ERR"]
    w.log(f"aero Tier-2 scan: {len(pools)} census pools, {WINDOWS} windows "
          f"of {WIDTH:,} blocks across era {w.ERA_LO:,}-{w.ERA_HI:,}")
    firings = {}
    t2 = {"classes": {}, "id_errs": [], "mint_errs": [],
          "price_errs": [], "ops": {}}
    if FULL:
        w.stream_pass(pools, w.ERA_LO, w.ERA_HI, firings, t2, AERO_NFPM)
        w.log(f"  full era: clean {len(t2['id_errs'])}, "
              f"classes {t2['classes']}")
    else:
        step = (w.ERA_HI - w.ERA_LO - WIDTH) // (WINDOWS - 1)
        for i in range(WINDOWS):
            lo = w.ERA_LO + i * step
            w.stream_pass(pools, lo, lo + WIDTH - 1, firings, t2, AERO_NFPM)
            w.log(f"  window {i + 1}/{WINDOWS}: cumulative clean "
                  f"{len(t2['id_errs'])}, classes {t2['classes']}")

    ie = t2["id_errs"]
    ops10 = sum(1 for v in t2["ops"].values() if v >= 10)
    summary = {
        "venue": "aerodrome-slipstream",
        "sampled_blocks": (w.ERA_HI - w.ERA_LO if FULL else WINDOWS * WIDTH),
        "era": [w.ERA_LO, w.ERA_HI],
        "classes": t2["classes"],
        "n_clean": len(ie),
        "n_operators": len(t2["ops"]),
        "n_ops_ge10": ops10,
        "n_firings_sampled": sum(firings.values()),
        "id_err": {"median": t2_eval.q(ie, .5), "q99": t2_eval.q(ie, .99),
                   "max": t2_eval.q(ie, 1)},
        "mint_err": {"median": t2_eval.q(t2["mint_errs"], .5),
                     "q99": t2_eval.q(t2["mint_errs"], .99)},
        "price_consist": {"median": t2_eval.q(t2["price_errs"], .5),
                          "q99": t2_eval.q(t2["price_errs"], .99)},
    }
    json.dump(summary, open(OUT, "w"), indent=1)
    w.log("aero scan done: " + json.dumps(summary))


if __name__ == "__main__":
    main()
