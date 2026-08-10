/-
The corridor, the tangency constant, and the impulse inequality, §The
fixed-width floor and §The width-uniform floor, with Appendix "Proofs for the
floors".

The floors are proved by a verification function: a function `U` of the state
whose second derivative is bounded below as a measure and which loses no more
across any admissible impulse than the impulse costs. This file machine-checks
the part of that argument that is not stochastic, which is all of it except the
Itô step and the telescoping.

Three statements carry the constant two.

* In the narrow limit, in the displacement coordinate, the extremal
  verification derivative `4δ/h²` sits inside the envelope corridor
  `-1/(h+δ) ≤ U' ≤ 1/(h-δ)` and is tangent to both envelopes at `±h/2`. The
  certifying inequalities are `(h - 2δ)² ≥ 0` and `(h + 2δ)² ≥ 0`. The
  corridor's defining infimum is exactly `4/h²`, so `c_min = 2`. This is the
  tangency constant.
* Away from the narrow limit the era corrections cost at most `3/s₋`, and the
  split at `δ₂ - δ₁ = h/4` gives `c_min ≥ 2(1 - 3h/s₋)`.
* In the share coordinate, at any width, `U(ω) = 8(ω - 1/2)²` satisfies the
  impulse inequality against the exact share potentials of Theorem 2, tangent
  at `ω = 1/4` and `3/4`, with certifying inequalities `(4ω - 1)² ≥ 0` and
  `(4ω - 3)² ≥ 0`. This part carries no narrow-limit correction, which is why
  the same two appears in both coordinates.

What is not formalised, and is stated as such in the README, is the Itô-Tanaka
step of the verification scheme and the renewal-reward evaluation, both of
which need stochastic-analysis machinery absent from mathlib.
-/
import LocalTime.Potentials

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

variable {h s δ δ' δ₁ δ₂ ω ω' : ℝ}

/-! ## The narrow-limit envelopes and the tangency inequalities -/

/-- The narrow-limit upper envelope slope, `(C↑₀)'(δ) = 1/(h - δ)`. -/
noncomputable def Eup0 (h δ : ℝ) : ℝ := 1 / (h - δ)

/-- The narrow-limit lower envelope slope, `(C↓₀)'(δ) = -1/(h + δ)`. -/
noncomputable def Edn0 (h δ : ℝ) : ℝ := -(1 / (h + δ))

