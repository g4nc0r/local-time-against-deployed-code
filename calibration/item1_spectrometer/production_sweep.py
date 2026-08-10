"""Spectrometer calibration with the census-derived geometry draw.

The geometry draw is taken from the operator-keyed Uniswap V3 census
on Base reported in the manuscript (1,046 admitted cells over 691
operators; the 495 clean line-recovery cells carry per-cell trigger
fractions phi).  That census artefact is not vendored here: point
LT_CENSUS_UNIV3 at it, or drop it beside this file under the default
name below.  This file and its outputs publish the recovery curves
and the parameterisation shape of the draw only; the census numbers
themselves flow through the runtime draw and are never restated.

Draw parameterisation (stated, not census data):
  - per-operator trigger-line distance w_i = phi_i * W_REF, phi_i
    sampled uniformly from the artefact's clean cells; W_REF = 75
    local scales, anchoring the census median trigger distance near
    22 sigma so per-cell firing counts land in the production range;
  - cadence/filter mix (the census does not recover cadence):
    60 % check-every-block plain, 20 % period 5, 10 % period 20 with
    dwell 3, 10 % penetration 0.3 w; flagged for re-run if a future
    census layer recovers cadence.

Worlds (planted ground truth, never a price model): W1 sigma 1,
lam 0.012, z0 7.5, alpha 2.5; W2 sigma 1, lam 0.004, z0 20,
alpha 3.5.  12 pools per world, era 800,000 blocks.

Sweeps (one axis at a time from the anchor cell k = 32 operators,
era 800k, abar = 10):
  population k in {2, 4, 8, 16, 32}
  era length in {100k, 200k, 400k, 800k}  (event-prefix truncation)
  delay cut abar in {2, 5, 10, 30}

Per cell, across pools: bias and RMSE of pi_J_hat against planted
labels, mean Wilson half-width, Theorem 6 bracket coverage,
Hill tail read, admitted-event counts.  The power curve is the
smallest k whose RMSE clears the stated precision.

Run:  python3 production_sweep.py          (~2-6 min CPU, stdlib)
"""
from __future__ import annotations

import json
import math
import os
import random
import time

from spectrometer import (simulate_world, run_operator, bipower_prefix,
                          invert_pool)

SEED = 20260813
CENSUS = os.environ.get("LT_CENSUS_UNIV3") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "census-univ3-base.json")
W_REF = 75.0
N_POOLS = 12
B_FULL = 800_000
N_OPS = 32
INV = {"kappa": 3.0, "trail_blocks": 43200, "min_events": 300}
WORLDS = {
    "W1": {"sigma": 1.0, "mu": 0.0, "lam": 0.012, "z0": 7.5,
           "alpha": 2.5, "o_ref": 15.0},
    "W2": {"sigma": 1.0, "mu": 0.0, "lam": 0.004, "z0": 20.0,
           "alpha": 3.5, "o_ref": 40.0},
}
CADENCE_MIX = [
    (0.60, {"period": 1}),
    (0.20, {"period": 5}),
    (0.10, {"period": 20, "dwell": 3}),
    (0.10, {"period": 1, "pen_frac": 0.3}),
]


def require_census(path, what, env):
    """Exit with an instruction rather than a traceback. The census
    artefacts are not vendored here, so a missing one is the normal state
    of a fresh clone."""
    if not os.path.exists(path):
        raise SystemExit(
            "missing input: %s\n  looked in: %s\n  set %s to its location.\n"
            "  The census artefacts are not vendored in this repository;\n"
            "  see this file's docstring for what the draw needs."
            % (what, path, env))
    return path


def load_phis():
    cells = json.load(open(require_census(
        CENSUS, "the Uniswap V3 census on Base", "LT_CENSUS_UNIV3")))["clean_cells"]
    return [c["phi"] for c in cells]


def draw_population(rng, phis):
    ops = []
    for _ in range(N_OPS):
        phi = rng.choice(phis)
        r = rng.random()
        acc = 0.0
        for wgt, comp in CADENCE_MIX:
            acc += wgt
            if r <= acc:
                break
        w = phi * W_REF
        ops.append({"w": w, "period": comp.get("period", 1),
                    "dwell": comp.get("dwell", 0),
                    "pen": comp.get("pen_frac", 0.0) * w})
    return ops


def cell_metrics(pools, k, b_era, abar, wname):
    """Invert each pool on the first k operators, events truncated to
    the era prefix; aggregate across pools."""
    wcfg = WORLDS[wname]
    res = []
    for pool in pools:
        ev = {f"op{i}": [e for e in pool["events"][i]
                         if e[3] < b_era]
              for i in range(k)}
        comp = {f"op{i}": f"c{pool['ops'][i]['period']}"
                for i in range(k)}
        cfg = dict(INV, abar=abar, o_ref=wcfg["o_ref"])
        r = invert_pool(ev, pool["cp"], cfg, comp,
                        truth=(wcfg["z0"], wcfg["alpha"]))
        res.append(r)
    ok = [r for r in res if r["status"] == "ok"]
    out = {"n_pools_admitted": len(ok), "n_pools": len(res)}
    if not ok:
        return out
    errs = [r["pi_J_hat"] - r["pi_J_true_labels"] for r in ok]
    out.update({
        "m_mean": sum(r["m_admitted"] for r in ok) / len(ok),
        "bias": sum(errs) / len(errs),
        "rmse": math.sqrt(sum(e * e for e in errs) / len(errs)),
        "wilson_mean": sum(r["wilson_half"] for r in ok) / len(ok),
        "bracket_cover": sum(1 for r in ok if r.get("inside_bracket"))
        / len(ok),
    })
    alphas = [r["hill_alpha_hat"] for r in ok
              if r.get("hill_alpha_hat") is not None]
    if alphas:
        mu = sum(alphas) / len(alphas)
        out["hill_mean"] = mu
        out["hill_sd"] = math.sqrt(
            sum((a - mu) ** 2 for a in alphas) / len(alphas))
        out["hill_n_pools"] = len(alphas)
    return out


def fmt(cell):
    if cell.get("n_pools_admitted", 0) == 0:
        return "no pool admitted"
    s = (f"adm {cell['n_pools_admitted']}/{cell['n_pools']}, "
         f"m~{cell['m_mean']:.0f}, bias {cell['bias']:+.3f}, "
         f"rmse {cell['rmse']:.3f}, wilson {cell['wilson_mean']:.3f}, "
         f"bracket {cell['bracket_cover']:.2f}")
    if "hill_mean" in cell:
        s += (f", alpha_hat {cell['hill_mean']:.2f}"
              f"+-{cell['hill_sd']:.2f}")
    return s


def main():
    t0 = time.time()
    phis = load_phis()
    print(f"census draw: {len(phis)} clean cells loaded from the "
          f"artefact (path in header); W_REF = {W_REF}")
    results = {"seed": SEED, "W_REF": W_REF,
               "cadence_mix": str(CADENCE_MIX), "sweeps": {}}
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
            ops = draw_population(rng, phis)
            events = [run_operator(xs, js, o["w"], pen=o["pen"],
                                   dwell=o["dwell"],
                                   period=o["period"])
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
        results["sweeps"][wname] = sw
    with open("production_results.json", "w") as fp:
        json.dump(results, fp, indent=2)
    print(f"\nwrote production_results.json "
          f"({time.time() - t0:.0f} s total)")


if __name__ == "__main__":
    main()
