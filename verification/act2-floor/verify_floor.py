"""Reference implementation for the second act, the floors.

Standard library only, no dependencies, deterministic seed. The design
is adversarial: checks 5 to 7 and 10 search their policy classes for a
member that undercuts its floor, and a member found below the floor
fails the run rather than being reported as a curiosity.

Ten checks. The first three are the algebraic layer.

  1. the placement-family potential identity at equal width over a
     random parameter sweep: log-cost equals the maximum of the
     potential differences
  2. the share-potential identity at general widths: log-cost equals
     max(ln(w0'/w0), ln(w1'/w1)) exactly, for any old and new range
  3. the free locus: solved ratio-preserving re-placements, widenings
     included, cost zero

The remaining seven are the floor layer.

  4. the corridor constant c_min(rho), regression values
  5. the centred trigger sweep by Monte Carlo against the exact c(x),
     with no policy below c_min
  6. the renewal placement family on an analytic grid: the minimum sits
     above c_min and is attained at the symmetric point
  7. widen-slide adversaries under a width cap, measured rate against
     the width-uniform floor 8 sigma^2 / W_max^2
  8. the exact clock and drift bounds, phi <= w, |omega0'| >= (a/b)/w,
     the closed form of omega0', and |omega0''| <= 12 b^2/(a^3 w),
     against finite differences over random geometries
  9. the analytic corollary c_min >= 2(1 - 3 u/s_-) against the
     corridor values
 10. the swap class: the constant A(eta, gamma, F) against the
     manuscript's production table, edge-hugging convergence to the
     fee-only floor, and Monte Carlo return-point policies against the
     renewal form and above the floor

Numbers printed here are quoted in the manuscript's section on
numerical verification and captured in OUTPUT.md, which is the
regression target: a numeric shift is a manuscript-level event.

Run:  python3 verify_floor.py     (about twenty-six seconds)
"""

import math
import random

random.seed(31)

S0, U, SIG = 100.0, 5.0, 16.0
RHO = U / S0


# ---------------------------------------------------------------- CL geometry

def phi(s, sa, sb):
    """Per-unit-liquidity position value in token1 units (Geometric Siphon eq. 3)."""
    return 2.0 * s - s * s / sb - sa


def withdraw(L, s, sa, sb):
    """Withdrawable token amounts, price clamped to the range."""
    sc = min(max(s, sa), sb)
    return L * (1.0 / sc - 1.0 / sb), L * (sc - sa)


def rebalance(L, s, sa1, sb1, sa2, sb2):
    """Isolated re-placement: returns (L_new, log_cost)."""
    x, y = withdraw(L, s, sa1, sb1)
    xu, yu = 1.0 / s - 1.0 / sb2, s - sa2
    L2 = min(x / xu, y / yu)
    v_old = x * s * s + y
    v_new = L2 * (xu * s * s + yu)
    return L2, -math.log(v_new / v_old)


def shares(x, y, s):
    v = x * s * s + y
    return x * s * s / v, y / v


# --------------------------------------------------- check 1: equal-width form

def check1():
    worst = 0.0
    for _ in range(20000):
        sbar = random.uniform(20.0, 500.0)
        u = random.uniform(0.001, 0.8) * sbar
        d = random.uniform(-0.98, 0.98) * u
        dp = random.uniform(-0.98, 0.98) * u
        s = sbar + d
        c2 = s - dp
        _, k = rebalance(1.0, s, sbar - u, sbar + u, c2 - u, c2 + u)
        P = 2.0 * s + u

        def cup(x):
            return math.log((u * P - x * x) / (u - x))

        def cdn(x):
            return math.log((u * P - x * x) / ((u + x) * (s + u - x)))

        pred = max(cup(d) - cup(dp), cdn(d) - cdn(dp))
        worst = max(worst, abs(k - pred))
    print(f"[1] equal-width potential identity (20000 draws): "
          f"max |direct - potential| = {worst:.3e}")
    assert worst < 1e-8


# ------------------------------------------------- check 2: share-potential form

def check2():
    worst = 0.0
    for _ in range(20000):
        sbar = random.uniform(20.0, 500.0)
        u1 = random.uniform(0.001, 0.8) * sbar
        s = sbar + random.uniform(-0.98, 0.98) * u1
        lo = s - random.uniform(0.02, 1.5) * u1
        hi = s + random.uniform(0.02, 1.5) * u1
        x, y = withdraw(1.0, s, sbar - u1, sbar + u1)
        w0, w1 = shares(x, y, s)
        xu, yu = 1.0 / s - 1.0 / hi, s - lo
        t0, t1 = shares(xu, yu, s)
        _, k = rebalance(1.0, s, sbar - u1, sbar + u1, lo, hi)
        pred = max(math.log(t0 / w0), math.log(t1 / w1))
        worst = max(worst, abs(k - pred))
    print(f"[2] share-potential identity, general widths (20000 draws): "
          f"max |direct - potential| = {worst:.3e}")
    assert worst < 1e-8


