"""Scoping probe for the second act: does the fixed-width floor bind?

The earlier of the act's two artefacts, kept because the manuscript
quotes its minimum and because it reaches the same constant by a route
independent of the reference harness.

Simulates the fixed-width band policy at several trigger displacements
x, firing when |s - centre| >= x*u, under the isolated mint arithmetic
with an arithmetic Brownian square-root price. Checks that the realised
fractional dissipation rate matches c(x)*sigma^2/u^2 with c taken from
the closed-form per-event fractions, that the minimum over x sits near
the predicted interior optimum, and that no tested policy beats the
floor.

The off-centre extension, the placement family, is appended after the
original sweep rather than interleaved with it, so that the same seed
and the same draw order reproduce the original numbers exactly.

Standard library only, seeded. Run: python3 probe_bound.py  (~30 s)
"""

import math
import random

random.seed(229)

S0, U, SIG = 100.0, 5.0, 16.0
N_STEPS, N_PATHS, T = 1_000_000, 6, 1.0


def phi(s, sa, sb):
    return 2.0 * s - s * s / sb - sa


def mint_min(L, s, sa, sb, sa2, sb2):
    x_w = L * (1.0 / s - 1.0 / sb)
    y_w = L * (s - sa)
    return min(x_w / (1.0 / s - 1.0 / sb2), y_w / (s - sa2))


def event_fraction(sbar, u, delta):
    """Exact Delta R / V at displacement delta (either sign)."""
    s = sbar + delta
    sa, sb = sbar - u, sbar + u
    Lnew = mint_min(1.0, s, sa, sb, s - u, s + u)
    v_old = phi(s, sa, sb)
    return (v_old - Lnew * phi(s, s - u, s + u)) / v_old


def c_pred(x, sbar=S0, u=U):
    gu = event_fraction(sbar, u, x * u)
    gd = event_fraction(sbar, u, -x * u)
    return (-0.5 * math.log(1 - gu) - 0.5 * math.log(1 - gd)) / (x * x)


def run_policy(x):
    dt_sd = SIG * math.sqrt(T / N_STEPS)
    log_decay = 0.0
    for _ in range(N_PATHS):
        s, centre, L = S0, S0, 1.0
        for _ in range(N_STEPS):
            s += dt_sd * random.gauss(0.0, 1.0)
            if abs(s - centre) >= x * U:
                sa, sb = centre - U, centre + U
                Lnew = mint_min(L, s, sa, sb, s - U, s + U)
                log_decay += math.log(
                    (Lnew * phi(s, s - U, s + U)) / (L * phi(s, sa, sb)))
                L, centre = Lnew, s
    return -log_decay / (N_PATHS * T)


base = SIG * SIG / (U * U)
print(f"floor scale sigma^2/u^2 = {base:.3f} per unit time; "
      f"narrow-limit optimum x* ~ 0.715, c* ~ 2.455")
worst_c = float("inf")
for x in (0.3, 0.5, 0.72, 0.9):
    rate = run_policy(x)
    cm, cp = rate / base, c_pred(x)
    worst_c = min(worst_c, cm)
    print(f"x = {x:4.2f}: measured rate = {rate:8.3f}  c_meas = {cm:5.2f}  "
          f"c_pred = {cp:5.2f}  ratio = {cm / cp:5.2f}")
assert worst_c > 2.0, "a tested policy beat the conjectured floor"
print(f"minimum measured c = {worst_c:.2f} > 2.0: floor holds on the "
      f"tested family")


# ---------------------------------------------------------------------------
# The placement family: off-centre re-placements. Appended here rather
# than interleaved above, because the output above is a regression
# target and must reproduce draw for draw.

def event_fraction2(sbar, u, delta, deltap):
    """Exact Delta R / V: fire at displacement delta, re-place with the
    price at displacement deltap of the new (equal-width) range."""
    s = sbar + delta
    sa, sb = sbar - u, sbar + u
    c2 = s - deltap
    Lnew = mint_min(1.0, s, sa, sb, c2 - u, c2 + u)
    v_old = phi(s, sa, sb)
    return (v_old - Lnew * phi(s, c2 - u, c2 + u)) / v_old


