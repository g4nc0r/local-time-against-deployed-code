"""GPU arm of the Sharp Constant search: a Monte Carlo policy zoo.

Simulates fixed-width A0 policies against synthetic era paths at scale
(PyTorch, columns = policy x regime x replica in lockstep), with the
wandering price tracked absolutely and every impulse priced by the
exact isolated re-placement mint arithmetic (no narrow-limit shortcut,
no fixed-s shortcut).  Purpose: confirm under full path realism the
CPU result of qvi_solver.py, that two-target tangency-chattering
policies drive the dissipation rate to the corridor floor and below
the conjectured constant c* = 2.4554, and map the same zoo across
jump regimes.

Policy family: fire when the displacement d = s - centre reaches
du = a_u * h (up) or -a_d * h (down); re-place so the new displacement
is t_u * h (up side) or -t_d * h (down side).  Classic centred renewal
is t = 0; tangency chattering is t = a - eps.

Zoo per regime:
  - chattering ladder a = 0.5, eps in {0.10, 0.03, 0.01} (x2 step sizes)
  - reflection-point sweep a in {0.3, 0.4, 0.5, 0.6, 0.7}, eps = 0.01
  - classic renewal x in {0.5, 0.7153, 0.9}, full recentre
  - 128 random four-parameter policies (seeded numpy draw)

Regimes: rho in {0.005, 0.05, 0.20} diffusive; jump regimes at
rho = 0.05 with two-sided Pareto jumps, alpha in {1.6, 2.5, 3.5},
jump scale z0 = 0.5 h, jump rate lambda = 0.5 sigma_s^2/h^2 (about one
jump per two diffusive half-width times).  Jumps land the state beyond
the trigger (straddle); the exact arithmetic prices the landed state,
including landings beyond the range boundary (withdraw clamp).

Conventions: float64 throughout (tensors are
small; kernel-launch overhead dominates, so the FP64 penalty on this
hardware is immaterial and is characterised in the run log);
torch.manual_seed + use_deterministic_algorithms(True); the captured
OUTPUT.md states seed and tolerances.  Simulation is controlled
synthetic ground truth only; no price model enters as an assumption.

Run:  python3 mc_policy_zoo.py [--validate] [--out results.json]
      --validate: small CPU run reproducing verify_floor.py-adjacent
      numbers (classic renewal vs analytic c(x)) before any big burn.
"""
from __future__ import annotations

import argparse
import json
import math
import time

import numpy as np
import torch

S0 = 100.0
SEED = 20260810
SIG = 16.0                 # sqrt-price volatility, verify_floor anchor

torch.manual_seed(SEED)
try:
    torch.use_deterministic_algorithms(True)
    DET = True
except Exception:
    DET = False


def k_exact_torch(s, centre_old, centre_new, h):
    """Exact isolated re-placement log-cost, elementwise float64."""
    sa1, sb1 = centre_old - h, centre_old + h
    sc = torch.clamp(s, sa1, sb1)
    x = 1.0 / sc - 1.0 / sb1
    y = sc - sa1
    sa2, sb2 = centre_new - h, centre_new + h
    xu = 1.0 / s - 1.0 / sb2
    yu = s - sa2
    L2 = torch.minimum(x / xu, y / yu)
    v_old = x * s * s + y
    v_new = L2 * (xu * s * s + yu)
    return -torch.log(v_new / v_old)


def build_zoo(rng):
    """Returns list of (name, a_u, t_u, a_d, t_d) in half-width units."""
    zoo = []
    for eps in (0.10, 0.03, 0.01):
        zoo.append((f"chat_a0.5_e{eps}", 0.5, 0.5 - eps, 0.5, 0.5 - eps))
    for a in (0.3, 0.4, 0.5, 0.6, 0.7):
        zoo.append((f"refl_a{a}", a, a - 0.01, a, a - 0.01))
    for x in (0.5, 0.7153, 0.9):
        zoo.append((f"classic_x{x}", x, 0.0, x, 0.0))
    for i in range(128):
        au = rng.uniform(0.10, 0.97)
        ad = rng.uniform(0.10, 0.97)
        tu = rng.uniform(-ad + 0.02, au - 0.02)
        td = rng.uniform(-au + 0.02, ad - 0.02)
        zoo.append((f"rand{i:03d}", au, tu, ad, td))
    return zoo


