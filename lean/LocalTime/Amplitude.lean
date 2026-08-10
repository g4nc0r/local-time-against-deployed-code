/-
The amplitude layer, §The amplitude layer and Appendix "Proofs for the
amplitude layer".

The equal-width recentred rebalance: the old range is `[sbar - h, sbar + h]`,
the price is `s = sbar + δ`, the new range is `[s - h, s + h]`. The file proves
the Binding Side lemma, the Two-Branch Amplitude in closed form (as the exact
difference between the withdrawn and the re-minted value, not as a posited
formula), the branch relation through the factor `s / sb'`, the Corner Values
corollary, and the Exact Fractional Slopes lemma of §The cost structure.

The upper branch is the Geometric Siphon's closed form; the lower branch is the
value-surrendered form of the swap-free credit published in Operator &
Quantisation Microstructure. What is new here, and what this file checks, is
the assembly of the two into one function of the displacement, the two
published boundary factors as its two limits, and the monotonicity threshold
(the latter in `LocalTime/Monotonicity.lean`).
-/
import LocalTime.Defs

set_option linter.style.header false
-- Hypotheses that delimit the domain of a statement are kept even where the
-- proof does not consume them, so the Lean statement matches the paper's.
set_option linter.unusedVariables false

namespace LocalTime

variable {L sbar h δ : ℝ}

/-! ## The two candidate liquidities -/

/-- The token0-limited candidate liquidity of the recentred mint. -/
noncomputable def cand0 (L sbar h δ : ℝ) : ℝ :=
  L * (h - δ) * (sbar + δ + h) / (h * (sbar + h))

/-- The token1-limited candidate liquidity of the recentred mint. -/
noncomputable def cand1 (L h δ : ℝ) : ℝ := L * (h + δ) / h

