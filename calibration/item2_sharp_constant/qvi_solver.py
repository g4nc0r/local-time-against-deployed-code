"""Sharp Constant search: exact CPU-side tools.

Deterministic, float64, no RNG anywhere in this file. Three tools:

  1. VALIDATION: reproduce the captured verify_floor.py regression
     numbers (corridor constants c_min(rho); the narrow-limit c(x);
     the exact three-parameter renewal-grid minimum 2.397 at rho 0.05)
     with this file's own geometry code, so the geometry here is tied
     to the paper's shipped reference implementation before anything
     new is trusted.
  2. FOUR-PARAMETER RENEWAL SWEEP: the family (fire at du -> target
     tu, fire at dd -> target td), evaluated in closed form by the
     embedded two-state semi-Markov cycle algebra (Brownian exit
     probabilities and expected exit times are exact), swept densely
     and refined.  The three-parameter family of Proposition 6 is the
     tu = td slice.
  3. GRID QVI (the decisive tool): average-cost impulse control on
     the displacement coordinate, discretised as the symmetric random
     walk (whose exit probabilities and expected exit times agree with
     Brownian motion exactly at grid points), solved by policy
     iteration with NO structural assumption on the policy.  Actions
     per state: continue, or fire to any grid state, at the exact
     placement-family cost.  The converged gain g is the grid-optimal
     dissipation rate; c = g h^2 / sigma^2.  Grid policies are a
     subset of admissible policies, so the grid optimum converges to
     the Markov-class infimum from above as the grid refines.

Cost modes:
  narrow  : k(d -> d') = max( ln((h-d')/(h-d)), ln((h+d)/(h+d')) ),
            the narrow-limit placement-family potentials
            (paper Corollary 4, narrow limit).
  exact   : the isolated re-placement mint arithmetic at price
            s = S0 + d, old range [S0 - h, S0 + h], new midpoint
            s - d' (the fixed-s convention of verify_floor.py's
            c_renewal and c_min_corridor(band = 0)).

Geometry functions are copied from
  verification/act2-floor/verify_floor.py  (upstream owner)
per the programme's share-by-copy rule.

Simulation here is controlled synthetic ground truth only; no price
model enters as an assumption.

Run:  python3 qvi_solver.py            (full: validation + sweeps + QVI)
      python3 qvi_solver.py --validate (validation section only)
"""
from __future__ import annotations

import json
import math
import sys
import time

import numpy as np

S0 = 100.0

# ---------------------------------------------------------------- geometry
# copied from verification/act2-floor/verify_floor.py (owner)


def phi(s, sa, sb):
    return 2.0 * s - s * s / sb - sa


def withdraw(L, s, sa, sb):
    sc = min(max(s, sa), sb)
    return L * (1.0 / sc - 1.0 / sb), L * (sc - sa)


def rebalance(L, s, sa1, sb1, sa2, sb2):
    x, y = withdraw(L, s, sa1, sb1)
    xu, yu = 1.0 / s - 1.0 / sb2, s - sa2
    L2 = min(x / xu, y / yu)
    v_old = x * s * s + y
    v_new = L2 * (xu * s * s + yu)
    return L2, -math.log(v_new / v_old)


def c_min_corridor(sbar, u, band):
    svals = [sbar - band + i * (2.0 * band) / 40 for i in range(41)] \
        if band > 0 else [sbar]

    def up_slope(x):
        return min(1.0 / (u - x) - 2.0 * x / (u * (2.0 * s + u) - x * x)
                   for s in svals)

    def dn_slope(x):
        return max(-2.0 * x / (u * (2.0 * s + u) - x * x) - 1.0 / (u + x)
                   + 1.0 / (s + u - x) for s in svals)

    n = 400
    xs = [-u + 1e-9 + (2.0 * u - 2e-9) * i / n for i in range(n + 1)]
    ups = np.array([up_slope(x) for x in xs])
    dns = np.array([dn_slope(x) for x in xs])
    xa = np.array(xs)
    best = float("inf")
    for i in range(n + 1):
        j = np.arange(i + 1, n + 1)
        if len(j):
            best = min(best, float(np.min(
                (ups[j] - dns[i]) / (xa[j] - xa[i]))))
    return u * u * best / 2.0


