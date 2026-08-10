/-
Proposition (Jump Surcharge), §The jump surcharge and Appendix "Proofs for the
floors".

A jump fires the trigger from beyond the line, so every crossing it causes is
settled at a deeper displacement than the same policy would have paid
diffusively, and the placement potentials price the difference exactly. Three
deterministic statements carry the proposition: the per-event cost difference
telescopes through the potentials so that the return point cancels, positivity
is the strict monotonicity of the upward potential, and in the narrow limit the
increment is a log ratio bounded below by the straddle depth over the
half-width.

The expectation over the straddle law and the multiplication by the
jump-crossing rate are the probabilistic wrapper and are not formalised.
-/
import LocalTime.Corridor

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

variable {s h a v r : ℝ}

/-- **Proposition (Jump Surcharge), the return point cancels.** The difference
between the jump-shifted and the diffusive per-event cost telescopes through the
upward potential, and the return displacement `r` drops out. -/
theorem surcharge_telescopes (s h a v r : ℝ) :
    (Cup s h (a + v) - Cup s h r) - (Cup s h a - Cup s h r)
      = Cup s h (a + v) - Cup s h a := by
  ring

/-- **Proposition (Jump Surcharge), positivity.** The surcharge is
non-negative, and strictly positive for a strictly positive straddle depth,
because the upward potential is strictly increasing. -/
theorem surcharge_nonneg (hs : 0 < s) (hh : 0 < h) (hv : 0 ≤ v)
    (ha : -h < a) (hav : a + v < h) :
    0 ≤ Cup s h (a + v) - Cup s h a := by
  rcases eq_or_lt_of_le hv with heq | hlt
  · rw [← heq]; simp
  · have hmem : a ∈ Set.Ioo (-h) h := ⟨ha, by linarith⟩
    have hmem' : a + v ∈ Set.Ioo (-h) h := ⟨by linarith, hav⟩
    have := strictMonoOn_Cup hs hh hmem hmem' (by linarith)
    linarith

theorem surcharge_pos (hs : 0 < s) (hh : 0 < h) (hv : 0 < v)
    (ha : -h < a) (hav : a + v < h) :
    0 < Cup s h (a + v) - Cup s h a := by
  have hmem : a ∈ Set.Ioo (-h) h := ⟨ha, by linarith⟩
  have hmem' : a + v ∈ Set.Ioo (-h) h := ⟨by linarith, hav⟩
  have := strictMonoOn_Cup hs hh hmem hmem' (by linarith)
  linarith

/-- The narrow-limit surcharge is the log ratio of the two residual distances to
the range bound. -/
theorem surcharge_narrow_eq (hh : 0 < h) (ha : a < h) (hav : a + v < h) :
    Cup0 h (a + v) - Cup0 h a = Real.log ((h - a) / (h - a - v)) := by
  have h1 : (0:ℝ) < h - a := by linarith
  have h2 : (0:ℝ) < h - (a + v) := by linarith
  unfold Cup0
  rw [Real.log_div h1.ne' (by intro hc; apply h2.ne'; linarith)]
  have : h - (a + v) = h - a - v := by ring
  rw [this]
  ring

/-- The elementary bound `v/A ≤ log(A/(A - v))`, the source of the surcharge's
lower bound `E[O_J]/h`. -/
theorem log_ratio_ge (hv : 0 < v) (hA : v < a) (ha : 0 < a) :
    v / a ≤ Real.log (a / (a - v)) := by
  have hAv : (0:ℝ) < a - v := by linarith
  have hkey : Real.log ((a - v) / a) ≤ (a - v) / a - 1 :=
    Real.log_le_sub_one_of_pos (by positivity)
  have heq : Real.log ((a - v) / a) = -Real.log (a / (a - v)) := by
    rw [← Real.log_inv]
    congr 1
    rw [inv_div]
  rw [heq] at hkey
  have : (a - v) / a - 1 = -(v / a) := by
    field_simp
    ring
  rw [this] at hkey
  linarith

/-- **Proposition (Jump Surcharge), the narrow-limit lower bound.** Every jump
crossing pays at least its straddle depth over the half-width, in log value, on
top of everything the diffusive floor already charges. -/
theorem surcharge_narrow_ge (hh : 0 < h) (hv : 0 < v) (ha0 : 0 ≤ a)
    (hav : a + v < h) :
    v / h ≤ Cup0 h (a + v) - Cup0 h a := by
  have h1 : (0:ℝ) < h - a := by linarith
  rw [surcharge_narrow_eq hh (by linarith) hav]
  have hb := log_ratio_ge (v := v) (a := h - a) hv (by linarith) h1
  have hmono : v / h ≤ v / (h - a) := by
    apply div_le_div_of_nonneg_left hv.le h1
    linarith
  have : h - a - v = (h - a) - v := by ring
  rw [this]
  linarith

end LocalTime