/-- The token0 term of the mint minimum, in closed form. -/
lemma cand0_form (hL : 0 < L) (hh : 0 < h) (hsb : 0 < sbar - h)
    (hd : -h ≤ δ) (hd' : δ ≤ h) :
    L * amt0 (sbar + δ) (sbar + h) / amt0 (sbar + δ) (sbar + δ + h)
      = cand0 L sbar h δ := by
  have hs : (0:ℝ) < sbar + δ := by linarith
  have h1 : (0:ℝ) < sbar + h := by linarith
  have h2 : (0:ℝ) < sbar + δ + h := by linarith
  have hh0 : h ≠ 0 := hh.ne'
  have hs0 : sbar + δ ≠ 0 := hs.ne'
  have h10 : sbar + h ≠ 0 := h1.ne'
  have h20 : sbar + δ + h ≠ 0 := h2.ne'
  have hp1 : δ + sbar + h ≠ 0 := fun hc => h20 (by linarith)
  have hp2 : sbar + h + δ ≠ 0 := fun hc => h20 (by linarith)
  unfold amt0 cand0
  field_simp
  linear_combination (h - δ) * mul_inv_cancel₀ hh0

/-- The token1 term of the mint minimum, in closed form. -/
lemma cand1_form (hh0 : h ≠ 0) :
    L * amt1 (sbar + δ) (sbar - h) / amt1 (sbar + δ) (sbar + δ - h)
      = cand1 L h δ := by
  unfold amt1 cand1
  have : sbar + δ - (sbar + δ - h) = h := by ring
  rw [this]
  ring_nf

/-- **Lemma (Binding Side).** The difference of the two candidate liquidities
carries the sign of `-δ`. -/
lemma cand_diff (hh : 0 < h) (hsb : 0 < sbar - h) :
    cand0 L sbar h δ - cand1 L h δ
      = -(L * δ * (2 * sbar + h + δ)) / (h * (sbar + h)) := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have hh0 : h ≠ 0 := hh.ne'
  have h10 : sbar + h ≠ 0 := h1.ne'
  unfold cand0 cand1
  field_simp
  ring

/-- **Lemma (Binding Side), upper half.** For a price above the old midpoint the
token0 term binds. -/
lemma cand0_le_cand1 (hL : 0 < L) (hh : 0 < h) (hsb : 0 < sbar - h)
    (hd : 0 ≤ δ) (hd' : δ ≤ h) : cand0 L sbar h δ ≤ cand1 L h δ := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have hbr : (0:ℝ) < 2 * sbar + h + δ := by linarith
  have hdiff := cand_diff (L := L) (sbar := sbar) (h := h) (δ := δ) hh hsb
  rw [neg_div] at hdiff
  have hnum : 0 ≤ L * δ * (2 * sbar + h + δ) :=
    mul_nonneg (mul_nonneg hL.le hd) hbr.le
  have hden : (0:ℝ) < h * (sbar + h) := by positivity
  have hq := div_nonneg hnum hden.le
  linarith

/-- **Lemma (Binding Side), lower half.** For a price below the old midpoint the
token1 term binds. -/
lemma cand1_le_cand0 (hL : 0 < L) (hh : 0 < h) (hsb : 0 < sbar - h)
    (hd : -h ≤ δ) (hd' : δ ≤ 0) : cand1 L h δ ≤ cand0 L sbar h δ := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have hbr : (0:ℝ) < 2 * sbar + h + δ := by linarith
  have hdiff := cand_diff (L := L) (sbar := sbar) (h := h) (δ := δ) hh hsb
  rw [neg_div] at hdiff
  have hnum : L * δ * (2 * sbar + h + δ) ≤ 0 :=
    mul_nonpos_of_nonpos_of_nonneg (mul_nonpos_of_nonneg_of_nonpos hL.le hd') hbr.le
  have hden : (0:ℝ) < h * (sbar + h) := by positivity
  have hq := div_nonpos_of_nonpos_of_nonneg hnum hden.le
  linarith

/-! ## The withdrawn and re-minted values -/

/-- The per-liquidity value of the old range at the displaced price. -/
lemma phi_old (hh : 0 < h) (hsb : 0 < sbar - h) :
    phi (sbar + δ) (sbar - h) (sbar + h)
      = (2 * sbar * h + h ^ 2 + 2 * δ * h - δ ^ 2) / (sbar + h) := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have h10 : sbar + h ≠ 0 := h1.ne'
  unfold phi
  field_simp
  ring

/-- The per-liquidity value of the new, recentred range. -/
lemma phi_new (hh : 0 < h) (hsb : 0 < sbar - h) (hd : -h ≤ δ) :
    phi (sbar + δ) (sbar + δ - h) (sbar + δ + h)
      = h * (2 * (sbar + δ) + h) / (sbar + δ + h) := by
  have h2 : (0:ℝ) < sbar + δ + h := by linarith
  have h20 : sbar + δ + h ≠ 0 := h2.ne'
  unfold phi
  field_simp
  ring

/-! ## The two-branch amplitude -/

/-- The upper branch of the amplitude, for `0 ≤ δ ≤ h`. -/
noncomputable def ampUp (L sbar h δ : ℝ) : ℝ :=
  L * δ * (2 * sbar + h + δ) / (sbar + h)

/-- The lower branch of the amplitude, for `-h ≤ δ ≤ 0`. -/
noncomputable def ampDn (L sbar h δ : ℝ) : ℝ :=
  -(L * δ * (sbar + δ) * (2 * sbar + h + δ)) / ((sbar + h) * (sbar + h + δ))

/-- **Proposition (Two-Branch Amplitude), upper branch.** For a price above the
old midpoint, the value surrendered by the recentred rebalance is `ampUp`. -/
theorem amplitude_up (hL : 0 < L) (hh : 0 < h) (hsb : 0 < sbar - h)
    (hd : 0 ≤ δ) (hd' : δ ≤ h) :
    L * phi (sbar + δ) (sbar - h) (sbar + h)
        - Lnew L (sbar + δ) (sbar - h) (sbar + h) (sbar + δ - h) (sbar + δ + h)
          * phi (sbar + δ) (sbar + δ - h) (sbar + δ + h)
      = ampUp L sbar h δ := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have h2 : (0:ℝ) < sbar + δ + h := by linarith
  have hmin : Lnew L (sbar + δ) (sbar - h) (sbar + h) (sbar + δ - h)
      (sbar + δ + h) = cand0 L sbar h δ := by
    unfold Lnew
    rw [cand0_form hL hh hsb (by linarith) hd', cand1_form hh.ne']
    exact min_eq_left (cand0_le_cand1 hL hh hsb hd hd')
  have hh0 : h ≠ 0 := hh.ne'
  have h10 : sbar + h ≠ 0 := h1.ne'
  have h20 : sbar + δ + h ≠ 0 := h2.ne'
  rw [hmin, phi_old hh hsb, phi_new hh hsb (by linarith)]
  unfold cand0 ampUp
  field_simp
  ring

/-- **Proposition (Two-Branch Amplitude), lower branch.** For a price below the
old midpoint, the value surrendered is `ampDn`. -/
theorem amplitude_dn (hL : 0 < L) (hh : 0 < h) (hsb : 0 < sbar - h)
    (hd : -h ≤ δ) (hd' : δ ≤ 0) :
    L * phi (sbar + δ) (sbar - h) (sbar + h)
        - Lnew L (sbar + δ) (sbar - h) (sbar + h) (sbar + δ - h) (sbar + δ + h)
          * phi (sbar + δ) (sbar + δ - h) (sbar + δ + h)
      = ampDn L sbar h δ := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have h2 : (0:ℝ) < sbar + δ + h := by linarith
  have hmin : Lnew L (sbar + δ) (sbar - h) (sbar + h) (sbar + δ - h)
      (sbar + δ + h) = cand1 L h δ := by
    unfold Lnew
    rw [cand0_form hL hh hsb hd (by linarith), cand1_form hh.ne']
    exact min_eq_right (cand1_le_cand0 hL hh hsb hd hd')
  have hh0 : h ≠ 0 := hh.ne'
  have h10 : sbar + h ≠ 0 := h1.ne'
  have h20 : sbar + δ + h ≠ 0 := h2.ne'
  have hp1 : δ + sbar + h ≠ 0 := fun hc => h20 (by linarith)
  have hp2 : sbar + h + δ ≠ 0 := fun hc => h20 (by linarith)
  rw [hmin, phi_old hh hsb, phi_new hh hsb hd]
  unfold cand1 ampDn
  field_simp
  ring

/-- **Proposition (Two-Branch Amplitude), branch relation.** The lower branch is
the continued upper branch, in magnitude, times `s / sb'`. -/
theorem ampDn_eq_cont_mul (hh : 0 < h) (hsb : 0 < sbar - h)
    (hd : -h ≤ δ) (hd' : δ ≤ 0) :
    ampDn L sbar h δ
      = (-(ampUp L sbar h δ)) * ((sbar + δ) / (sbar + δ + h)) := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have h2 : (0:ℝ) < sbar + δ + h := by linarith
  have h10 : sbar + h ≠ 0 := h1.ne'
  have h20 : sbar + δ + h ≠ 0 := h2.ne'
  have hp1 : δ + sbar + h ≠ 0 := fun hc => h20 (by linarith)
  have hp2 : sbar + h + δ ≠ 0 := fun hc => h20 (by linarith)
  unfold ampDn ampUp
  field_simp
  ring

/-! ## The corners -/

/-- **Corollary (Corner Values), upper corner.** At the upper corner the mint is
empty and the amplitude is the whole position value `L w`. -/
theorem amplitude_corner_up (hh : 0 < h) (hsb : 0 < sbar - h) :
    ampUp L sbar h h = L * (2 * h) := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have h10 : sbar + h ≠ 0 := h1.ne'
  unfold ampUp
  field_simp
  ring

/-- **Corollary (Corner Values), lower corner.** At the lower corner the
amplitude is `L w` times the corner ratio `sa / sb`. -/
theorem amplitude_corner_dn (hh : 0 < h) (hsb : 0 < sbar - h) :
    ampDn L sbar h (-h) = L * (2 * h) * ((sbar - h) / (sbar + h)) := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have h3 : (0:ℝ) < sbar := by linarith
  have h10 : sbar + h ≠ 0 := h1.ne'
  have h30 : sbar ≠ 0 := h3.ne'
  unfold ampDn
  rw [show sbar + h + -h = sbar by ring, show sbar + -h = sbar - h by ring]
  field_simp
  ring

/-! ## The exact fractional slopes

The amplitude as a fraction of the position value at the old midpoint,
`V(sbar) = L h (2 sbar + h)/(sbar + h)`. -/

/-- The upper branch as a fraction of position value. -/
noncomputable def gUp (sbar h δ : ℝ) : ℝ :=
  δ * (2 * sbar + h + δ) / (h * (2 * sbar + h))

/-- The lower branch as a fraction of position value. -/
noncomputable def gDn (sbar h δ : ℝ) : ℝ :=
  -(δ * (sbar + δ) * (2 * sbar + h + δ)) / ((sbar + h + δ) * (h * (2 * sbar + h)))

/-- The fractional upper branch is the amplitude over the position value. -/
lemma gUp_eq (hL : 0 < L) (hh : 0 < h) (hsb : 0 < sbar - h) :
    ampUp L sbar h δ / (L * h * (2 * sbar + h) / (sbar + h)) = gUp sbar h δ := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have h4 : (0:ℝ) < 2 * sbar + h := by linarith
  have hh0 : h ≠ 0 := hh.ne'
  have hL0 : L ≠ 0 := hL.ne'
  have h10 : sbar + h ≠ 0 := h1.ne'
  have h40 : 2 * sbar + h ≠ 0 := h4.ne'
  unfold ampUp gUp
  field_simp

/-- The fractional lower branch is the amplitude over the position value. -/
lemma gDn_eq (hL : 0 < L) (hh : 0 < h) (hsb : 0 < sbar - h)
    (hd : -h ≤ δ) (hd' : δ ≤ 0) :
    ampDn L sbar h δ / (L * h * (2 * sbar + h) / (sbar + h)) = gDn sbar h δ := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have h2 : (0:ℝ) < sbar + δ + h := by linarith
  have h4 : (0:ℝ) < 2 * sbar + h := by linarith
  have hh0 : h ≠ 0 := hh.ne'
  have hL0 : L ≠ 0 := hL.ne'
  have h10 : sbar + h ≠ 0 := h1.ne'
  have h20 : sbar + δ + h ≠ 0 := h2.ne'
  have h40 : 2 * sbar + h ≠ 0 := h4.ne'
  have hp1 : δ + sbar + h ≠ 0 := fun hc => h20 (by linarith)
  have hp2 : sbar + h + δ ≠ 0 := fun hc => h20 (by linarith)
  unfold ampDn gDn
  rw [show sbar + h + δ = sbar + δ + h by ring]
  field_simp

/-- **Lemma (Exact Fractional Slopes), upper branch.** `g'(0⁺) = 1/h` exactly,
the position-value factors cancelling. -/
theorem hasDerivAt_gUp_zero (hh : 0 < h) (hsb : 0 < sbar - h) :
    HasDerivAt (fun z : ℝ => gUp sbar h z) (1 / h) 0 := by
  have h4 : (0:ℝ) < 2 * sbar + h := by linarith
  have hden : h * (2 * sbar + h) ≠ 0 := by positivity
  have hnum : HasDerivAt (fun z : ℝ => z * (2 * sbar + h + z)) (2 * sbar + h) 0 := by
    have ha : HasDerivAt (fun z : ℝ => z) 1 0 := hasDerivAt_id 0
    have hb : HasDerivAt (fun z : ℝ => 2 * sbar + h + z) 1 0 := by
      simpa using (hasDerivAt_id (0:ℝ)).const_add (2 * sbar + h)
    exact (ha.mul hb).congr_deriv (by ring)
  have hh0 : h ≠ 0 := hh.ne'
  have h40 : 2 * sbar + h ≠ 0 := h4.ne'
  have := hnum.div_const (h * (2 * sbar + h))
  refine this.congr_deriv ?_
  field_simp

/-- **Lemma (Exact Fractional Slopes), lower branch.** `g'(0⁻) = -(sbar/sb)(1/h)`
exactly, the boundary asymmetry factor appearing as the interior limit. -/
theorem hasDerivAt_gDn_zero (hh : 0 < h) (hsb : 0 < sbar - h) :
    HasDerivAt (fun z : ℝ => gDn sbar h z)
      (-(sbar / (sbar + h)) * (1 / h)) 0 := by
  have h1 : (0:ℝ) < sbar + h := by linarith
  have h3 : (0:ℝ) < sbar := by linarith
  have h4 : (0:ℝ) < 2 * sbar + h := by linarith
  have hnum : HasDerivAt (fun z : ℝ => -(z * (sbar + z) * (2 * sbar + h + z)))
      (-(sbar * (2 * sbar + h))) 0 := by
    have ha : HasDerivAt (fun z : ℝ => z) 1 0 := hasDerivAt_id 0
    have hb : HasDerivAt (fun z : ℝ => sbar + z) 1 0 := by
      simpa using (hasDerivAt_id (0:ℝ)).const_add sbar
    have hc : HasDerivAt (fun z : ℝ => 2 * sbar + h + z) 1 0 := by
      simpa using (hasDerivAt_id (0:ℝ)).const_add (2 * sbar + h)
    exact (((ha.mul hb).mul hc).neg).congr_deriv (by simp only [Pi.mul_apply]; ring)
  have hden : HasDerivAt (fun z : ℝ => (sbar + h + z) * (h * (2 * sbar + h)))
      (h * (2 * sbar + h)) 0 := by
    have hb : HasDerivAt (fun z : ℝ => sbar + h + z) 1 0 := by
      simpa using (hasDerivAt_id (0:ℝ)).const_add (sbar + h)
    exact (hb.mul_const (h * (2 * sbar + h))).congr_deriv (by ring)
  have hne : (sbar + h + 0) * (h * (2 * sbar + h)) ≠ 0 := by
    simp only [add_zero]; positivity
  have hh0 : h ≠ 0 := hh.ne'
  have h10 : sbar + h ≠ 0 := h1.ne'
  have h40 : 2 * sbar + h ≠ 0 := h4.ne'
  have := hnum.div hden hne
  refine this.congr_deriv ?_
  field_simp
  ring

end LocalTime