# ------------------------------------------------------------- cost kernels

def k_exact_vec(d, dp, h):
    """Exact isolated re-placement log-cost, vectorised.

    d, dp broadcastable arrays of old/new displacements (|dp| < h;
    d may lie beyond +-h, the withdraw clamp handles it).  Fixed-s
    convention: price s = S0 + d, old range [S0 - h, S0 + h].
    """
    d = np.asarray(d, dtype=np.float64)
    dp = np.asarray(dp, dtype=np.float64)
    s = S0 + d
    sa1, sb1 = S0 - h, S0 + h
    sc = np.clip(s, sa1, sb1)
    x = 1.0 / sc - 1.0 / sb1
    y = sc - sa1
    c2 = s - dp
    sa2, sb2 = c2 - h, c2 + h
    xu = 1.0 / s - 1.0 / sb2
    yu = s - sa2
    L2 = np.minimum(x / xu, y / yu)
    v_old = x * s * s + y
    v_new = L2 * (xu * s * s + yu)
    return -np.log(v_new / v_old)


def k_narrow_vec(d, dp, h):
    """Narrow-limit placement-family cost (Corollary 4, narrow limit)."""
    d = np.asarray(d, dtype=np.float64)
    dp = np.asarray(dp, dtype=np.float64)
    up = np.log((h - dp) / (h - d))          # Cup(d) - Cup(d'), Cup = -ln(h-z)
    dn = np.log((h + dp) / (h + d))          # Cdn(d) - Cdn(d'), Cdn = -ln(h+z)
    return np.maximum(up, dn)


# ------------------------------------------ four-parameter renewal algebra

def four_param_rate(du, tu, dd, td, h, kfun):
    """Long-run dissipation coefficient c = r h^2 / sigma^2 for the
    policy: fire at displacement du -> re-place to tu; fire at dd ->
    re-place to td.  Exact Brownian cycle algebra (embedded two-state
    chain); all inputs broadcastable arrays.  Requires dd < td, tu < du.
    """
    ku = kfun(du, tu, h)
    kd = kfun(dd, td, h)
    span = du - dd
    pu = (tu - dd) / span          # P(next fire is at du | at tu)
    pd = (td - dd) / span
    Tu = (tu - dd) * (du - tu)     # sigma^2 * E[excursion time from tu]
    Td = (td - dd) * (du - td)
    # stationary weights over {just re-placed at tu, at td}
    piu = pd / (1.0 - pu + pd)
    pid = 1.0 - piu
    cost = piu * (pu * ku + (1.0 - pu) * kd) \
        + pid * (pd * ku + (1.0 - pd) * kd)
    tm = piu * Tu + pid * Td
    return cost * h * h / tm


def sweep_four_param(h, kfun, n_coarse=48, refine_rounds=6):
    """Dense coarse grid then nested refinement.  Returns (c_min, argmin)."""
    lo_t, hi_t = -0.995 * h, 0.995 * h

    def grid_eval(du_g, tu_g, dd_g, td_g):
        DU, TU, DD, TD = np.meshgrid(du_g, tu_g, dd_g, td_g,
                                     indexing="ij")
        ok = (DD < TD) & (TD < DU) & (DD < TU) & (TU < DU)
        c = np.full(DU.shape, np.inf)
        c[ok] = four_param_rate(DU[ok], TU[ok], DD[ok], TD[ok], h, kfun)
        i = np.unravel_index(np.argmin(c), c.shape)
        return c[i], (DU[i], TU[i], DD[i], TD[i])

    du_g = np.linspace(0.05 * h, hi_t, n_coarse)
    dd_g = np.linspace(lo_t, -0.05 * h, n_coarse)
    tu_g = np.linspace(lo_t, hi_t, n_coarse)
    td_g = np.linspace(lo_t, hi_t, n_coarse)
    best, arg = grid_eval(du_g, tu_g, dd_g, td_g)
    width = (hi_t - lo_t) / n_coarse
    for _ in range(refine_rounds):
        du0, tu0, dd0, td0 = arg
        m = 13
        du_g = np.linspace(max(du0 - width, 1e-4 * h),
                           min(du0 + width, hi_t), m)
        tu_g = np.linspace(max(tu0 - width, lo_t),
                           min(tu0 + width, hi_t), m)
        dd_g = np.linspace(max(dd0 - width, lo_t),
                           min(dd0 + width, -1e-4 * h), m)
        td_g = np.linspace(max(td0 - width, lo_t),
                           min(td0 + width, hi_t), m)
        best, arg = grid_eval(du_g, tu_g, dd_g, td_g)
        width /= 4.0
    return float(best), tuple(float(v) for v in arg)


