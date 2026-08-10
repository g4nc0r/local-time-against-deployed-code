/-
Proposition (Leg Comparison), §The two legs compared.

The concavity leg of the dissipation identity runs at fractional rate about
`σ²/(2 s̄ h)` for a centred narrow range. Against the isolated-class floor
`2σ²/h²` the ratio is `4/ρ`; against the swap-mediated floor `η σ²/(4h²)` it is
`η/(2ρ)`. The comparison reverses across architectures, which is the practical
content of the architecture choice.

The two statements are exact ratio identities in the narrow-range parameter.
-/
import Mathlib

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

variable {σ sbar h η : ℝ}

/-- **Proposition (Leg Comparison), isolated class.** The isolated-class floor
exceeds the concavity leg by the factor `4/ρ`. -/
theorem leg_ratio_isolated (hσ : 0 < σ) (hs : 0 < sbar) (hh : 0 < h) :
    (2 * σ ^ 2 / h ^ 2) / (σ ^ 2 / (2 * sbar * h)) = 4 * sbar / h := by
  have hσ0 : σ ≠ 0 := hσ.ne'
  have hs0 : sbar ≠ 0 := hs.ne'
  have hh0 : h ≠ 0 := hh.ne'
  field_simp
  ring

/-- **Proposition (Leg Comparison), swap class.** The swap-mediated floor is
smaller than the concavity leg by the factor `η/(2ρ)`. -/
theorem leg_ratio_swap (hσ : 0 < σ) (hs : 0 < sbar) (hh : 0 < h) :
    (η * σ ^ 2 / (4 * h ^ 2)) / (σ ^ 2 / (2 * sbar * h)) = η * sbar / (2 * h) := by
  have hσ0 : σ ≠ 0 := hσ.ne'
  have hs0 : sbar ≠ 0 := hs.ne'
  have hh0 : h ≠ 0 := hh.ne'
  field_simp
  ring

/-- The two ratios in the narrow-range parameter `ρ = h/s̄`: the first is `4/ρ`,
the second `η/(2ρ)`. -/
theorem leg_ratios_in_rho (hs : 0 < sbar) (hh : 0 < h) :
    4 * sbar / h = 4 / (h / sbar) ∧ η * sbar / (2 * h) = η / (2 * (h / sbar)) := by
  have hs0 : sbar ≠ 0 := hs.ne'
  have hh0 : h ≠ 0 := hh.ne'
  constructor <;> field_simp

end LocalTime
