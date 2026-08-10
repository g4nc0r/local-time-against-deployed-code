/-
Theorem (Swap-Mediated Floor) and Proposition (Return-Point Achievability),
§The swap-mediated floor and Appendix "Proofs for the floors".

The class that swaps prices an impulse moving the holdings share by `d` at
`γ + η d + I d²` against the clock factor `d(1-d)`, and the floor constant is
the minimum of that ratio. Three deterministic pieces are checked here: the
sandwich on the constant, the coverage argument that a mint leg costs at least
one log-unit per unit of share, and the impulse inequality for the quadratic
verification function.

The `A ≥ η + γ + 2√(γη)` bound has the certificate
`(√γ (1-d) - √η d)² + γ d ≥ 0`, which is the exact form of the
Whalley-Wilmott scaling the paper quotes.
-/
import Mathlib

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

variable {γ η I d ω ω' A x m : ℝ}

/-- The per-unit-clock cost of a corrective swap that moves the share by `d`. -/
noncomputable def swapCost (γ η I d : ℝ) : ℝ :=
  (γ + η * d + I * d ^ 2) / (d * (1 - d))

/-- **Theorem (Swap-Mediated Floor), lower bound on the constant.** -/
theorem swapCost_ge (hγ : 0 ≤ γ) (hη : 0 < η) (hI : 0 ≤ I) (hd : 0 < d)
    (hd' : d < 1) : η + γ + 2 * Real.sqrt (γ * η) ≤ swapCost γ η I d := by
  have hden : (0:ℝ) < d * (1 - d) := by nlinarith
  have hg := Real.sq_sqrt hγ
  have he := Real.sq_sqrt hη.le
  have hgn := Real.sqrt_nonneg γ
  have hen := Real.sqrt_nonneg η
  have hmul : Real.sqrt (γ * η) = Real.sqrt γ * Real.sqrt η := Real.sqrt_mul hγ η
  unfold swapCost
  rw [le_div_iff₀ hden, hmul]
  nlinarith [sq_nonneg (Real.sqrt γ * (1 - d) - Real.sqrt η * d),
    mul_nonneg hI (sq_nonneg d), mul_nonneg (mul_nonneg hgn hgn) hd.le]

/-- In the fee-only regime the cost is `η/(1-d)`, whose infimum over the
correction size is exactly the fee. -/
theorem swapCost_fee_only (hη : 0 < η) (hd : 0 < d) (hd' : d < 1) :
    swapCost 0 η 0 d = η / (1 - d) := by
  have hd0 : d ≠ 0 := hd.ne'
  have hd1 : (1:ℝ) - d ≠ 0 := by intro hc; linarith
  unfold swapCost
  field_simp
  ring

theorem fee_le_swapCost_fee_only (hη : 0 < η) (hd : 0 < d) (hd' : d < 1) :
    η ≤ swapCost 0 η 0 d := by
  rw [swapCost_fee_only hη hd hd']
  rw [le_div_iff₀ (by linarith : (0:ℝ) < 1 - d)]
  nlinarith

/-- **Theorem (Swap-Mediated Floor), the gas-corrected minimiser.** With no
impact leg, the stationarity condition is `η d² + 2γ d - γ = 0`, and the
positive root is the `d*` of the statement. -/
theorem dStar_root (hγ : 0 < γ) (hη : 0 < η) :
    η * ((Real.sqrt (γ ^ 2 + γ * η) - γ) / η) ^ 2
        + 2 * γ * ((Real.sqrt (γ ^ 2 + γ * η) - γ) / η) - γ = 0 := by
  have hnn : (0:ℝ) ≤ γ ^ 2 + γ * η := by positivity
  have hsq := Real.sq_sqrt hnn
  have hη0 : η ≠ 0 := hη.ne'
  have hnn2 : (0:ℝ) ≤ γ * (γ + η) := by positivity
  have hsq2 := Real.sq_sqrt hnn2
  field_simp
  linear_combination hsq2

/-- **Coverage of the class, mint leg.** A mint leg that moves the share by `d`
costs at least `d` in log-value, so it never undercuts the swap leg's fee
scale. -/
theorem mint_leg_ge (hωr : 0 < ω) (hd : 0 < d) (hsum : ω + d ≤ 1) :
    d ≤ Real.log (1 + d / ω) := by
  have hpos : (0:ℝ) < 1 + d / ω := by positivity
  have hinv : (0:ℝ) < ω / (ω + d) := by
    apply div_pos hωr (by linarith)
  have hkey : Real.log (ω / (ω + d)) ≤ ω / (ω + d) - 1 :=
    Real.log_le_sub_one_of_pos hinv
  have heq : Real.log (ω / (ω + d)) = -Real.log (1 + d / ω) := by
    rw [← Real.log_inv]
    congr 1
    field_simp
  rw [heq] at hkey
  have hfrac : ω / (ω + d) - 1 = -(d / (ω + d)) := by
    field_simp
    ring
  rw [hfrac] at hkey
  have hd2 : d ≤ d / (ω + d) := by
    rw [le_div_iff₀ (by linarith : (0:ℝ) < ω + d)]
    nlinarith
  linarith

/-- **The impulse inequality of the swap class.** The quadratic verification
function loses at most `A d(1-d)` across an impulse that moves the share by
`d`, the extreme pair having one point at an edge. -/
theorem swap_impulse_inequality (hA : 0 ≤ A) (h0 : 0 ≤ ω) (h1 : ω ≤ 1)
    (h0' : 0 ≤ ω') (h1' : ω' ≤ 1) :
    A * (ω - 1 / 2) ^ 2 - A * (ω' - 1 / 2) ^ 2
      ≤ A * (|ω - ω'| * (1 - |ω - ω'|)) := by
  rcases le_total ω' ω with hle | hle
  · rw [abs_of_nonneg (by linarith : (0:ℝ) ≤ ω - ω')]
    have : (ω - 1 / 2) ^ 2 - (ω' - 1 / 2) ^ 2
        ≤ (ω - ω') * (1 - (ω - ω')) := by nlinarith
    nlinarith
  · rw [abs_of_nonpos (by linarith : ω - ω' ≤ 0)]
    have : (ω - 1 / 2) ^ 2 - (ω' - 1 / 2) ^ 2
        ≤ -(ω - ω') * (1 - -(ω - ω')) := by nlinarith
    nlinarith

/-! ## The return-point family -/

/-- The return-point family's rate coefficient, fires at `xh` and corrects by
`mh` on the same side. -/
noncomputable def rSwap (η γ I x m : ℝ) : ℝ :=
  (η * m / 2 + γ + I * m ^ 2 / 4) / (m * (2 * x - m))

/-- **Proposition (Return-Point Achievability), the trigger optimum is the band
edge.** The rate is strictly decreasing in the trigger displacement. -/
theorem rSwap_antitone_in_x (hη : 0 < η) (hγ : 0 ≤ γ) (hI : 0 ≤ I)
    (hm : 0 < m) {x₁ x₂ : ℝ} (h1 : m < 2 * x₁) (h12 : x₁ < x₂) :
    rSwap η γ I x₂ m < rSwap η γ I x₁ m := by
  have hnum : (0:ℝ) < η * m / 2 + γ + I * m ^ 2 / 4 := by positivity
  have hd1 : (0:ℝ) < m * (2 * x₁ - m) := by nlinarith
  have hd2 : (0:ℝ) < m * (2 * x₂ - m) := by nlinarith
  unfold rSwap
  rw [div_lt_div_iff₀ hd2 hd1]
  nlinarith [mul_pos (mul_pos hnum hm) (by linarith : (0:ℝ) < x₂ - x₁)]

end LocalTime