# ----------------------------------------------------------- grid QVI (PI)

def qvi_policy_iteration(n, h, kfun, jump=None, verbose=False):
    """Average-cost impulse control on the displacement grid by policy
    iteration.  States d_i = -h + (i+1) * 2h/(n+1), i = 0..n-1 (open
    interval).  Per walk step of duration dt = Delta^2/sigma^2 the
    diffusion moves +-1 (exact Brownian hitting laws at grid points).
    Edge states are forced-fire (the boundary itself is
    infinitely expensive; the optimum never approaches it).

    jump: optional dict {lam_dt: probability of a jump per walk step,
    probs: array over signed grid offsets, offsets: int array}.  With
    jumps, states are extended beyond +-h (forced fire, exact cost via
    the withdraw clamp).

    Returns dict with c = g h^2/sigma^2 (sigma-free formulation:
    work in units sigma = 1), the policy arrays, and diagnostics.
    """
    delta = 2.0 * h / (n + 1)
    dt = delta * delta               # sigma = 1
    if jump is None:
        d = -h + delta * (np.arange(n) + 1.0)
        n_ext = n
        interior = np.ones(n_ext, dtype=bool)
    else:
        # extend the grid by the jump support beyond the band
        ext = int(np.max(np.abs(jump["offsets"])))
        n_ext = n + 2 * ext
        d = -h + delta * (np.arange(n_ext) - ext + 1.0)
        interior = (np.arange(n_ext) >= ext) & (np.arange(n_ext) < ext + n)
    # fire targets must lie strictly inside the band
    tgt_ok = np.abs(d) < h - 0.5 * delta
    tgt_idx = np.where(tgt_ok)[0]
    # cost matrix K[i, j] for j in tgt_idx
    K = kfun(d[:, None], d[None, tgt_idx], h)
    K = np.asarray(K, dtype=np.float64)
    # beyond-range states have infinite isolated-class log-cost; cap
    # at 10 (de facto total loss, stated wherever jump results land)
    K[~np.isfinite(K)] = 10.0
    np.clip(K, None, 10.0, out=K)
    # self-fire (zero-cost no-op) excluded
    for row, i in [(np.searchsorted(tgt_idx, i), i)
                   for i in tgt_idx]:
        K[i, row] = np.inf

    forced = ~interior.copy()
    forced[0] = forced[-1] = True
    # also force-fire the first/last interior state (walking out of it
    # would hit the boundary)
    ii = np.where(interior)[0]
    forced[ii[0]] = forced[ii[-1]] = True

    centre_col = np.argmin(np.abs(d[tgt_idx]))
    action = np.full(n_ext, -1, dtype=int)     # -1 = continue
    action[forced] = centre_col                # column into tgt_idx

    if jump is not None:
        lam_dt = jump["lam_dt"]
        joff = jump["offsets"]
        jpr = jump["probs"]

    def evaluate(act):
        m = n_ext + 1                          # h[0..n_ext-1], g
        A = np.zeros((m, m))
        b = np.zeros(m)
        for i in range(n_ext):
            if act[i] >= 0:
                j = tgt_idx[act[i]]
                A[i, i] += 1.0
                A[i, j] -= 1.0
                b[i] = K[i, act[i]]
            else:
                A[i, i] += 1.0
                A[i, n_ext] = dt
                if jump is None:
                    A[i, i - 1] -= 0.5
                    A[i, i + 1] -= 0.5
                else:
                    A[i, i - 1] -= 0.5 * (1.0 - lam_dt)
                    A[i, i + 1] -= 0.5 * (1.0 - lam_dt)
                    for o, p in zip(joff, jpr):
                        A[i, min(max(i + o, 0), n_ext - 1)] -= lam_dt * p
        ref = tgt_idx[centre_col]
        A[n_ext, ref] = 1.0
        sol = np.linalg.solve(A, b)
        return sol[n_ext], sol[:n_ext]

    g_hist = []
    for it in range(200):
        g, hval = evaluate(action)
        g_hist.append(g)
        fire_val = K + hval[tgt_idx][None, :]
        best_col = np.argmin(fire_val, axis=1)
        best_fire = fire_val[np.arange(n_ext), best_col]
        cont = np.full(n_ext, np.inf)
        free = ~forced
        idx = np.where(free)[0]
        if jump is None:
            cont[idx] = 0.5 * (hval[idx - 1] + hval[idx + 1]) - dt * g
        else:
            base = 0.5 * (1.0 - lam_dt) * (hval[idx - 1] + hval[idx + 1])
            jp = np.zeros(len(idx))
            for o, p in zip(joff, jpr):
                jj = np.minimum(np.maximum(idx + o, 0), n_ext - 1)
                jp += p * hval[jj]
            cont[idx] = base + lam_dt * jp - dt * g
        # current action values
        cur = np.where(action >= 0,
                       K[np.arange(n_ext),
                         np.clip(action, 0, K.shape[1] - 1)]
                       + hval[tgt_idx[np.clip(action, 0,
                                              len(tgt_idx) - 1)]],
                       cont)
        new_action = action.copy()
        take_fire = best_fire < np.minimum(cont, cur) - 1e-12
        take_cont = cont < np.minimum(best_fire, cur) - 1e-12
        new_action[take_fire] = best_col[take_fire]
        new_action[take_cont] = -1
        new_action[forced & (new_action < 0)] = \
            best_col[forced & (new_action < 0)]
        if np.array_equal(new_action, action):
            break
        action = new_action
        if verbose:
            print(f"    PI iter {it}: g h^2 = {g * h * h:.6f}")
    c = g * h * h
    fire_states = np.where(action >= 0)[0]
    fs_int = fire_states[interior[fire_states] & ~forced[fire_states]] \
        if jump is None else fire_states
    out = {
        "n": n, "c": float(c), "iters": it,
        "fire_from": [float(d[i] / h) for i in fire_states[:6]],
        "n_fire_states": int(len(fire_states)),
    }
    # policy shape summary: innermost voluntary fire thresholds/targets
    vol = [i for i in fire_states if not forced[i]]
    if vol:
        ups = [i for i in vol if d[i] > 0]
        dns = [i for i in vol if d[i] < 0]
        if ups:
            iu = min(ups, key=lambda i: d[i])
            out["up_trigger"] = float(d[iu] / h)
            out["up_target"] = float(d[tgt_idx[action[iu]]] / h)
        if dns:
            idn = max(dns, key=lambda i: d[i])
            out["dn_trigger"] = float(d[idn] / h)
            out["dn_target"] = float(d[tgt_idx[action[idn]]] / h)
    else:
        # only forced-edge fires: effective triggers are the forced ring
        iu = ii[-1]
        idn = ii[0]
        out["up_trigger"] = float(d[iu] / h)
        out["up_target"] = float(d[tgt_idx[action[iu]]] / h)
        out["dn_trigger"] = float(d[idn] / h)
        out["dn_target"] = float(d[tgt_idx[action[idn]]] / h)
    return out