/-- **Tangency, upper side.** The extremal verification derivative lies under
the upper envelope, the certificate being `(h - 2δ)² ≥ 0`. -/
theorem tangency_upper (hh : 0 < h) (hδ : -h < δ) (hδ' : δ < h) :
    4 * δ / h ^ 2 ≤ Eup0 h δ := by
  have hA : (0:ℝ) < h - δ := by linarith
  unfold Eup0
  rw [div_le_div_iff₀ (by positivity) hA]
  nlinarith [sq_nonneg (h - 2 * δ)]

/-- **Tangency, lower side.** The extremal verification derivative lies over the
lower envelope, the certificate being `(h + 2δ)² ≥ 0`. -/
theorem tangency_lower (hh : 0 < h) (hδ : -h < δ) (hδ' : δ < h) :
    Edn0 h δ ≤ 4 * δ / h ^ 2 := by
  have hB : (0:ℝ) < h + δ := by linarith
  unfold Edn0
  rw [neg_le, ← neg_div, div_le_div_iff₀ (pow_pos hh 2) hB]
  nlinarith [sq_nonneg (h + 2 * δ)]

/-- Tangency is attained on the upper side at `δ = h/2`. -/
theorem tangency_upper_eq (hh : 0 < h) : 4 * (h / 2) / h ^ 2 = Eup0 h (h / 2) := by
  unfold Eup0
  rw [div_eq_div_iff (pow_pos hh 2).ne' (by linarith : (0:ℝ) < h - h / 2).ne']
  ring

/-- Tangency is attained on the lower side at `δ = -h/2`. -/
theorem tangency_lower_eq (hh : 0 < h) :
    Edn0 h (-(h / 2)) = 4 * (-(h / 2)) / h ^ 2 := by
  unfold Edn0
  rw [neg_eq_iff_eq_neg, ← neg_div, ← neg_div]
  rw [div_eq_div_iff (by linarith : (0:ℝ) < h + -h / 2).ne' (pow_pos hh 2).ne']
  ring

/-! ## The corridor gap and the constant two -/

/-- **The tangency constant, lower bound.** The corridor gap over any pair of
displacements is at least `4/h²` times their separation, so the infimum
defining `c_min` is at least `4/h²` and `c_min ≥ 2`. -/
theorem corridor_gap_ge (hh : 0 < h) (h1 : -h < δ₁) (h12 : δ₁ < δ₂)
    (h2 : δ₂ < h) :
    4 * (δ₂ - δ₁) / h ^ 2 ≤ Eup0 h δ₂ - Edn0 h δ₁ := by
  have hu := tangency_upper (h := h) (δ := δ₂) hh (by linarith) h2
  have hl := tangency_lower (h := h) (δ := δ₁) hh h1 (by linarith)
  have : 4 * (δ₂ - δ₁) / h ^ 2 = 4 * δ₂ / h ^ 2 - 4 * δ₁ / h ^ 2 := by ring
  rw [this]
  linarith

/-- **The tangency constant, attainment.** At the tangency pair `±h/2` the
corridor gap equals `4/h²` times the separation, so the infimum is exactly
`4/h²` and the constant is exactly two. -/
theorem corridor_gap_eq_at_tangency (hh : 0 < h) :
    4 * (h / 2 - -(h / 2)) / h ^ 2 = Eup0 h (h / 2) - Edn0 h (-(h / 2)) := by
  rw [← tangency_upper_eq hh, tangency_lower_eq hh]
  ring

/-- The uncorrected corridor gap is never smaller than `1/h`; each of its two
terms is at least `1/(2h)`. This is the second of the two lower bounds the
analytic corollary splits between. -/
theorem corridor_gap_ge_inv (hh : 0 < h) (h1 : -h < δ₁) (h12 : δ₁ < δ₂)
    (h2 : δ₂ < h) : 1 / h ≤ Eup0 h δ₂ - Edn0 h δ₁ := by
  have hA : (0:ℝ) < h - δ₂ := by linarith
  have hB : (0:ℝ) < h + δ₁ := by linarith
  have hA' : h - δ₂ < 2 * h := by linarith
  have hB' : h + δ₁ < 2 * h := by linarith
  have e1 : 1 / (2 * h) ≤ 1 / (h - δ₂) := by
    apply one_div_le_one_div_of_le hA hA'.le
  have e2 : 1 / (2 * h) ≤ 1 / (h + δ₁) := by
    apply one_div_le_one_div_of_le hB hB'.le
  unfold Eup0 Edn0
  have : (1:ℝ) / h = 1 / (2 * h) + 1 / (2 * h) := by field_simp; ring
  rw [this]
  linarith

/-- **The analytic corollary, `c_min ≥ 2(1 - 3h/s₋)`.** With era-uniformised
envelopes that lose at most `3/s₋` against the narrow-limit ones, the corridor
ratio is bounded below by `(4/h²)(1 - 3h/s₋)`. The proof splits at separation
`h/4`, using the tangent bound above it and the `1/h` bound below it. -/
theorem corridor_ratio_era_bound (hh : 0 < h) (hs : 0 < s) (hstand : 5 * h ≤ s)
    (Eu Ed : ℝ → ℝ)
    (hEu : ∀ z, -h < z → z < h → Eup0 h z - 1 / s ≤ Eu z)
    (hEd : ∀ z, -h < z → z < h → Ed z ≤ Edn0 h z + 2 / s)
    (h1 : -h < δ₁) (h12 : δ₁ < δ₂) (h2 : δ₂ < h) :
    4 / h ^ 2 * (1 - 3 * h / s) * (δ₂ - δ₁) ≤ Eu δ₂ - Ed δ₁ := by
  have hΔ : (0:ℝ) < δ₂ - δ₁ := by linarith
  have hgap : Eup0 h δ₂ - Edn0 h δ₁ - 3 / s ≤ Eu δ₂ - Ed δ₁ := by
    have a1 := hEu δ₂ (by linarith) h2
    have a2 := hEd δ₁ h1 (by linarith)
    have h3s : (3:ℝ) / s = 1 / s + 2 / s := by ring
    rw [h3s]
    linarith
  have hkey : 4 / h ^ 2 * (1 - 3 * h / s) * (δ₂ - δ₁)
      ≤ Eup0 h δ₂ - Edn0 h δ₁ - 3 / s := by
    have hexp : 4 / h ^ 2 * (1 - 3 * h / s) * (δ₂ - δ₁)
        = 4 * (δ₂ - δ₁) / h ^ 2 - 12 * (δ₂ - δ₁) / (h * s) := by
      field_simp
      ring
    rw [hexp]
    rcases le_total (h / 4) (δ₂ - δ₁) with hcase | hcase
    · have hg := corridor_gap_ge hh h1 h12 h2
      have : 12 * (δ₂ - δ₁) / (h * s) ≥ 3 / s := by
        rw [ge_iff_le, div_le_div_iff₀ hs (by positivity)]
        nlinarith
      linarith
    · have hg := corridor_gap_ge_inv hh h1 h12 h2
      have hK : (0:ℝ) < 1 / h - 3 / s := by
        have : (3:ℝ) / s < 1 / h := by
          rw [div_lt_div_iff₀ hs hh]; linarith
        linarith
      have hfac : 4 * (δ₂ - δ₁) / h ^ 2 - 12 * (δ₂ - δ₁) / (h * s)
          = ((δ₂ - δ₁) * 4 / h) * (1 / h - 3 / s) := by
        field_simp
        ring
      have hle1 : (δ₂ - δ₁) * 4 / h ≤ 1 := by
        rw [div_le_one hh]; linarith
      rw [hfac]
      have hmul : ((δ₂ - δ₁) * 4 / h) * (1 / h - 3 / s) ≤ 1 * (1 / h - 3 / s) :=
        mul_le_mul_of_nonneg_right hle1 hK.le
      linarith
  linarith

/-! ## The share coordinate: the corridor at any width -/

/-- **The share corridor, upper side.** `U'(ω) = 16(ω - 1/2)` lies under
`1/(1 - ω)`, the certificate being `(4ω - 3)² ≥ 0`, with tangency at
`ω = 3/4`. -/
theorem share_corridor_upper (hω : 0 < ω) (hω' : ω < 1) :
    16 * (ω - 1 / 2) ≤ 1 / (1 - ω) := by
  have hA : (0:ℝ) < 1 - ω := by linarith
  rw [le_div_iff₀ hA]
  nlinarith [sq_nonneg (4 * ω - 3)]

/-- **The share corridor, lower side.** `U'(ω) = 16(ω - 1/2)` lies over
`-1/ω`, the certificate being `(4ω - 1)² ≥ 0`, with tangency at `ω = 1/4`. -/
theorem share_corridor_lower (hω : 0 < ω) (hω' : ω < 1) :
    -(1 / ω) ≤ 16 * (ω - 1 / 2) := by
  rw [neg_le, le_div_iff₀ hω]
  nlinarith [sq_nonneg (4 * ω - 1)]

/-- The verification function of the width-uniform floor. -/
noncomputable def Ushare (ω : ℝ) : ℝ := 8 * (ω - 1 / 2) ^ 2

/-- `U - C↑_share`, whose monotonicity prices the moves that raise the token0
share. -/
noncomputable def Fshare (ω : ℝ) : ℝ := Ushare ω + Real.log ω

/-- `U - C↓_share`, whose monotonicity prices the moves that lower it. -/
noncomputable def Gshare (ω : ℝ) : ℝ := Ushare ω + Real.log (1 - ω)

lemma hasDerivAt_Ushare (x : ℝ) : HasDerivAt Ushare (16 * (x - 1 / 2)) x := by
  have hb : HasDerivAt (fun y : ℝ => y - 1 / 2) 1 x := by
    simpa using (hasDerivAt_id x).sub_const (1 / 2)
  have hp := hb.pow 2
  have h1 := hp.const_mul (8:ℝ)
  refine h1.congr_deriv ?_
  norm_num
  ring

lemma hasDerivAt_Fshare (hω : 0 < ω) :
    HasDerivAt Fshare (16 * (ω - 1 / 2) + 1 / ω) ω := by
  have h1 := hasDerivAt_Ushare ω
  have h2 := Real.hasDerivAt_log hω.ne'
  refine (h1.add h2).congr_deriv ?_
  simp [one_div]

lemma hasDerivAt_Gshare (hω' : ω < 1) :
    HasDerivAt Gshare (16 * (ω - 1 / 2) - 1 / (1 - ω)) ω := by
  have h1 := hasDerivAt_Ushare ω
  have h3 : HasDerivAt (fun y : ℝ => 1 - y) (-1) ω := by
    simpa using (hasDerivAt_id ω).const_sub 1
  have h4 := h3.log (by intro hc; linarith [sub_eq_zero.mp hc])
  refine (h1.add h4).congr_deriv ?_
  field_simp
  ring

/-- `U + log ω` is nondecreasing on `(0,1)`: this is the lower corridor. -/
theorem monotoneOn_Fshare : MonotoneOn Fshare (Set.Ioo 0 1) := by
  have hcont : ContinuousOn Fshare (Set.Ioo 0 1) := by
    intro x hx
    simp only [Set.mem_Ioo] at hx
    exact ((hasDerivAt_Fshare hx.1).continuousAt).continuousWithinAt
  refine monotoneOn_of_deriv_nonneg (convex_Ioo 0 1) hcont ?_ ?_
  · intro x hx
    rw [interior_Ioo, Set.mem_Ioo] at hx
    exact (hasDerivAt_Fshare hx.1).differentiableAt.differentiableWithinAt
  · intro x hx
    rw [interior_Ioo, Set.mem_Ioo] at hx
    rw [(hasDerivAt_Fshare hx.1).deriv]
    have := share_corridor_lower hx.1 hx.2
    linarith

/-- `U + log(1 - ω)` is nonincreasing on `(0,1)`: this is the upper corridor. -/
theorem antitoneOn_Gshare : AntitoneOn Gshare (Set.Ioo 0 1) := by
  have hcont : ContinuousOn Gshare (Set.Ioo 0 1) := by
    intro x hx
    simp only [Set.mem_Ioo] at hx
    exact ((hasDerivAt_Gshare hx.2).continuousAt).continuousWithinAt
  refine antitoneOn_of_deriv_nonpos (convex_Ioo 0 1) hcont ?_ ?_
  · intro x hx
    rw [interior_Ioo, Set.mem_Ioo] at hx
    exact (hasDerivAt_Gshare hx.2).differentiableAt.differentiableWithinAt
  · intro x hx
    rw [interior_Ioo, Set.mem_Ioo] at hx
    rw [(hasDerivAt_Gshare hx.2).deriv]
    have := share_corridor_upper hx.1 hx.2
    linarith

/-- **The impulse inequality of the width-uniform floor.** The verification
function loses no more across any impulse than the impulse's kerf, which by
Theorem 2 is the larger of the two log share increments. The statement is exact
at every width and carries no narrow-limit correction. -/
theorem share_impulse_inequality (hω : 0 < ω) (hω' : ω < 1) (he : 0 < ω')
    (he' : ω' < 1) :
    Ushare ω - Ushare ω'
      ≤ max (Real.log (ω' / ω)) (Real.log ((1 - ω') / (1 - ω))) := by
  have hmem : ω ∈ Set.Ioo (0:ℝ) 1 := ⟨hω, hω'⟩
  have hmem' : ω' ∈ Set.Ioo (0:ℝ) 1 := ⟨he, he'⟩
  rcases lt_trichotomy ω ω' with hlt | heq | hgt
  · have hF := monotoneOn_Fshare hmem hmem' hlt.le
    unfold Fshare at hF
    have hle : Ushare ω - Ushare ω' ≤ Real.log ω' - Real.log ω := by linarith
    have hlog : Real.log (ω' / ω) = Real.log ω' - Real.log ω :=
      Real.log_div he.ne' hω.ne'
    rw [hlog]
    exact le_trans hle (le_max_left _ _)
  · subst heq
    simp
  · have hG := antitoneOn_Gshare hmem' hmem hgt.le
    unfold Gshare at hG
    have hle : Ushare ω - Ushare ω' ≤ Real.log (1 - ω') - Real.log (1 - ω) := by
      linarith
    have hlog : Real.log ((1 - ω') / (1 - ω))
        = Real.log (1 - ω') - Real.log (1 - ω) :=
      Real.log_div (by linarith) (by linarith)
    rw [hlog]
    exact le_trans hle (le_max_right _ _)

/-! ## The displacement coordinate: the narrow-limit impulse inequality -/

/-- The narrow-limit verification function of the fixed-width floor. -/
noncomputable def Ufix (h δ : ℝ) : ℝ := 2 * δ ^ 2 / h ^ 2

/-- `U - C↑₀`, nonincreasing, which prices the moves that raise the
displacement's potential. -/
noncomputable def Ffix (h δ : ℝ) : ℝ := Ufix h δ + Real.log (h - δ)

/-- `U - C↓₀`, nondecreasing. -/
noncomputable def Gfix (h δ : ℝ) : ℝ := Ufix h δ + Real.log (h + δ)

lemma hasDerivAt_Ufix (hh : 0 < h) (x : ℝ) :
    HasDerivAt (Ufix h) (4 * x / h ^ 2) x := by
  have hp : HasDerivAt (fun y : ℝ => y ^ 2) (2 * x) x := by
    simpa using hasDerivAt_pow 2 x
  have h1 := (hp.const_mul (2:ℝ)).div_const (h ^ 2)
  refine h1.congr_deriv ?_
  ring

lemma hasDerivAt_Ffix (hh : 0 < h) (hδ : -h < δ) (hδ' : δ < h) :
    HasDerivAt (Ffix h) (4 * δ / h ^ 2 - 1 / (h - δ)) δ := by
  have h1 := hasDerivAt_Ufix hh δ
  have h3 : HasDerivAt (fun y : ℝ => h - y) (-1) δ := by
    simpa using (hasDerivAt_id δ).const_sub h
  have h4 := h3.log (by intro hc; linarith [sub_eq_zero.mp hc])
  refine (h1.add h4).congr_deriv ?_
  field_simp
  ring

lemma hasDerivAt_Gfix (hh : 0 < h) (hδ : -h < δ) (hδ' : δ < h) :
    HasDerivAt (Gfix h) (4 * δ / h ^ 2 + 1 / (h + δ)) δ := by
  have h1 := hasDerivAt_Ufix hh δ
  have h3 : HasDerivAt (fun y : ℝ => h + y) 1 δ := by
    simpa using (hasDerivAt_id δ).const_add h
  have h4 := h3.log (by intro hc; linarith)
  refine (h1.add h4).congr_deriv ?_
  simp [one_div]

/-- `U + log(h - δ)` is nonincreasing on `(-h, h)`: the upper corridor. -/
theorem antitoneOn_Ffix (hh : 0 < h) : AntitoneOn (Ffix h) (Set.Ioo (-h) h) := by
  have hcont : ContinuousOn (Ffix h) (Set.Ioo (-h) h) := by
    intro x hx
    simp only [Set.mem_Ioo] at hx
    exact ((hasDerivAt_Ffix hh hx.1 hx.2).continuousAt).continuousWithinAt
  refine antitoneOn_of_deriv_nonpos (convex_Ioo _ _) hcont ?_ ?_
  · intro x hx
    rw [interior_Ioo, Set.mem_Ioo] at hx
    exact (hasDerivAt_Ffix hh hx.1 hx.2).differentiableAt.differentiableWithinAt
  · intro x hx
    rw [interior_Ioo, Set.mem_Ioo] at hx
    rw [(hasDerivAt_Ffix hh hx.1 hx.2).deriv]
    have := tangency_upper hh hx.1 hx.2
    unfold Eup0 at this
    linarith

/-- `U + log(h + δ)` is nondecreasing on `(-h, h)`: the lower corridor. -/
theorem monotoneOn_Gfix (hh : 0 < h) : MonotoneOn (Gfix h) (Set.Ioo (-h) h) := by
  have hcont : ContinuousOn (Gfix h) (Set.Ioo (-h) h) := by
    intro x hx
    simp only [Set.mem_Ioo] at hx
    exact ((hasDerivAt_Gfix hh hx.1 hx.2).continuousAt).continuousWithinAt
  refine monotoneOn_of_deriv_nonneg (convex_Ioo _ _) hcont ?_ ?_
  · intro x hx
    rw [interior_Ioo, Set.mem_Ioo] at hx
    exact (hasDerivAt_Gfix hh hx.1 hx.2).differentiableAt.differentiableWithinAt
  · intro x hx
    rw [interior_Ioo, Set.mem_Ioo] at hx
    rw [(hasDerivAt_Gfix hh hx.1 hx.2).deriv]
    have := tangency_lower hh hx.1 hx.2
    unfold Edn0 at this
    linarith

/-- **The impulse inequality of the fixed-width floor, narrow limit.** The
quadratic verification function loses no more across an impulse than the
narrow-limit potentials charge for it. -/
theorem fixed_impulse_inequality (hh : 0 < h) (hδ : -h < δ) (hδ' : δ < h)
    (he : -h < δ') (he' : δ' < h) :
    Ufix h δ - Ufix h δ'
      ≤ max (Cup0 h δ - Cup0 h δ') (Cdn0 h δ - Cdn0 h δ') := by
  have hmem : δ ∈ Set.Ioo (-h) h := ⟨hδ, hδ'⟩
  have hmem' : δ' ∈ Set.Ioo (-h) h := ⟨he, he'⟩
  unfold Cup0 Cdn0
  rcases lt_trichotomy δ' δ with hlt | heq | hgt
  · have hF := antitoneOn_Ffix hh hmem' hmem hlt.le
    unfold Ffix at hF
    have : Ufix h δ - Ufix h δ' ≤ -Real.log (h - δ) - -Real.log (h - δ') := by
      linarith
    exact le_trans this (le_max_left _ _)
  · subst heq
    simp
  · have hG := monotoneOn_Gfix hh hmem hmem' hgt.le
    unfold Gfix at hG
    have : Ufix h δ - Ufix h δ' ≤ -Real.log (h + δ) - -Real.log (h + δ') := by
      linarith
    exact le_trans this (le_max_right _ _)

end LocalTime
