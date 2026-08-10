/-
Proposition (Down-Branch Monotonicity), §The amplitude layer and Appendix
"Proofs for the amplitude layer".

The down branch of the amplitude, written in the magnitude coordinate `m = -δ`,
is `L G(m) / (sbar + h)` with

  G(m) = m (sbar - m) (2 sbar + h - m) / (sbar + h - m).

The paper's claim is that `G` is strictly increasing on `(0, h]` exactly when
`h / sbar ≤ (√17 - 3)/2`, and that above the threshold it turns over. The
numerator of `G'` is the cubic `GdnNum` below; its value at the corner is
`sbar (2 sbar² - 3 sbar h - h²)`, which is the sign the threshold controls.

As published, the Geometric Siphon's monotonicity theorem asserts both branches
strictly monotone with no width hypothesis. This file supplies the condition the
down branch needs. Production ranges sit one to two orders inside the threshold,
so the empirical content of that paper is unaffected.
-/
import LocalTime.Amplitude

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

variable {L sbar h m : ℝ}

/-- The down branch in the magnitude coordinate `m = -δ`. -/
noncomputable def Gdn (sbar h m : ℝ) : ℝ :=
  m * (sbar - m) * (2 * sbar + h - m) / (sbar + h - m)

/-- The down-branch amplitude is `L G(m)/(sbar + h)`. -/
lemma ampDn_eq_Gdn (hh : 0 < h) (hsb : 0 < sbar - h) (hm : 0 ≤ m) (hm' : m ≤ h) :
    ampDn L sbar h (-m) = L * Gdn sbar h m / (sbar + h) := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have h2 : (0:ℝ) < sbar + h - m := by linarith
  have h10 : sbar + h ≠ 0 := h1.ne'
  have h20 : sbar + h - m ≠ 0 := h2.ne'
  have h21 : sbar + h + -m ≠ 0 := fun hc => h20 (by linarith)
  unfold ampDn Gdn
  field_simp
  ring

/-- The numerator of `G'`, a cubic in `m`. -/
def GdnNum (sbar h m : ℝ) : ℝ :=
  (2 * sbar ^ 2 + sbar * h) * (sbar + h)
    - 2 * (3 * sbar + h) * (sbar + h) * m
    + (6 * sbar + 4 * h) * m ^ 2 - 2 * m ^ 3

/-- The derivative of the down branch, with `GdnNum` as its numerator. -/
lemma hasDerivAt_Gdn (hd : sbar + h - m ≠ 0) :
    HasDerivAt (Gdn sbar h) (GdnNum sbar h m / (sbar + h - m) ^ 2) m := by
  have ha : HasDerivAt (fun x : ℝ => x) 1 m := hasDerivAt_id m
  have hb : HasDerivAt (fun x : ℝ => sbar - x) (-1) m := by
    simpa using (hasDerivAt_id m).const_sub sbar
  have hc : HasDerivAt (fun x : ℝ => 2 * sbar + h - x) (-1) m := by
    simpa using (hasDerivAt_id m).const_sub (2 * sbar + h)
  have hD : HasDerivAt (fun x : ℝ => sbar + h - x) (-1) m := by
    simpa using (hasDerivAt_id m).const_sub (sbar + h)
  have hN := (ha.mul hb).mul hc
  have := hN.div hD hd
  refine this.congr_deriv ?_
  unfold GdnNum
  simp only [Pi.mul_apply]
  field_simp
  ring

/-- The corner value of the numerator, the sign the threshold controls. -/
lemma GdnNum_corner : GdnNum sbar h h = sbar * (2 * sbar ^ 2 - 3 * sbar * h - h ^ 2) := by
  unfold GdnNum; ring

/-- The numerator's decrement from the corner, factored. -/
lemma GdnNum_sub_corner :
    GdnNum sbar h m - GdnNum sbar h h
      = (h - m) * (2 * (3 * sbar + h) * (sbar + h)
          - (6 * sbar + 4 * h) * (m + h) + 2 * (m ^ 2 + m * h + h ^ 2)) := by
  unfold GdnNum; ring

/-- On the production side of the threshold the numerator is positive on the
open interval, so the branch is strictly increasing. -/
lemma GdnNum_pos (hh : 0 < h) (hsb : 0 < sbar - h)
    (hthr : 0 ≤ 2 * sbar ^ 2 - 3 * sbar * h - h ^ 2) (hm : 0 < m) (hm' : m < h) :
    0 < GdnNum sbar h m := by
  have hcorner : 0 ≤ GdnNum sbar h h := by
    rw [GdnNum_corner]; nlinarith
  have hbracket : 0 < 2 * (3 * sbar + h) * (sbar + h)
      - (6 * sbar + 4 * h) * (m + h) + 2 * (m ^ 2 + m * h + h ^ 2) := by
    nlinarith [sq_nonneg (sbar - h), sq_nonneg m, sq_nonneg (m - h)]
  have := GdnNum_sub_corner (sbar := sbar) (h := h) (m := m)
  nlinarith [mul_pos (by linarith : (0:ℝ) < h - m) hbracket]

/-- **Proposition (Down-Branch Monotonicity), sufficiency.** Below the threshold
the down branch is strictly increasing in the displacement magnitude. -/
theorem strictMonoOn_Gdn (hh : 0 < h) (hsb : 0 < sbar - h)
    (hthr : 0 ≤ 2 * sbar ^ 2 - 3 * sbar * h - h ^ 2) :
    StrictMonoOn (Gdn sbar h) (Set.Icc 0 h) := by
  have hcont : ContinuousOn (Gdn sbar h) (Set.Icc 0 h) := by
    apply ContinuousOn.div (by fun_prop) (by fun_prop)
    intro x hx
    simp only [Set.mem_Icc] at hx
    intro hc
    linarith [hx.2]
  refine strictMonoOn_of_deriv_pos (convex_Icc 0 h) hcont ?_
  intro x hx
  rw [interior_Icc, Set.mem_Ioo] at hx
  have hne : sbar + h - x ≠ 0 := by
    intro hc; linarith [hx.2]
  rw [(hasDerivAt_Gdn hne).deriv]
  have := GdnNum_pos (sbar := sbar) (h := h) (m := x) hh hsb hthr hx.1 hx.2
  positivity

/-- **Proposition (Down-Branch Monotonicity), necessity at the corner.** Above
the threshold the derivative at the corner is negative, so the branch has
already turned over there. -/
theorem deriv_Gdn_corner_neg (hh : 0 < h) (hsb : 0 < sbar - h)
    (hthr : 2 * sbar ^ 2 - 3 * sbar * h - h ^ 2 < 0) :
    deriv (Gdn sbar h) h < 0 := by
  have hne : sbar + h - h ≠ 0 := by
    have : (0:ℝ) < sbar := by linarith
    simpa using this.ne'
  rw [(hasDerivAt_Gdn (m := h) hne).deriv, GdnNum_corner]
  have hs : (0:ℝ) < sbar := by linarith
  have hden : (0:ℝ) < (sbar + h - h) ^ 2 := by
    have : sbar + h - h = sbar := by ring
    rw [this]; positivity
  apply div_neg_of_neg_of_pos _ hden
  nlinarith

/-- **Proposition (Down-Branch Monotonicity), necessity.** Above the threshold
the branch is not strictly increasing up to the corner: the corner value is
undercut from the interior, which is the interior maximum of the statement. -/
theorem not_strictMonoOn_Gdn (hh : 0 < h) (hsb : 0 < sbar - h)
    (hthr : 2 * sbar ^ 2 - 3 * sbar * h - h ^ 2 < 0) :
    ¬ StrictMonoOn (Gdn sbar h) (Set.Icc 0 h) := by
  intro hmono
  have hne : sbar + h - h ≠ 0 := by
    have : (0:ℝ) < sbar := by linarith
    simpa using this.ne'
  have hd := hasDerivAt_Gdn (sbar := sbar) (h := h) (m := h) hne
  have hslope := hasDerivAt_iff_tendsto_slope.mp hd
  have hsub : nhdsWithin h (Set.Iio h) ≤ nhdsWithin h {h}ᶜ := by
    apply nhdsWithin_mono
    intro x hx
    simp only [Set.mem_Iio] at hx
    simp only [Set.mem_compl_iff, Set.mem_singleton_iff]
    exact ne_of_lt hx
  have hlim := hslope.mono_left hsub
  have hpos : ∀ᶠ x in nhdsWithin h (Set.Iio h), (0:ℝ) < x :=
    (eventually_gt_nhds hh).filter_mono nhdsWithin_le_nhds
  have hnonneg : 0 ≤ GdnNum sbar h h / (sbar + h - h) ^ 2 := by
    refine ge_of_tendsto hlim ?_
    filter_upwards [self_mem_nhdsWithin, hpos] with x hx hx0
    simp only [Set.mem_Iio] at hx
    have hxmem : x ∈ Set.Icc (0:ℝ) h := ⟨hx0.le, hx.le⟩
    have hhmem : h ∈ Set.Icc (0:ℝ) h := ⟨hh.le, le_refl h⟩
    have hlt : Gdn sbar h x < Gdn sbar h h := hmono hxmem hhmem hx
    rw [slope_def_field, div_nonneg_iff]
    right
    constructor
    · simp only [sub_nonpos]; exact hlt.le
    · simp only [sub_nonpos]; exact hx.le
  have hneg := deriv_Gdn_corner_neg (sbar := sbar) (h := h) hh hsb hthr
  rw [hd.deriv] at hneg
  linarith

/-! ## The threshold in the narrow-range parameter -/

/-- The threshold in the narrow-range parameter: `2 sbar² - 3 sbar h - h² ≥ 0`
is exactly `h / sbar ≤ (√17 - 3)/2`. -/
theorem threshold_iff (hs : 0 < sbar) (hh : 0 < h) :
    0 ≤ 2 * sbar ^ 2 - 3 * sbar * h - h ^ 2 ↔ h / sbar ≤ (Real.sqrt 17 - 3) / 2 := by
  have h17 : Real.sqrt 17 ^ 2 = 17 := Real.sq_sqrt (by norm_num)
  have h9 : Real.sqrt 9 = 3 := by
    rw [show (9:ℝ) = 3 ^ 2 by norm_num, Real.sqrt_sq (by norm_num)]
  have h17pos : (3:ℝ) < Real.sqrt 17 := by
    have := Real.sqrt_lt_sqrt (by norm_num : (0:ℝ) ≤ 9) (by norm_num : (9:ℝ) < 17)
    rwa [h9] at this
  rw [div_le_iff₀ hs]
  have hsq : (Real.sqrt 17 * sbar) ^ 2 = 17 * sbar ^ 2 := by rw [mul_pow, h17]
  constructor
  · intro hthr
    have key : (2 * h + 3 * sbar) ^ 2 ≤ (Real.sqrt 17 * sbar) ^ 2 := by
      rw [hsq]; nlinarith
    have hb : 0 < Real.sqrt 17 * sbar := by nlinarith
    have ha : 0 < 2 * h + 3 * sbar := by linarith
    have hle : 2 * h + 3 * sbar ≤ Real.sqrt 17 * sbar := by nlinarith
    linarith
  · intro hthr
    have hle : 2 * h + 3 * sbar ≤ Real.sqrt 17 * sbar := by linarith
    have ha : 0 < 2 * h + 3 * sbar := by linarith
    have key : (2 * h + 3 * sbar) ^ 2 ≤ (Real.sqrt 17 * sbar) ^ 2 := by nlinarith
    rw [hsq] at key
    nlinarith

end LocalTime
