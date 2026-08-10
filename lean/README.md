# Lean formalisation

Machine-checked proofs of the theorem layer of *Local Time Against Deployed
Code: The Exact Cost Law of Concentrated Liquidity Rebalancing, Its Sharp Floor, and
Its Inversion*, written in Lean 4 against mathlib. The scope is the idealised
real-arithmetic model of the paper. The Foundry suites under `../foundry/`
remain the check against fixed-point pool arithmetic on unmodified production
bytecode, the Python harnesses under the three source papers' `verification/`
folders and under `../calibration/` remain the numerical checks, and
`../verification/` remains the production-history anchor.

The library root is `LocalTime.lean`. The concentrated liquidity primitives of
§The object and §The central law live in `LocalTime/Defs.lean`, which every
other file imports. File names follow the mathlib convention of descriptive
content names; the mapping to the paper's numbering is recorded below and in
each file's doc comments. All statements refer to the 2026-08-10 consolidated
manuscript, in which the half-width is `h`, the per-event log-cost is the mint
kerf `k`, and the narrow-limit floor constant is the tangency constant.

The `phi` and mint-minimum definitions are a copy of the corresponding surface
in the Geometric Siphon formalisation, generalised from that paper's isolated
single-pool case to an arbitrary admissible target range. That repository owns
the original. Programme convention is to share by copy, not by symlink.

## Coverage

### Act I: the forward law

`LocalTime/Defs.lean` - the V3 range primitives of §The object: the
per-liquidity token amounts, the value coefficient `φ`, the holdings shares
`ω₀` and `ω₁`, the binding-side mint minimum, the retained fraction, and the
mint kerf of eq. (kdef). `share_add_eq_one` is the only structural fact the
central law consumes.

`LocalTime/ShareIdentity.lean` - **Theorem 2 (Share-Potential Identity)** and
its corollary, §The central law and Appendix "Proofs for the cost structure".

- `min_ratio_le_one`, `min_ratio_eq_one_iff` - the abstract half of the
  argument, isolated first. For two share pairs each summing to one, the
  smaller cross ratio is at most one, with equality exactly when the pairs
  agree. That is the entire source of the kerf's sign and of the free locus;
  nothing about pool geometry enters it.
- `retained_eq_min_share_ratio` - the substance of the theorem: the retained
  value fraction of an isolated re-placement, from any range containing the
  price to any admissible range containing the price, at any width pair, is
  `min(ω₀/ω₀', ω₁/ω₁')`. Width, centring, and the price level enter only
  through the shares.
- `kerf_eq_max_log` - the theorem as stated in the paper,
  `k = max(log(ω₀'/ω₀), log(ω₁'/ω₁))`.
- `kerf_nonneg` - `k ≥ 0` always. This is the sign that agrees with the
  machine-checked non-positivity of the isolated residual in the Geometric
  Siphon formalisation.
- `kerf_eq_zero_iff` - **Corollary (Free Locus)**: the kerf vanishes exactly on
  the share-preserving re-placements, at every width. This is what settles the
  free-riding question; centre motion is not the charged variable.

`LocalTime/Amplitude.lean` - **Lemma (Binding Side)**, **Proposition
(Two-Branch Amplitude)**, **Corollary (Corner Values)**, and **Lemma (Exact
Fractional Slopes)**, §The amplitude layer and §The cost structure.

- `cand0_form`, `cand1_form`, `cand_diff`, `cand0_le_cand1`, `cand1_le_cand0`
  the binding side, as the exact sign of `-δ(2s̄ + h + δ)`.
- `amplitude_up`, `amplitude_dn` - the two branches, proved as the exact
  difference between the withdrawn value and the value re-minted through the
  mint minimum, not posited as formulae. The upper branch is the Geometric
  Siphon's closed form; the lower branch is the value-surrendered form of
  Operator & Quantisation Microstructure's swap-free credit. What is new, and
  what these two theorems check, is the assembly.
- `ampDn_eq_cont_mul` - the branch relation `ΔR↓ = |ΔR↑ continued| · s/s_b'`.
- `amplitude_corner_up`, `amplitude_corner_dn` - the corner values `Lw` and
  `Lw · s_a/s_b`, so the corner ratio of OQM's sign corollary is one of the
  two limits of a single function.
- `hasDerivAt_gUp_zero`, `hasDerivAt_gDn_zero` - the exact fractional slopes
  `g'(0⁺) = 1/h` and `g'(0⁻) = -(s̄/s_b)(1/h)`, the position-value factors
  cancelling exactly. The second exhibits the factor `s̄/s_b` stated in the
  Geometric Siphon as the interior limit.

