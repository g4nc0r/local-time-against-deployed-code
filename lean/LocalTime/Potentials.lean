/-
Corollary (Placement-Family Potentials), §The cost structure and Appendix
"Proofs for the cost structure".

The floors' working form of the central law. For the equal-width placement
family at price `s` and half-width `h`, the retained fraction on each branch is
a ratio of one function of the displacement, so the kerf of a move from
displacement `δ` to displacement `δ'` is the larger of two potential
differences. Costs therefore telescope along same-direction sequences and there
are no free round trips.

Write `P = 2s + h`. The two branch functions are

  Q↑(z) = (h - z)/(hP - z²),   Q↓(z) = (h + z)(s + h - z)/(hP - z²),

and the potentials are `C↑ = -log Q↑`, `C↓ = -log Q↓`.

The standing hypothesis of the floor sections, `5h ≤ s`, is carried explicitly
on every statement that needs it; the paper states it as `h/s₋ ≤ 1/5`. The
upward potential's monotonicity turns out not to need it, the inequality being
`2sh + (h - z)² > 0`; the downward potential's does.
-/
import LocalTime.ShareIdentity

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

variable {L s h z z' δ δ' : ℝ}

/-! ## The branch functions and the potentials -/

/-- The common denominator `hP - z²` of the two branch functions. Kept as a
definition so that the field-clearing tactics treat it as one symbol. -/
def Dden (s h z : ℝ) : ℝ := h * (2 * s + h) - z ^ 2

lemma continuous_Dden : Continuous (Dden s h) := by unfold Dden; fun_prop

/-- The token0 branch function `Q↑(z) = (h - z)/(hP - z²)`. -/
noncomputable def Qup (s h z : ℝ) : ℝ := (h - z) / Dden s h z

/-- The token1 branch function `Q↓(z) = (h + z)(s + h - z)/(hP - z²)`. -/
noncomputable def Qdn (s h z : ℝ) : ℝ := (h + z) * (s + h - z) / Dden s h z

/-- The token0 placement potential `C↑ = -log Q↑`. -/
noncomputable def Cup (s h z : ℝ) : ℝ := Real.log (Dden s h z) - Real.log (h - z)

/-- The token1 placement potential `C↓ = -log Q↓`. -/
noncomputable def Cdn (s h z : ℝ) : ℝ :=
  Real.log (Dden s h z) - Real.log (h + z) - Real.log (s + h - z)

/-- The narrow-limit token0 potential, `-log(h - z)`. -/
noncomputable def Cup0 (h z : ℝ) : ℝ := -Real.log (h - z)

/-- The narrow-limit token1 potential, `-log(h + z)`. -/
noncomputable def Cdn0 (h z : ℝ) : ℝ := -Real.log (h + z)

/-! ## Positivity bookkeeping -/

