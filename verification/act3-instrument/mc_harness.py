"""Reference implementation for the third act, the instrument.

Standard library only, fixed seed, no on-chain data anywhere; the
sibling of the first act's `mc_harness.py` and the second act's
`verify_floor.py`. Eight checks, each with its own independently seeded
generator, random.Random(1000*k + SEED), so that a later edit to one
check never shifts another's draws. Extensions add new check numbers
and never reorder existing ones.

Numbers printed here are quoted in the manuscript's section on
numerical verification and captured in OUTPUT.md, which is the
regression target: a numeric shift is a manuscript-level event.

 [1] The flat-entry delay law, density proportional to (Dt-a)^(-1/2),
     mixed against the half-normal kernel reproduces the overshoot
     density exactly, the Owen T identity, by smooth quadrature.
 [2] The joint flat-entry law by exact simulation: flat entry, Levy
     first-passage sampling with no path discretisation, and
     Kolmogorov-Smirnov agreement of the overshoot marginal, of the
     delay distribution 1 - sqrt(1-a), and of O/sqrt(a) against the
     folded normal.
 [3] Planted recovery on the full pipeline. The world is a jump
     diffusion with a planted Pareto tail; the threshold operator and
     the trailing bipower scale with candidate exclusion run unchanged.
     The realised-variance variant of the scale fails here by design,
     because the planted world's jump variance share inflates it about
     twofold, far beyond the empirical 1.198, which is the bias
     budget's third row made visible. Two recoveries are asserted, the
     jump share inside the small-delay bracket around the per-event
     ground truth, and the planted tail index by Hill on the exceedance
     sizes.
 [4] The delay-invariance dichotomy. A penetration operator's overshoot
     is delay-invariant, med[O^2/a] falling with a because its
     attainment time spreads the delay axis, while a sparse-check lag
     operator scales diffusively, med[O^2/a] flat in a. A dwell-in-time
     rule under dense checking clusters the actuation time at the dwell
     value instead of spreading it, so the population signature mixes
     operator clusters and the per-operator scan needs the penetration
     form, which is what this check exercises.
 [5] Jump enrichment: a penetration operator's near-zero-delay firings
     are nearly pure jump, and more jump-loaded than a plain operator's.
 [6] Agreement-test size: Fisher exact on synthetic pool-common nulls
     at realistic stratum counts holds its nominal level.
 [7] The tick-discreteness sweep behind the bias budget's eighth row. A
     rounded diffusion cannot reproduce the quiet-pool pathology,
     because its per-block moves under-disperse, so the honest jump-free
     null is a compound-Poisson trade stream: Poisson trade counts,
     signed geometric multi-tick moves averaging two ticks, per-block
     variance set by the grid value of sigma*sqrt(a-bar)/spacing,
     watched by a two-sided every-block operator with lines at half-tick
     offsets. The spurious exceedance rate against the grid delivers the
     admission constant c_tick.
 [8] Cox checking, densified after jumps, shifts the small-delay jump
     share in level but not the recovered tail in shape.

Run:  python3 mc_harness.py     (under two seconds)
"""
from __future__ import annotations

import math
import random
import sys
import time

SEED = 37
Z95 = 1.959963984540054
BASE3 = 0.0027            # 2*nsf(3), folded-normal mass beyond 3

_results = []


def nsf(x):
    return 0.5 * math.erfc(x / math.sqrt(2))


def npdf(x):
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def check(num, desc, ok, detail):
    _results.append(ok)
    print(f"[{num}] {desc}: {detail}{'' if ok else '   ** FAIL **'}")


