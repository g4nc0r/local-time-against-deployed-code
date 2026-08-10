"""Reference implementation for the first act, the forward law.

Standard library only, no dependencies, deterministic seed. Six checks,
each named for the result of the manuscript it asserts.

  1. the two-branch amplitude, both branches, against the venue's
     mint-minimum arithmetic over a random parameter sweep
  2. the corner values of the amplitude against L*w and L*w*s_a/s_b
  3. the down-branch monotonicity threshold against the closed form
     rho* = (sqrt(17)-3)/2
  4. the pathwise dissipation identity on a simulated path with
     impulsive re-placement
  5. offset equidistribution: occupation sampling against the bound of
     the equidistribution lemma, then firing-time sampling under coarse
     and fine monitoring, the monitoring dichotomy
  6. the direction split against its scale-function form

Numbers printed here are quoted in the manuscript's section on
numerical verification and captured in OUTPUT.md, which is the
regression target: a numeric shift is a manuscript-level event.

Run:  python3 mc_harness.py     (about sixteen seconds)
"""

import math
import random

random.seed(29)


# ---------------------------------------------------------------- CL geometry

def phi(s, sa, sb):
    """Per-unit-liquidity position value in token1 units (Geometric Siphon eq. 3)."""
    return 2.0 * s - s * s / sb - sa


def mint_min(L, s, sa, sb, sa2, sb2):
    """Binding-side mint minimum (Geometric Siphon eq. 4), isolated case."""
    x_w = L * (1.0 / s - 1.0 / sb)
    y_w = L * (s - sa)
    t0 = x_w / (1.0 / s - 1.0 / sb2)
    t1 = y_w / (s - sa2)
    return min(t0, t1)


def residual_mint(L, sbar, u, delta):
    """Value surrendered by the equal-width recentred rebalance at
    displacement delta, from the mint arithmetic directly."""
    s = sbar + delta
    sa, sb = sbar - u, sbar + u
    sa2, sb2 = s - u, s + u
    Lnew = mint_min(L, s, sa, sb, sa2, sb2)
    return L * phi(s, sa, sb) - Lnew * phi(s, sa2, sb2)


def residual_up_closed(L, sbar, u, delta):
    """Up branch, token0-binding, delta in [0, u]. The Geometric
    Siphon's Theorem 4 closed form."""
    return L * delta * (2.0 * sbar + u + delta) / (sbar + u)


def residual_down_closed(L, sbar, u, delta):
    """Down branch, token1-binding, delta in [-u, 0]."""
    return (-L * delta * (sbar + delta) * (2.0 * sbar + u + delta)
            / ((sbar + u) * (sbar + u + delta)))


# ------------------------------------------------------------------- check 1

def check_amplitudes(n=20000):
    worst = 0.0
    for _ in range(n):
        sbar = math.exp(random.uniform(math.log(0.5), math.log(500.0)))
        rho = random.uniform(0.01, 0.95)
        u = rho * sbar
        L = math.exp(random.uniform(0.0, 10.0))
        frac = random.uniform(0.001, 0.999)
        for delta, closed in (
            (frac * u, residual_up_closed(L, sbar, u, frac * u)),
            (-frac * u, residual_down_closed(L, sbar, u, -frac * u)),
        ):
            m = residual_mint(L, sbar, u, delta)
            scale = max(abs(m), abs(closed), L * u * 1e-12)
            worst = max(worst, abs(m - closed) / scale)
    print(f"[1] amplitude closed forms vs mint arithmetic "
          f"({2*n} draws): max rel err = {worst:.3e}")
    assert worst < 1e-9


# ------------------------------------------------------------------- check 2

def check_corners(n=2000):
    worst_up = worst_dn = 0.0
    for _ in range(n):
        sbar = math.exp(random.uniform(math.log(0.5), math.log(500.0)))
        rho = random.uniform(0.01, 0.95)
        u = rho * sbar
        L = math.exp(random.uniform(0.0, 6.0))
        w = 2.0 * u
        sa, sb = sbar - u, sbar + u
        up = residual_mint(L, sbar, u, u)
        dn = residual_mint(L, sbar, u, -u)
        worst_up = max(worst_up, abs(up - L * w) / (L * w))
        worst_dn = max(worst_dn, abs(dn - L * w * sa / sb) / (L * w * sa / sb))
    print(f"[2] corner values: up vs L*w max rel err = {worst_up:.3e}; "
          f"down vs L*w*sa/sb max rel err = {worst_dn:.3e}")
    assert worst_up < 1e-9 and worst_dn < 1e-9


# ------------------------------------------------------------------- check 3

def check_monotonicity_threshold():
    rho_star = (math.sqrt(17.0) - 3.0) / 2.0
    sbar, L = 10.0, 1.0

    def monotone(rho, grid=4000):
        u = rho * sbar
        prev = 0.0
        for i in range(1, grid + 1):
            m = u * i / grid
            v = residual_down_closed(L, sbar, u, -m)
            if v < prev - 1e-13 * (1.0 + abs(prev)):
                return False
            prev = v
        return True

    lo, hi = 0.3, 0.9
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if monotone(mid):
            lo = mid
        else:
            hi = mid
    found = 0.5 * (lo + hi)
    print(f"[3] down-branch monotonicity threshold: numerical rho = "
          f"{found:.6f}, analytic (sqrt(17)-3)/2 = {rho_star:.6f}, "
          f"diff = {abs(found - rho_star):.2e}")
    assert abs(found - rho_star) < 1e-3


# ------------------------------------------------------------------- check 4

def f_val(s, L, sa, sb):
    if s <= sa:
        return L * (1.0 / sa - 1.0 / sb) * s * s
    if s >= sb:
        return L * (sb - sa)
    return L * phi(s, sa, sb)


