# Captured output: the Sharp Constant search

Runs 2026-08-10.  CPU side: `qvi_solver.py` on the workstation
(float64, deterministic, NO RNG; full stdout in
`qvi_captured_stdout.txt`, results `qvi_results.json`).  GPU side:
`mc_policy_zoo.py` on the GPU host (R9700, HIP device 0, float64,
`use_deterministic_algorithms(True)`, seed 20260810, 18.8 min wall;
artefact `../output/zoo_results.json`).  This file is a regression
target: a numeric shift is a manuscript-level event.  MC numbers
carry the per-cell standard errors quoted below (96 replicas per
policy per regime); ROCm bitwise reproducibility was not certified,
so regression comparisons use seed + tolerance.

Ground truth only: driftless era diffusion in the sqrt-price
coordinate (plus planted two-sided truncated-Pareto jumps in the
jump arm); every impulse is priced by the exact isolated
re-placement mint arithmetic of the paper's own reference
implementation (validated against `verify_floor.py`'s captured
numbers before any search; transcripts in `../RUN-LOG.md`).

## Verdict: counterexample found. Conjecture 1 is false in both limbs

**The centred renewal family does not attain the infimum, the
narrow-limit optimal constant is 2 (not c\* = 2.4554), and the
corridor floor of Theorem 3 is sharp.**  The extremal
structure the conjecture was meant to expose is singular control:
two-sided reflection of the displacement at the corridor's tangency
points +-h/2, implemented as the limit of "tangency chattering"
policies, fire at |delta| = h/2 and re-place eps inward ON THE SAME
SIDE.  The paper's three-parameter renewal family cannot express
this because its single shared target forces the far-side excursion
to pay a large-move cost; two per-side targets are exactly the
missing instrument.  In hindsight the corridor argument itself
predicts the attainment: the extremal quadratic U = 2 delta^2/h^2
satisfies Ito with EQUALITY everywhere (U'' is constant), so the
only slack is the impulse inequality, which vanishes for
infinitesimal moves at the tangency points +-h/2; the reflection
family closes precisely that slack.  Closed form for the reflection
family at reflection displacement a (narrow limit, exact cycle
algebra):

    c(a) = h^2 / (2 a (h - a)),   minimised at a = h/2 with c = 2,

which is also the exact corridor expression, so the chattering limit
EQUALS the corridor infimum.  Verified c(a) against the cycle
algebra at a/h in {0.3, 0.4, 0.5, 0.6, 0.7}: 2.3832/2.0842/2.0000/
2.0825/2.3787 vs formula 2.3810/2.0833/2.0000/2.0833/2.3810
(eps = 0.001 h residual).

Corner riding (rem:corner) is untouched: riding at |delta| -> h
still diverges; the cheap ride is at the tangency h/2, where the
corridor formula gives the interior minimum of a U-shaped cost of
reflection points.

## Evidence, four independent instruments

1. **Exact cycle algebra** (closed-form Brownian exit laws, no MC,
   no discretisation).  Narrow limit: chattering c(eps) =
   2.0258/2.0024/2.000265/2.000024/2.000003 at eps/h = 0.1/0.03/
   0.01/0.003/0.001.  Every value below 2.39 kills the conjecture's
   attainment claim; the limit 2 kills the sharp-constant value.
2. **Grid QVI, policy iteration with no structural assumption**
   (states = displacement grid; actions = continue or fire to ANY
   grid state at exact cost; symmetric-walk discretisation whose
   exit laws match Brownian motion exactly at grid points).  Narrow
   limit: c_opt = 2.000017/2.000004/2.000001 at n = 401/801/1601,
   converging to the floor from above; the converged policy is
   fire-everywhere-beyond +-h/2 with one-grid-step inward targets,
   i.e. the discrete reflection.  Exact kernel: c_opt = 1.980273/
   1.951570/1.821901 at rho = 0.02/0.05/0.20 against corridor
   constants 1.9804/1.9522/1.8292 (fixed-s convention; the ~5e-4
   gap at rho 0.05 is the s-at-event vs s-at-midpoint convention,
   covered by the era-banded corridor, see `../RUN-LOG.md`).