lemma denom_pos (hs : 0 < s) (hh : 0 < h) (hz : -h < z) (hz' : z < h) :
    0 < Dden s h z := by
  unfold Dden; nlinarith [sq_nonneg (h - z), sq_nonneg (h + z)]

lemma Qup_pos (hs : 0 < s) (hh : 0 < h) (hz : -h < z) (hz' : z < h) :
    0 < Qup s h z :=
  div_pos (by linarith) (denom_pos hs hh hz hz')

lemma Qdn_pos (hs : 0 < s) (hh : 0 < h) (hstand : 5 * h ≤ s)
    (hz : -h < z) (hz' : z < h) : 0 < Qdn s h z :=
  div_pos (by nlinarith) (denom_pos hs hh hz hz')

lemma Cup_eq_neg_log (hs : 0 < s) (hh : 0 < h) (hz : -h < z) (hz' : z < h) :
    Cup s h z = -Real.log (Qup s h z) := by
  have hd := denom_pos hs hh hz hz'
  unfold Cup Qup
  rw [Real.log_div (by linarith) (by linarith)]
  ring

lemma Cdn_eq_neg_log (hs : 0 < s) (hh : 0 < h) (hstand : 5 * h ≤ s)
    (hz : -h < z) (hz' : z < h) : Cdn s h z = -Real.log (Qdn s h z) := by
  have hd := denom_pos hs hh hz hz'
  unfold Cdn Qdn
  rw [Real.log_div (by nlinarith) (by linarith),
    Real.log_mul (by linarith) (by linarith)]
  ring

/-! ## The retained fractions -/

/-- The per-liquidity value of the equal-width range at displacement `z` from
the price. -/
lemma phi_disp (hs : 0 < s) (hh : 0 < h) (hstand : 5 * h ≤ s)
    (hz : -h < z) (hz' : z < h) :
    phi s (s - z - h) (s - z + h) = Dden s h z / (s + h - z) := by
  have hden0 : s - z + h ≠ 0 := by intro hc; linarith
  have hden1 : s + h - z ≠ 0 := by intro hc; linarith
  unfold phi Dden
  field_simp
  ring

/-- The token0 share of the equal-width position at displacement `z` is
`s Q↑(z)`: the branch function is the share up to the price factor. -/
lemma share0_eq_Qup (hs : 0 < s) (hh : 0 < h) (hstand : 5 * h ≤ s)
    (hz : -h < z) (hz' : z < h) :
    share0 s (s - z - h) (s - z + h) = s * Qup s h z := by
  have hnum : (0:ℝ) < Dden s h z := denom_pos hs hh hz hz'
  have hDv : Dden s h z = h * (2 * s + h) - z ^ 2 := rfl
  unfold share0 Qup
  rw [phi_disp hs hh hstand hz hz']
  unfold amt0
  have hs0 : s ≠ 0 := hs.ne'
  have ha : s - z + h ≠ 0 := by intro hc; linarith
  have hc1 : s + h - z ≠ 0 := by intro hc; linarith
  have hd1 : Dden s h z ≠ 0 := hnum.ne'
  field_simp
  ring

/-- The token1 share of the equal-width position at displacement `z` is exactly
`Q↓(z)`. -/
lemma share1_eq_Qdn (hs : 0 < s) (hh : 0 < h) (hstand : 5 * h ≤ s)
    (hz : -h < z) (hz' : z < h) :
    share1 s (s - z - h) (s - z + h) = Qdn s h z := by
  have hnum : (0:ℝ) < Dden s h z := denom_pos hs hh hz hz'
  unfold share1 Qdn
  rw [phi_disp hs hh hstand hz hz']
  unfold amt1
  have hc1 : s + h - z ≠ 0 := by intro hc; linarith
  have hd1 : Dden s h z ≠ 0 := hnum.ne'
  rw [show s - (s - z - h) = z + h by ring]
  field_simp
  ring

/-- **Corollary (Placement-Family Potentials), token0 branch.** The token0
branch retains `Q↑(δ)/Q↑(δ')`. -/
theorem shareRatio0_eq (hs : 0 < s) (hh : 0 < h) (hstand : 5 * h ≤ s)
    (hd : -h < δ) (hd' : δ < h) (he : -h < δ') (he' : δ' < h) :
    share0 s (s - δ - h) (s - δ + h) / share0 s (s - δ' - h) (s - δ' + h)
      = Qup s h δ / Qup s h δ' := by
  rw [share0_eq_Qup hs hh hstand hd hd', share0_eq_Qup hs hh hstand he he']
  rw [mul_div_mul_left _ _ hs.ne']

/-- **Corollary (Placement-Family Potentials), token1 branch.** The token1
branch retains `Q↓(δ)/Q↓(δ')`. -/
theorem shareRatio1_eq (hs : 0 < s) (hh : 0 < h) (hstand : 5 * h ≤ s)
    (hd : -h < δ) (hd' : δ < h) (he : -h < δ') (he' : δ' < h) :
    share1 s (s - δ - h) (s - δ + h) / share1 s (s - δ' - h) (s - δ' + h)
      = Qdn s h δ / Qdn s h δ' := by
  rw [share1_eq_Qdn hs hh hstand hd hd', share1_eq_Qdn hs hh hstand he he']

/-- **Corollary (Placement-Family Potentials).** The kerf of an equal-width
re-placement is the larger of the two potential differences; the return point
enters only through the potentials' values, so costs telescope. -/
theorem kerf_eq_max_potential (hL : 0 < L) (hs : 0 < s) (hh : 0 < h)
    (hstand : 5 * h ≤ s) (hd : -h < δ) (hd' : δ < h) (he : -h < δ')
    (he' : δ' < h) :
    kerf L s (s - δ - h) (s - δ + h) (s - δ' - h) (s - δ' + h)
      = max (Cup s h δ - Cup s h δ') (Cdn s h δ - Cdn s h δ') := by
  have i1 : (0:ℝ) < s - δ - h := by linarith
  have i2 : s - δ - h < s := by linarith
  have i3 : s < s - δ + h := by linarith
  have j1 : (0:ℝ) < s - δ' - h := by linarith
  have j2 : s - δ' - h < s := by linarith
  have j3 : s < s - δ' + h := by linarith
  have hup : 0 < Qup s h δ := Qup_pos hs hh hd hd'
  have hup' : 0 < Qup s h δ' := Qup_pos hs hh he he'
  have hdn : 0 < Qdn s h δ := Qdn_pos hs hh hstand hd hd'
  have hdn' : 0 < Qdn s h δ' := Qdn_pos hs hh hstand he he'
  have hw : 0 < share0 s (s - δ - h) (s - δ + h) := share0_pos i1 i2 i3
  have hw' : 0 < share0 s (s - δ' - h) (s - δ' + h) := share0_pos j1 j2 j3
  have hv : 0 < share1 s (s - δ - h) (s - δ + h) := share1_pos i1 i2 i3
  have hv' : 0 < share1 s (s - δ' - h) (s - δ' + h) := share1_pos j1 j2 j3
  rw [kerf_eq_max_log hL i1 i2 i3 j1 j2 j3]
  have e0 : share0 s (s - δ' - h) (s - δ' + h) / share0 s (s - δ - h) (s - δ + h)
      = Qup s h δ' / Qup s h δ := by
    rw [← inv_div (share0 s (s - δ - h) (s - δ + h))
        (share0 s (s - δ' - h) (s - δ' + h)),
      shareRatio0_eq hs hh hstand hd hd' he he', inv_div]
  have e1 : share1 s (s - δ' - h) (s - δ' + h) / share1 s (s - δ - h) (s - δ + h)
      = Qdn s h δ' / Qdn s h δ := by
    rw [← inv_div (share1 s (s - δ - h) (s - δ + h))
        (share1 s (s - δ' - h) (s - δ' + h)),
      shareRatio1_eq hs hh hstand hd hd' he he', inv_div]
  rw [e0, e1, Real.log_div hup'.ne' hup.ne', Real.log_div hdn'.ne' hdn.ne',
    Cup_eq_neg_log hs hh hd hd', Cup_eq_neg_log hs hh he he',
    Cdn_eq_neg_log hs hh hstand hd hd', Cdn_eq_neg_log hs hh hstand he he']
  congr 1 <;> ring

/-! ## Monotonicity of the potentials -/

/-- The derivative of the token0 potential. -/
lemma hasDerivAt_Cup (hs : 0 < s) (hh : 0 < h) (hz : -h < z) (hz' : z < h) :
    HasDerivAt (Cup s h)
      (1 / (h - z) - 2 * z / Dden s h z) z := by
  have hD : (0:ℝ) < Dden s h z := denom_pos hs hh hz hz'
  have hA : (0:ℝ) < h - z := by linarith
  have h1 : HasDerivAt (Dden s h) (-(2 * z)) z := by
    unfold Dden
    simpa using ((hasDerivAt_pow 2 z).const_sub (h * (2 * s + h)))
  have h2 := h1.log hD.ne'
  have h3 : HasDerivAt (fun x : ℝ => h - x) (-1) z := by
    simpa using (hasDerivAt_id z).const_sub h
  have h4 := h3.log hA.ne'
  refine (h2.sub h4).congr_deriv ?_
  field_simp
  ring

/-- The token0 potential is strictly increasing: the certifying inequality is
`2sh + (h - z)² > 0`, which needs no width hypothesis. -/
lemma Cup_deriv_pos (hs : 0 < s) (hh : 0 < h) (hz : -h < z) (hz' : z < h) :
    0 < 1 / (h - z) - 2 * z / Dden s h z := by
  have hD : (0:ℝ) < Dden s h z := denom_pos hs hh hz hz'
  have hDv : Dden s h z = h * (2 * s + h) - z ^ 2 := rfl
  have hA : (0:ℝ) < h - z := by linarith
  have expand : 1 / (h - z) - 2 * z / Dden s h z
      = (2 * s * h + (h - z) ^ 2) / ((h - z) * Dden s h z) := by
    field_simp
    unfold Dden
    ring
  rw [expand]
  apply div_pos (by nlinarith [sq_nonneg (h - z)]) (by positivity)

/-- **Corollary (Placement-Family Potentials), monotonicity of `C↑`.** -/
theorem strictMonoOn_Cup (hs : 0 < s) (hh : 0 < h) :
    StrictMonoOn (Cup s h) (Set.Ioo (-h) h) := by
  have hcont : ContinuousOn (Cup s h) (Set.Ioo (-h) h) := by
    apply ContinuousOn.sub
    · apply ContinuousOn.log continuous_Dden.continuousOn
      intro x hx
      simp only [Set.mem_Ioo] at hx
      exact (denom_pos hs hh hx.1 hx.2).ne'
    · apply ContinuousOn.log (by fun_prop)
      intro x hx
      simp only [Set.mem_Ioo] at hx
      intro hc; linarith [hx.2]
  refine strictMonoOn_of_deriv_pos (convex_Ioo _ _) hcont ?_
  intro x hx
  rw [interior_Ioo, Set.mem_Ioo] at hx
  rw [(hasDerivAt_Cup hs hh hx.1 hx.2).deriv]
  exact Cup_deriv_pos hs hh hx.1 hx.2

/-- The derivative of the token1 potential. -/
lemma hasDerivAt_Cdn (hs : 0 < s) (hh : 0 < h) (hstand : 5 * h ≤ s)
    (hz : -h < z) (hz' : z < h) :
    HasDerivAt (Cdn s h)
      (-(2 * z) / Dden s h z - 1 / (h + z) + 1 / (s + h - z)) z := by
  have hD : (0:ℝ) < Dden s h z := denom_pos hs hh hz hz'
  have hB : (0:ℝ) < h + z := by linarith
  have hC : (0:ℝ) < s + h - z := by linarith
  have h1 : HasDerivAt (Dden s h) (-(2 * z)) z := by
    unfold Dden
    simpa using ((hasDerivAt_pow 2 z).const_sub (h * (2 * s + h)))
  have h2 := h1.log hD.ne'
  have h3 : HasDerivAt (fun x : ℝ => h + x) 1 z := by
    simpa using (hasDerivAt_id z).const_add h
  have h4 := h3.log hB.ne'
  have h5 : HasDerivAt (fun x : ℝ => s + h - x) (-1) z := by
    simpa using (hasDerivAt_id z).const_sub (s + h)
  have h6 := h5.log hC.ne'
  refine ((h2.sub h4).sub h6).congr_deriv ?_
  field_simp
  ring

/-- The token1 potential is strictly decreasing under the standing hypothesis. -/
lemma Cdn_deriv_neg (hs : 0 < s) (hh : 0 < h) (hstand : 5 * h ≤ s)
    (hz : -h < z) (hz' : z < h) :
    -(2 * z) / Dden s h z - 1 / (h + z) + 1 / (s + h - z) < 0 := by
  have hD : (0:ℝ) < Dden s h z := denom_pos hs hh hz hz'
  have hDv : Dden s h z = h * (2 * s + h) - z ^ 2 := rfl
  have hB : (0:ℝ) < h + z := by linarith
  have hC : (0:ℝ) < s + h - z := by linarith
  have expand : -(2 * z) / Dden s h z - 1 / (h + z) + 1 / (s + h - z)
      = (-(2 * z) * (h + z) * (s + h - z) + Dden s h z * (2 * z - s))
        / (Dden s h z * ((h + z) * (s + h - z))) := by
    field_simp
    ring
  rw [expand]
  apply div_neg_of_neg_of_pos _ (by positivity)
  rw [hDv]
  nlinarith [sq_nonneg (h - z), sq_nonneg (h + z), sq_nonneg z, sq_nonneg (s - z),
    mul_pos hB hC]

/-- **Corollary (Placement-Family Potentials), monotonicity of `C↓`.** -/
theorem strictAntiOn_Cdn (hs : 0 < s) (hh : 0 < h) (hstand : 5 * h ≤ s) :
    StrictAntiOn (Cdn s h) (Set.Ioo (-h) h) := by
  have hcont : ContinuousOn (Cdn s h) (Set.Ioo (-h) h) := by
    refine ContinuousOn.sub (ContinuousOn.sub ?_ ?_) ?_
    · apply ContinuousOn.log continuous_Dden.continuousOn
      intro x hx
      simp only [Set.mem_Ioo] at hx
      exact (denom_pos hs hh hx.1 hx.2).ne'
    · apply ContinuousOn.log (by fun_prop)
      intro x hx
      simp only [Set.mem_Ioo] at hx
      intro hc; linarith [hx.1]
    · apply ContinuousOn.log (by fun_prop)
      intro x hx
      simp only [Set.mem_Ioo] at hx
      intro hc; linarith [hx.2]
  refine strictAntiOn_of_deriv_neg (convex_Ioo _ _) hcont ?_
  intro x hx
  rw [interior_Ioo, Set.mem_Ioo] at hx
  rw [(hasDerivAt_Cdn hs hh hstand hx.1 hx.2).deriv]
  exact Cdn_deriv_neg hs hh hstand hx.1 hx.2

/-! ## No free round trips -/

/-- **Corollary (Placement-Family Potentials), no free round trips.** A move off
the current displacement and back costs strictly more than nothing: the upward
potential rises where the downward one falls, so the two branch increments
cannot both vanish. -/
theorem round_trip_pos (hL : 0 < L) (hs : 0 < s) (hh : 0 < h)
    (hstand : 5 * h ≤ s) (hd : -h < δ) (hd' : δ < h) (he : -h < δ')
    (he' : δ' < h) (hne : δ ≠ δ') :
    0 < kerf L s (s - δ - h) (s - δ + h) (s - δ' - h) (s - δ' + h)
        + kerf L s (s - δ' - h) (s - δ' + h) (s - δ - h) (s - δ + h) := by
  rw [kerf_eq_max_potential hL hs hh hstand hd hd' he he',
    kerf_eq_max_potential hL hs hh hstand he he' hd hd']
  have hmem : δ ∈ Set.Ioo (-h) h := ⟨hd, hd'⟩
  have hmem' : δ' ∈ Set.Ioo (-h) h := ⟨he, he'⟩
  rcases lt_or_gt_of_ne hne with hlt | hlt
  · have h1 : Cup s h δ < Cup s h δ' := strictMonoOn_Cup hs hh hmem hmem' hlt
    have h2 : Cdn s h δ' < Cdn s h δ := strictAntiOn_Cdn hs hh hstand hmem hmem' hlt
    have hA : 0 < Cdn s h δ - Cdn s h δ' := by linarith
    have hB : 0 < Cup s h δ' - Cup s h δ := by linarith
    have := le_max_right (Cup s h δ - Cup s h δ') (Cdn s h δ - Cdn s h δ')
    have := le_max_left (Cup s h δ' - Cup s h δ) (Cdn s h δ' - Cdn s h δ)
    linarith
  · have h1 : Cup s h δ' < Cup s h δ := strictMonoOn_Cup hs hh hmem' hmem hlt
    have h2 : Cdn s h δ < Cdn s h δ' := strictAntiOn_Cdn hs hh hstand hmem' hmem hlt
    have := le_max_left (Cup s h δ - Cup s h δ') (Cdn s h δ - Cdn s h δ')
    have := le_max_right (Cup s h δ' - Cup s h δ) (Cdn s h δ' - Cdn s h δ)
    linarith

/-! ## The boundary case δ' = 0

Setting the return displacement to zero recovers the two-branch amplitude of
§The amplitude layer, in fractional form against the withdrawn value. -/

/-- The token0 branch at `δ' = 0` is the upper branch of the amplitude,
in fractional form against the withdrawn value. -/
theorem reduction_up (hs : 0 < s) (hh : 0 < h) (hd : -h < δ) (hd' : δ < h) :
    1 - Qup s h δ / Qup s h 0 = δ * (2 * s + h - δ) / Dden s h δ := by
  have hD : (0:ℝ) < Dden s h δ := denom_pos hs hh hd hd'
  have hD0 : (0:ℝ) < Dden s h 0 := denom_pos hs hh (by linarith) hh
  have hz0 : Qup s h 0 = h / Dden s h 0 := by unfold Qup; rw [sub_zero]
  have hDz : Dden s h 0 = h * (2 * s + h) := by unfold Dden; ring
  have hkey : Dden s h δ - (h - δ) * (2 * s + h) = δ * (2 * s + h - δ) := by
    unfold Dden; ring
  rw [hz0, hDz]
  unfold Qup
  rw [div_div_div_comm]
  rw [← hkey]
  field_simp

/-- The token1 branch at `δ' = 0` is the lower branch of the amplitude,
in fractional form against the withdrawn value. -/
theorem reduction_dn (hs : 0 < s) (hh : 0 < h) (hstand : 5 * h ≤ s)
    (hd : -h < δ) (hd' : δ < h) :
    1 - Qdn s h δ / Qdn s h 0
      = -(δ * s * (2 * s + h - δ)) / ((s + h) * Dden s h δ) := by
  have hD : (0:ℝ) < Dden s h δ := denom_pos hs hh hd hd'
  have hsh : (0:ℝ) < s + h := by linarith
  have hP : (0:ℝ) < 2 * s + h := by linarith
  have hz0 : Qdn s h 0 = (s + h) / (2 * s + h) := by
    unfold Qdn Dden
    rw [div_eq_div_iff (by nlinarith) hP.ne']
    ring
  have hkey : Dden s h δ * (s + h) - (h + δ) * (s + h - δ) * (2 * s + h)
      = -(δ * s * (2 * s + h - δ)) := by
    unfold Dden; ring
  rw [hz0]
  unfold Qdn
  rw [div_div_div_comm, ← hkey]
  field_simp

end LocalTime
