"""Robustness draw: the spectrometer calibration re-run with the Base
sender-keyed census standing in for the Uniswap V3 one.

`production_sweep.py` draws its per-operator trigger-line distances
from the operator-keyed Uniswap V3 census on Base.  This asks whether
the recovery curves it captured are a property of the instrument or of
that one census: the same planted worlds, the same seed, the same
three sweeps, with the geometry draw taken instead from the Base
sender-keyed operator layer of the companion paper.

The sender-keyed layer's clean pool set is multi-venue on Base,
predominantly Aerodrome Slipstream but including PancakeSwap V3,
Uniswap V3 and V3-fork pools, so the artefact and this file say Base
sender-keyed rather than Aerodrome.

Neither census artefact is vendored here.  Point LT_CENSUS_UNIV3 and
LT_CENSUS_SENDER at them, or drop them beside this file under the
default names below.  As in the production sweep, each census is read
by path at runtime and its numbers never enter this file or its
outputs; what is published is the recovery curves and the
parameterisation shape of the draw.  The sender-keyed layer is not
public, so this file restates no cell counts, phi tables, pools or
operators from it.

Three draws against the production run:

  same-W_REF   W_REF = 75 local scales unchanged, so the draw carries
               this census's own trigger-distance location as well as
               its shape.  The venue-swap comparison proper.
  matched      W_REF rescaled so the drawn median trigger distance
               equals the production draw's, isolating shape from
               location.  Reported when the rescaling is non-trivial;
               the two censuses' median trigger fractions agree to
               below the artefacts' phi resolution, so this variant
               collapses onto the first and is recorded, not re-run.
  half, double W_REF halved and doubled on the same draw.  The
               venue swap moves the geometry too little to say what
               the curves are insensitive TO, so this brackets it:
               a location shift of a factor four, far larger than any
               census-to-census difference, is the sensitivity scale
               the null should be read against.

Worlds, seed, sweeps and inversion settings are production_sweep.py's
unchanged, so cells are paired: same price paths, same cadence mix,
same inversion, only the phi draw differs.

Run:  python3 robustness_sweep.py       (~2-4 min CPU, stdlib)
"""
from __future__ import annotations

import json
import math
import os
import random
import time

from spectrometer import (simulate_world, run_operator, bipower_prefix,
                          invert_pool)
from production_sweep import (SEED, CENSUS, W_REF, N_POOLS, B_FULL, N_OPS,
                              require_census,
                              INV, WORLDS, CADENCE_MIX, cell_metrics, fmt)

SENDER_CENSUS = os.environ.get("LT_CENSUS_SENDER") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "census-sender-base.json")
OUT = "robustness_results.json"


def load_phis():
    """The production draw's phi list."""
    return [c["phi"] for c in json.load(open(require_census(
        CENSUS, "the Uniswap V3 census on Base",
        "LT_CENSUS_UNIV3")))["clean_cells"]]


def load_sender_phis():
    """Clean-cell trigger fractions from the Base sender-keyed layer."""
    d = json.load(open(require_census(
        SENDER_CENSUS, "the Base sender-keyed census", "LT_CENSUS_SENDER")))
    return [c["phi"] for op in d["operators"].values()
            for c in op["cells"] if c.get("phi") is not None]


