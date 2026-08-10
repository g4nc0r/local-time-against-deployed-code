/-
The verification scheme in discrete monitoring, §The fixed-width floor,
§The width-uniform floor, and Appendix "Proofs for the floors".

The paper's verification scheme runs Itô-Tanaka between impulses and telescopes.
Mathlib carries no stochastic integral, so that assembly is out of reach. It is
also not needed: for a quadratic verification function the second-order
expansion is exact, with no remainder, so the whole argument goes through
pathwise on a discretely monitored trajectory with nothing but finite sums.

This file proves that pathwise inequality and instantiates it at both
verification functions of the paper. The result is a genuine floor theorem, not
merely the corridor inequality: every discretely monitored policy pays, over any
horizon, at least the verification constant times the realised quadratic
variation, less a boundary term and the accumulated drift pairing.

Deployed operators monitor on a keeper cadence, so the discrete statement is
closer to the object than the continuous one; the paper's own monitoring section
treats continuous monitoring as the idealisation. The continuous statement
remains unformalised and is recorded as such in the README.

The trajectory is presented as three sequences. `pre t` is the state entering
step `t`, `post t` the state leaving it, and `k t` the kerf paid by the impulse
between step `t` and step `t + 1`. A step with no impulse is the case
`pre (t+1) = post t`, which costs nothing and is admitted with `k t = 0`.
-/
import LocalTime.Corridor
import LocalTime.SwapFloor

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

variable {A m h : ℝ} {n : ℕ} {pre post k : ℕ → ℝ}

/-! ## The quadratic verification function -/

/-- A quadratic verification function `U(x) = A (x - m)²`, whose second
derivative is the constant `2A`. -/
noncomputable def Uquad (A m x : ℝ) : ℝ := A * (x - m) ^ 2

/-- Its derivative. -/
noncomputable def Uquad' (A m x : ℝ) : ℝ := 2 * A * (x - m)

/-- **The exact step expansion.** For a quadratic verification function the
second-order Taylor expansion is an identity, with no remainder. This is what
replaces the Itô step: the drift pairing and the quadratic-variation term
appear with no error, on every path. -/
lemma Uquad_step (A m x y : ℝ) :
    Uquad A m y - Uquad A m x = Uquad' A m x * (y - x) + A * (y - x) ^ 2 := by
  unfold Uquad Uquad'
  ring

/-! ## The pathwise verification inequality -/