`LocalTime/Monotonicity.lean` - **Proposition (Down-Branch Monotonicity)**.

- `hasDerivAt_Gdn`, `GdnNum_corner`, `GdnNum_sub_corner`, `GdnNum_pos` - the
  derivative's cubic numerator, its corner value `s̄(2s̄² - 3s̄h - h²)`, and its
  positivity on the interior below the threshold.
- `strictMonoOn_Gdn` - sufficiency: below the threshold the down branch is
  strictly increasing in the displacement magnitude.
- `deriv_Gdn_corner_neg`, `not_strictMonoOn_Gdn` - necessity: above it the
  derivative at the corner is negative and the branch is not increasing up to
  the corner, which is the interior maximum of the statement.
- `threshold_iff` - the threshold in the narrow-range parameter,
  `2s̄² - 3s̄h - h² ≥ 0 ↔ h/s̄ ≤ (√17 - 3)/2`.

As published, the Geometric Siphon's monotonicity theorem asserts both branches
strictly monotone with no width hypothesis. This file supplies the condition the
down branch needs. Production ranges sit one to two orders inside the threshold,
so the empirical content of that paper is unaffected.

`LocalTime/Potentials.lean` - **Corollary (Placement-Family Potentials)**, §The
cost structure.

- `share0_eq_Qup`, `share1_eq_Qdn` - the branch functions are the shares: the
  token0 share of the equal-width position at displacement `z` is `s Q↑(z)` and
  the token1 share is exactly `Q↓(z)`. This is the cleanest statement of why
  the potential form and the central law are the same fact.
- `kerf_eq_max_potential` - the kerf of an equal-width re-placement is the
  larger of the two potential differences, so costs telescope along
  same-direction sequences and the return point enters only through the
  potentials' values.
- `strictMonoOn_Cup`, `strictAntiOn_Cdn` - the monotonicity of the two
  potentials. `C↑` needs no width hypothesis, the certifying inequality being
  `2sh + (h - z)² > 0`; `C↓` needs the standing hypothesis `5h ≤ s`, which the
  paper writes `h/s₋ ≤ 1/5`.
- `round_trip_pos` - **no free round trips**: a move off the current
  displacement and back costs strictly more than nothing. The proof is that
  `C↑` rises where `C↓` falls, so the two branch increments cannot both vanish.
- `reduction_up`, `reduction_dn` - setting the return displacement to zero
  recovers the two-branch amplitude on both branches, in fractional form
  against the withdrawn value.

`LocalTime/Offset.lean` - **Lemma (Offset Uniformity)**, §The equidistribution
lemma.

- `monotone_lattice_sum` - the interleaving core: along any sequence of pairwise
  interleaved intervals, the increments of a bounded monotone function sum to at
  most its oscillation. This is the whole content of the paper's "increments
  along any increasing sequence are dominated by the total variation".
- `bv_lattice_sum` - the same for a function of bounded variation, in Jordan
  form `q = f - g`, which is the form mathlib's
  `BoundedVariationOn.exists_monotoneOn_sub_monotoneOn` supplies.
- `latticeA_le_latticeB`, `latticeB_le_latticeA_succ`, `offset_window_bound`
  the two lattices `ϑ(k+z)` and `ϑ(k+z')` interleave exactly when
  `0 ≤ z ≤ z' < 1`, and the windowed bound is uniform in the window.
- `sup_dev_of_oscillation` - the step from oscillation to sup deviation, which
  is what integrating to one supplies.
- `occupation_constant`, `occupation_constant_value` - the Brownian constant of
  the occupation corollary in closed form, `2√2/√π`, and the check that it lies
  strictly between 1.59 and 1.60, which is the `1.60` quoted in the text.

The measure-theoretic identification of the pushforward density with the lattice
sum is standard change of variables and is not the content of the lemma; it is
the one hypothesis the file takes rather than proves.

### Act II: the floors

`LocalTime/Corridor.lean` - the corridor argument, §The fixed-width floor and
§The width-uniform floor. This is the keystone file: it machine-checks
everything in the verification scheme except the Itô step and the telescoping.

- `tangency_upper`, `tangency_lower` - the extremal verification derivative
  `4δ/h²` lies inside the narrow-limit corridor `-1/(h+δ) ≤ U' ≤ 1/(h-δ)`, the
  certificates being `(h - 2δ)² ≥ 0` and `(h + 2δ)² ≥ 0`.
- `tangency_upper_eq`, `tangency_lower_eq` - tangency is attained at `±h/2`.
- `corridor_gap_ge`, `corridor_gap_eq_at_tangency` - the corridor gap over any
  pair of displacements is at least `4/h²` times their separation, with
  equality at the tangency pair. The infimum defining `c_min` is therefore
  exactly `4/h²` and **the constant is exactly two**. This is the tangency
  constant.