# --------------------------------------------------------- check 3: free locus

def solve_free(L, s, sa, sb, w2):
    """Bottom bound of the ratio-preserving range of width w2 at price s."""
    x, y = withdraw(L, s, sa, sb)
    r = y / x
    lo, hi = s - w2 + 1e-12, s - 1e-12
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        f = (s - mid) - r * (1.0 / s - 1.0 / (mid + w2))
        if f > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def check3():
    worst = 0.0
    for _ in range(2000):
        sbar = random.uniform(20.0, 500.0)
        u1 = random.uniform(0.005, 0.4) * sbar
        s = sbar + random.uniform(-0.9, 0.9) * u1
        w2 = random.uniform(1.1, 4.0) * 2.0 * u1
        a2 = solve_free(1.0, s, sbar - u1, sbar + u1, w2)
        _, k = rebalance(1.0, s, sbar - u1, sbar + u1, a2, a2 + w2)
        worst = max(worst, abs(k))
    print(f"[3] free locus (2000 solved widenings): max |log-cost| = "
          f"{worst:.3e}")
    assert worst < 1e-9


# --------------------------------------------- check 4: corridor constant c_min

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
    ups = [up_slope(x) for x in xs]
    dns = [dn_slope(x) for x in xs]
    best = float("inf")
    for i in range(n + 1):
        for j in range(i + 1, n + 1):
            best = min(best, (ups[j] - dns[i]) / (xs[j] - xs[i]))
    return u * u * best / 2.0


CMIN_TARGETS = ((0.05, 1.9522), (0.02, 1.9804), (0.005, 1.9950))


def check4():
    vals = []
    for rho, target in CMIN_TARGETS:
        c = c_min_corridor(100.0, 100.0 * rho, 0.0)
        vals.append(c)
        assert abs(c - target) < 2e-3, (rho, c, target)
        assert c <= 2.0
    cb = c_min_corridor(100.0, 5.0, 5.0)
    print(f"[4] corridor constants: c_min(0.05) = {vals[0]:.4f}, "
          f"c_min(0.02) = {vals[1]:.4f}, c_min(0.005) = {vals[2]:.4f}; "
          f"one-cycle era band at rho 0.05: {cb:.4f}")
    assert abs(cb - 1.9498) < 2e-3


# ------------------------------------------- checks 5 and 6: A0 policy families

def event_fraction2(sbar, u, delta, deltap):
    s = sbar + delta
    c2 = s - deltap
    _, k = rebalance(1.0, s, sbar - u, sbar + u, c2 - u, c2 + u)
    return 1.0 - math.exp(-k)


def c_renewal(dd, d0, du, sbar=S0, u=U):
    ku = -math.log(1.0 - event_fraction2(sbar, u, du, d0))
    kd = -math.log(1.0 - event_fraction2(sbar, u, dd, d0))
    pu = (d0 - dd) / (du - dd)
    return (pu * ku + (1.0 - pu) * kd) * u * u / ((d0 - dd) * (du - d0))


def mc_renewal(dd, d0, du, n_steps=250_000, n_paths=4):
    dt_sd = SIG * math.sqrt(1.0 / n_steps)
    log_decay = 0.0
    for _ in range(n_paths):
        s, centre, L = S0, S0 - d0, 1.0
        for _ in range(n_steps):
            s += dt_sd * random.gauss(0.0, 1.0)
            d = s - centre
            if d >= du or d <= dd:
                c2 = s - d0
                L, k = rebalance(L, s, centre - U, centre + U,
                                 c2 - U, c2 + U)
                centre = c2
                log_decay += k
    return log_decay / n_paths


def check5():
    base = SIG * SIG / (U * U)
    cmin = c_min_corridor(S0, U, 0.0)
    worst = float("inf")
    line = []
    for x in (0.3, 0.5, 0.72, 0.9):
        cm = mc_renewal(-x * U, 0.0, x * U) / base
        cp = c_renewal(-x * U, 0.0, x * U)
        assert 0.8 < cm / cp < 1.2, (x, cm, cp)
        worst = min(worst, cm)
        line.append(f"c({x}) = {cm:.2f}")
    print(f"[5] centred trigger sweep (MC): {', '.join(line)}; "
          f"minimum {worst:.2f} > c_min {cmin:.3f}")
    assert worst > cmin