/-- **The discrete verification inequality.** Along any finite trajectory whose
impulses satisfy the impulse inequality, the accumulated drift pairing plus `A`
times the realised quadratic variation is at most the accumulated kerf plus the
boundary term. Every quantity here is pathwise; no expectation is taken. -/
theorem discrete_verification (A m : ℝ) (n : ℕ) (pre post k : ℕ → ℝ)
    (himp : ∀ t < n, Uquad A m (post t) - Uquad A m (pre (t + 1)) ≤ k t) :
    (∑ t ∈ Finset.range n, Uquad' A m (pre t) * (post t - pre t))
        + A * ∑ t ∈ Finset.range n, (post t - pre t) ^ 2
      ≤ (∑ t ∈ Finset.range n, k t)
          + (Uquad A m (pre n) - Uquad A m (pre 0)) := by
  -- the step expansion, summed
  have hexp : ∑ t ∈ Finset.range n,
      (Uquad A m (post t) - Uquad A m (pre t))
      = (∑ t ∈ Finset.range n, Uquad' A m (pre t) * (post t - pre t))
          + A * ∑ t ∈ Finset.range n, (post t - pre t) ^ 2 := by
    rw [Finset.mul_sum, ← Finset.sum_add_distrib]
    exact Finset.sum_congr rfl fun t _ => Uquad_step A m (pre t) (post t)
  -- the telescoping split
  have hsplit : ∑ t ∈ Finset.range n, (Uquad A m (post t) - Uquad A m (pre t))
      = (∑ t ∈ Finset.range n, (Uquad A m (post t) - Uquad A m (pre (t + 1))))
          + (Uquad A m (pre n) - Uquad A m (pre 0)) := by
    have htel : ∑ t ∈ Finset.range n,
        (Uquad A m (pre (t + 1)) - Uquad A m (pre t))
        = Uquad A m (pre n) - Uquad A m (pre 0) :=
      Finset.sum_range_sub (fun t => Uquad A m (pre t)) n
    rw [← htel, ← Finset.sum_add_distrib]
    exact Finset.sum_congr rfl fun t _ => by ring
  have hbound : ∑ t ∈ Finset.range n,
      (Uquad A m (post t) - Uquad A m (pre (t + 1)))
      ≤ ∑ t ∈ Finset.range n, k t := by
    apply Finset.sum_le_sum
    intro t ht
    exact himp t (Finset.mem_range.mp ht)
  rw [← hexp, hsplit]
  linarith

/-- **The discrete floor.** If the drift pairing is non-negative, which is what
the martingale hypothesis of the continuous argument supplies, the accumulated
kerf is at least `A` times the realised quadratic variation, less the boundary
term. -/
theorem discrete_floor (A m : ℝ) (n : ℕ) (pre post k : ℕ → ℝ)
    (himp : ∀ t < n, Uquad A m (post t) - Uquad A m (pre (t + 1)) ≤ k t)
    (hdrift : 0 ≤ ∑ t ∈ Finset.range n, Uquad' A m (pre t) * (post t - pre t)) :
    A * (∑ t ∈ Finset.range n, (post t - pre t) ^ 2)
        - (Uquad A m (pre n) - Uquad A m (pre 0))
      ≤ ∑ t ∈ Finset.range n, k t := by
  have := discrete_verification A m n pre post k himp
  linarith

/-- **The floor in rate form.** With a per-step lower bound `σ₀²` on the
realised quadratic increment, the accumulated kerf over `n` steps is at least
`A σ₀² n` less the boundary term, so the rate per step is at least `A σ₀²`. -/
theorem discrete_floor_rate (A m σ₀ : ℝ) (hA : 0 ≤ A) (n : ℕ)
    (pre post k : ℕ → ℝ)
    (himp : ∀ t < n, Uquad A m (post t) - Uquad A m (pre (t + 1)) ≤ k t)
    (hdrift : 0 ≤ ∑ t ∈ Finset.range n, Uquad' A m (pre t) * (post t - pre t))
    (hstep : ∀ t < n, σ₀ ^ 2 ≤ (post t - pre t) ^ 2) :
    A * σ₀ ^ 2 * n - (Uquad A m (pre n) - Uquad A m (pre 0))
      ≤ ∑ t ∈ Finset.range n, k t := by
  have hqv : (σ₀ ^ 2) * n ≤ ∑ t ∈ Finset.range n, (post t - pre t) ^ 2 := by
    have : ∑ _t ∈ Finset.range n, σ₀ ^ 2 ≤ ∑ t ∈ Finset.range n,
        (post t - pre t) ^ 2 := by
      apply Finset.sum_le_sum
      intro t ht
      exact hstep t (Finset.mem_range.mp ht)
    simpa [Finset.sum_const, nsmul_eq_mul, mul_comm] using this
  have hmul : A * (σ₀ ^ 2 * n) ≤ A * ∑ t ∈ Finset.range n, (post t - pre t) ^ 2 :=
    mul_le_mul_of_nonneg_left hqv hA
  have := discrete_floor A m n pre post k himp hdrift
  nlinarith

/-! ## The fixed-width instantiation

`U(δ) = 2δ²/h²` is `Uquad (2/h²) 0`, and its impulse inequality against the
narrow-limit potentials is `fixed_impulse_inequality`. The floor constant that
emerges is the tangency constant: the rate is `2 σ₀²/h²`. -/

lemma Ufix_eq_Uquad (h δ : ℝ) : Ufix h δ = Uquad (2 / h ^ 2) 0 δ := by
  unfold Ufix Uquad
  ring

/-- **The fixed-width discrete floor.** Every discretely monitored policy of the
isolated class, whose impulses are priced by the narrow-limit placement
potentials, pays at least `2/h²` times its realised quadratic variation, less
the boundary term. -/
theorem fixed_width_discrete_floor (hh : 0 < h) (n : ℕ) (pre post k : ℕ → ℝ)
    (hpre : ∀ t, -h < pre t ∧ pre t < h)
    (hpost : ∀ t, -h < post t ∧ post t < h)
    (hk : ∀ t < n, max (Cup0 h (post t) - Cup0 h (pre (t + 1)))
        (Cdn0 h (post t) - Cdn0 h (pre (t + 1))) ≤ k t)
    (hdrift : 0 ≤ ∑ t ∈ Finset.range n,
      Uquad' (2 / h ^ 2) 0 (pre t) * (post t - pre t)) :
    (2 / h ^ 2) * (∑ t ∈ Finset.range n, (post t - pre t) ^ 2)
        - (Uquad (2 / h ^ 2) 0 (pre n) - Uquad (2 / h ^ 2) 0 (pre 0))
      ≤ ∑ t ∈ Finset.range n, k t := by
  refine discrete_floor (2 / h ^ 2) 0 n pre post k ?_ hdrift
  intro t ht
  have himp := fixed_impulse_inequality hh (hpost t).1 (hpost t).2
    (hpre (t + 1)).1 (hpre (t + 1)).2
  rw [← Ufix_eq_Uquad, ← Ufix_eq_Uquad]
  exact le_trans himp (hk t ht)

/-! ## The share-coordinate instantiation

`U(ω) = 8(ω - 1/2)²` is `Uquad 8 (1/2)`, and its impulse inequality against the
exact share potentials of Theorem 2 is `share_impulse_inequality`, which holds
at every width with no narrow-limit correction. -/

lemma Ushare_eq_Uquad (ω : ℝ) : Ushare ω = Uquad 8 (1 / 2) ω := rfl

/-- **The width-uniform discrete floor.** Every discretely monitored policy,
whose impulses are priced by the exact share potentials of Theorem 2, pays at
least `8` times the realised quadratic variation of its holdings share, less the
boundary term. The statement is exact at every width. -/
theorem width_uniform_discrete_floor (n : ℕ) (pre post k : ℕ → ℝ)
    (hpre : ∀ t, 0 < pre t ∧ pre t < 1)
    (hpost : ∀ t, 0 < post t ∧ post t < 1)
    (hk : ∀ t < n, max (Real.log (pre (t + 1) / post t))
        (Real.log ((1 - pre (t + 1)) / (1 - post t))) ≤ k t)
    (hdrift : 0 ≤ ∑ t ∈ Finset.range n,
      Uquad' 8 (1 / 2) (pre t) * (post t - pre t)) :
    8 * (∑ t ∈ Finset.range n, (post t - pre t) ^ 2)
        - (Uquad 8 (1 / 2) (pre n) - Uquad 8 (1 / 2) (pre 0))
      ≤ ∑ t ∈ Finset.range n, k t := by
  refine discrete_floor 8 (1 / 2) n pre post k ?_ hdrift
  intro t ht
  have himp := share_impulse_inequality (hpost t).1 (hpost t).2
    (hpre (t + 1)).1 (hpre (t + 1)).2
  rw [← Ushare_eq_Uquad, ← Ushare_eq_Uquad]
  exact le_trans himp (hk t ht)

/-- **The tangency constant, in rate form.** At the fixed width, with a per-step
quadratic increment of at least `σ₀²`, the accumulated kerf over `n` steps is at
least `2 σ₀² n / h²` less the boundary term. This is the paper's floor
`r ≥ 2 σ_s²/h²` with the continuous clock replaced by the realised one. -/
theorem tangency_constant_rate (hh : 0 < h) (σ₀ : ℝ) (n : ℕ) (pre post k : ℕ → ℝ)
    (hpre : ∀ t, -h < pre t ∧ pre t < h)
    (hpost : ∀ t, -h < post t ∧ post t < h)
    (hk : ∀ t < n, max (Cup0 h (post t) - Cup0 h (pre (t + 1)))
        (Cdn0 h (post t) - Cdn0 h (pre (t + 1))) ≤ k t)
    (hdrift : 0 ≤ ∑ t ∈ Finset.range n,
      Uquad' (2 / h ^ 2) 0 (pre t) * (post t - pre t))
    (hstep : ∀ t < n, σ₀ ^ 2 ≤ (post t - pre t) ^ 2) :
    2 * σ₀ ^ 2 * n / h ^ 2
        - (Uquad (2 / h ^ 2) 0 (pre n) - Uquad (2 / h ^ 2) 0 (pre 0))
      ≤ ∑ t ∈ Finset.range n, k t := by
  have hA : (0:ℝ) ≤ 2 / h ^ 2 := by positivity
  have himp : ∀ t < n, Uquad (2 / h ^ 2) 0 (post t)
      - Uquad (2 / h ^ 2) 0 (pre (t + 1)) ≤ k t := by
    intro t ht
    have h1 := fixed_impulse_inequality hh (hpost t).1 (hpost t).2
      (hpre (t + 1)).1 (hpre (t + 1)).2
    rw [← Ufix_eq_Uquad, ← Ufix_eq_Uquad]
    exact le_trans h1 (hk t ht)
  have := discrete_floor_rate (2 / h ^ 2) 0 σ₀ hA n pre post k himp hdrift hstep
  have heq : 2 / h ^ 2 * σ₀ ^ 2 * n = 2 * σ₀ ^ 2 * n / h ^ 2 := by ring
  linarith [heq ▸ this]

/-! ## The swap-class instantiation

For the swap class the impulse inequality is `swap_impulse_inequality`, and the
verification constant is the floor constant `A` of the swap sandwich. The
statement needs no width hypothesis and no narrow limit. -/

/-- **The swap-mediated discrete floor.** Every discretely monitored policy of
the swap class pays at least `A` times the realised quadratic variation of its
holdings share, less the boundary term, where `A` is the floor constant of the
swap sandwich. -/
theorem swap_discrete_floor (A : ℝ) (hA : 0 ≤ A) (n : ℕ) (pre post k : ℕ → ℝ)
    (hpre : ∀ t, 0 ≤ pre t ∧ pre t ≤ 1)
    (hpost : ∀ t, 0 ≤ post t ∧ post t ≤ 1)
    (hk : ∀ t < n, A * (|post t - pre (t + 1)|
        * (1 - |post t - pre (t + 1)|)) ≤ k t)
    (hdrift : 0 ≤ ∑ t ∈ Finset.range n,
      Uquad' A (1 / 2) (pre t) * (post t - pre t)) :
    A * (∑ t ∈ Finset.range n, (post t - pre t) ^ 2)
        - (Uquad A (1 / 2) (pre n) - Uquad A (1 / 2) (pre 0))
      ≤ ∑ t ∈ Finset.range n, k t := by
  refine discrete_floor A (1 / 2) n pre post k ?_ hdrift
  intro t ht
  have himp := swap_impulse_inequality hA (hpost t).1 (hpost t).2
    (hpre (t + 1)).1 (hpre (t + 1)).2
  exact le_trans himp (hk t ht)

end LocalTime