- `corridor_gap_ge_inv`, `corridor_ratio_era_bound` - the analytic corollary
  `c_min ≥ 2(1 - 3h/s₋)`, by the split at separation `h/4`.
- `share_corridor_upper`, `share_corridor_lower` - the same corridor in the
  share coordinate, `-1/ω ≤ 16(ω - 1/2) ≤ 1/(1-ω)`, with certificates
  `(4ω - 1)² ≥ 0` and `(4ω - 3)² ≥ 0` and tangency at `ω = 1/4` and `3/4`.
- `share_impulse_inequality` - the impulse inequality of the width-uniform
  floor: `U(ω) = 8(ω - 1/2)²` loses no more across an impulse than the impulse's
  kerf, which by Theorem 2 is the larger of the two log share increments. **This
  statement is exact at every width and carries no narrow-limit correction**,
  which is why the same two appears in both coordinates: the tangency constant
  is not an artefact of one coordinate.
- `fixed_impulse_inequality` - the displacement-coordinate counterpart in the
  narrow limit.

`LocalTime/DiscreteFloor.lean` - **the verification scheme, in discrete
monitoring.** This closes the one structural gap the corridor file leaves. The
paper's scheme runs Itô–Tanaka between impulses and telescopes; mathlib has no
stochastic integral, but for a *quadratic* verification function the
second-order expansion is an exact identity with no remainder, so the whole
argument goes through pathwise with nothing but finite sums.

- `Uquad_step` - the exact step expansion. This is what replaces the Itô step:
  the drift pairing and the quadratic-variation term appear with no error, on
  every path.
- `discrete_verification`, `discrete_floor`, `discrete_floor_rate` - the
  pathwise verification inequality, the floor under a non-negative drift pairing
  (which is what the martingale hypothesis supplies), and the rate form under a
  per-step lower bound on the quadratic increment.
- `fixed_width_discrete_floor`, `tangency_constant_rate` - the isolated class:
  every discretely monitored policy pays at least `2/h²` times its realised
  quadratic variation, less the boundary term. **This is a floor theorem, not
  merely the corridor inequality.**
- `width_uniform_discrete_floor` - the share-coordinate version, exact at every
  width.
- `swap_discrete_floor` - the swap class, at the sandwich's constant.

Deployed operators monitor on a keeper cadence, so the discrete statement is
closer to the object than the continuous one; the paper's own monitoring section
treats continuous monitoring as the idealisation.

`LocalTime/Achievability.lean` - **Proposition (Achievability)** and
**Proposition (Sharpness of the Floor)**.

- `cCentred_ge_two` - the centred renewal family pays at least the tangency
  constant at every trigger. The certificate is `(1 - 2x)² ≥ 0`, the same
  square that makes the verification derivative tangent to both envelopes.
- `cCentred_half` - the production convention `x = 1/2` pays `4 log 2`.
- `hasDerivAt_cCentred` - the stationarity condition of the family optimum,
  `x/(1-x) + 2 log(1-x) = 0`. The numerical root `x* = 0.7153` with
  `c* = 2.4554` is the harness's, not Lean's.
- `cRefl_ge_two`, `cRefl_half` - the reflection family never goes below the
  floor and meets it exactly at the tangency displacement.
- `reflection_ratio_tendsto` - the reflection family's exact per-cycle
  cost-to-clock ratio tends to `c_refl(x)` as the correction vanishes.

`LocalTime/SwapFloor.lean` - **Theorem (Swap-Mediated Floor)** and
**Proposition (Return-Point Achievability)**.

- `swapCost_ge` - the constant satisfies `A ≥ η + γ + 2√(γη)`, with certificate
  `(√γ(1-d) - √η d)² + γd ≥ 0`. This is the exact form of the Whalley–Wilmott
  scaling the paper quotes.
- `swapCost_fee_only`, `fee_le_swapCost_fee_only` - the fee-only regime, where
  the cost is `η/(1-d)` and the infimum is exactly the fee.
- `dStar_root` - the gas-corrected minimiser solves `ηd² + 2γd - γ = 0`.
- `mint_leg_ge` - the coverage argument: a mint leg moving the share by `d`
  costs at least `d` in log value, so it never undercuts the swap leg's fee
  scale and the sandwich covers every impulse of the class.
- `swap_impulse_inequality` - the quadratic verification function loses at most
  `A d(1-d)` across an impulse, the extreme pair having one point at an edge.