def median(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def draw_population(rng, phis, w_ref):
    ops = []
    for _ in range(N_OPS):
        phi = rng.choice(phis)
        r = rng.random()
        acc = 0.0
        for wgt, comp in CADENCE_MIX:
            acc += wgt
            if r <= acc:
                break
        w = phi * w_ref
        ops.append({"w": w, "period": comp.get("period", 1),
                    "dwell": comp.get("dwell", 0),
                    "pen": comp.get("pen_frac", 0.0) * w})
    return ops


def run_draw(name, phis, w_ref, results):
    t0 = time.time()
    gated_wref = name == "matched" and not os.environ.get("GATED_VERBOSE")
    shown = "gated" if gated_wref else f"{w_ref:.2f}"
    print(f"\n########## draw {name}: W_REF = {shown} ##########")
    results["draws"][name] = {"W_REF": "gated" if gated_wref else w_ref,
                              "sweeps": {}}
    for wname, wcfg in WORLDS.items():
        print(f"\n=== world {wname}: planted alpha {wcfg['alpha']}, "
              f"z0 {wcfg['z0']}, lam {wcfg['lam']} ===")
        pools = []
        for p in range(N_POOLS):
            rng = random.Random(SEED + 10_000 * p
                                + (0 if wname == "W1" else 5_000))
            xs, js = simulate_world(B_FULL, wcfg["sigma"], wcfg["mu"],
                                    wcfg["lam"], wcfg["z0"],
                                    wcfg["alpha"], rng)
            ops = draw_population(rng, phis, w_ref)
            events = [run_operator(xs, js, o["w"], pen=o["pen"],
                                   dwell=o["dwell"], period=o["period"])
                      for o in ops]
            pools.append({"cp": bipower_prefix(xs), "ops": ops,
                          "events": events})
            del xs, js
        print(f"  worlds + scans done ({time.time() - t0:.0f} s)")
        sw = {}
        print("  population curve (era 800k, abar 10):")
        for k in (2, 4, 8, 16, 32):
            c = cell_metrics(pools, k, B_FULL, 10, wname)
            sw[f"pop_k{k}"] = c
            print(f"    k = {k:2d}: {fmt(c)}")
        print("  era-length curve (k 32, abar 10):")
        for b in (100_000, 200_000, 400_000, 800_000):
            c = cell_metrics(pools, N_OPS, b, 10, wname)
            sw[f"era_{b}"] = c
            print(f"    era {b:>7,}: {fmt(c)}")
        print("  delay-cut curve (k 32, era 800k):")
        for a in (2, 5, 10, 30):
            c = cell_metrics(pools, N_OPS, B_FULL, a, wname)
            sw[f"abar_{a}"] = c
            print(f"    abar {a:3d}: {fmt(c)}")
        results["draws"][name]["sweeps"][wname] = sw


def compare(results, prod):
    """Paired deltas against the production run's captured cells."""
    print("\n########## paired deltas vs the production draw ##########")
    deltas = {}
    for dname, d in results["draws"].items():
        rows = []
        for wname, sw in d["sweeps"].items():
            for cell, c in sw.items():
                p = prod["sweeps"][wname].get(cell)
                if not p or "bias" not in c or "bias" not in p:
                    continue
                rows.append({
                    "world": wname, "cell": cell,
                    "d_bias": c["bias"] - p["bias"],
                    "d_rmse": c["rmse"] - p["rmse"],
                    "d_wilson": c["wilson_mean"] - p["wilson_mean"],
                    "d_m": c["m_mean"] - p["m_mean"],
                    "cover": c["bracket_cover"],
                    "cover_prod": p["bracket_cover"],
                })
        deltas[dname] = rows
        if not rows:
            continue
        ab = sorted(abs(r["d_bias"]) for r in rows)
        aw = sorted(abs(r["d_wilson"]) for r in rows)
        worst = max(rows, key=lambda r: abs(r["d_bias"]))
        print(f"  {dname}: {len(rows)} paired cells; "
              f"|d bias| median {median(ab):.4f}, max {ab[-1]:.4f} "
              f"(at {worst['world']}/{worst['cell']}); "
              f"|d wilson| median {median(aw):.4f}, max {aw[-1]:.4f}; "
              f"bracket coverage "
              f"{min(r['cover'] for r in rows):.2f}-"
              f"{max(r['cover'] for r in rows):.2f} "
              f"(production "
              f"{min(r['cover_prod'] for r in rows):.2f}-"
              f"{max(r['cover_prod'] for r in rows):.2f})")
    results["paired_deltas"] = deltas


def main():
    t0 = time.time()
    prod_phis = load_phis()
    sender_phis = load_sender_phis()
    m_prod, m_send = median(prod_phis), median(sender_phis)
    w_matched = W_REF * m_prod / m_send
    gated = bool(os.environ.get("GATED_VERBOSE"))
    print(f"production draw: {len(prod_phis)} clean cells "
          f"(artefact path in production_sweep.py), W_REF {W_REF}")
    print("robustness draw: clean cells loaded from the gated artefact "
          "(path in this file's header)")
    print("median trigger-distance ratio (robustness / production): "
          + (f"{m_send / m_prod:.3f}, matched W_REF {w_matched:.2f}"
             if gated else "withheld under the disclosure gate; the "
             "matched variant rescales W_REF by it"))
    results = {"seed": SEED, "cadence_mix": str(CADENCE_MIX),
               "n_phis_production": len(prod_phis),
               "gate": "robustness-draw census statistics withheld",
               "draws": {}}
    run_draw("same_wref", sender_phis, W_REF, results)
    if abs(w_matched / W_REF - 1) < 1e-9:
        print("\nmatched draw: rescaling factor is unity at the "
              "artefacts' phi resolution; variant collapses onto "
              "same_wref and is not re-run")
        results["matched_collapsed"] = True
    else:
        run_draw("matched", sender_phis, w_matched, results)
    run_draw("wref_half", sender_phis, W_REF / 2, results)
    run_draw("wref_double", sender_phis, W_REF * 2, results)
    prod = json.load(open("production_results.json"))
    compare(results, prod)
    with open(OUT, "w") as fp:
        json.dump(results, fp, indent=2)
    print(f"\nwrote {OUT} ({time.time() - t0:.0f} s total)")


if __name__ == "__main__":
    main()
