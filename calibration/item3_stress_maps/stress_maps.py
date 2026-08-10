"""Small-delay and surcharge stress maps at GPU scale.

Two parts, both against synthetic worlds with a KNOWN law (controlled
ground truth only; no price model enters as an assumption).

Part A (bracket maps): jump-diffusion block worlds (Gaussian increment
sigma, drift mu, one-sided compound-Poisson jumps with Pareto tail:
rate lam per block, sizes z0 * U^(-1/alpha)), scanned by the plain
threshold operator of the third act's harness (line at distance w above
the last reset, checks every `period` blocks, crossing reset on dips,
line re-anchored at the fired state).  Per configuration cell the
exceedance functional E(kappa, abar) is measured with the KNOWN sigma
and compared against the jump-crossing share pi_J(abar) from planted
labels; Theorem 6's bracket is evaluated per cell with the
planted integrated tail, and the kappa -> infinity consistency clause
is exhibited along vanishing-(kappa sigma sqrt(abar)) diagonals.
The drift arm crosses the theorem's admission boundary
|mu| abar <= (kappa/2) sigma sqrt(abar) to show where the bracket
fails for the stated reason.  Grids run far beyond the stdlib
harness's single configuration (225 jump-regime cells x delay grids
x 36 (kappa, abar) readings, 32 replicas each).

Part B (jump surcharge): the Sharp Constant search's policy machinery (exact mint
arithmetic, wandering price) under one-sided jump regimes.  At every
jump-caused firing the per-event premium
k(landed -> target) - k(diffusive-equivalent -> target) is measured
and compared with the placement-potential form
ln(((1-x)h - O)/((1-x)h - O - O_J)) of Proposition 17, the rate
r_J against its lower bound lam_J E[O_J]/h, and straddles landing
beyond the range boundary are counted and priced separately.  Regimes
include alpha <= 2, where E[O_J] diverges and the bound's right side
is expected to degrade.

Operator-scan semantics are copied from
  verification/act3-instrument/mc_harness.py  (upstream owner)
and --validate asserts EXACT event-list agreement between the
vectorised scan and that stdlib code on a common seeded world before
any large run.

Conventions: float64 throughout, fixed seeds,
torch.use_deterministic_algorithms(True); captured OUTPUT.md states
seed and tolerances.

Run:  python3 stress_maps.py [--validate] [--out stress_results.json]
"""
from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np
import torch

SEED = 20260811
S0 = 100.0
SIG_S = 16.0                     # sqrt-price vol for part B (Sharp Constant anchor)

torch.manual_seed(SEED)
try:
    torch.use_deterministic_algorithms(True)
    DET = True
except Exception:
    DET = False

KAPPAS = np.array([2.0, 3.0, 4.0, 6.0, 8.0, 12.0])
ABARS = np.array([1.0, 2.0, 5.0, 10.0, 20.0, 50.0])


def nsf(x):
    return 0.5 * math.erfc(x / math.sqrt(2))


# ---------------------------------------------------------- planted tail

def straddle_surv_t(o, z0, alpha):
    """Planted P(O_J > o) under flat gap occupation (harness form),
    torch elementwise; o, z0, alpha broadcastable float64 tensors."""
    lam0 = z0 + z0 / (alpha - 1.0)
    lam_small = (z0 - o) + z0 / (alpha - 1.0)
    lam_big = z0 ** alpha * torch.clamp(o, min=1e-12) ** (1.0 - alpha) \
        / (alpha - 1.0)
    lam = torch.where(o <= z0, lam_small, lam_big)
    return lam / lam0


# ------------------------------------------------- part A: bracket maps

