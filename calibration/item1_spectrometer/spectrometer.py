"""Spectrometer calibration harness (config-driven).

Full pipeline: synthetic price paths with a KNOWN law (diffusion +
jump measure) -> simulated operator populations whose trigger
geometries are drawn from a PARAMETERISED geometry mix -> the paper's
ACTUAL inversion pipeline (trailing bipower local scale with candidate
exclusion, admission thresholds, exceedance functional, folded-normal
baseline subtraction, Wilson intervals, Hill tail read, fast/slow
agreement test) -> recovery of the planted jump measure, reported
against ground truth.

The production geometry mix is census-derived and is not vendored
here; `config_census_STUB.json` marks the slot, and the live draw is
in `production_sweep.py`.  No census-derived number appears anywhere
in this folder.  Nothing here is a price model
assumption; simulation is controlled synthetic ground truth only.

Pipeline pieces (bipower estimator, operator scan, admission logic,
estimator formulas) are copied from
  verification/act3-instrument/mc_harness.py  (upstream owner)
and paper/local-time.tex Appendix G; the operator scan is the same
code validated event-exactly in ../item3_stress_maps/stress_maps.py.

Run:  python3 spectrometer.py config_toy.json
"""
from __future__ import annotations

import json
import math
import random
import sys
import time

Z95 = 1.959963984540054


def nsf(x):
    return 0.5 * math.erfc(x / math.sqrt(2))


# --------------------------------------------------- world and operators
# copied/adapted from verification/act3-instrument/mc_harness.py (owner)

def simulate_world(B, sigma, mu, lam, z0, alpha, rng):
    xs = [0.0] * B
    js = [0.0] * B
    x = 0.0
    for i in range(B):
        s = z0 * rng.random() ** (-1.0 / alpha) \
            if rng.random() < lam else 0.0
        x += mu + rng.gauss(0.0, sigma) + s
        xs[i] = x
        js[i] = s
    return xs, js


def run_operator(xs, js, w, pen=0.0, dwell=0, period=1):
    """Plain/penetration/dwell threshold detector (harness semantics).
    Returns events (t_act, O, jump_label, fire_block, cross_block)."""
    events = []
    b = w
    crossed = None
    consec = 0
    for i, x in enumerate(xs):
        if crossed is None:
            if x >= b:
                crossed = i
                consec = 1
            else:
                continue
        else:
            if x < b:
                crossed = None
                consec = 0
                continue
            consec += 1
        if (i % period == 0) and x >= b + pen \
                and consec >= max(dwell, 1):
            jl = js[crossed] > 0 and xs[crossed] - js[crossed] < b
            events.append((i - crossed + 1, x - b, jl, i, crossed))
            b = x + w
            crossed = None
            consec = 0
    return events


# ----------------------------------------------- inversion (Appendix G)

def bipower_prefix(xs):
    cp = [0.0] * (len(xs) + 1)
    prev_x = 0.0
    prev_d = 0.0
    for i, x in enumerate(xs):
        d = x - prev_x
        cp[i + 1] = cp[i] + abs(d) * abs(prev_d)
        prev_x, prev_d = x, d
    return cp


def sigma_bv(cp, cross, trail):
    lo = cross - trail
    if lo < 0:
        return None
    return math.sqrt((math.pi / 2) * (cp[cross] - cp[lo]) / trail)


def hill_alpha(vals, o_ref):
    logs = [math.log(v / o_ref) for v in vals if v > o_ref]
    if len(logs) < 30:
        return None, len(logs)
    return 1.0 + 1.0 / (sum(logs) / len(logs)), len(logs)


def fisher_exact_2s(a, b, c, d):
    n = a + b + c + d
    r1, c1 = a + b, a + c
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)

    def logp(x):
        return (math.lgamma(r1 + 1) - math.lgamma(x + 1)
                - math.lgamma(r1 - x + 1)
                + math.lgamma(n - r1 + 1) - math.lgamma(c1 - x + 1)
                - math.lgamma(n - r1 - c1 + x + 1)
                - math.lgamma(n + 1) + math.lgamma(c1 + 1)
                + math.lgamma(n - c1 + 1))
    obs = logp(a)
    tot = 0.0
    for x in range(lo, hi + 1):
        lp = logp(x)
        if lp <= obs + 1e-9:
            tot += math.exp(lp)
    return min(1.0, tot)


