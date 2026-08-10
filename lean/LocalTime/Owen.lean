/-
Proposition (Exact Reproduction), §The forward map and Appendix "Proofs for the
instrument".

The paper's proof reduces the delay-resolved overshoot integral to Owen's `T`
function by the substitution `a = 1/(1+s²)` and then quotes `T(o,∞) = ½ Q(o)`.
Mathlib carries no Owen `T`, and the substitution route needs differentiation
under the integral sign against an integrand singular at both endpoints.

The identity has a second proof that needs neither. Writing `c = 1 + s²`, the
elementary antiderivative

  ∫_o^∞ t exp(-t²c/2) dt = exp(-o²c/2)/c

turns the Owen integrand into an inner integral, and interchanging the order of
integration leaves a Gaussian integral in `s` that mathlib already has. What
survives is `(√(2π)/2) ∫_o^∞ exp(-t²/2) dt`, which is the Gaussian tail. So the
identity is Tonelli plus two closed forms, with no special function anywhere.

This file proves that. The two closed forms come first, then the interchange.
-/
import Mathlib

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

open MeasureTheory Filter Topology Set Real

/-! ## The two closed forms -/

/-- The integrand of the inner antiderivative is integrable on every
half-line. -/
theorem integrableOn_mul_exp_neg_mul_sq_div (c o : ℝ) (hc : 0 < c) :
    IntegrableOn (fun t : ℝ => t * Real.exp (-(t ^ 2 * c) / 2)) (Ioi o) := by
  have hb := integrable_mul_exp_neg_mul_sq (b := c / 2) (by linarith)
  have hcongr : (fun x : ℝ => x * Real.exp (-(c / 2) * x ^ 2))
      = fun x : ℝ => x * Real.exp (-(x ^ 2 * c) / 2) := by
    funext x; ring_nf
  exact ((hcongr ▸ hb)).integrableOn

/-- **The inner antiderivative.** For every positive `c`, the first moment of a
Gaussian kernel over a half-line is elementary. This is what turns the Owen
integrand into an inner integral. -/
theorem integral_Ioi_mul_exp_neg_mul_sq_div (c o : ℝ) (hc : 0 < c) :
    ∫ t in Ioi o, t * Real.exp (-(t ^ 2 * c) / 2) = Real.exp (-(o ^ 2 * c) / 2) / c := by
  have hcont : ContinuousWithinAt
      (fun y : ℝ => -Real.exp (-(y ^ 2 * c) / 2) / c) (Ici o) o := by
    have : Continuous (fun y : ℝ => -Real.exp (-(y ^ 2 * c) / 2) / c) := by fun_prop
    exact this.continuousWithinAt
  have hderiv : ∀ x ∈ Ioi o,
      HasDerivAt (fun y : ℝ => -Real.exp (-(y ^ 2 * c) / 2) / c)
        (x * Real.exp (-(x ^ 2 * c) / 2)) x := by
    intro x hx
    have hp : HasDerivAt (fun y : ℝ => y ^ 2) (2 * x) x := by
      simpa using hasDerivAt_pow 2 x
    have h1 : HasDerivAt (fun y : ℝ => -(y ^ 2 * c) / 2) (-(x * c)) x :=
      (((hp.mul_const c).neg).div_const 2).congr_deriv (by ring)
    have h2 := (h1.exp).neg.div_const c
    refine h2.congr_deriv ?_
    field_simp
  have hint := integrableOn_mul_exp_neg_mul_sq_div c o hc
  have htend : Tendsto (fun y : ℝ => -Real.exp (-(y ^ 2 * c) / 2) / c) atTop
      (nhds 0) := by
    have hsq : Tendsto (fun y : ℝ => -(y ^ 2 * c) / 2) atTop atBot := by
      have h1 : Tendsto (fun y : ℝ => y ^ 2) atTop atTop :=
        tendsto_pow_atTop (by norm_num)
      have h2 : Tendsto (fun y : ℝ => y ^ 2 * c) atTop atTop :=
        h1.atTop_mul_const hc
      exact (tendsto_neg_atTop_atBot.comp h2).atBot_div_const (by norm_num)
    have h3 := Real.tendsto_exp_atBot.comp hsq
    simpa using (h3.neg).div_const c
  have hres := integral_Ioi_of_hasDerivAt_of_tendsto hcont hderiv hint htend
  rw [hres]
  ring