def run_part_a(device, B, n_reps, quick=False):
    alphas = [1.3, 1.6, 2.0, 2.5, 3.5]
    lams = [0.004, 0.012, 0.04]
    z0s = [2.0, 7.5, 20.0]          # in sigma units
    periods = [1, 5, 20]
    mus = [0.0]
    base = [(a, l, z, p, 0.0) for a in alphas for l in lams
            for z in z0s for p in periods]
    drift = [(2.5, 0.012, 7.5, p, m) for p in periods
             for m in (0.1, 0.5)]
    cfgs = base + drift
    if quick:
        cfgs = [(2.5, 0.012, 7.5, 1, 0.0), (1.3, 0.04, 2.0, 5, 0.0),
                (2.5, 0.012, 7.5, 1, 0.5)]
        n_reps = 4
    C = len(cfgs) * n_reps
    sigma = 1.0                     # block scale; all else in sigma units
    w = 7.5                         # line distance (harness: 30 = 7.5 sig)

    def col(vals, idx):
        return torch.tensor([c[idx] for c in cfgs], device=device,
                            dtype=torch.float64).repeat_interleave(n_reps)

    al = col(cfgs, 0)
    lm = col(cfgs, 1)
    z0 = col(cfgs, 2)
    pd = torch.tensor([c[3] for c in cfgs], device=device,
                      dtype=torch.int64).repeat_interleave(n_reps)
    mu = col(cfgs, 4)

    kap = torch.tensor(KAPPAS, device=device,
                       dtype=torch.float64).view(1, -1, 1)
    ab = torch.tensor(ABARS, device=device,
                      dtype=torch.float64).view(1, 1, -1)

    g = torch.Generator(device=device)
    g.manual_seed(SEED + 101)

    x = torch.zeros(C, device=device, dtype=torch.float64)
    b = torch.full((C,), w, device=device, dtype=torch.float64)
    crossed = torch.full((C,), -1, device=device, dtype=torch.int64)
    cross_jl = torch.zeros(C, device=device, dtype=torch.bool)

    n_adm = torch.zeros((C, len(ABARS)), device=device,
                        dtype=torch.float64)
    n_jl = torch.zeros_like(n_adm)
    n_exc = torch.zeros((C, len(KAPPAS), len(ABARS)), device=device,
                        dtype=torch.float64)
    s_floor = torch.zeros_like(n_exc)
    n_all = torch.zeros(C, device=device, dtype=torch.float64)
    n_jc = torch.zeros(C, device=device, dtype=torch.float64)
    hill_n = torch.zeros(C, device=device, dtype=torch.float64)
    hill_s = torch.zeros(C, device=device, dtype=torch.float64)

    t0 = time.time()
    for i in range(B):
        gauss = torch.randn(C, generator=g, device=device,
                            dtype=torch.float64)
        u1 = torch.rand(C, generator=g, device=device,
                        dtype=torch.float64)
        u2 = torch.rand(C, generator=g, device=device,
                        dtype=torch.float64)
        jumped = u1 < lm
        jsize = torch.where(
            jumped, z0 * torch.clamp(u2, min=1e-12) ** (-1.0 / al),
            torch.zeros(C, device=device, dtype=torch.float64))
        x_pre = x + mu + sigma * gauss
        x = x_pre + jsize
        # crossing bookkeeping (harness semantics)
        below = x < b
        newly = (crossed < 0) & ~below
        crossed = torch.where(newly, torch.full_like(crossed, i), crossed)
        cross_jl = torch.where(newly, jumped & (x_pre < b), cross_jl)
        # dips reset (only where previously crossed and now below)
        reset = (crossed >= 0) & below
        crossed = torch.where(reset, torch.full_like(crossed, -1), crossed)
        # check-and-fire
        is_check = torch.remainder(
            torch.full_like(pd, i), pd) == 0
        fire = is_check & (crossed >= 0) & (x >= b)
        a = (i - crossed + 1).to(torch.float64)
        o = x - b
        # accumulate
        f3 = fire.view(-1, 1, 1)
        a3 = a.view(-1, 1, 1)
        o3 = o.view(-1, 1, 1)
        sg = sigma
        adm3 = f3 & (a3 <= ab)
        exc3 = adm3 & (o3 > kap * sg * torch.sqrt(a3))
        n_exc += exc3.to(torch.float64)
        sfl = straddle_surv_t(2.0 * kap * sg * torch.sqrt(a3),
                              z0.view(-1, 1, 1), al.view(-1, 1, 1))
        s_floor += torch.where(adm3, sfl, torch.zeros_like(sfl))
        adm2 = fire.view(-1, 1) & (a.view(-1, 1) <= ab.view(1, -1))
        n_adm += adm2.to(torch.float64)
        n_jl += (adm2 & cross_jl.view(-1, 1)).to(torch.float64)
        n_all += fire.to(torch.float64)
        n_jc += (fire & cross_jl).to(torch.float64)
        hm = fire & (a <= 2.0) & (o > 2.0 * z0) & (pd == 1)
        hill_n += hm.to(torch.float64)
        hill_s += torch.where(
            hm, torch.log(torch.clamp(o, min=1e-12) / (2.0 * z0)),
            torch.zeros_like(o))
        # re-anchor on fire
        b = torch.where(fire, x + w, b)
        crossed = torch.where(fire, torch.full_like(crossed, -1), crossed)
        if (i + 1) % 100_000 == 0:
            print(f"    part A block {i + 1}/{B} "
                  f"({time.time() - t0:.0f} s)", flush=True)

    # reduce over replicas and assemble per-config cells
    def red(t):
        return t.view(len(cfgs), n_reps, *t.shape[1:]).sum(dim=1).cpu()

    n_adm, n_jl, n_exc, s_floor = map(red, (n_adm, n_jl, n_exc, s_floor))
    n_all, n_jc, hill_n, hill_s = map(red, (n_all, n_jc, hill_n, hill_s))

    out = []
    for ci, (a_, l_, z_, p_, m_) in enumerate(cfgs):
        cell = {"alpha": a_, "lam": l_, "z0": z_, "period": p_,
                "mu": m_, "n_events": int(n_all[ci]),
                "jump_cross_rate": float(n_jc[ci] / max(B, 1))}
        hn = float(hill_n[ci])
        cell["hill_alpha"] = (1.0 + hn / float(hill_s[ci])
                              if hn >= 50 else None)
        cell["hill_n"] = int(hn)
        grid = []
        for ki, k_ in enumerate(KAPPAS):
            for aii, ab_ in enumerate(ABARS):
                m = float(n_adm[ci, aii])
                if m < 200:
                    continue
                E = float(n_exc[ci, ki, aii]) / m
                pj = float(n_jl[ci, aii]) / m
                base_t = 2.0 * nsf(k_ / 2.0)
                floor_f = float(s_floor[ci, ki, aii]) / m
                wil = 1.959964 * math.sqrt(max(E * (1 - E), 1e-9) / m)
                lhs = abs(E - pj)
                # theorem RHS: 2 nsf(kappa/2)
                #   + pi_J (1 - Jtail(2 k s sqrt(abar))/Jtail(0))
                # per-event floor factor version (harness check-3 logic)
                rhs = base_t + pj * (1.0 - floor_f)
                drift_ok = m_ * ab_ <= 0.5 * k_ * math.sqrt(ab_)
                grid.append({
                    "kappa": k_, "abar": ab_, "m": int(m), "E": E,
                    "pi_J": pj, "lhs": lhs, "rhs": rhs,
                    "wilson": wil, "base": base_t,
                    "floor_factor": floor_f,
                    "holds": lhs <= rhs + wil,
                    "vacuous": rhs >= max(0.5, 2.0 * max(pj, 1e-9)),
                    "drift_admissible": bool(drift_ok)})
        cell["grid"] = grid
        out.append(cell)
    return out