def straddle_surv(o, z0, alpha):
    """Planted P(O_J > o), flat-gap form (harness, owner as above).
    Ground truth: used only for the validation bracket, never by the
    inversion itself."""
    lam0 = z0 + z0 / (alpha - 1.0)
    if o <= z0:
        lam = (z0 - o) + z0 / (alpha - 1.0)
    else:
        lam = z0 ** alpha * o ** (1.0 - alpha) / (alpha - 1.0)
    return lam / lam0


def invert_pool(events_by_op, cp, cfg, op_component, truth=None):
    """The per-pool-era inversion of Appendix G, on the pooled
    small-delay sample with per-stratum replication."""
    kappa = cfg["kappa"]
    abar = cfg["abar"]
    trail = cfg["trail_blocks"]
    base = 2.0 * nsf(kappa)
    admitted = []            # (op, a, o, jl, sigma_hat)
    for op, evs in events_by_op.items():
        for a, o, jl, fb, cr in evs:
            if a <= abar and cr >= trail:
                sg = sigma_bv(cp, cr, trail)
                if sg and sg > 0:
                    admitted.append((op, a, o, jl, sg))
    m = len(admitted)
    out = {"m_admitted": m}
    if m < cfg["min_events"]:
        out["status"] = "not admitted (too few events)"
        return out
    exc = [(op, a, o, jl) for op, a, o, jl, sg in admitted
           if o > kappa * sg * math.sqrt(a)]
    E = len(exc) / m
    w_hat = max(0.0, (E - base) / (1.0 - base))
    wil = Z95 * math.sqrt(max(E * (1 - E), 1e-9) / m) / (1.0 - base)
    pi_true = sum(1 for *_, jl, sg in admitted if jl) / m
    out.update({"E": E, "pi_J_hat": w_hat, "wilson_half": wil,
                "pi_J_true_labels": pi_true, "status": "ok"})
    # validation bracket (Theorem 6 via the harness check-3 logic):
    # resolution floor from the planted tail, Wilson noise both sides
    if truth is not None:
        z0t, alt = truth
        floor_acc = sum(straddle_surv(2.0 * kappa * sg * math.sqrt(a),
                                      z0t, alt)
                        for _, a, _, _, sg in admitted) / m
        lo_b = pi_true * floor_acc * (1.0 - nsf(kappa / 2.0)) - wil
        hi_b = pi_true + base + wil
        out["bracket"] = [lo_b, hi_b]
        out["inside_bracket"] = bool(lo_b <= w_hat <= hi_b)
    # tail read on the small-delay exceedance sizes (harness: a <= 2,
    # larger delays admit diffusive contamination that steepens the
    # apparent tail)
    a_hat, n_exc = hill_alpha([o for _, a, o, jl in exc if a <= 2],
                              cfg["o_ref"])
    out["hill_alpha_hat"] = a_hat
    out["hill_n_exceed"] = n_exc
    # agreement test WITHIN the dominant geometry component (the
    # cross-component split mixes geometries whose crossing-type
    # shares differ by construction, the multiscale signal, and is
    # reported separately below)
    comps = {}
    for op in events_by_op:
        comps.setdefault(op_component[op], []).append(op)
    dom = max(comps.values(), key=len)
    half = set(dom[: len(dom) // 2])
    k1 = sum(1 for op, a, o, jl in exc if op in half)
    n1 = sum(1 for op, a, o, jl, sg in admitted if op in half)
    in_dom = set(dom)
    k2 = sum(1 for op, a, o, jl in exc
             if op in in_dom and op not in half)
    n2 = sum(1 for op, a, o, jl, sg in admitted
             if op in in_dom and op not in half)
    if min(n1, n2) >= 20:
        out["agreement_p_within_component"] = \
            fisher_exact_2s(k1, n1 - k1, k2, n2 - k2)
    # per-component exceedance levels (the multiscale spread, data
    # for Proposition 15 once the census draw is wired in)
    lv = {}
    for cname, ops_ in comps.items():
        so = set(ops_)
        mm = sum(1 for op, a, o, jl, sg in admitted if op in so)
        ee = sum(1 for op, a, o, jl in exc if op in so)
        if mm >= 50:
            lv[cname] = round(ee / mm, 4)
    out["per_component_E"] = lv
    return out


# ------------------------------------------------------------------ main

def main(cfg_path):
    cfg = json.load(open(cfg_path))
    if cfg.get("GATED", False):
        sys.exit("this configuration is a disclosure-gated stub; "
                 "the census draw has not been wired in")
    t0 = time.time()
    seed = cfg["seed"]
    world = cfg["world"]
    inv = cfg["inversion"]
    print(f"spectrometer harness, config {cfg_path}, seed {seed}")
    print(f"world: sigma {world['sigma']}, mu {world.get('mu', 0.0)}, "
          f"lam {world['lam']}, z0 {world['z0']}, "
          f"alpha {world['alpha']} (planted), B {world['B']}, "
          f"{cfg['n_pools']} pools")
    mix = cfg["population"]["geometry_mix"]
    print(f"geometry mix: {len(mix)} components "
          f"(PARAMETERISED; census draw gated)")
    results = []
    for p in range(cfg["n_pools"]):
        rng = random.Random(seed + 1000 * p)
        xs, js = simulate_world(world["B"], world["sigma"],
                                world.get("mu", 0.0), world["lam"],
                                world["z0"], world["alpha"], rng)
        cp = bipower_prefix(xs)
        events_by_op = {}
        op_component = {}
        n_ops = cfg["population"]["operators_per_pool"]
        for oi in range(n_ops):
            ci = rng.choices(range(len(mix)),
                             weights=[c["weight"] for c in mix])[0]
            comp = mix[ci]
            w = comp["w_over_sigma"] * world["sigma"]
            evs = run_operator(xs, js, w, pen=comp.get("pen", 0.0)
                               * world["sigma"],
                               dwell=comp.get("dwell", 0),
                               period=comp.get("period", 1))
            events_by_op[f"op{oi}"] = evs
            op_component[f"op{oi}"] = f"c{ci}"
        r = invert_pool(events_by_op, cp, inv, op_component,
                        truth=(world["z0"], world["alpha"]))
        r["pool"] = p
        results.append(r)
        if r["status"] == "ok":
            ah = r["hill_alpha_hat"]
            print(f"  pool {p}: m = {r['m_admitted']}, "
                  f"E = {r['E']:.3f}, pi_J_hat = {r['pi_J_hat']:.3f} "
                  f"+- {r['wilson_half']:.3f} "
                  f"(labels {r['pi_J_true_labels']:.3f}), "
                  f"alpha_hat = "
                  f"{'n/a' if ah is None else format(ah, '.3f')} "
                  f"(planted {world['alpha']}, "
                  f"n_exc {r['hill_n_exceed']})"
                  + (f", bracket [{r['bracket'][0]:.3f}, "
                     f"{r['bracket'][1]:.3f}] "
                     f"{'inside' if r['inside_bracket'] else 'OUTSIDE'}"
                     if "bracket" in r else "")
                  + (f", within-component agreement p = "
                     f"{r['agreement_p_within_component']:.3f}"
                     if "agreement_p_within_component" in r else ""))
            print(f"          per-component E: {r['per_component_E']}")
        else:
            print(f"  pool {p}: {r['status']}")
    # cross-pool summary of the recovery
    oks = [r for r in results if r["status"] == "ok"]
    if oks:
        n_in = sum(1 for r in oks if r.get("inside_bracket"))
        alphas = [r["hill_alpha_hat"] for r in oks
                  if r["hill_alpha_hat"] is not None]
        print(f"recovery: {len(oks)}/{len(results)} pools admitted; "
              f"{n_in}/{len(oks)} inside the Theorem 6 bracket; "
              + (f"alpha_hat mean {sum(alphas)/len(alphas):.3f} vs "
                 f"planted {world['alpha']} "
                 f"(finite-o_ref kernel bias expected upward)"
                 if alphas else "no tail reads"))
    out_path = cfg.get("out", "spectrometer_toy_results.json")
    with open(out_path, "w") as fp:
        json.dump({"config": cfg, "results": results,
                   "elapsed_s": time.time() - t0}, fp, indent=2)
    print(f"wrote {out_path} ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "config_toy.json")