def median(xs):
    s = sorted(xs)
    n = len(s)
    return 0.5 * (s[(n - 1) // 2] + s[n // 2])


def ks_stat(sample, cdf):
    s = sorted(sample)
    n = len(s)
    d = 0.0
    for i, v in enumerate(s):
        c = cdf(v)
        d = max(d, abs((i + 1) / n - c), abs(i / n - c))
    return d


def hill_alpha(vals, o_ref):
    logs = [math.log(v / o_ref) for v in vals if v > o_ref]
    if len(logs) < 50:
        return None, len(logs)
    return 1.0 + 1.0 / (sum(logs) / len(logs)), len(logs)


def wilson_half(p, n):
    return Z95 * math.sqrt(max(p * (1 - p), 1e-9) / n)


# ----------------------------------------------------------------------
# [1] the Owen-T identity, by smooth quadrature (a = sin^2 theta)

def check1():
    def lhs(o, n=4000):
        h = (math.pi / 2) / n
        tot = 0.0
        for i in range(n + 1):
            th = i * h
            wgt = 1 if i in (0, n) else (4 if i % 2 else 2)
            s = math.sin(th)
            v = 0.0 if (s == 0.0 and o > 0) else 2 * npdf(o / s if s else 0.0)
            tot += wgt * v
        return tot * h / 3

    err = 0.0
    for o in (0.0, 0.3, 0.7, 1.0, 1.5, 2.0, 3.0):
        target = math.sqrt(2 * math.pi) * nsf(o)
        err = max(err, abs(lhs(o) / target - 1))
    check(1, "delay-law mixture reproduces the overshoot density (Owen-T identity)",
          err < 1e-6, f"max rel err over 7 points = {err:.2e}")


# ----------------------------------------------------------------------
# [2] flat-entry laws by exact Levy first-passage sampling

def check2():
    rng = random.Random(1000 * 2 + SEED)
    n_trials = 1_000_000
    DEPTH = 8.0                      # entry flat on (0, 8) below the line
    ev_a, ev_o = [], []
    for _ in range(n_trials):
        h = DEPTH * rng.random()
        z = rng.gauss(0.0, 1.0)
        if z == 0.0:
            continue
        tau = (h / z) ** 2           # Levy first-passage time, sigma = 1
        if tau > 1.0:
            continue
        o = rng.gauss(0.0, 1.0) * math.sqrt(1.0 - tau)
        if o <= 0:
            continue
        ev_a.append(1.0 - tau)
        ev_o.append(o)

    def cdf_over(o):                 # sqrt(2pi)*(o*nsf(o) + n(0) - n(o))
        return math.sqrt(2 * math.pi) * (o * nsf(o) + npdf(0.0) - npdf(o))

    def cdf_delay(a):
        return 1.0 - math.sqrt(max(0.0, 1.0 - a))

    def cdf_folded(r):
        return 1.0 - 2.0 * nsf(r)

    d1 = ks_stat(ev_o, cdf_over)
    d2 = ks_stat(ev_a, cdf_delay)
    d3 = ks_stat([o / math.sqrt(a) for o, a in zip(ev_o, ev_a)], cdf_folded)
    ok = max(d1, d2, d3) < 0.015 and len(ev_o) > 20_000
    check(2, "flat-entry kernel and delay law (exact sampler)",
          ok, f"n = {len(ev_o)}, KS: overshoot {d1:.4f}, "
              f"delay {d2:.4f}, folded ratio {d3:.4f}")


# ----------------------------------------------------------------------
# shared world simulation for [3], [4], [5], [8]

def simulate_world(B, sigma, lam, z0, alpha, rng):
    xs = [0.0] * B
    js = [0.0] * B
    x = 0.0
    for i in range(B):
        s = z0 * rng.random() ** (-1.0 / alpha) if rng.random() < lam else 0.0
        x += rng.gauss(0.0, sigma) + s
        xs[i] = x
        js[i] = s
    return xs, js


def run_operator(xs, js, w, pen=0.0, dwell=0, period=1,
                 bern_p=None, cox_after=None, rng=None):
    """Threshold detector on the common price stream. Returns events
    (t_act, O, jump_label, fire_block, cross_block). Crossing = most
    recent entry into the outside region (mirrors the probes'
    tick-walk convention); dips back inside reset it."""
    events = []
    b = w
    crossed = None
    consec = 0
    last_jump = -10
    for i, x in enumerate(xs):
        if js[i] > 0:
            last_jump = i
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
        if bern_p is not None:
            p = 1.0 if (cox_after is not None
                        and i - last_jump <= cox_after) else bern_p
            is_check = rng.random() < p
        else:
            is_check = (i % period == 0)
        if is_check and x >= b + pen and consec >= max(dwell, 1):
            jl = js[crossed] > 0 and xs[crossed] - js[crossed] < b
            events.append((i - crossed + 1, x - b, jl, i, crossed))
            b = x + w
            crossed = None
            consec = 0
    return events


def straddle_surv(o, z0, alpha):
    """Planted P(O_J > o) under flat gap occupation."""
    lam0 = z0 + z0 / (alpha - 1)
    if o <= z0:
        lam = (z0 - o) + z0 / (alpha - 1)
    else:
        lam = z0 ** alpha * o ** (1 - alpha) / (alpha - 1)
    return lam / lam0


B = 400_000
SIGMA = 4.0
LAM = 0.012
Z0 = 30.0
ALPHA = 2.5
W_LINE = 30.0
TRAIL = 43_200


def checks_3_4_5_8():
    rng = random.Random(1000 * 3 + SEED)
    xs, js = simulate_world(B, SIGMA, LAM, Z0, ALPHA, rng)

    # prefix sums of adjacent-increment products for the trailing
    # bipower sigma-hat, the designated scale estimator; the window ends
    # before the crossing block
    cp = [0.0] * (B + 1)
    prev_x = 0.0
    prev_d = 0.0
    for i, x in enumerate(xs):
        d = x - prev_x
        cp[i + 1] = cp[i] + abs(d) * abs(prev_d)
        prev_x, prev_d = x, d

    def sigma_bv(cross):
        lo = cross - TRAIL
        if lo < 0:
            return None
        return math.sqrt((math.pi / 2) * (cp[cross] - cp[lo]) / TRAIL)

    fast = run_operator(xs, js, W_LINE)
    pen = run_operator(xs, js, W_LINE, pen=32.0)
    lag = run_operator(xs, js, W_LINE, period=40)

    # --- [3a] jump share within the small-delay bracket ---------------
    adm = [(a, o, jl, cr) for a, o, jl, fb, cr in fast
           if a <= 10 and cr >= TRAIL]
    m = len(adm)
    exceed = 0
    w_true = 0
    floor_acc = 0.0
    sizes_d2 = []
    for a, o, jl, cr in adm:
        sg = sigma_bv(cr)
        if sg and o > 3.0 * sg * math.sqrt(a):
            exceed += 1
        w_true += jl
        floor_acc += straddle_surv(6.0 * SIGMA * math.sqrt(a), Z0, ALPHA)
        if a <= 2:
            sizes_d2.append(o)
    ehat = exceed / m
    w_hat = max(0.0, (ehat - BASE3) / (1 - BASE3))
    w_true /= m
    floor_factor = floor_acc / m
    half = wilson_half(ehat, m) / (1 - BASE3)
    # lower bound: straddles above the doubled cut pass unless the
    # monitoring noise dips below -kappa/2 (mass nsf(1.5))
    lo_b = w_true * floor_factor * (1 - nsf(1.5)) - half
    hi_b = w_true + BASE3 + half
    ok3a = lo_b <= w_hat <= hi_b and m >= 500
    check(3, "planted jump-share inside the small-delay bracket (bipower pipeline)",
          ok3a, f"m = {m}, w_hat = {w_hat:.3f}, truth = {w_true:.3f}, "
                f"bracket [{lo_b:.3f}, {hi_b:.3f}] "
                f"(floor factor {floor_factor:.2f})")

    # --- [3b] Hill recovery of the planted tail index ------------------
    a_hat, n_exc = hill_alpha(sizes_d2, 60.0)
    ok3b = a_hat is not None and abs(a_hat - ALPHA) <= 0.35
    check("3b", "Hill recovery of planted alpha from exceedance sizes",
          ok3b, f"alpha_hat = {a_hat:.3f} (planted {ALPHA}), "
                f"n_exceed = {n_exc}" if a_hat else f"n_exceed = {n_exc}")

    # --- [4] delay-invariance dichotomy --------------------------------
    def med_o2_per_a(evs, alo, ahi):
        v = [o * o / a for a, o, _, _, _ in evs if alo <= a <= ahi]
        return median(v) if len(v) >= 30 else None

    pn_s = med_o2_per_a(pen, 1, 20)
    pn_l = med_o2_per_a(pen, 60, 400)
    lg_s = med_o2_per_a(lag, 1, 10)
    lg_l = med_o2_per_a(lag, 30, 40)
    # the lag band is [0.5, 3]: long-delay survivors are meander-
    # conditioned (Rayleigh factor ~2 over the endpoint-conditioned
    # short-delay events), so diffusive scaling means an O(1) ratio
    # near 2, against the policy collapse far below 1.
    r_pn = pn_l / pn_s if pn_s and pn_l else None
    r_lg = lg_l / lg_s if lg_s and lg_l else None
    ok4 = (r_pn is not None and r_pn < 0.35
           and r_lg is not None and 0.5 <= r_lg <= 3.0)
    check(4, "penetration delay-invariance vs lag diffusive scaling",
          ok4, f"penetration med[O^2/a] long/short = "
               f"{r_pn if r_pn is None else round(r_pn, 3)} (<0.35), "
               f"lag = {r_lg if r_lg is None else round(r_lg, 3)} "
               f"(in [0.5, 3])")

    # --- [5] jump enrichment under penetration -------------------------
    # threshold 0.8, not ~1: the label marks the CROSSING type, and a
    # diffusive crossing followed by a second jump inside the delay
    # window fires the penetration condition with a diffusive label,
    # real physics the mixture's kernel K(do|a; o_J) accommodates.
    pen_d2 = [jl for a, o, jl, _, _ in pen if a <= 2]
    fast_d2 = [jl for a, o, jl, _, _ in fast if a <= 2]
    sh_pen = sum(pen_d2) / len(pen_d2) if pen_d2 else None
    sh_fast = sum(fast_d2) / len(fast_d2) if fast_d2 else None
    ok5 = (sh_pen is not None and sh_fast is not None
           and sh_pen >= 0.80 and sh_pen > sh_fast and len(pen_d2) >= 50)
    check(5, "penetration filter jump-enriches the small-delay sample",
          ok5, f"jump share <=2blk: penetration {sh_pen:.3f} "
               f"(n {len(pen_d2)}), plain {sh_fast:.3f} (n {len(fast_d2)})")

    return xs, js


# ----------------------------------------------------------------------
# [8] Cox checking: level shifts, shape does not

def check8(xs, js):
    rng8 = random.Random(1000 * 8 + SEED)
    poi = run_operator(xs, js, W_LINE, bern_p=0.15, rng=rng8)
    cox = run_operator(xs, js, W_LINE, bern_p=0.15, cox_after=2, rng=rng8)

    def wshare(evs):
        d = [jl for a, o, jl, _, _ in evs if a <= 10]
        return (sum(d) / len(d), len(d)) if d else (None, 0)

    def fmt(x):
        return "n/a" if x is None else f"{x:.3f}"

    wp, np_ = wshare(poi)
    wc, nc = wshare(cox)
    ap, nap = hill_alpha([o for a, o, _, _, _ in poi if a <= 5], 60.0)
    ac, nac = hill_alpha([o for a, o, _, _, _ in cox if a <= 5], 60.0)
    ok8 = (wp is not None and wc is not None and wc >= wp - 0.02
           and ap is not None and ac is not None
           and abs(ac - ap) <= 0.40 and np_ >= 100 and nc >= 100)
    check(8, "Cox checking shifts jump-share level, not tail shape",
          ok8, f"w_share: cox {fmt(wc)} (n {nc}) vs poisson {fmt(wp)} "
               f"(n {np_}); alpha_hat: cox {fmt(ac)} (n_exc {nac}) "
               f"vs poisson {fmt(ap)} (n_exc {nap})")


# ----------------------------------------------------------------------
# [6] agreement-test size on synthetic pool-common nulls

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


def check6():
    rng = random.Random(1000 * 6 + SEED)
    R = 400
    p = 0.15
    worst = 0.0
    detail = []
    for n1, n2 in ((100, 100), (30, 500)):
        rej = 0
        for _ in range(R):
            k1 = sum(1 for _ in range(n1) if rng.random() < p)
            k2 = sum(1 for _ in range(n2) if rng.random() < p)
            if fisher_exact_2s(k1, n1 - k1, k2, n2 - k2) < 0.05:
                rej += 1
        rate = rej / R
        worst = max(worst, rate)
        detail.append(f"({n1},{n2}): {rate:.3f}")
    check(6, "Fisher agreement test holds nominal size on common-p nulls",
          worst <= 0.07, f"rejection rates at 0.05: {', '.join(detail)}")


# ----------------------------------------------------------------------
# [7] tick-discreteness sweep: the c_tick admission constant

def _poisson(rng, nu):
    limit = math.exp(-nu)
    k, p = 0, 1.0
    while p > limit:
        k += 1
        p *= rng.random()
    return k - 1


def _scan_two_sided(xr, half):
    """Every-block two-sided detector; lines at anchor +- half (half-tick
    offset keeps the line off the integer grid, like a recovered phi*W).
    Crossing = most recent entry into the outside region of the fired
    side; returns (t_act, O)."""
    events = []
    anchor = xr[0]
    up, dn = anchor + half, anchor - half
    crossed, side = None, 0
    for i, x in enumerate(xr):
        if crossed is None:
            if x > up:
                crossed, side = i, 1
            elif x < dn:
                crossed, side = i, -1
            else:
                continue
        elif (side > 0 and x <= up) or (side < 0 and x >= dn):
            crossed = None
            continue
        events.append((i - crossed + 1, (x - up) if side > 0 else (dn - x)))
        anchor = x
        up, dn = anchor + half, anchor - half
        crossed = None
    return events


def check7():
    rng = random.Random(1000 * 7 + SEED)
    ABAR = 10
    EJ2 = 6.0                    # E[J^2] for the +-geometric(1/2) trade move
    grid = (1.0, 2.0, 4.0, 8.0, 16.0, 32.0)   # sigma*sqrt(a-bar) / spacing
    rates = []
    for v in grid:
        sigma = v / math.sqrt(ABAR)
        nu = sigma * sigma / EJ2             # trades per block
        half = max(2.0, round(7.5 * sigma)) + 0.5
        Bd = 120_000
        x = 0
        xr = [0] * Bd
        for i in range(Bd):
            for _ in range(_poisson(rng, nu)):
                j = 1
                while rng.random() < 0.5:
                    j += 1
                x += j if rng.random() < 0.5 else -j
            xr[i] = x
        rr = [o / (sigma * math.sqrt(a))
              for a, o in _scan_two_sided(xr, half) if a <= ABAR]
        rates.append(sum(1 for r in rr if r > 3.0) / len(rr)
                     if len(rr) >= 200 else None)
    mono = all(r is not None for r in rates) and \
        all(rates[i + 1] <= rates[i] + 0.01 for i in range(len(grid) - 1))
    c_tick = next((v for v, r in zip(grid, rates)
                   if r is not None and r <= 2 * BASE3), None)
    ok = mono and c_tick is not None
    check(7, "discreteness sweep delivers c_tick (spurious <= 2x baseline)",
          ok, "spurious rates " + ", ".join(
              f"{v:g}:{'n/a' if r is None else format(r, '.4f')}"
              for v, r in zip(grid, rates))
          + f"; c_tick = {'none' if c_tick is None else format(c_tick, 'g')}")


# ----------------------------------------------------------------------

def main():
    t0 = time.time()
    print(f"instrument synthetic harness, seed {SEED}")
    check1()
    check2()
    xs, js = checks_3_4_5_8()
    check6()
    check7()
    check8(xs, js)
    dt = time.time() - t0
    print(f"({dt:.1f} s)")
    if all(_results):
        print("all checks passed")
    else:
        print("CHECK FAILURES PRESENT")
        sys.exit(1)


if __name__ == "__main__":
    main()