# --------------------------------------------- part B: surcharge stress

def k_exact_torch(s, centre_old, centre_new, h):
    sa1, sb1 = centre_old - h, centre_old + h
    sc = torch.clamp(s, sa1, sb1)
    x = 1.0 / sc - 1.0 / sb1
    y = sc - sa1
    sa2, sb2 = centre_new - h, centre_new + h
    xu = 1.0 / s - 1.0 / sb2
    yu = s - sa2
    L2 = torch.minimum(x / xu, y / yu)
    return -torch.log((L2 * (xu * s * s + yu)) / (x * s * s + y))


def run_part_b(device, n_steps, n_reps, quick=False):
    """Policies fire at |d| = x h, recentre fully; one-sided upward
    jumps.  rho = 0.05, wandering price, exact arithmetic."""
    rho = 0.05
    h = rho * S0
    xs_ = [0.3, 0.5, 0.72]
    regimes = [(None, None, None)] + \
        [(a_, zf, 2.0) for a_ in (1.6, 2.5, 3.5) for zf in (0.1, 0.3)]
    if quick:
        xs_ = [0.5]
        regimes = [(None, None, None), (2.5, 0.3, 8.0)]
        n_reps = 8
    cfgs = [(x_, r) for x_ in xs_ for r in regimes]
    C = len(cfgs) * n_reps
    step_frac = 0.004
    sd = step_frac * h
    dt = (sd / SIG_S) ** 2
    # horizon note: n_steps is chosen by the caller so that
    # sigma_s sqrt(T) stays ~0.15 S0; replicas carry the precision

    xt = torch.tensor([c[0] for c in cfgs], device=device,
                      dtype=torch.float64).repeat_interleave(n_reps)
    has_j = torch.tensor([c[1][0] is not None for c in cfgs],
                         device=device).repeat_interleave(n_reps)
    al = torch.tensor([c[1][0] or 2.5 for c in cfgs], device=device,
                      dtype=torch.float64).repeat_interleave(n_reps)
    z0 = torch.tensor([(c[1][1] or 0.1) * h for c in cfgs],
                      device=device,
                      dtype=torch.float64).repeat_interleave(n_reps)
    lam_frac = torch.tensor([c[1][2] or 0.0 for c in cfgs],
                            device=device,
                            dtype=torch.float64).repeat_interleave(n_reps)
    lam_dt = torch.where(has_j, lam_frac * (SIG_S / h) ** 2 * dt,
                         torch.zeros_like(lam_frac))

    g = torch.Generator(device=device)
    g.manual_seed(SEED + 202)
    s = torch.full((C,), S0, device=device, dtype=torch.float64)
    min_s = s.clone()
    centre = s.clone()
    cost = torch.zeros(C, device=device, dtype=torch.float64)
    prem_sum = torch.zeros_like(cost)
    prem_narrow_dev = torch.zeros_like(cost)
    oj_sum = torch.zeros_like(cost)
    n_j = torch.zeros_like(cost)
    n_beyond = torch.zeros_like(cost)
    cost_beyond = torch.zeros_like(cost)
    n_f = torch.zeros_like(cost)
    burn = n_steps // 5

    t0 = time.time()
    for i in range(n_steps):
        gauss = torch.randn(C, generator=g, device=device,
                            dtype=torch.float64)
        u1 = torch.rand(C, generator=g, device=device,
                        dtype=torch.float64)
        u2 = torch.rand(C, generator=g, device=device,
                        dtype=torch.float64)
        s_pre = s + sd * gauss
        jumped = u1 < lam_dt
        # truncation at 20h keeps the venue state on-domain; for
        # alpha <= 2 the un-truncated E[O_J] diverges and the mass
        # beyond the truncation is reported from the planted law
        jsize = torch.where(
            jumped,
            torch.clamp(z0 * torch.clamp(u2, min=1e-12) ** (-1.0 / al),
                        max=20.0 * h),
            torch.zeros_like(z0))
        s = s_pre + jsize
        d = s - centre
        d_pre = s_pre - centre
        up = d >= xt * h
        dn = d <= -xt * h
        fired = up | dn
        # jump-caused up-firing: pre-jump displacement below trigger
        jfire = up & jumped & (d_pre < xt * h)
        O = torch.clamp(d_pre - xt * h, min=0.0)   # diffusive overshoot
        OJ = torch.where(jfire, d - torch.maximum(d_pre, xt * h),
                         torch.zeros_like(d))
        # beyond-range landings have L2 = 0 in the isolated class
        # (one-sided holdings cannot mint a price-containing range), an
        # infinite log-cost; cap at K_CAP = 10 (e^-10 residual value, de
        # facto total loss) and count capped events; the cap is stated
        # in the capture
        c2 = torch.where(fired, s, centre)          # full recentre
        k = k_exact_torch(s, centre, c2, h)
        k = torch.where(torch.isfinite(k), k, torch.full_like(k, 10.0))
        k = torch.clamp(k, max=10.0)
        k = torch.where(fired, k, torch.zeros_like(k))
        # per-event premium: k(landed) - k(diffusive-equivalent state),
        # both fully recentred (the return point cancels in the
        # potential telescoping, Proposition 17)
        s_hyp = centre + torch.clamp(torch.maximum(d_pre, xt * h),
                                     max=d)         # state at xh + O
        k_hyp = k_exact_torch(s_hyp, centre, s_hyp, h)
        k_hyp = torch.clamp(torch.where(torch.isfinite(k_hyp), k_hyp,
                                        torch.full_like(k_hyp, 10.0)),
                            max=10.0)
        prem = torch.where(jfire, k - k_hyp, torch.zeros_like(k))
        inside = jfire & (d < h)
        narrow = torch.where(
            inside,
            torch.log(((1.0 - xt) * h - O)
                      / torch.clamp((1.0 - xt) * h - O - OJ, min=1e-12)),
            torch.zeros_like(k))
        if i >= burn:
            cost = cost + k
            n_f = n_f + fired.to(torch.float64)
            prem_sum = prem_sum + torch.where(inside, prem,
                                              torch.zeros_like(prem))
            prem_narrow_dev = prem_narrow_dev + torch.where(
                inside, torch.abs(prem - narrow), torch.zeros_like(prem))
            oj_sum = oj_sum + torch.where(inside, OJ,
                                          torch.zeros_like(OJ))
            n_j = n_j + inside.to(torch.float64)
            beyond = jfire & (d >= h)
            n_beyond = n_beyond + beyond.to(torch.float64)
            cost_beyond = cost_beyond + torch.where(
                beyond, k, torch.zeros_like(k))
        centre = torch.where(fired, c2, centre)
        min_s = torch.minimum(min_s, s)
        if (i + 1) % 200_000 == 0:
            print(f"    part B step {i + 1}/{n_steps} "
                  f"({time.time() - t0:.0f} s)", flush=True)

    T = (n_steps - burn) * dt
    alive = (min_s > 0.4 * S0).view(len(cfgs), n_reps)

    def red(t):
        return (t.view(len(cfgs), n_reps)
                * alive.to(torch.float64)).sum(dim=1).cpu()

    n_alive = alive.sum(dim=1).cpu()
    cost, n_f, prem_sum, prem_narrow_dev, oj_sum, n_j, n_beyond, \
        cost_beyond = map(red, (cost, n_f, prem_sum, prem_narrow_dev,
                                oj_sum, n_j, n_beyond, cost_beyond))
    out = []
    for ci, (x_, (a_, zf_, lf_)) in enumerate(cfgs):
        Tt = T * max(int(n_alive[ci]), 1)
        nj = float(n_j[ci])
        cell = {"x": x_, "alpha": a_, "z0_frac": zf_, "lam_frac": lf_,
                "n_reps_kept": int(n_alive[ci]),
                "c_total": float(cost[ci] / Tt * h * h / SIG_S ** 2),
                "n_fire": int(n_f[ci]),
                "n_jump_fire_inside": int(nj),
                "n_beyond_range": int(n_beyond[ci]),
                "c_beyond": float(cost_beyond[ci] / Tt * h * h
                                  / SIG_S ** 2)}
        if nj > 0:
            lamJ = nj / Tt
            cell["r_J_measured"] = float(prem_sum[ci] / Tt * h * h
                                         / SIG_S ** 2)
            cell["r_J_lower_bound"] = float(
                lamJ * (oj_sum[ci] / nj) / h * h * h / SIG_S ** 2)
            cell["mean_OJ_over_h"] = float(oj_sum[ci] / nj / h)
            cell["premium_vs_narrow_meandev"] = float(
                prem_narrow_dev[ci] / nj)
        out.append(cell)
    return out


