/-
Theorem 2 (Share-Potential Identity) and Corollary (Free Locus), §The central
law and Appendix "Proofs for the cost structure".

The paper's central result: the mint kerf of an isolated re-placement, from any
range containing the price to any admissible range containing the price, at any
width pair, is exactly the larger of the two log share increments. Width,
centring, and the price level enter only through the shares.

The abstract half of the argument is isolated first: for two probability pairs
the smaller of the two cross ratios is at most one, with equality exactly when
the pairs agree. That is the whole source of the sign, and of the free locus.
-/
import LocalTime.Defs

set_option linter.style.header false

namespace LocalTime

/-! ## The abstract share lemma -/

private lemma min_mul_nonneg {a b c : ℝ} (hc : 0 ≤ c) :
    min a b * c = min (a * c) (b * c) := by
  rcases le_total a b with h | h
  · rw [min_eq_left h, min_eq_left (by nlinarith)]
  · rw [min_eq_right h, min_eq_right (by nlinarith)]

/-- Two share pairs, each summing to one: the smaller cross ratio is at most
one. This is the sign of the kerf, and nothing else enters it. -/
lemma min_ratio_le_one {w v w' v' : ℝ} (_hw : 0 < w) (_hv : 0 < v)
    (hw' : 0 < w') (hv' : 0 < v') (h : w + v = 1) (h' : w' + v' = 1) :
    min (w / w') (v / v') ≤ 1 := by
  by_contra hcon
  obtain ⟨hx, hy⟩ := lt_min_iff.mp (not_le.mp hcon)
  have hx' : w' < w := (one_lt_div hw').mp hx
  have hy' : v' < v := (one_lt_div hv').mp hy
  linarith

/-- The smaller cross ratio equals one exactly on the matched-share locus. -/
lemma min_ratio_eq_one_iff {w v w' v' : ℝ} (hw : 0 < w) (hv : 0 < v)
    (hw' : 0 < w') (hv' : 0 < v') (h : w + v = 1) (h' : w' + v' = 1) :
    min (w / w') (v / v') = 1 ↔ w = w' ∧ v = v' := by
  constructor
  · intro hmin
    have hx : (1:ℝ) ≤ w / w' := hmin ▸ min_le_left _ _
    have hy : (1:ℝ) ≤ v / v' := hmin ▸ min_le_right _ _
    have hx' : w' ≤ w := (one_le_div hw').mp hx
    have hy' : v' ≤ v := (one_le_div hv').mp hy
    constructor <;> linarith
  · rintro ⟨rfl, rfl⟩
    simp [div_self hw.ne', div_self hv.ne']

/-! ## The identity -/

/-- The retained value fraction of an isolated re-placement is the smaller of
the two share ratios. This is the substance of Theorem 2; the kerf statement
below is its negative logarithm. -/
theorem retained_eq_min_share_ratio {L s sa sb sa' sb' : ℝ}
    (hL : 0 < L) (h0 : 0 < sa) (h1 : sa < s) (h2 : s < sb)
    (h0' : 0 < sa') (h1' : sa' < s) (h2' : s < sb') :
    retained L s sa sb sa' sb'
      = min (share0 s sa sb / share0 s sa' sb')
            (share1 s sa sb / share1 s sa' sb') := by
  have hs : (0:ℝ) < s := h0.trans h1
  have ha0' : 0 < amt0 s sb' := amt0_pos hs h2'
  have ha1' : 0 < amt1 s sa' := amt1_pos h1'
  have hphi : 0 < phi s sa sb := phi_pos h0 h1 h2
  have hphi' : 0 < phi s sa' sb' := phi_pos h0' h1' h2'
  have ha0 : 0 < amt0 s sb := amt0_pos hs h2
  have ha1 : 0 < amt1 s sa := amt1_pos h1
  have hs0 : s ≠ 0 := hs.ne'
  have hL0 : L ≠ 0 := hL.ne'
  have hn0 : amt0 s sb ≠ 0 := ha0.ne'
  have hn1 : amt1 s sa ≠ 0 := ha1.ne'
  have hn0' : amt0 s sb' ≠ 0 := ha0'.ne'
  have hn1' : amt1 s sa' ≠ 0 := ha1'.ne'
  have hp0 : phi s sa sb ≠ 0 := hphi.ne'
  have hp0' : phi s sa' sb' ≠ 0 := hphi'.ne'
  have hc : (0:ℝ) ≤ phi s sa' sb' / (L * phi s sa sb) := by positivity
  unfold retained Lnew
  rw [mul_div_assoc, min_mul_nonneg hc]
  congr 1
  · unfold share0
    field_simp
  · unfold share1
    field_simp

lemma retained_pos {L s sa sb sa' sb' : ℝ}
    (hL : 0 < L) (h0 : 0 < sa) (h1 : sa < s) (h2 : s < sb)
    (h0' : 0 < sa') (h1' : sa' < s) (h2' : s < sb') :
    0 < retained L s sa sb sa' sb' := by
  rw [retained_eq_min_share_ratio hL h0 h1 h2 h0' h1' h2']
  have := share0_pos h0 h1 h2
  have := share1_pos h0 h1 h2
  have := share0_pos h0' h1' h2'
  have := share1_pos h0' h1' h2'
  exact lt_min (by positivity) (by positivity)

/-- The retained fraction never exceeds one. -/
lemma retained_le_one {L s sa sb sa' sb' : ℝ}
    (hL : 0 < L) (h0 : 0 < sa) (h1 : sa < s) (h2 : s < sb)
    (h0' : 0 < sa') (h1' : sa' < s) (h2' : s < sb') :
    retained L s sa sb sa' sb' ≤ 1 := by
  rw [retained_eq_min_share_ratio hL h0 h1 h2 h0' h1' h2']
  exact min_ratio_le_one (share0_pos h0 h1 h2) (share1_pos h0 h1 h2)
    (share0_pos h0' h1' h2') (share1_pos h0' h1' h2')
    (share_add_eq_one h0 h1 h2) (share_add_eq_one h0' h1' h2')

/-- **Theorem 2 (Share-Potential Identity).** The mint kerf is the larger of the
two log share increments. -/
theorem kerf_eq_max_log {L s sa sb sa' sb' : ℝ}
    (hL : 0 < L) (h0 : 0 < sa) (h1 : sa < s) (h2 : s < sb)
    (h0' : 0 < sa') (h1' : sa' < s) (h2' : s < sb') :
    kerf L s sa sb sa' sb'
      = max (Real.log (share0 s sa' sb' / share0 s sa sb))
            (Real.log (share1 s sa' sb' / share1 s sa sb)) := by
  have hw : 0 < share0 s sa sb := share0_pos h0 h1 h2
  have hv : 0 < share1 s sa sb := share1_pos h0 h1 h2
  have hw' : 0 < share0 s sa' sb' := share0_pos h0' h1' h2'
  have hv' : 0 < share1 s sa' sb' := share1_pos h0' h1' h2'
  have hlog0 : Real.log (share0 s sa' sb' / share0 s sa sb)
      = -Real.log (share0 s sa sb / share0 s sa' sb') := by
    rw [← Real.log_inv, inv_div]
  have hlog1 : Real.log (share1 s sa' sb' / share1 s sa sb)
      = -Real.log (share1 s sa sb / share1 s sa' sb') := by
    rw [← Real.log_inv, inv_div]
  unfold kerf
  rw [retained_eq_min_share_ratio hL h0 h1 h2 h0' h1' h2', hlog0, hlog1,
    max_neg_neg]
  congr 1
  rcases le_total (share0 s sa sb / share0 s sa' sb')
      (share1 s sa sb / share1 s sa' sb') with hle | hle
  · rw [min_eq_left hle, min_eq_left (Real.log_le_log (by positivity) hle)]
  · rw [min_eq_right hle, min_eq_right (Real.log_le_log (by positivity) hle)]

/-- The kerf is non-negative: no isolated re-placement is free of charge. -/
theorem kerf_nonneg {L s sa sb sa' sb' : ℝ}
    (hL : 0 < L) (h0 : 0 < sa) (h1 : sa < s) (h2 : s < sb)
    (h0' : 0 < sa') (h1' : sa' < s) (h2' : s < sb') :
    0 ≤ kerf L s sa sb sa' sb' := by
  have hpos := retained_pos hL h0 h1 h2 h0' h1' h2'
  have hle := retained_le_one hL h0 h1 h2 h0' h1' h2'
  unfold kerf
  simpa using Real.log_nonpos hpos.le hle

/-- **Corollary (Free Locus).** The kerf vanishes exactly on the
share-preserving re-placements, at every width. -/
theorem kerf_eq_zero_iff {L s sa sb sa' sb' : ℝ}
    (hL : 0 < L) (h0 : 0 < sa) (h1 : sa < s) (h2 : s < sb)
    (h0' : 0 < sa') (h1' : sa' < s) (h2' : s < sb') :
    kerf L s sa sb sa' sb' = 0 ↔
      share0 s sa sb = share0 s sa' sb' ∧ share1 s sa sb = share1 s sa' sb' := by
  have hpos := retained_pos hL h0 h1 h2 h0' h1' h2'
  rw [← min_ratio_eq_one_iff (share0_pos h0 h1 h2) (share1_pos h0 h1 h2)
      (share0_pos h0' h1' h2') (share1_pos h0' h1' h2')
      (share_add_eq_one h0 h1 h2) (share_add_eq_one h0' h1' h2'),
    ← retained_eq_min_share_ratio hL h0 h1 h2 h0' h1' h2']
  unfold kerf
  constructor
  · intro hk
    have hlog : Real.log (retained L s sa sb sa' sb') = 0 := by linarith
    have hex := Real.exp_log hpos
    rw [hlog, Real.exp_zero] at hex
    exact hex.symm
  · intro hr; rw [hr]; simp

end LocalTime
