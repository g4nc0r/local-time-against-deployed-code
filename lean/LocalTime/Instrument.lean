/-
Theorem (Small-Delay Identification) and the estimator's debiasing,
§Identification, §Estimators and the bias budget, and Appendix "Estimator
definitions".

The instrument's identification argument has a probabilistic half, the two
branch estimates (the diffusive branch cannot manufacture large overshoots at
small delay; the jump branch fails the cut only on a tail event), and a
deterministic half, the assembly of those two estimates into the signed bracket
of the bias budget. The deterministic half is formalised here, together with the
algebraic inversion that turns the measured exceedance fraction into the jump
share by subtracting the folded-normal baseline.

The branch estimates themselves, the folded-normal kernel, the flat-entry delay
law, and Owen's `T` identity of the exact-reproduction proposition are not
formalised; they need Gaussian first-passage machinery that mathlib does not
carry in the form the paper uses. The README records this.
-/
import Mathlib

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

variable {pc pJ ec eJ e1 e2 E q p : ℝ}

/-- **Theorem (Small-Delay Identification), the bracket assembly.** Given the
two-branch mixture of the instrument response, a diffusive-branch exceedance
bounded by the leakage term and a jump-branch exceedance failing only on the
resolution-floor tail, the measured exceedance functional brackets the
small-delay jump share by the sum of the two terms. -/
theorem exceedance_bracket (hpc : 0 ≤ pc) (hpJ : 0 ≤ pJ) (hsum : pc + pJ = 1)
    (hec0 : 0 ≤ ec) (hec : ec ≤ e1) (heJ1 : eJ ≤ 1) (heJ : 1 - e2 ≤ eJ)
    (he1 : 0 ≤ e1) (he2 : 0 ≤ e2) :
    |pc * ec + pJ * eJ - pJ| ≤ e1 + pJ * e2 := by
  rw [abs_le]
  constructor
  · nlinarith
  · nlinarith

/-- **The estimator's debiasing.** If the measured exceedance fraction is the
jump share plus the folded-normal baseline on the complementary mass, the jump
share is recovered by subtracting the baseline and renormalising. This is the
`π̂_J` of the estimator definitions. -/
theorem jump_share_inversion (hq : q ≠ 1) (h : E = p + (1 - p) * q) :
    p = (E - q) / (1 - q) := by
  have hq1 : (1:ℝ) - q ≠ 0 := by intro hc; apply hq; linarith
  rw [h]
  field_simp
  ring

/-- The inversion is monotone in the measured fraction, so a conservative
measurement gives a conservative jump share. -/
theorem jump_share_inversion_mono (hq : q < 1) {E₁ E₂ : ℝ} (h : E₁ ≤ E₂) :
    (E₁ - q) / (1 - q) ≤ (E₂ - q) / (1 - q) := by
  rw [div_le_div_iff_of_pos_right (by linarith : (0:ℝ) < 1 - q)]
  linarith

end LocalTime
