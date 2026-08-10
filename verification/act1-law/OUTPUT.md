# Captured output: the forward law

`python3 mc_harness.py`, seed 29, run 2026-08-10, about sixteen
seconds on the reference machine. This capture is the regression
target for the first act: a numeric shift here is a manuscript-level
event.

```
[1] amplitude closed forms vs mint arithmetic (40000 draws): max rel err = 2.135e-12
[2] corner values: up vs L*w max rel err = 4.930e-15; down vs L*w*sa/sb max rel err = 1.026e-14
[3] down-branch monotonicity threshold: numerical rho = 0.561617, analytic (sqrt(17)-3)/2 = 0.561553, diff = 6.39e-05
[4] dissipation identity: 250 firings, sum J = 9.868119, f_T - f_0 = -9.761905, Ito = 0.276210, Tanaka = -0.169996; |LHS-RHS|/scale = 1.551e-14
[5] occupation offsets: sup|density-1| = 0.034 (mean-occupation bound 0.053); firing offsets sup|density-1|: fine monitoring = 4.48, coarse monitoring = 0.48 (degeneracy vs uniformity)
[6] directional firing ratio: empirical N+/N- = 1.5641, scale-function prediction = 1.4918, rel diff = 0.048
all checks passed
```

Reading of each line.

1. Both branches of the amplitude match the venue's mint-minimum
   arithmetic to floating-point noise across the full parameter range,
   including near-degenerate wide ranges. The draw count is forty
   thousand because each of the twenty thousand geometries is evaluated
   on both branches.
2. The corner values are attained exactly. The down-branch boundary
   magnitude is `L*w*s_a/s_b` rather than `L*w*sbar/s_b`, which is the
   point at which the down branch parts company with a naive
   symmetrisation of the up branch.
3. The down-branch monotonicity threshold `rho* = (sqrt(17)-3)/2` is
   confirmed by bisection on a four thousand point grid.
4. The pathwise dissipation identity checks to machine precision rather
   than to discretisation error, because the holding value is piecewise
   quadratic in the square-root price coordinate, so the per-step
   second-order expansion is exact whenever a step does not straddle a
   range bound. With triggers interior to the range, straddling steps
   are rare and none occurred at this seed. On a payoff carrying cubic
   or higher terms the same check would agree only to order sqrt(dt).
5. The occupation-offset deviation sits inside the mean-occupation
   bound at sigma*sqrt(T) of thirty ticks. The firing-offset contrast
   is the monitoring dichotomy: near-continuous monitoring concentrates
   the offset, a deviation of 4.48 on 250 events being point-mass-like,
   and coarse monitoring restores near-uniformity, 0.48 being
   consistent with uniform plus sampling noise at that count.
6. The two-barrier direction ratio matches the scale-function form
   within Monte Carlo and discrete-step overshoot error at eight
   thousand cycles.