def jump_spec(n, h, alpha, z0_frac, lam_frac, trunc=2.0):
    """Two-sided truncated-Pareto jump law discretised to grid offsets.
    lam_frac is the jump rate in units sigma^2/h^2; sizes are
    z0 U^(-1/alpha), truncated at trunc*h with the tail mass folded
    into the last bin (the truncation and the k-cap are stated
    wherever jump results land)."""
    delta = 2.0 * h / (n + 1)
    z0 = z0_frac * h
    max_off = int(np.ceil(trunc * h / delta))
    min_off = max(1, int(np.floor(z0 / delta)))
    offs, probs = [], []
    for o in range(min_off, max_off + 1):
        lo, hi = o * delta, (o + 1) * delta
        p_lo = min(1.0, (lo / z0) ** (-alpha)) if lo > z0 else 1.0
        p_hi = min(1.0, (hi / z0) ** (-alpha)) if hi > z0 else 1.0
        m = max(p_lo - p_hi, 0.0)
        if o == max_off:
            m = p_lo
        if m > 0:
            offs += [o, -o]
            probs += [m / 2, m / 2]
    probs = np.array(probs)
    probs /= probs.sum()
    return {"offsets": np.array(offs, dtype=int), "probs": probs,
            "lam_dt": lam_frac * (1.0 / h ** 2) * delta ** 2}


