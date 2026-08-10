/-
The monitoring layer's two normalisations, §Monitoring, §The forward map, and
Appendix "Proofs for the instrument".

Two exact integrals underlie the instrument's diffusive branch. The flat-entry
delay law of the paper is a density on `(0, Δt)`, and the one-sided Gaussian
first moment is the normalising constant of the monitoring overshoot law. Both
are ordinary calculus and are proved here outright; the first-passage and
qualification arguments that produce those densities are not, and are recorded
in the README.

The delay density is `g_act(a) = 1/(2√Δt √(Δt - a))`, increasing towards the
check, and the statement below is that it integrates to one over the check
interval. The overshoot density carries the factor `√(2π)/σ₁`, and its
normalising constant is `∫₀^∞ x φ(x) dx = 1/√(2π)`, which is the second
statement in raw form.
-/
import Mathlib

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

open MeasureTheory Filter Topology Set

/-! ## The flat-entry delay law -/

/-- The flat-entry delay density of the paper, on `(0, Δt)`. -/
noncomputable def gact (Δt a : ℝ) : ℝ :=
  1 / (2 * Real.sqrt Δt * Real.sqrt (Δt - a))

/-- The reciprocal square root, as a real power, so that mathlib's power-rule
integral applies. The two agree everywhere, including at the origin, where both
are zero by the junk-value conventions. -/
lemma one_div_sqrt_eq_rpow (x : ℝ) (hx : 0 ≤ x) :
    1 / Real.sqrt x = x ^ (-(1/2 : ℝ)) := by
  rcases eq_or_lt_of_le hx with h | h
  · rw [← h]
    simp [Real.zero_rpow]
  · rw [Real.rpow_neg hx, Real.rpow_def_of_pos h]
    rw [Real.sqrt_eq_rpow, Real.rpow_def_of_pos h]
    rw [one_div]

/-- **Lemma (Flat-Entry Delay Law), normalisation.** The delay density
integrates to one over the check interval. -/
theorem delay_density_integral {Δt : ℝ} (hΔ : 0 < Δt) :
    ∫ a in (0:ℝ)..Δt, gact Δt a = 1 := by
  have hs : (0:ℝ) < Real.sqrt Δt := Real.sqrt_pos.mpr hΔ
  -- reduce to the power-rule integral after reflecting the interval
  have hstep1 : ∫ a in (0:ℝ)..Δt, gact Δt a
      = (1 / (2 * Real.sqrt Δt)) * ∫ a in (0:ℝ)..Δt, 1 / Real.sqrt (Δt - a) := by
    rw [← intervalIntegral.integral_const_mul]
    apply intervalIntegral.integral_congr
    intro x hx
    unfold gact
    field_simp
  have hstep2 : ∫ a in (0:ℝ)..Δt, 1 / Real.sqrt (Δt - a)
      = ∫ x in (0:ℝ)..Δt, 1 / Real.sqrt x := by
    have := intervalIntegral.integral_comp_sub_left
      (fun x : ℝ => 1 / Real.sqrt x) Δt (a := 0) (b := Δt)
    simpa using this
  have hstep3 : ∫ x in (0:ℝ)..Δt, 1 / Real.sqrt x = 2 * Real.sqrt Δt := by
    have hcongr : ∫ x in (0:ℝ)..Δt, 1 / Real.sqrt x
        = ∫ x in (0:ℝ)..Δt, x ^ (-(1/2 : ℝ)) := by
      apply intervalIntegral.integral_congr
      intro x hx
      rw [uIcc_of_le hΔ.le] at hx
      exact one_div_sqrt_eq_rpow x hx.1
    rw [hcongr, integral_rpow (Or.inl (by norm_num))]
    have hexp : -(1/2 : ℝ) + 1 = 1/2 := by norm_num
    rw [hexp, Real.zero_rpow (by norm_num), ← Real.sqrt_eq_rpow]
    ring
  rw [hstep1, hstep2, hstep3]
  field_simp

/-! ## The one-sided Gaussian first moment