def simulate(zoo, rho, n_steps, n_reps, step_frac, device, seed,
             jump=None, progress=None):
    """Run the zoo at one regime.  Returns per-policy dict.

    step_frac: per-step sigma displacement as a fraction of h.
    jump: None or dict(alpha=..., z0_frac=..., lam_frac=...) with
    lam_frac the jump rate in units sigma_s^2/h^2.
    """
    h = rho * S0
    P = len(zoo)
    M = P * n_reps
    g = torch.Generator(device=device)
    g.manual_seed(seed)
    au = torch.tensor([z[1] for z in zoo], device=device,
                      dtype=torch.float64).repeat_interleave(n_reps) * h
    tu = torch.tensor([z[2] for z in zoo], device=device,
                      dtype=torch.float64).repeat_interleave(n_reps) * h
    ad = torch.tensor([z[3] for z in zoo], device=device,
                      dtype=torch.float64).repeat_interleave(n_reps) * h
    td = torch.tensor([z[4] for z in zoo], device=device,
                      dtype=torch.float64).repeat_interleave(n_reps) * h

    sd = step_frac * h
    dt = (sd / SIG) ** 2                       # time units of sigma_s = SIG
    s = torch.full((M,), S0, device=device, dtype=torch.float64)
    min_s = s.clone()
    centre = s.clone()
    cost = torch.zeros(M, device=device, dtype=torch.float64)
    nfire = torch.zeros(M, device=device, dtype=torch.float64)
    jcost = torch.zeros(M, device=device, dtype=torch.float64)
    njfire = torch.zeros(M, device=device, dtype=torch.float64)
    ncap = torch.zeros(M, device=device, dtype=torch.float64)

    if jump is not None:
        lam_dt = jump["lam_frac"] * (SIG / h) ** 2 * dt
        z0 = jump["z0_frac"] * h
        inv_alpha = 1.0 / jump["alpha"]

    # burn-in: discard the transient from the centred start (paths begin
    # at displacement zero, a costless interior state; without discard
    # the measured rate is biased low, seen in the local calibration run)
    burn = n_steps // 5

    for i in range(n_steps):
        noise = torch.randn(M, generator=g, device=device,
                            dtype=torch.float64)
        s = s + sd * noise
        jumped = None
        if jump is not None:
            u1 = torch.rand(M, generator=g, device=device,
                            dtype=torch.float64)
            u2 = torch.rand(M, generator=g, device=device,
                            dtype=torch.float64)
            u3 = torch.rand(M, generator=g, device=device,
                            dtype=torch.float64)
            jumped = u1 < lam_dt
            # truncation at 4h keeps the venue state on-domain over
            # the era; the truncated mass is stated in the capture
            size = torch.clamp(
                z0 * torch.clamp(u2, min=1e-12) ** (-inv_alpha),
                max=4.0 * h)
            sign = torch.where(u3 < 0.5, -1.0, 1.0)
            s = s + torch.where(jumped, sign * size,
                                torch.zeros_like(size))
        d = s - centre
        up = d >= au
        dn = d <= -ad
        fired = up | dn
        tgt = torch.where(up, tu, -td)
        c2 = s - tgt
        # beyond-range landings have L2 = 0 in the isolated class
        # (one-sided holdings cannot mint a price-containing range), an
        # infinite log-cost; cap at K_CAP = 10 (e^-10 residual value, de
        # facto total loss) and count capped events; the cap is stated
        # in the capture
        k = k_exact_torch(s, centre, c2, h)
        k = torch.where(torch.isfinite(k), k, torch.full_like(k, 10.0))
        capped = fired & (k >= 10.0)
        k = torch.clamp(k, max=10.0)
        k = torch.where(fired, k, torch.zeros_like(k))
        if i >= burn:
            cost = cost + k
            nfire = nfire + fired.to(torch.float64)
            ncap = ncap + capped.to(torch.float64)
            if jump is not None:
                jf = fired & jumped
                jcost = jcost + torch.where(jf, k, torch.zeros_like(k))
                njfire = njfire + jf.to(torch.float64)
        centre = torch.where(fired, c2, centre)
        min_s = torch.minimum(min_s, s)
        if progress and (i + 1) % progress == 0:
            print(f"    step {i + 1}/{n_steps}", flush=True)

    T = (n_steps - burn) * dt
    c_cols = (cost / T) * (h * h) / (SIG * SIG)
    c_cols = c_cols.reshape(P, n_reps)
    # exclude replicas whose price approached the domain edge (the
    # era-band hypothesis; excluded counts reported)
    alive = (min_s > 0.4 * S0).reshape(P, n_reps)
    nf = nfire.reshape(P, n_reps).sum(dim=1)
    out = {}
    for p, z in enumerate(zoo):
        keep = alive[p]
        vals = c_cols[p][keep]
        n_keep = int(keep.sum())
        out[z[0]] = {
            "policy": [z[1], z[2], z[3], z[4]],
            "c_mean": float(vals.mean()) if n_keep else None,
            "c_se": float(vals.std(unbiased=True)
                          / math.sqrt(n_keep)) if n_keep > 1 else None,
            "n_fire": int(nf[p]),
            "n_capped": int(ncap.reshape(P, n_reps)[p].sum()),
            "n_reps_kept": n_keep,
            "n_reps_excluded": n_reps - n_keep,
        }
        if jump is not None:
            jc = jcost.reshape(P, n_reps)[p].sum()
            jn = njfire.reshape(P, n_reps)[p].sum()
            out[z[0]]["jump_fire"] = int(jn)
            out[z[0]]["jump_cost_share"] = float(
                jc / max(float(cost.reshape(P, n_reps)[p].sum()), 1e-300))
    return out


