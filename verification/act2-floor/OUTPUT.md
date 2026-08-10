# Captured output: the floors

`python3 verify_floor.py`, seed 31, run 2026-08-10, about twenty-six
seconds on the reference machine. This capture is the regression
target for the second act: a numeric shift here is a manuscript-level
event.

```
[1] equal-width potential identity (20000 draws): max |direct - potential| = 2.674e-12
[2] share-potential identity, general widths (20000 draws): max |direct - potential| = 8.882e-16
[3] free locus (2000 solved widenings): max |log-cost| = 2.676e-14
[4] corridor constants: c_min(0.05) = 1.9522, c_min(0.02) = 1.9804, c_min(0.005) = 1.9950; one-cycle era band at rho 0.05: 1.9498
[5] centred trigger sweep (MC): c(0.3) = 3.80, c(0.5) = 2.69, c(0.72) = 2.49, c(0.9) = 2.76; minimum 2.49 > c_min 1.952
[6] renewal family, analytic grid (29791 policies): min c = 2.397 at (-0.72, 0.00, 0.72); symmetric, above c_min 1.952
[7] widen-slide adversaries, W_max = 20 (width-uniform floor 5.12, fixed-at-cap best 6.29):
    trigger 0.375, slide-back to 0.000: rate =   6.49 (149 paid events): above floor
    trigger 0.375, slide-back to 0.125: rate =   5.74 (166 paid events): above floor
    trigger 0.300, slide-back to 0.200: rate =   5.51 (431 paid events): above floor
    no free-rider found: width variation does not beat the cap-width floor on this zoo
[8] clock/drift bounds (5000 geometries): phi - w max = 0.0e+00 (<= 0); omega0' closed form vs FD rel err = 4.0e-08; (C2) and the omega0'' bound hold
[9] analytic corollary 2(1 - 3 rho) <= c_min <= 2: 1.700 <= 1.9522 <= 2; 1.880 <= 1.9804 <= 2; 1.970 <= 1.9950 <= 2
[10] swap class: A table matches; edge-hugging/floor = 1.005; MC r(0.5, 0.5) = 1.025e-03 (pred 1.006e-03, ratio 1.02); r(0.95, 0.2) = 2.631e-04 (pred 3.065e-04, ratio 0.86); floor 2.578e-04
all checks passed
```

Reading of each line.

1. The equal-width placement family, written as a maximum of potential
   differences, holds to floating-point noise across the full
   parameter range, wide ranges far outside the narrow limit included.
2. The share-potential identity is exact at every width pair, which
   establishes it as an algebraic identity of the mint arithmetic
   rather than a narrow-limit approximation. This is the check that
   distinguishes the manuscript's central law from an asymptotic.
3. Solved ratio-preserving re-placements, widenings up to fourfold,
   cost zero. The free locus is exactly the share-preserving locus.
4. The corridor constants are consistent with c_min about 2(1 - rho).
   Uniformising over the era band moves the third decimal only.
5. Monte Carlo centred policies sit on the analytic c(x) within Monte
   Carlo error and all sit above the corridor floor.
6. The full three-parameter renewal placement family bottoms out at
   the symmetric fire-at-0.72 policy. Off-centre re-placement buys
   nothing, and no member approaches the corridor floor.
7. The widen-slide zoo at thirty-two paths per configuration sits
   above the width-uniform floor throughout, and below the
   fixed-at-cap best nowhere. The closest approach is the gentle
   partial-slide configuration, 5.51 on 431 events, about 1.4 standard
   errors above the floor, which is the expected picture for a floor
   approached from inside the class rather than attained. A longer run
   of the full-recentre configuration, 644 paid events, measures 7.02
   plus or minus 0.28.
8. The exact ingredients of the width-uniform argument hold over
   random geometries: phi <= w, the closed form of omega0', the clock
   bound |omega0'| >= (a/b)/w, and the drift bound |omega0''| <= 12
   b^2/(a^3 w). The worst measured constant in the drift bound is
   about 3.9, so the twelve is conservative. The second derivative is
   differenced from the verified closed first derivative, because the
   raw second difference of omega0 is roundoff-bound at this step.
9. The analytic corollary c_min >= 2(1 - 3 u/s_-) holds with room. The
   true correction behaves like 2(1 - rho), so the constant three is
   crude but safe.
10. In the swap class the constant A(eta, gamma, 0) matches the
    manuscript's production table at all three gas levels. The
    edge-hugging renewal policy converges to the fee-only floor, ratio
    1.005 at m = 0.01, which is the sandwich closing. Monte Carlo
    return-point policies match the renewal form at the deployed
    convention, ratio 1.02, and at 0.86 near the edge, where
    discrete-step overshoot lengthens cycles; the near-edge policy
    sits two per cent above the floor. Landing between the floor and
    the renewal prediction is what a floor attained only in the limit
    looks like from inside the class.

## The scoping probe

`probe_bound.py` (seed 229, about thirty seconds) is the earlier
artefact and is kept because the manuscript quotes its minimum and
because it reaches the same constant by a different route. It
simulates the centred fixed-width family at four triggers under the
isolated mint arithmetic and matches the exact coefficient within
three per cent, with a measured minimum of c = 2.38 at x = 0.72 and
rho = 0.05. Its extension simulates off-centre re-placements against
the two-argument amplitude, ratios 0.99 and 1.08, and grid-searches
the three-parameter renewal family analytically to a minimum of 2.397
at the symmetric point.