def f_prime(s, L, sa, sb):
    if s <= sa:
        return 2.0 * L * (1.0 / sa - 1.0 / sb) * s
    if s >= sb:
        return 0.0
    return L * (2.0 - 2.0 * s / sb)


def f_second(s, L, sa, sb):
    if s <= sa:
        return 2.0 * L * (1.0 / sa - 1.0 / sb)
    if s >= sb:
        return 0.0
    return -2.0 * L / sb


def check_identity(n_steps=2_000_000, sigma=0.5, T=1.0):
    """Pathwise: sum J + f(X_T,R_T) - f(X_0,R_0)  ==  Ito integral
    + half * integral of f'' d<X>, discretised on the same grid."""
    dt = T / n_steps
    sd = sigma * math.sqrt(dt)
    s = 100.0
    u = 5.0
    L = 1.0
    varphi = 0.25
    sa, sb = s - u, s + u
    lo_trig = sa + varphi * 2.0 * u
    hi_trig = sb - varphi * 2.0 * u
    sum_J = 0.0
    ito = 0.0
    tanaka = 0.0
    f0 = f_val(s, L, sa, sb)
    n_fire = 0
    logs = math.log(s)
    for _ in range(n_steps):
        s_old = s
        logs += sd * random.gauss(0.0, 1.0)
        s = math.exp(logs)
        ds = s - s_old
        ito += f_prime(s_old, L, sa, sb) * ds
        tanaka += 0.5 * f_second(s_old, L, sa, sb) * ds * ds
        if s <= lo_trig or s >= hi_trig:
            sa2, sb2 = s - u, s + u
            Lnew = mint_min(L, s, sa, sb, sa2, sb2)
            J = L * phi(s, sa, sb) - Lnew * phi(s, sa2, sb2)
            sum_J += J
            n_fire += 1
            L, sa, sb = Lnew, sa2, sb2
            lo_trig = sa + varphi * 2.0 * u
            hi_trig = sb - varphi * 2.0 * u
    fT = f_val(s, L, sa, sb)
    lhs = sum_J + fT - f0
    rhs = ito + tanaka
    scale = max(abs(sum_J), abs(fT - f0), 1e-9)
    rel = abs(lhs - rhs) / scale
    print(f"[4] dissipation identity: {n_fire} firings, sum J = "
          f"{sum_J:.6f}, f_T - f_0 = {fT - f0:.6f}, Ito = {ito:.6f}, "
          f"Tanaka = {tanaka:.6f}; |LHS-RHS|/scale = {rel:.3e}")
    assert rel < 2e-2


# ------------------------------------------------------------------- check 5

def offset_hist(vals, bins=20):
    h = [0] * bins
    for v in vals:
        h[min(int(v * bins), bins - 1)] += 1
    n = len(vals)
    return [bins * c / n for c in h]


def check_offsets(n_steps=2_000_000, sigma_total=30.0):
    """Tick-coordinate Brownian motion over the window; sigma_total is
    sigma*sqrt(T) in ticks. Occupation offsets against the
    equidistribution bound, then firing offsets under fine and coarse
    monitoring."""
    sd = sigma_total / math.sqrt(n_steps)
    x = 0.3
    occ = []
    for _ in range(n_steps):
        x += sd * random.gauss(0.0, 1.0)
        occ.append(x - math.floor(x))
    dens = offset_hist(occ)
    dev_occ = max(abs(d - 1.0) for d in dens)
    bound = 1.60 * 1.0 / sigma_total

    # firing offsets: two-sided barriers (finite mean exit), record the
    # within-tick offset of the state at the first *check* past a barrier
    def firing_offsets(check_every, step_sd=0.05, cycles=250):
        out = []
        for _ in range(cycles):
            y = 0.3
            i = 0
            while True:
                y += step_sd * random.gauss(0.0, 1.0)
                i += 1
                if i % check_every == 0 and (y >= 8.0 or y <= -8.0):
                    out.append(y - math.floor(y))
                    break
        return out

    fine = firing_offsets(1)
    coarse = firing_offsets(400)
    dev_fine = max(abs(d - 1.0) for d in offset_hist(fine, 10))
    dev_coarse = max(abs(d - 1.0) for d in offset_hist(coarse, 10))
    print(f"[5] occupation offsets: sup|density-1| = {dev_occ:.3f} "
          f"(mean-occupation bound {bound:.3f}); firing offsets "
          f"sup|density-1|: fine monitoring = {dev_fine:.2f}, coarse "
          f"monitoring = {dev_coarse:.2f} (degeneracy vs uniformity)")
    assert dev_fine > 3.0 * dev_coarse


# ------------------------------------------------------------------- check 6

def check_direction_ratio(n_cycles=8000, mu=0.02, sigma=1.0,
                          w_u=10.0, w_d=10.0):
    theta = 2.0 * mu / (sigma * sigma)
    pred = (math.exp(theta * w_d) - 1.0) / (1.0 - math.exp(-theta * w_u))
    dt = 0.02
    sd = sigma * math.sqrt(dt)
    drift = mu * dt
    up = dn = 0
    for _ in range(n_cycles):
        y = 0.0
        while True:
            y += drift + sd * random.gauss(0.0, 1.0)
            if y >= w_u:
                up += 1
                break
            if y <= -w_d:
                dn += 1
                break
    emp = up / dn
    print(f"[6] directional firing ratio: empirical N+/N- = {emp:.4f}, "
          f"scale-function prediction = {pred:.4f}, rel diff = "
          f"{abs(emp - pred) / pred:.3f}")
    assert abs(emp - pred) / pred < 0.05


if __name__ == "__main__":
    check_amplitudes()
    check_corners()
    check_monotonicity_threshold()
    check_identity()
    check_offsets()
    check_direction_ratio()
    print("all checks passed")