3. **Four-parameter renewal sweep** (du, tu, dd, td; dense grid +
   refinement, closed form): minimum 2.000000 narrow at the
   symmetric tangency-chattering point; 1.995016/1.980258/1.951565/
   1.905980/1.821889 at rho = 0.005/0.02/0.05/0.10/0.20, each at
   the (slightly asymmetric) tangency point, tracking c_min(rho)
   throughout.  The tu = td slice reproduces the paper's captured
   three-parameter minimum 2.397 exactly.
4. **GPU Monte Carlo zoo** (139 policies x 96 replicas x 6 diffusive
   regime-step cells + 3 jump cells; wandering price, exact mint
   arithmetic, horizon-capped paths, burn-in, per-replica domain
   exclusion).  Chattering and reflection members sit on the floor
   at every regime; classic renewal members reproduce their analytic
   coefficients.  Representative (fine-step cells):

   | regime | chat e0.01 | refl a0.5 | classic x0.7153 | classic x0.5 | fixed-s c_min | era-banded c_min |
   |---|---|---|---|---|---|---|
   | rho 0.005 | 1.960 +- 0.020 | 1.967 +- 0.015 | 2.488 +- 0.023 | 2.738 +- 0.019 | 1.9950 | 1.9948 |
   | rho 0.05  | 1.928 +- 0.038 | 1.957 +- 0.052 | 2.388 +- 0.056 | 2.641 +- 0.045 | 1.9522 | 1.9447 |
   | rho 0.10  | 1.952 +- 0.076 | 1.953 +- 0.073 | 2.376 +- 0.106 | 2.576 +- 0.075 | 1.9081 | 1.8945 |

   No zoo member (139 policies including 128 random four-parameter
   draws) undercuts the era-banded floor beyond its noise; the
   rho 0.10 cells wander over a wide band (visited s down to
   ~0.55 S0) and their occasional sub-1.9 readings sit inside the
   corridor for the band actually visited.  Coarse-step cells agree
   within noise (no discretisation artefact at these eps).

## Jump regimes (rho 0.05, z0 = 0.5 h, lam = 0.5 sigma_s^2/h^2, two-sided, truncated 4 h, k-cap 10)

| alpha | grid-QVI c_opt (n 601) | QVI reflection point | MC zoo minimum |
|---|---|---|---|
| 1.6 | 4.160 | 0.445 h | 4.000 +- 0.163 (asymmetric two-target random member) |
| 2.5 | 3.509 | 0.425 h | 3.413 +- 0.150 (chattering, wider correction) |
| 3.5 | 3.092 | 0.412 h | 2.993 +- 0.121 (chattering, wider correction) |

The infimum rises with tail weight (the surcharge at work) and the
optimal reflection point moves INWARD from h/2, guarding against
straddles; the arg-min stays two-target chattering-like, with the
correction size growing with tail weight.  Beyond-range straddles
(L2 = 0, infinite isolated-class log-cost) are capped at k = 10 and
counted (20,136/13,439/9,438 capped events at alpha 1.6/2.5/3.5
across the zoo), so the quoted jump-regime values understate the
strict isolated ledger; see the stress maps' OUTPUT.md for the structural
statement.

## Status of Theorem 3 and Proposition 6

Both are CONFIRMED by everything here: no policy in any instrument
beats the corridor floor for its visited band, and the centred
renewal family's coefficients reproduce Proposition 6 exactly.  What
falls is only Conjecture 1's reading of the gap: the truth in "the
sandwich" lies at the BOTTOM, not the top.  c\* = 2.4554 remains
correct as the optimum of the single-target centred renewal family.

Caveats, stated plainly: (i) the QVI optimises over stationary
Markov policies on the displacement state, the standard sufficient
class for average-cost impulse control, and grid-restricted policies
converge from above; (ii) the eps -> 0 chattering limit has firing
rate diverging like 1/eps, so the infimum is approached, not
attained, within locally finite impulse policies, exactly the
singular-control boundary phenomenon; (iii) all exact-kernel
statements use the fixed-s convention of the paper's own
verification surface, with era-band corrections bracketed above.

Manuscript consequence, since applied: the Sharp Constant conjecture
this run refuted has been withdrawn and replaced by Proposition 7
(Sharpness of the Floor), which states that the corridor floor is
sharp, that the extremal policy is reflection at the tangency
displacements, and that c\* is the renewal-family optimum. That
strengthens Theorem 3 from a one-sided bound to a sharp
characterisation.  Note for the second act: the reflection
family is the constructive half of a matching upper bound for the
A_0 floor.