def analytic_c(zoo_entry, rho):
    """Exact cycle-algebra prediction (diffusive, fixed-s convention)."""
    import qvi_solver as q
    _, aU, tU, aD, tD = (zoo_entry[0], *zoo_entry[1:])
    h = rho * S0
    return float(q.four_param_rate(
        np.array(aU * h), np.array(tU * h), np.array(-aD * h),
        np.array(-tD * h), h, q.k_exact_vec))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--out", default="zoo_results.json")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device = {device}, deterministic = {DET}, seed = {SEED}",
          flush=True)
    if device.type == "cuda":
        print(f"gpu = {torch.cuda.get_device_name(0)}", flush=True)

    rng = np.random.RandomState(SEED)
    zoo = build_zoo(rng)

    if args.validate:
        small = [z for z in zoo if z[0].startswith(("classic", "chat"))]
        t0 = time.time()
        res = simulate(small, 0.05, 120_000, 16, 0.01,
                       torch.device("cpu"), SEED + 1)
        print(f"validation run ({time.time() - t0:.0f} s):")
        ok = True
        for z in small:
            pred = analytic_c(z, 0.05)
            r = res[z[0]]
            dev = abs(r["c_mean"] - pred) / pred
            # discretisation overshoot biases chattering up; allow it
            tol = 0.30 if z[0].startswith("chat") else 0.15
            good = dev < tol
            ok &= good
            print(f"  {z[0]:22s} c = {r['c_mean']:.3f} +- {r['c_se']:.3f} "
                  f"(analytic {pred:.3f}, dev {dev:.1%})"
                  f"{'' if good else '  ** FAIL **'}")
        print("validation " + ("PASSED" if ok else "FAILED"))
        return

    results = {"seed": SEED, "deterministic": DET,
               "device": str(device), "sig": SIG, "regimes": {}}

    # diffusive regimes, two step sizes for discretisation control.
    # Per-path horizon capped at T ~ 0.9 time units so the wandering
    # price stays on-domain (sigma_s sqrt(T) ~ 0.15 S0); precision
    # comes from replicas.  rho = 0.2 stays QVI-only: any usable
    # wander there violates the standing h/s_- <= 1/5 hypothesis.
    # horizon: whichever is smaller of T = 0.9 (domain-wander cap,
    # sigma_s sqrt(T) ~ 0.15 S0) and ~60 cycles of the slowest zoo
    # policy per path (0.19 h^2 in sigma_s = 16 units); replicas (96)
    # carry the precision
    for rho in (0.005, 0.05, 0.10):
        h_ = rho * S0
        T_target = min(0.9, 0.19 * h_ * h_ * 256.0 / (SIG * SIG))
        for step_frac in (0.01, 0.004):
            n_steps = int(T_target / (step_frac * h_ / SIG) ** 2)
            tag = f"rho{rho}_step{step_frac}"
            print(f"== {tag} (n_steps {n_steps}) ==", flush=True)
            t0 = time.time()
            res = simulate(zoo, rho, n_steps, 96, step_frac, device,
                           SEED + int(rho * 1000) + int(step_frac * 1000),
                           progress=200_000)
            el = time.time() - t0
            for z in zoo[:11] + [("classic_x0.7153",)]:
                pass
            best = min((kv for kv in res.items()
                        if kv[1]["c_mean"] is not None),
                       key=lambda kv: kv[1]["c_mean"])
            print(f"  done {el:.0f} s; zoo minimum {best[0]} "
                  f"c = {best[1]['c_mean']:.4f} +- {best[1]['c_se']:.4f}",
                  flush=True)
            results["regimes"][tag] = {
                "elapsed_s": el, "n_steps": n_steps, "n_reps": 96,
                "step_frac": step_frac, "policies": res}

    # jump regimes at rho = 0.05 (jump sizes truncated at 4h, stated)
    for alpha in (1.6, 2.5, 3.5):
        tag = f"jump_a{alpha}_rho0.05"
        n_steps = int(min(0.9, 0.19 * 25.0 * 256.0 / (SIG * SIG))
                      / (0.01 * 0.05 * S0 / SIG) ** 2)
        print(f"== {tag} (n_steps {n_steps}) ==", flush=True)
        t0 = time.time()
        res = simulate(zoo, 0.05, n_steps, 96, 0.01, device,
                       SEED + int(alpha * 100),
                       jump={"alpha": alpha, "z0_frac": 0.5,
                             "lam_frac": 0.5}, progress=200_000)
        el = time.time() - t0
        best = min((kv for kv in res.items()
                    if kv[1]["c_mean"] is not None),
                   key=lambda kv: kv[1]["c_mean"])
        print(f"  done {el:.0f} s; zoo minimum {best[0]} "
              f"c = {best[1]['c_mean']:.4f} +- {best[1]['c_se']:.4f}",
              flush=True)
        results["regimes"][tag] = {
            "elapsed_s": el, "n_steps": n_steps, "n_reps": 96,
            "step_frac": 0.01, "jump": {"alpha": alpha, "z0_frac": 0.5,
                                        "lam_frac": 0.5},
            "policies": res}

    with open(args.out, "w") as fp:
        json.dump(results, fp, indent=2)
    print(f"wrote {args.out}", flush=True)


if __name__ == "__main__":
    main()