The monitoring overshoot density of the paper is `g_O(o) = (√(2π)/σ₁) Q(o/σ₁)`,
whose normalising constant is `∫₀^∞ x φ(x) dx = 1/√(2π)`. That integral is the
statement below, in raw form and then normalised. -/

/-- The standard normal density. -/
noncomputable def nden (x : ℝ) : ℝ :=
  Real.exp (-(x ^ 2) / 2) / Real.sqrt (2 * Real.pi)

/-- **The one-sided Gaussian first moment, raw form.** -/
theorem integral_Ioi_mul_exp_neg_half_sq :
    ∫ x in Ioi (0:ℝ), x * Real.exp (-(x ^ 2) / 2) = 1 := by
  have hcont : ContinuousWithinAt (fun y : ℝ => -Real.exp (-(y ^ 2) / 2))
      (Ici (0:ℝ)) 0 := by
    have : Continuous (fun y : ℝ => -Real.exp (-(y ^ 2) / 2)) := by fun_prop
    exact this.continuousWithinAt
  have hderiv : ∀ x ∈ Ioi (0:ℝ),
      HasDerivAt (fun y : ℝ => -Real.exp (-(y ^ 2) / 2))
        (x * Real.exp (-(x ^ 2) / 2)) x := by
    intro x hx
    have hp : HasDerivAt (fun y : ℝ => y ^ 2) (2 * x) x := by
      simpa using hasDerivAt_pow 2 x
    have h1 : HasDerivAt (fun y : ℝ => -(y ^ 2) / 2) (-x) x :=
      (hp.neg.div_const 2).congr_deriv (by ring)
    exact (h1.exp).neg.congr_deriv (by ring)
  have hint : IntegrableOn (fun x : ℝ => x * Real.exp (-(x ^ 2) / 2))
      (Ioi (0:ℝ)) := by
    have hb := integrable_mul_exp_neg_mul_sq (b := (1:ℝ)/2) (by norm_num)
    have hcongr : (fun x : ℝ => x * Real.exp (-((1:ℝ)/2) * x ^ 2))
        = fun x : ℝ => x * Real.exp (-(x ^ 2) / 2) := by
      funext x; ring_nf
    exact ((hcongr ▸ hb)).integrableOn
  have htend : Tendsto (fun y : ℝ => -Real.exp (-(y ^ 2) / 2)) atTop (nhds 0) := by
    have hsq : Tendsto (fun y : ℝ => -(y ^ 2) / 2) atTop atBot := by
      have h1 : Tendsto (fun y : ℝ => y ^ 2) atTop atTop :=
        tendsto_pow_atTop (by norm_num)
      have h2 : Tendsto (fun y : ℝ => -(y ^ 2)) atTop atBot :=
        tendsto_neg_atTop_atBot.comp h1
      exact h2.atBot_div_const (by norm_num)
    have h3 := Real.tendsto_exp_atBot.comp hsq
    simpa using h3.neg
  have := integral_Ioi_of_hasDerivAt_of_tendsto hcont hderiv hint htend
  simpa using this

/-- **The one-sided Gaussian first moment, normalised.** This is the
normalising constant of the monitoring overshoot density. -/
theorem integral_Ioi_mul_nden :
    ∫ x in Ioi (0:ℝ), x * nden x = 1 / Real.sqrt (2 * Real.pi) := by
  have hcongr : ∀ x : ℝ, x * nden x
      = (x * Real.exp (-(x ^ 2) / 2)) / Real.sqrt (2 * Real.pi) := by
    intro x; unfold nden; ring
  calc ∫ x in Ioi (0:ℝ), x * nden x
      = ∫ x in Ioi (0:ℝ),
          (x * Real.exp (-(x ^ 2) / 2)) / Real.sqrt (2 * Real.pi) := by
        exact MeasureTheory.integral_congr_ae (Filter.Eventually.of_forall
          fun x => hcongr x)
    _ = (∫ x in Ioi (0:ℝ), x * Real.exp (-(x ^ 2) / 2))
          / Real.sqrt (2 * Real.pi) := by
        exact MeasureTheory.integral_div _ _
    _ = 1 / Real.sqrt (2 * Real.pi) := by
        rw [integral_Ioi_mul_exp_neg_half_sq]

end LocalTime
