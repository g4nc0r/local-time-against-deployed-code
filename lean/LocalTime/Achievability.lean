/-
Proposition (Achievability) and Proposition (Sharpness of the Floor),
§The fixed-width floor and Appendix "Proofs for the floors".

Two policy families are priced against the floor in the narrow limit. The
centred renewal family fires at `|δ| = xh` and re-places at the midpoint, with
coefficient `c(x) = -log(1-x)/x²`; the two-sided reflection family fires at
`|δ| = xh` and re-places at `(x - ε)h` on the firing side, with coefficient
tending to `c_refl(x) = 1/(2x(1-x))`.

The centred family never reaches the floor: `c(x) ≥ 2` everywhere, and the
certifying inequality is again a square, `(1 - 2x)² ≥ 0`, the same square that
makes the extremal verification derivative tangent to both envelopes. The
reflection family does reach it, `c_refl(1/2) = 2`, and no member goes below.

What is not formalised here is the renewal-reward step itself, which needs the
Brownian exit law; the ε → 0 limit of the reflection family's exact per-cycle
ratio is formalised, since that part is deterministic.
-/
import Mathlib

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

variable {x ε : ℝ}

/-! ## The centred renewal family -/

/-- The narrow-limit coefficient of the centred renewal family. -/
noncomputable def cCentred (x : ℝ) : ℝ := -Real.log (1 - x) / x ^ 2

/-- The gap function `-log(1-x) - 2x²`, whose derivative is `(1-2x)²/(1-x)`. -/
noncomputable def centredGap (x : ℝ) : ℝ := -Real.log (1 - x) - 2 * x ^ 2

lemma hasDerivAt_centredGap (hx : x < 1) :
    HasDerivAt centredGap (1 / (1 - x) - 4 * x) x := by
  have h3 : HasDerivAt (fun y : ℝ => 1 - y) (-1) x := by
    simpa using (hasDerivAt_id x).const_sub 1
  have h4 := h3.log (by intro hc; linarith [sub_eq_zero.mp hc])
  have h5 : HasDerivAt (fun y : ℝ => 2 * y ^ 2) (4 * x) x := by
    have hp : HasDerivAt (fun y : ℝ => y ^ 2) (2 * x) x := by
      simpa using hasDerivAt_pow 2 x
    exact (hp.const_mul (2:ℝ)).congr_deriv (by ring)
  refine (h4.neg.sub h5).congr_deriv ?_
  field_simp

/-- The derivative of the gap is non-negative, the certificate being
`(1 - 2x)² ≥ 0`: the same square as the corridor tangency. -/
lemma centredGap_deriv_nonneg (hx0 : 0 ≤ x) (hx : x < 1) :
    0 ≤ 1 / (1 - x) - 4 * x := by
  have hA : (0:ℝ) < 1 - x := by linarith
  rw [sub_nonneg, le_div_iff₀ hA]
  nlinarith [sq_nonneg (1 - 2 * x)]

/-- The gap is nondecreasing on `[0,1)`. -/
theorem monotoneOn_centredGap : MonotoneOn centredGap (Set.Ico 0 1) := by
  have hcont : ContinuousOn centredGap (Set.Ico 0 1) := by
    intro y hy
    simp only [Set.mem_Ico] at hy
    exact ((hasDerivAt_centredGap hy.2).continuousAt).continuousWithinAt
  refine monotoneOn_of_deriv_nonneg (convex_Ico 0 1) hcont ?_ ?_
  · intro y hy
    rw [interior_Ico, Set.mem_Ioo] at hy
    exact (hasDerivAt_centredGap hy.2).differentiableAt.differentiableWithinAt
  · intro y hy
    rw [interior_Ico, Set.mem_Ioo] at hy
    rw [(hasDerivAt_centredGap hy.2).deriv]
    exact centredGap_deriv_nonneg hy.1.le hy.2