def check6():
    cmin = c_min_corridor(S0, U, 0.0)
    best, arg = float("inf"), None
    n = 32
    for i in range(1, n):
        dd = -U + U * i / n
        for j in range(1, n):
            du = U * j / n
            for k in range(1, n):
                d0 = dd + (du - dd) * k / n
                c = c_renewal(dd, d0, du)
                if c < best:
                    best, arg = c, (dd / U, d0 / U, du / U)
    print(f"[6] renewal family, analytic grid (29791 policies): min c = "
          f"{best:.3f} at ({arg[0]:.2f}, {arg[1]:.2f}, {arg[2]:.2f}); "
          f"symmetric, above c_min {cmin:.3f}")
    assert best > cmin
    assert abs(arg[0] + arg[2]) < 0.1 and abs(arg[1]) < 0.1


# ------------------------------------ check 7: widen-slide adversaries

def omega0(L, s, sa, sb):
    x, y = withdraw(L, s, sa, sb)
    return shares(x, y, s)[0]


def widen_slide(trigger, target, w_max, n_steps=400_000, n_paths=32):
    """Free-widen toward the cap on trigger; once capped, pay a partial
    recentre in the share coordinate to `target` (or its mirror).
    trigger, target are omega distances from 1/2 (trigger > target)."""
    dt_sd = SIG * math.sqrt(1.0 / n_steps)
    log_decay = 0.0
    paid = 0
    for _ in range(n_paths):
        s, L = S0, 1.0
        sa, sb = S0 - U, S0 + U
        for _ in range(n_steps):
            s += dt_sd * random.gauss(0.0, 1.0)
            if not sa < s < sb:
                s = min(max(s, sa + 1e-9), sb - 1e-9)  # sub-step clamp
            w = sb - sa
            om = omega0(L, s, sa, sb)
            if abs(om - 0.5) >= trigger:
                if w < w_max - 1e-9:
                    w2 = min(w_max, 2.0 * w)      # free widen
                    a2 = solve_free(L, s, sa, sb, w2)
                    L2, k = rebalance(L, s, sa, sb, a2, a2 + w2)
                    assert k < 1e-9, "free widen was not free"
                    L, sa, sb = L2, a2, a2 + w2
                else:                              # paid slide-back at cap
                    om_t = 0.5 + (target if om > 0.5 else -target)
                    # equal-width-at-cap placement with target share om_t:
                    # bisect the centre offset
                    lo, hi = s - w_max / 2.0, s + w_max / 2.0
                    for _ in range(60):
                        c2 = 0.5 * (lo + hi)
                        cand = omega0(1.0, s, c2 - w_max / 2.0,
                                      c2 + w_max / 2.0)
                        if cand < om_t:
                            lo = c2
                        else:
                            hi = c2
                    c2 = 0.5 * (lo + hi)
                    L, k = rebalance(L, s, sa, sb, c2 - w_max / 2.0,
                                     c2 + w_max / 2.0)
                    sa, sb = c2 - w_max / 2.0, c2 + w_max / 2.0
                    log_decay += k
                    paid += 1
    return log_decay / n_paths, paid


def check7():
    w_max = 4.0 * U                      # cap ratio 2 on the base width
    u_max = w_max / 2.0
    floor = 8.0 * SIG * SIG / (w_max * w_max)
    attain = 2.4554 * SIG * SIG / (u_max * u_max)
    print(f"[7] widen-slide adversaries, W_max = {w_max:.0f} "
          f"(width-uniform floor {floor:.2f}, fixed-at-cap best "
          f"{attain:.2f}):")
    beaten = False
    for trigger, target in ((0.375, 0.0), (0.375, 0.125), (0.30, 0.20)):
        rate, paid = widen_slide(trigger, target, w_max)
        verdict = "above floor" if rate >= floor else "BEATS FLOOR"
        beaten = beaten or rate < floor
        print(f"    trigger {trigger:.3f}, slide-back to {target:.3f}: "
              f"rate = {rate:6.2f} ({paid} paid events): {verdict}")
    assert not beaten, ("a widen-slide policy beat the width-uniform floor: "
                        "stop and report the mechanism (session rule)")
    print("    no free-rider found: width variation does not beat the "
          "cap-width floor on this zoo")


# ------------------------------- check 8: the exact clock and drift bounds

def omega0_of_s(s, a, b):
    return (s - s * s / b) / (2.0 * s - s * s / b - a)


def check8():
    worst_c1 = worst_form = 0.0
    for _ in range(5000):
        sbar = random.uniform(20.0, 500.0)
        w = random.uniform(0.002, 0.35) * sbar
        a, b = sbar - w / 2.0, sbar + w / 2.0
        s = random.uniform(a + 0.02 * w, b - 0.02 * w)
        worst_c1 = max(worst_c1, phi(s, a, b) - w)                 # (C1)
        h = 1e-6 * w
        om = lambda z: omega0_of_s(z, a, b)

        def om1(z):
            return -((z - a) ** 2 + a * w) / (b * phi(z, a, b) ** 2)

        d1 = (om(s + h) - om(s - h)) / (2.0 * h)
        worst_form = max(worst_form, abs(d1 - om1(s)) / abs(om1(s)))
        # second derivative from the (just-verified) closed first
        # derivative; the raw second difference of om is roundoff-bound
        d2 = (om1(s + h) - om1(s - h)) / (2.0 * h)
        assert abs(d1) >= (a / b) / w - 1e-9, "clock bound (C2) failed"
        assert abs(d2) <= 12.0 * b * b / (a ** 3 * w), "drift bound failed"
    print(f"[8] clock/drift bounds (5000 geometries): phi - w max = "
          f"{worst_c1:.1e} (<= 0); omega0' closed form vs FD rel err = "
          f"{worst_form:.1e}; (C2) and the omega0'' bound hold")
    assert worst_c1 <= 1e-9