/-- **The Gaussian half-line integral, scaled.** For every positive `t`,
`∫₀^∞ exp(-t²s²/2) ds = √(2π)/(2t)`. -/
theorem integral_Ioi_exp_neg_sq_mul (t : ℝ) (ht : 0 < t) :
    ∫ s in Ioi (0:ℝ), Real.exp (-(t ^ 2 * s ^ 2) / 2)
      = Real.sqrt (2 * Real.pi) / (2 * t) := by
  have hcongr : (fun s : ℝ => Real.exp (-(t ^ 2 / 2) * s ^ 2))
      = fun s : ℝ => Real.exp (-(t ^ 2 * s ^ 2) / 2) := by
    funext s; ring_nf
  have hg := integral_gaussian_Ioi (t ^ 2 / 2)
  rw [hcongr] at hg
  rw [hg]
  have hpos : (0:ℝ) < t ^ 2 / 2 := by positivity
  have harg : Real.pi / (t ^ 2 / 2) = 2 * Real.pi / t ^ 2 := by
    field_simp
  rw [harg, Real.sqrt_div' _ (by positivity), Real.sqrt_sq ht.le]
  ring

/-! ## The interchange

Writing `K(s,t) = t exp(-t²(1+s²)/2)`, the closed form above says that the Owen
integrand at offset `s` is `∫_o^∞ K(s,t) dt`. Interchanging leaves a Gaussian
integral in `s`, which the second closed form evaluates. -/

/-- The kernel of the interchange. -/
noncomputable def owenKer (s t : ℝ) : ℝ :=
  t * Real.exp (-(t ^ 2 * (1 + s ^ 2)) / 2)

lemma owenKer_integrableOn (s o : ℝ) : IntegrableOn (owenKer s) (Ioi o) := by
  have hpos : (0:ℝ) < 1 + s ^ 2 := by positivity
  exact integrableOn_mul_exp_neg_mul_sq_div (1 + s ^ 2) o hpos

/-- The Owen integrand is the inner integral of the kernel. -/
lemma owen_integrand_eq (o s : ℝ) :
    Real.exp (-(o ^ 2 * (1 + s ^ 2)) / 2) / (1 + s ^ 2)
      = ∫ t in Ioi o, owenKer s t := by
  have hpos : (0:ℝ) < 1 + s ^ 2 := by positivity
  unfold owenKer
  rw [integral_Ioi_mul_exp_neg_mul_sq_div (1 + s ^ 2) o hpos]

/-- The kernel is jointly continuous. -/
lemma continuous_uncurry_owenKer : Continuous (Function.uncurry owenKer) := by
  unfold Function.uncurry owenKer
  fun_prop

/-- The kernel is product-integrable over the quadrant, which is what the
interchange consumes. -/
lemma owenKer_integrable_prod (o : ℝ) (ho : 0 ≤ o) :
    Integrable (Function.uncurry owenKer)
      ((volume.restrict (Ioi (0:ℝ))).prod (volume.restrict (Ioi o))) := by
  have hmeas : AEStronglyMeasurable (Function.uncurry owenKer)
      ((volume.restrict (Ioi (0:ℝ))).prod (volume.restrict (Ioi o))) :=
    continuous_uncurry_owenKer.aestronglyMeasurable
  rw [integrable_prod_iff hmeas]
  refine ⟨Filter.Eventually.of_forall (fun s => owenKer_integrableOn s o), ?_⟩
  have hnorm : ∀ s : ℝ, (∫ t in Ioi o, ‖owenKer s t‖)
      = Real.exp (-(o ^ 2 * (1 + s ^ 2)) / 2) / (1 + s ^ 2) := by
    intro s
    rw [owen_integrand_eq o s]
    refine setIntegral_congr_ae measurableSet_Ioi ?_
    refine Filter.Eventually.of_forall (fun t ht => ?_)
    have htpos : (0:ℝ) ≤ t := le_of_lt (lt_of_le_of_lt ho ht)
    rw [Real.norm_eq_abs, abs_of_nonneg]
    unfold owenKer
    exact mul_nonneg htpos (Real.exp_nonneg _)
  have hEq : (fun x : ℝ => ∫ y in Ioi o, ‖Function.uncurry owenKer (x, y)‖)
      = fun s : ℝ => Real.exp (-(o ^ 2 * (1 + s ^ 2)) / 2) / (1 + s ^ 2) := by
    funext s; exact hnorm s
  rw [hEq]
  have hdom : Integrable (fun s : ℝ => (1 + s ^ 2)⁻¹)
      (volume.restrict (Ioi (0:ℝ))) := integrable_inv_one_add_sq.integrableOn
  have hcont2 : Continuous
      (fun s : ℝ => Real.exp (-(o ^ 2 * (1 + s ^ 2)) / 2) / (1 + s ^ 2)) := by
    refine Continuous.div (by fun_prop) (by fun_prop) (fun s => ?_)
    positivity
  refine Integrable.mono hdom hcont2.aestronglyMeasurable ?_
  refine Filter.Eventually.of_forall (fun s => ?_)
  have hpos : (0:ℝ) < 1 + s ^ 2 := by positivity
  have hexp : Real.exp (-(o ^ 2 * (1 + s ^ 2)) / 2) ≤ 1 := by
    rw [Real.exp_le_one_iff]
    have : (0:ℝ) ≤ o ^ 2 * (1 + s ^ 2) := by positivity
    linarith
  rw [Real.norm_eq_abs, Real.norm_eq_abs,
    abs_of_nonneg (by positivity : (0:ℝ) ≤ Real.exp (-(o ^ 2 * (1 + s ^ 2)) / 2) / (1 + s ^ 2)),
    abs_of_nonneg (by positivity : (0:ℝ) ≤ (1 + s ^ 2)⁻¹), inv_eq_one_div]
  gcongr

/-- **Proposition (Exact Reproduction), analytic core.** The delay-resolved
overshoot integral equals the Gaussian tail, scaled. This is the identity the
paper proves through Owen's `T` function; the proof here is the interchange
above, with no special function involved. -/
theorem owen_reproduction (o : ℝ) (ho : 0 ≤ o) :
    (∫ s in Ioi (0:ℝ), Real.exp (-(o ^ 2 * (1 + s ^ 2)) / 2) / (1 + s ^ 2))
      = Real.sqrt (2 * Real.pi) / 2 * ∫ t in Ioi o, Real.exp (-(t ^ 2) / 2) := by
  have hL : (∫ s in Ioi (0:ℝ), Real.exp (-(o ^ 2 * (1 + s ^ 2)) / 2) / (1 + s ^ 2))
      = ∫ s in Ioi (0:ℝ), ∫ t in Ioi o, owenKer s t :=
    integral_congr_ae (Filter.Eventually.of_forall (fun s => owen_integrand_eq o s))
  rw [hL, MeasureTheory.integral_integral_swap (owenKer_integrable_prod o ho)]
  have hinner : ∀ t ∈ Ioi o, (∫ s in Ioi (0:ℝ), owenKer s t)
      = Real.sqrt (2 * Real.pi) / 2 * Real.exp (-(t ^ 2) / 2) := by
    intro t ht
    have htpos : (0:ℝ) < t := lt_of_le_of_lt ho ht
    have hsplit : ∀ s : ℝ, owenKer s t
        = t * Real.exp (-(t ^ 2) / 2) * Real.exp (-(t ^ 2 * s ^ 2) / 2) := by
      intro s
      unfold owenKer
      have hexp : -(t ^ 2 * (1 + s ^ 2)) / 2
          = -(t ^ 2) / 2 + -(t ^ 2 * s ^ 2) / 2 := by ring
      rw [hexp, Real.exp_add]
      ring
    calc (∫ s in Ioi (0:ℝ), owenKer s t)
        = ∫ s in Ioi (0:ℝ),
            t * Real.exp (-(t ^ 2) / 2) * Real.exp (-(t ^ 2 * s ^ 2) / 2) :=
          integral_congr_ae (Filter.Eventually.of_forall (fun s => hsplit s))
      _ = t * Real.exp (-(t ^ 2) / 2)
            * ∫ s in Ioi (0:ℝ), Real.exp (-(t ^ 2 * s ^ 2) / 2) := by
          rw [integral_const_mul]
      _ = t * Real.exp (-(t ^ 2) / 2) * (Real.sqrt (2 * Real.pi) / (2 * t)) := by
          rw [integral_Ioi_exp_neg_sq_mul t htpos]
      _ = Real.sqrt (2 * Real.pi) / 2 * Real.exp (-(t ^ 2) / 2) := by
          field_simp
  rw [setIntegral_congr_ae measurableSet_Ioi (Filter.Eventually.of_forall hinner),
    integral_const_mul]

/-! ## Owen's `T` at infinity

The paper's appendix quotes the limit value `T(o, ∞) = ½ Q(o)` of Owen's `T`
function. With

  T(h, a) = (1/2π) ∫₀^a exp(-h²(1+x²)/2)/(1+x²) dx,

that value is exactly the identity above, renormalised. The statement below is
therefore the fact the paper cites, proved rather than quoted, and with no
special function in the development. -/

/-- The standard normal survival function. -/
noncomputable def surv (o : ℝ) : ℝ :=
  ∫ t in Ioi o, Real.exp (-(t ^ 2) / 2) / Real.sqrt (2 * Real.pi)

lemma surv_eq (o : ℝ) :
    surv o = (∫ t in Ioi o, Real.exp (-(t ^ 2) / 2)) / Real.sqrt (2 * Real.pi) := by
  unfold surv
  exact integral_div _ _

/-- **Owen's `T` at infinity: `T(o, ∞) = ½ Q(o)`.** This is the limit value the
paper's exact-reproduction proof quotes from the literature on Owen's `T`
function. Mathlib carries no Owen `T`; the identity is proved here directly. -/
theorem owenT_atTop (o : ℝ) (ho : 0 ≤ o) :
    (1 / (2 * Real.pi))
        * ∫ s in Ioi (0:ℝ), Real.exp (-(o ^ 2 * (1 + s ^ 2)) / 2) / (1 + s ^ 2)
      = surv o / 2 := by
  have hpi : (0:ℝ) < Real.pi := Real.pi_pos
  have hs : (0:ℝ) < Real.sqrt (2 * Real.pi) := Real.sqrt_pos.mpr (by positivity)
  have hsq : Real.sqrt (2 * Real.pi) * Real.sqrt (2 * Real.pi) = 2 * Real.pi :=
    Real.mul_self_sqrt (by positivity)
  have h2 : Real.sqrt (2 * Real.pi) ^ 2 = 2 * Real.pi :=
    Real.sq_sqrt (by positivity)
  rw [owen_reproduction o ho, surv_eq]
  field_simp
  rw [h2]

end LocalTime