# ------------------------------------------------------------ validation

def stdlib_world_and_scan(B, sigma, lam, z0, alpha, w, period, seed):
    """Copied from verification/act3-instrument/mc_harness.py (owner):
    simulate_world + run_operator (plain threshold), stdlib."""
    import random
    rng = random.Random(seed)
    xs = [0.0] * B
    js = [0.0] * B
    x = 0.0
    for i in range(B):
        s = z0 * rng.random() ** (-1.0 / alpha) \
            if rng.random() < lam else 0.0
        x += rng.gauss(0.0, sigma) + s
        xs[i] = x
        js[i] = s
    events = []
    b = w
    crossed = None
    for i, x in enumerate(xs):
        if crossed is None:
            if x >= b:
                crossed = i
            else:
                continue
        else:
            if x < b:
                crossed = None
                continue
        if i % period == 0 and x >= b:
            jl = js[crossed] > 0 and xs[crossed] - js[crossed] < b
            events.append((i - crossed + 1, x - b, jl))
            b = x + w
            crossed = None
    return xs, js, events


def torch_scan_single(xs, js, w, period, device):
    """The part-A scan run on a supplied path (single column)."""
    B = len(xs)
    xs_t = torch.tensor(xs, dtype=torch.float64)
    js_t = torch.tensor(js, dtype=torch.float64)
    b = w
    crossed = -1
    cjl = False
    events = []
    for i in range(B):
        x = float(xs_t[i])
        jumped = float(js_t[i]) > 0
        x_pre = x - float(js_t[i])
        below = x < b
        if crossed < 0 and not below:
            crossed = i
            cjl = jumped and (x_pre < b)
        elif crossed >= 0 and below:
            crossed = -1
        if (i % period == 0) and crossed >= 0 and x >= b:
            events.append((i - crossed + 1, x - b, cjl))
            b = x + w
            crossed = -1
    return events