# ------------------------------------------------------------- validation

def validate():
    print("== validation against verify_floor.py captured targets ==")
    t0 = time.time()
    ok = True
    # corridor constants (verify_floor check 4)
    for rho, target in ((0.05, 1.9522), (0.02, 1.9804), (0.005, 1.9950)):
        c = c_min_corridor(100.0, 100.0 * rho, 0.0)
        good = abs(c - target) < 2e-3
        ok &= good
        print(f"  c_min({rho}) = {c:.4f}  (target {target})"
              f"{'' if good else '  ** FAIL **'}")
    # narrow-limit c(x) closed form vs four_param algebra (narrow kernel)
    for x, target in ((0.5, 2.7726), (0.7153, 2.4554)):
        c = float(four_param_rate(np.array(x), np.array(0.0),
                                  np.array(-x), np.array(0.0),
                                  1.0, k_narrow_vec))
        anal = -math.log(1.0 - x) / (x * x)
        good = abs(c - anal) < 1e-9 and abs(c - target) < 1e-3
        ok &= good
        print(f"  narrow c({x}) cycle algebra = {c:.4f} "
              f"(closed form {anal:.4f}, target {target})"
              f"{'' if good else '  ** FAIL **'}")
    # exact three-parameter renewal grid minimum at rho 0.05
    # (verify_floor check 6: min c = 2.397 at the symmetric point)
    h = 5.0
    n = 32
    best, arg = np.inf, None
    for i in range(1, n):
        dd = -h + h * i / n
        for j in range(1, n):
            du = h * j / n
            for k in range(1, n):
                d0 = dd + (du - dd) * k / n
                if not (dd < d0 < du):
                    continue
                c = float(four_param_rate(
                    np.array(du), np.array(d0), np.array(dd),
                    np.array(d0), h, k_exact_vec))
                if c < best:
                    best, arg = c, (dd / h, d0 / h, du / h)
    good = abs(best - 2.397) < 3e-3 and abs(arg[0] + arg[2]) < 0.1 \
        and abs(arg[1]) < 0.1
    ok &= good
    print(f"  exact 3-param grid (rho 0.05): min c = {best:.3f} at "
          f"({arg[0]:.2f}, {arg[1]:.2f}, {arg[2]:.2f}) "
          f"(target 2.397 symmetric){'' if good else '  ** FAIL **'}")
    # exact vs narrow kernel agreement in the narrow regime
    rng_d = np.linspace(-0.9, 0.9, 41)
    devs = []
    for rho_n in (0.005, 0.0005):
        h_n = rho_n * S0
        ke = k_exact_vec(rng_d[:, None] * h_n, rng_d[None, :] * h_n, h_n)
        kn = k_narrow_vec(rng_d[:, None] * h_n, rng_d[None, :] * h_n, h_n)
        devs.append(float(np.max(np.abs(ke - kn))))
    print(f"  exact vs narrow kernel: max |diff| = {devs[0]:.2e} at "
          f"rho 0.005, {devs[1]:.2e} at rho 0.0005 "
          f"(O(rho) correction, ratio {devs[0] / devs[1]:.1f})")
    ok &= devs[0] < 2e-2 and 5.0 < devs[0] / devs[1] < 20.0
    print(f"  validation {'PASSED' if ok else 'FAILED'} "
          f"({time.time() - t0:.1f} s)")
    return ok