def logcost_potential(sbar, u, delta, deltap):
    """Exact per-event log-cost as a potential difference."""
    s = sbar + delta
    P = 2.0 * s + u

    def cup(x):
        return math.log((u * P - x * x) / (u - x))

    def cdn(x):
        return math.log((u * P - x * x) / ((u + x) * (s + u - x)))

    return max(cup(delta) - cup(deltap), cdn(delta) - cdn(deltap))


worst_id = 0.0
for d in (-4.5, -2.0, 0.0, 1.0, 3.0, 4.5):
    for dp in (-4.0, -1.5, 0.0, 2.0, 4.0):
        direct = -math.log(1.0 - event_fraction2(S0, U, d, dp))
        worst_id = max(worst_id, abs(direct - logcost_potential(S0, U, d, dp)))
assert worst_id < 1e-9, "placement-family potential identity failed"
print(f"placement-family potential identity: "
      f"max |direct - potential| = {worst_id:.2e}")


def c_renewal(dd, d0, du, sbar=S0, u=U):
    """Analytic coefficient of the renewal policy: place at d0, fire on
    hitting du (up) or dd (down), re-place at d0. Exact per-event
    fractions, Brownian exit probability and mean exit time."""
    ku = -math.log(1.0 - event_fraction2(sbar, u, du, d0))
    kd = -math.log(1.0 - event_fraction2(sbar, u, dd, d0))
    pu = (d0 - dd) / (du - dd)
    return (pu * ku + (1.0 - pu) * kd) * u * u / ((d0 - dd) * (du - d0))


def run_policy2(dd, d0, du):
    """Monte Carlo of the renewal policy (off-centre re-placement)."""
    dt_sd = SIG * math.sqrt(T / N_STEPS)
    log_decay = 0.0
    for _ in range(N_PATHS):
        s, centre, L = S0, S0 - d0, 1.0
        for _ in range(N_STEPS):
            s += dt_sd * random.gauss(0.0, 1.0)
            d = s - centre
            if d >= du or d <= dd:
                sa, sb = centre - U, centre + U
                c2 = s - d0
                Lnew = mint_min(L, s, sa, sb, c2 - U, c2 + U)
                log_decay += math.log(
                    (Lnew * phi(s, c2 - U, c2 + U)) / (L * phi(s, sa, sb)))
                L, centre = Lnew, c2
    return -log_decay / (N_PATHS * T)


print("off-centre re-placements (renewal family, displacements in u units):")
for dd, d0, du in ((-0.6 * U, 0.2 * U, 0.8 * U), (-0.9 * U, -0.3 * U, 0.5 * U)):
    rate = run_policy2(dd, d0, du)
    cm, cp = rate / base, c_renewal(dd, d0, du)
    print(f"  dd = {dd / U:5.2f}, d0 = {d0 / U:5.2f}, du = {du / U:5.2f}: "
          f"c_meas = {cm:5.2f}  c_pred = {cp:5.2f}  ratio = {cm / cp:5.2f}")
    assert 0.85 < cm / cp < 1.15, "off-centre analytic prediction missed"
    assert cm > 2.0, "an off-centre policy beat the conjectured floor"

best, arg = float("inf"), None
n = 24
for i in range(1, n):
    dd = -U + U * i / n
    for j in range(1, n):
        du = U * j / n
        for k in range(1, n):
            d0 = dd + (du - dd) * k / n
            c = c_renewal(dd, d0, du)
            if c < best:
                best, arg = c, (dd / U, d0 / U, du / U)
print(f"analytic renewal-family minimum: c = {best:.3f} at "
      f"dd = {arg[0]:.2f}, d0 = {arg[1]:.2f}, du = {arg[2]:.2f} (u units)")
assert best > 2.0, "renewal-family grid found a policy below c = 2"
print("floor holds on the placement family")