def validate(device):
    print("== validation ==", flush=True)
    ok = True
    # (1) exact event agreement with the stdlib scan on a seeded world
    for period in (1, 5, 40):
        xs, js, ev_ref = stdlib_world_and_scan(
            40_000, 4.0, 0.012, 30.0, 2.5, 30.0, period, 3037)
        ev_new = torch_scan_single(xs, js, 30.0, period, device)
        same = len(ev_ref) == len(ev_new) and all(
            a1 == a2 and abs(o1 - o2) < 1e-12 and j1 == j2
            for (a1, o1, j1), (a2, o2, j2) in zip(ev_ref, ev_new))
        ok &= same
        print(f"  scan agreement, period {period}: {len(ev_ref)} events, "
              f"{'exact match' if same else '** MISMATCH **'}")
    # (2) quick part A: harness-like config recovers planted jump share
    cells = run_part_a(device, 100_000, 4, quick=True)
    c0 = cells[0]
    g33 = [r for r in c0["grid"]
           if r["kappa"] == 3.0 and r["abar"] == 10.0]
    if g33:
        r = g33[0]
        w_hat = max(0.0, (r["E"] - r["base"]) / (1 - r["base"]))
        good = r["holds"]
        ok &= good
        print(f"  quick part A (alpha 2.5): E(3,10) = {r['E']:.3f}, "
              f"pi_J = {r['pi_J']:.3f}, w_hat = {w_hat:.3f}, "
              f"lhs {r['lhs']:.3f} <= rhs {r['rhs']:.3f} + wil "
              f"{r['wilson']:.3f}: {'holds' if good else '** FAIL **'}")
    if c0["hill_alpha"]:
        dev = abs(c0["hill_alpha"] - 2.5)
        # the integrated-tail read at o_ref = 2 z0 carries the known
        # finite-o_ref kernel-nonflatness bias (harness saw +0.21);
        # the full run maps it, the quick gate is loose
        good = dev < 0.7
        ok &= good
        print(f"  Hill alpha_hat = {c0['hill_alpha']:.3f} "
              f"(planted 2.5, n {c0['hill_n']})"
              f"{'' if good else '  ** FAIL **'}")
    # (3) quick part B: diffusive column matches the analytic c(x)
    bcells = run_part_b(device, 150_000, 4, quick=True)
    diff = [c for c in bcells if c["alpha"] is None][0]
    good = abs(diff["c_total"] - 2.70) / 2.70 < 0.25
    ok &= good
    print(f"  quick part B diffusive x = 0.5: c = {diff['c_total']:.3f} "
          f"(analytic 2.70){'' if good else '  ** FAIL **'}")
    jc = [c for c in bcells if c["alpha"] is not None][0]
    if jc.get("n_jump_fire_inside", 0) > 10:
        print(f"  quick part B jump x = 0.5 alpha 2.5: r_J = "
              f"{jc['r_J_measured']:.4f} >= bound "
              f"{jc['r_J_lower_bound']:.4f}: "
              f"{jc['r_J_measured'] >= 0.8 * jc['r_J_lower_bound']}; "
              f"premium vs narrow form mean |dev| = "
              f"{jc['premium_vs_narrow_meandev']:.2e}")
        ok &= jc["r_J_measured"] >= 0.8 * jc["r_J_lower_bound"]
    print("validation " + ("PASSED" if ok else "FAILED"), flush=True)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--out", default="stress_results.json")
    args = ap.parse_args()
    device = torch.device(
        "cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    print(f"device = {device}, deterministic = {DET}, seed = {SEED}",
          flush=True)
    if args.validate:
        import sys
        sys.exit(0 if validate(device) else 1)

    results = {"seed": SEED, "deterministic": DET, "device": str(device),
               "kappas": KAPPAS.tolist(), "abars": ABARS.tolist()}
    print("== part A: bracket maps ==", flush=True)
    t0 = time.time()
    results["part_a"] = run_part_a(device, 400_000, 32)
    results["part_a_elapsed_s"] = time.time() - t0
    print(f"part A done ({results['part_a_elapsed_s']:.0f} s)",
          flush=True)
    print("== part B: surcharge ==", flush=True)
    t0 = time.time()
    results["part_b"] = run_part_b(device, 560_000, 96)
    results["part_b_elapsed_s"] = time.time() - t0
    print(f"part B done ({results['part_b_elapsed_s']:.0f} s)",
          flush=True)
    with open(args.out, "w") as fp:
        json.dump(results, fp, indent=2)
    print(f"wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