- `rSwap_antitone_in_x` - the rate is strictly decreasing in the trigger, so
  the trigger optimum is the band edge and the optimisation lives in the
  correction size. Late firing is cost-optimal in direction.

`LocalTime/Retention.lean` - **Proposition (Retention Collapse)**.
`system_value_conserved` and `token_conserved` are the ledger-inclusive mint
identity in the value and token coordinates;
`system_value_loss_eq_swap_cost` is the swap-corrected half. No verification
function is needed, which is why the file contains no analysis: retention
deletes the floor rather than lowering it.

`LocalTime/Legs.lean` - **Proposition (Leg Comparison)**. The two ratio
identities `4/ρ` and `η/(2ρ)`, which is the reversal across architectures.

`LocalTime/Surcharge.lean` - **Proposition (Jump Surcharge)**.

- `surcharge_telescopes` - the return point cancels: the difference between the
  jump-shifted and the diffusive per-event cost telescopes through the upward
  potential, so no return convention avoids the surcharge.
- `surcharge_nonneg`, `surcharge_pos` - positivity, as the strict monotonicity
  of `C↑`.
- `surcharge_narrow_eq`, `log_ratio_ge`, `surcharge_narrow_ge` - the
  narrow-limit form and its lower bound: every jump crossing pays at least its
  straddle depth over the half-width, in log value.

### Act III: the instrument

`LocalTime/Monitoring.lean` - the monitoring layer's two exact integrals.

- `delay_density_integral` - **Lemma (Flat-Entry Delay Law)**, normalisation:
  the delay density `1/(2√Δt √(Δt - a))` integrates to one over the check
  interval.
- `integral_Ioi_mul_exp_neg_half_sq`, `integral_Ioi_mul_nden` - the one-sided
  Gaussian first moment `∫₀^∞ x φ(x) dx = 1/√(2π)`, which is the normalising
  constant of the monitoring overshoot density.

`LocalTime/Owen.lean` - **Proposition (Exact Reproduction)**, analytic core.

The paper reduces the delay-resolved overshoot integral to Owen's `T` function
and quotes the literature value `T(o,∞) = ½ Q(o)`. Mathlib has no Owen `T`, and
the substitution route needs differentiation under the integral sign against an
integrand singular at both endpoints. The identity has a second proof that needs
neither: the elementary antiderivative `∫_o^∞ t exp(-t²c/2) dt = exp(-o²c/2)/c`
turns the Owen integrand into an inner integral, and interchanging the order of
integration leaves a Gaussian integral in `s` that mathlib already has.

- `integral_Ioi_mul_exp_neg_mul_sq_div` - the inner antiderivative.
- `integral_Ioi_exp_neg_sq_mul` - the scaled Gaussian half-line integral,
  `∫₀^∞ exp(-t²s²/2) ds = √(2π)/(2t)`.
- `owenKer_integrable_prod` - product integrability over the quadrant, which is
  what the interchange consumes.
- `owen_reproduction` - the core identity: the `s`-integral equals
  `(√(2π)/2) ∫_o^∞ exp(-t²/2) dt`, the scaled Gaussian tail.
- `owenT_atTop` - **`T(o,∞) = ½ Q(o)`**, the literature fact the paper cites,
  proved rather than quoted, with no special function anywhere in the
  development.

What is *not* closed is the change of variables `a = 1/(1+s²)` that takes the
paper's delay-marginal integral over `(0,1)` to the `s`-integral over `(0,∞)`.
Both endpoints are improper there, and mathlib's change-of-variables theorems
are for compact intervals, so it needs a separate limit argument. The step this
file closes is the one the paper delegates to the literature.

`LocalTime/Instrument.lean` - the deterministic half of **Theorem (Small-Delay
Identification)** and of the estimator's debiasing.

- `exceedance_bracket` - the bracket assembly. Given the two-branch mixture, a
  diffusive-branch exceedance bounded by the leakage term and a jump-branch
  exceedance failing only on the resolution-floor tail, the measured exceedance
  functional brackets the small-delay jump share by the sum of the two terms.
  This is rows 1 and 2 of the bias budget, assembled.
- `jump_share_inversion`, `jump_share_inversion_mono` - the estimator's
  debiasing, `π̂_J = (Ê - 2Q(κ))/(1 - 2Q(κ))`, as an algebraic inversion, and
  its monotonicity, so a conservative measurement gives a conservative jump
  share.

## Scope: what is not formalised

Recorded explicitly, since several results of the paper are stochastic and the
formalisation does not change their status. Each item is tagged with where it
stands, so that the list can be read at a glance across revisions:

- **Open** - nothing of the result is machine-checked.
- **Core proved** - the mathematical content is machine-checked and what
  remains is a standard wrapper carried as an explicit hypothesis of the file,
  not a gap in the argument.
- **Superseded in discrete time** - the continuous statement is out of reach,
  but a counterpart that is arguably closer to the deployed object is proved
  in full.

The second pass (2026-08-11) moved three items: offset uniformity to *core
proved*, the verification scheme to *superseded in discrete time*, and part of
the instrument layer to *core proved*. A third pass the same day closed the
Owen's `T` value the exact-reproduction proof quotes, leaving only its change of
variables. The other five items are unchanged.

- **Theorem 1 (Dissipation Identity). Open.** The pathwise identity is
  Itô–Tanaka applied on each inter-firing interval and telescoped. Mathlib has
  neither the local-time field of a continuous semimartingale nor the
  Itô–Tanaka formula for a difference of convex functions, so the identity is
  out of reach. Everything the identity's impulse term consumes downstream is
  formalised.
- **Proposition (Intensity Representation). Open.** The renewal structure, the
  two-barrier direction split through the scale function, and the almost-sure
  firing-rate limit need first-passage theory absent from mathlib. The
  deterministic amplitude that item (iv) integrates is formalised in
  `Amplitude.lean`.
- **Lemma (Offset Uniformity). Core proved.** The analytic core is now proved
  in `Offset.lean`, together with the step from oscillation to sup deviation
  and the Brownian constant. What remains unproved is the identification of
  the pushforward density with the lattice sum, standard change of variables,
  and the ℤ-summability that turns the uniform windowed bound into a bound on
  the full sum. Both are hypotheses of the file rather than gaps in the
  argument.
- **The verification scheme. Superseded in discrete time.** The step from the
  corridor and the impulse inequality to `r ≥ ½ μ₀ σ₀² - U₁ b₀` is Itô between
  impulses plus telescoping plus a true-martingale argument, and is out of
  reach. The discrete-monitoring counterpart is proved in full in
  `DiscreteFloor.lean`, pathwise, and is arguably the more faithful statement,
  since deployed operators monitor on a cadence. What the continuous version
  adds is the passage to the continuous clock, not the mechanism.
- **Renewal reward. Open.** The mean exit time `ε(2x - ε)h²/σ_s²` of the
  reflection cycle and the mean cycle `x²h²/σ_s²` of the centred family are
  Brownian exit computations. The deterministic ε → 0 limit of the reflection
  family's ratio is formalised; the exit law is not.
- **The instrument's branch estimates. Core proved in part; the Owen change of
  variables open.**
  The folded-normal conditional kernel, the straddle law, delay invariance,
  and jump enrichment are statements about Gaussian first passage and Lévy
  jump measures, and are not formalised; only the deterministic assembly of
  their conclusions is. Two of the layer's exact integrals *are* formalised,
  in `Monitoring.lean`, and the exact-reproduction identity's analytic core is
  proved in `Owen.lean`, including the value `T(o,∞) = ½ Q(o)` that the paper
  quotes from the literature on Owen's `T`. What remains there is the change of
  variables `a = 1/(1+s²)`, improper at both endpoints, which mathlib's
  compact-interval change-of-variables theorems do not cover.
- **Fixed-point arithmetic. Out of scope by design** - it remains the Foundry
  suites' job. Everything here is over `ℝ`, so tick rounding, wei-level
  truncation, and the placement and sizing floors of the impulse map are
  outside the model.
- **The model-to-process identification. Out of scope by design.** That the
  declared venue presentation describes the deployed manager is an empirical
  matter settled by the fork suites, the production-history anchor, and the
  population read, not by Lean.

Two conventions worth stating. Hypotheses that delimit the domain of a
statement are kept on the Lean statement even where the proof does not consume
them, so that the statement matches the paper's; the unused-variable linter is
disabled per file for that reason. And the era-uniformised envelopes of the
analytic corollary are taken as an abstract pair of functions satisfying the
two-sided bound, rather than as the specific selections of the appendix, so
that the corollary is proved for every admissible uniformisation.

## Building

Requires elan, the Lean toolchain manager. The pinned toolchain is in
`lean-toolchain`; mathlib is pinned by `lake-manifest.json`, at the same
revision as the Geometric Siphon and Master Equation formalisations.

```
lake exe cache get   # fetch prebuilt mathlib (several GB, one-off)
lake build
```

Axiom audit, confirming that every theorem depends only on `propext`,
`Classical.choice` and `Quot.sound`, and that none contains a `sorry`:

```
lake env lean AxiomCheck.lean
```

136 checks, all clean.