# ------------------------------------------ check 9: the analytic corollary

def check9():
    line = []
    for rho, _ in CMIN_TARGETS:
        c = c_min_corridor(100.0, 100.0 * rho, 0.0)
        lower = 2.0 * (1.0 - 3.0 * rho)
        assert lower <= c <= 2.0, (rho, c, lower)
        line.append(f"{lower:.3f} <= {c:.4f} <= 2")
    print(f"[9] analytic corollary 2(1 - 3 rho) <= c_min <= 2: "
          f"{'; '.join(line)}")


# ------------------------------------------------- check 10: the swap class

ETA = 1e-4


def qvi_A(eta, gamma, foot, n=200_000):
    best = float("inf")
    for i in range(1, n):
        d = i / n
        best = min(best, (gamma + eta * d + foot * d * d) / (d * (1.0 - d)))
    return best


def swap_cost(delta, delta0, gamma, foot):
    """Exact per-event fractional cost of the return-point move."""
    s = S0 + delta
    om_fire = omega0(1.0, s, S0 - U, S0 + U)
    c2 = s - delta0
    om_ret = omega0(1.0, s, c2 - U, c2 + U)
    dw = abs(om_ret - om_fire)
    return ETA * dw + gamma + foot * dw * dw


def r_swap_renewal(x, m, gamma, foot):
    """Renewal rate of: fire at |delta| = x u, correct back by m u on
    the same side. Exact shares in the cost; Brownian cycle algebra."""
    k = swap_cost(x * U, (x - m) * U, gamma, foot)
    return k * SIG * SIG / (U * U * m * (2.0 * x - m))


def mc_swap(x, m, gamma, foot, n_steps=250_000, n_paths=6):
    dt_sd = SIG * math.sqrt(1.0 / n_steps)
    total = 0.0
    for _ in range(n_paths):
        s, centre = S0, S0
        for _ in range(n_steps):
            s += dt_sd * random.gauss(0.0, 1.0)
            d = s - centre
            if abs(d) >= x * U:
                sign = 1.0 if d > 0 else -1.0
                k = swap_cost(d, sign * (x - m) * U, gamma, foot)
                total += -math.log1p(-k)
                centre = s - sign * (x - m) * U
    return total / n_paths


def check10():
    # table values as printed in the manuscript (eta 1e-4, F 0)
    for gamma, dstar_t, a_t in ((3e-6, 0.146, 1.411e-4),
                                (3e-7, 0.052, 1.116e-4),
                                (3e-8, 0.017, 1.035e-4)):
        a = qvi_A(ETA, gamma, 0.0)
        assert abs(a - a_t) / a_t < 2e-3, (gamma, a, a_t)
    # fee-only: A -> eta, and edge-hugging attains it
    a0 = qvi_A(ETA, 0.0, 0.0)
    assert abs(a0 - ETA) / ETA < 1e-2
    edge = r_swap_renewal(1.0, 0.01, 0.0, 0.0) / (ETA * SIG * SIG /
                                                  (4.0 * U * U))
    assert abs(edge - 1.0) < 0.02, edge
    # Monte Carlo return-point policies vs the renewal formula and floor
    gamma = 3e-7
    floor = qvi_A(ETA, gamma, 0.0) * (1.0 - RHO) ** 2 * SIG * SIG / \
        (4.0 * U * U)
    line = []
    for x, m in ((0.5, 0.5), (0.95, 0.2)):
        cm = mc_swap(x, m, gamma, 0.0)
        cp = r_swap_renewal(x, m, gamma, 0.0)
        assert 0.85 < cm / cp < 1.15, (x, m, cm, cp)
        assert cm > floor
        line.append(f"r({x}, {m}) = {cm:.3e} (pred {cp:.3e}, "
                    f"ratio {cm / cp:.2f})")
    print(f"[10] swap class: A table matches; edge-hugging/floor = "
          f"{edge:.3f}; MC {'; '.join(line)}; floor {floor:.3e}")


for chk in (check1, check2, check3, check4, check5, check6, check7,
            check8, check9, check10):
    chk()
print("all checks passed")