/-- **Proposition (Achievability), the family sits above the floor.** The
centred renewal family pays at least the tangency constant at every trigger. -/
theorem cCentred_ge_two (hx : 0 < x) (hx' : x < 1) : 2 ≤ cCentred x := by
  have h0 : centredGap 0 ≤ centredGap x :=
    monotoneOn_centredGap ⟨le_refl 0, by norm_num⟩ ⟨hx.le, hx'⟩ hx.le
  have hz : centredGap 0 = 0 := by
    unfold centredGap; norm_num
  rw [hz] at h0
  unfold centredGap at h0
  unfold cCentred
  rw [le_div_iff₀ (by positivity)]
  linarith

/-- The centred family at the production convention `x = 1/2` pays `4 log 2`. -/
theorem cCentred_half : cCentred (1 / 2) = 4 * Real.log 2 := by
  unfold cCentred
  rw [show (1:ℝ) - 1 / 2 = 2⁻¹ by norm_num, Real.log_inv]
  norm_num
  ring

/-- The stationarity condition of the centred family: the derivative of `c`
vanishes exactly where `x/(1-x) + 2 log(1-x) = 0`. -/
theorem hasDerivAt_cCentred (hx : 0 < x) (hx' : x < 1) :
    HasDerivAt cCentred
      ((x / (1 - x) + 2 * Real.log (1 - x)) / x ^ 3) x := by
  have hA : (0:ℝ) < 1 - x := by linarith
  have h3 : HasDerivAt (fun y : ℝ => 1 - y) (-1) x := by
    simpa using (hasDerivAt_id x).const_sub 1
  have h4 := h3.log hA.ne'
  have hp : HasDerivAt (fun y : ℝ => y ^ 2) (2 * x) x := by
    simpa using hasDerivAt_pow 2 x
  have := h4.neg.div hp (by positivity)
  refine this.congr_deriv ?_
  simp only [Pi.neg_apply]
  field_simp
  ring

/-! ## The two-sided reflection family -/

/-- The narrow-limit coefficient of the reflection family. -/
noncomputable def cRefl (x : ℝ) : ℝ := 1 / (2 * x * (1 - x))

/-- **Proposition (Sharpness), the family never goes below the floor.** -/
theorem cRefl_ge_two (hx : 0 < x) (hx' : x < 1) : 2 ≤ cRefl x := by
  have hden : (0:ℝ) < 2 * x * (1 - x) := by nlinarith
  unfold cRefl
  rw [le_div_iff₀ hden]
  nlinarith [sq_nonneg (1 - 2 * x)]

/-- **Proposition (Sharpness), the floor is met at the tangency
displacement.** -/
theorem cRefl_half : cRefl (1 / 2) = 2 := by
  unfold cRefl; norm_num

/-- **Proposition (Sharpness), the per-cycle limit.** The reflection family's
exact per-cycle cost-to-clock ratio tends to the reflection coefficient as the
correction vanishes. The numerator is the near-side potential increment
`log(1 + ε/(1-x))`, the denominator the Brownian mean exit time factor
`ε(2x - ε)`. -/
theorem reflection_ratio_tendsto (hx : 0 < x) (hx' : x < 1) :
    Filter.Tendsto
      (fun e : ℝ => Real.log (1 + e / (1 - x)) / (e * (2 * x - e)))
      (nhdsWithin 0 (Set.Ioi 0)) (nhds (cRefl x)) := by
  have hA : (0:ℝ) < 1 - x := by linarith
  -- the slope of `e ↦ log(1 + e/(1-x))` at zero
  have hd : HasDerivAt (fun e : ℝ => Real.log (1 + e / (1 - x)))
      (1 / (1 - x)) 0 := by
    have h1 : HasDerivAt (fun e : ℝ => 1 + e / (1 - x)) (1 / (1 - x)) 0 := by
      have := ((hasDerivAt_id (0:ℝ)).div_const (1 - x)).const_add 1
      exact this.congr_deriv (by field_simp)
    have h2 := h1.log (by norm_num)
    exact h2.congr_deriv (by norm_num)
  have hslope := hasDerivAt_iff_tendsto_slope.mp hd
  have hsub : nhdsWithin (0:ℝ) (Set.Ioi 0) ≤ nhdsWithin 0 {(0:ℝ)}ᶜ := by
    apply nhdsWithin_mono
    intro y hy
    simp only [Set.mem_Ioi] at hy
    simp only [Set.mem_compl_iff, Set.mem_singleton_iff]
    exact ne_of_gt hy
  have hlim1 := hslope.mono_left hsub
  have hlim2 : Filter.Tendsto (fun e : ℝ => 1 / (2 * x - e))
      (nhdsWithin 0 (Set.Ioi 0)) (nhds (1 / (2 * x))) := by
    have hc : Filter.Tendsto (fun e : ℝ => 2 * x - e) (nhds 0) (nhds (2 * x)) := by
      have hcont : Continuous (fun e : ℝ => 2 * x - e) := by fun_prop
      simpa using hcont.tendsto (0:ℝ)
    exact (tendsto_const_nhds.div hc (by linarith : (0:ℝ) < 2 * x).ne').mono_left
      nhdsWithin_le_nhds
  have hprod := hlim1.mul hlim2
  have hval : 1 / (1 - x) * (1 / (2 * x)) = cRefl x := by
    unfold cRefl
    field_simp
  rw [← hval]
  refine hprod.congr' ?_
  filter_upwards [self_mem_nhdsWithin] with e he
  simp only [Set.mem_Ioi] at he
  rw [slope_def_field]
  have hlog0 : Real.log (1 + (0:ℝ) / (1 - x)) = 0 := by norm_num
  rw [hlog0]
  field_simp
  ring

end LocalTime