# ------------------------------------------------------------------- main

def main(full=True):
    if not validate():
        sys.exit("validation failed; stopping before any search")
    if not full:
        return
    results = {"narrow": {}, "exact": {}, "jump": {}}

    print("\n== four-parameter renewal sweep ==")
    t0 = time.time()
    c4, arg4 = sweep_four_param(1.0, k_narrow_vec)
    print(f"  narrow limit: min c = {c4:.6f} at du = {arg4[0]:.4f}, "
          f"tu = {arg4[1]:.4f}, dd = {arg4[2]:.4f}, td = {arg4[3]:.4f} "
          f"({time.time() - t0:.1f} s)   [conjectured c* = 2.4554]")
    results["narrow"]["four_param"] = {"c": c4, "arg": arg4}
    for rho in (0.005, 0.02, 0.05, 0.10, 0.20):
        h = rho * S0
        t0 = time.time()
        c4e, arg4e = sweep_four_param(h, k_exact_vec)
        cmin = c_min_corridor(S0, h, 0.0)
        print(f"  exact rho = {rho}: min c = {c4e:.6f} at "
              f"(du, tu, dd, td)/h = ({arg4e[0]/h:.4f}, {arg4e[1]/h:.4f}, "
              f"{arg4e[2]/h:.4f}, {arg4e[3]/h:.4f}); c_min = {cmin:.4f} "
              f"({time.time() - t0:.1f} s)")
        results["exact"][str(rho)] = {
            "c": c4e, "arg_over_h": [v / h for v in arg4e],
            "c_min": cmin}

    print("\n== grid QVI, policy iteration (no structural assumption) ==")
    for n in (401, 801, 1601):
        t0 = time.time()
        r = qvi_policy_iteration(n, 1.0, k_narrow_vec)
        print(f"  narrow, n = {n}: c_opt = {r['c']:.6f}, "
              f"up trig/tgt = {r.get('up_trigger'):.4f}/"
              f"{r.get('up_target'):.4f}, "
              f"dn = {r.get('dn_trigger'):.4f}/{r.get('dn_target'):.4f}, "
              f"{r['n_fire_states']} fire states, PI iters {r['iters']} "
              f"({time.time() - t0:.1f} s)")
        results["narrow"][f"qvi_n{n}"] = r
    for rho in (0.02, 0.05, 0.20):
        h = rho * S0
        t0 = time.time()
        r = qvi_policy_iteration(801, h, k_exact_vec)
        print(f"  exact rho = {rho}, n = 801: c_opt = {r['c']:.6f}, "
              f"up = {r.get('up_trigger'):.4f}/{r.get('up_target'):.4f}, "
              f"dn = {r.get('dn_trigger'):.4f}/{r.get('dn_target'):.4f} "
              f"({time.time() - t0:.1f} s)")
        results["exact"][f"qvi_rho{rho}"] = r

    print("\n== jump-regime grid QVI (rho 0.05, z0 = 0.5h, "
          "lam = 0.5 sigma^2/h^2, trunc 2h, k-cap 10) ==")
    for alpha in (1.6, 2.5, 3.5):
        for n in (301, 601):
            t0 = time.time()
            r = qvi_policy_iteration(n, 5.0, k_exact_vec,
                                     jump=jump_spec(n, 5.0, alpha,
                                                    0.5, 0.5))
            print(f"  alpha = {alpha}, n = {n}: c_opt = {r['c']:.4f}, "
                  f"up = {r.get('up_trigger'):.4f}/"
                  f"{r.get('up_target'):.4f}, "
                  f"dn = {r.get('dn_trigger'):.4f}/"
                  f"{r.get('dn_target'):.4f} "
                  f"({time.time() - t0:.0f} s)")
            results["jump"][f"a{alpha}_n{n}"] = r

    with open("qvi_results.json", "w") as fp:
        json.dump(results, fp, indent=2)
    print("\nwrote qvi_results.json")


if __name__ == "__main__":
    main(full="--validate" not in sys.argv)
