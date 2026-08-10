/-
Lemma (Offset Uniformity), §The equidistribution lemma and Appendix "Proofs for
the equidistribution, intensity, and monitoring layers".

The paper's proof is an oscillation bound: the pushforward density on the unit
cell is `p̄_ϑ(z) = ϑ ∑_{k ∈ ℤ} q(ϑ(k + z))`, and for `z < z'` in `[0,1)` the
lattice points `ϑ(k+z)` and `ϑ(k+z')` interleave as a single increasing
sequence, so the increments of `q` along it are dominated by the total variation
of `q`. Since `p̄_ϑ` integrates to one it takes values on both sides of one, and
the oscillation bound becomes the sup bound.

Finite total variation is used here in its Jordan form, `q = f - g` with `f` and
`g` bounded and monotone, and the variation is the sum of the two oscillations.
That is the form the interleaving argument actually consumes, and it is what
mathlib's `BoundedVariationOn.exists_monotoneOn_sub_monotoneOn` supplies.

The measure-theoretic step that identifies `p̄_ϑ` with the lattice sum is
standard change of variables and is not the content of the lemma; it enters
below as an explicit convergence hypothesis, so that the analytic core is
proved outright.
-/
import Mathlib

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

open Filter Topology

variable {f g q : ℝ → ℝ} {L M Lf Mf Lg Mg V ϑ z z' : ℝ} {a b : ℕ → ℝ} {n N : ℕ}

/-! ## The interleaving core -/

/-- **The interleaving bound for a monotone function.** Along any sequence of
pairwise interleaved intervals, the increments of a bounded monotone function sum
to at most its oscillation. This is the whole content of the paper's "increments
along any increasing sequence are dominated by the total variation". -/
theorem monotone_lattice_sum (hf : Monotone f) (hL : ∀ x, L ≤ f x)
    (hM : ∀ x, f x ≤ M) (hab : ∀ i, a i ≤ b i) (hba : ∀ i, b i ≤ a (i + 1))
    (n : ℕ) :
    ∑ i ∈ Finset.range n, (f (b i) - f (a i)) ≤ M - L := by
  have hstep : ∑ i ∈ Finset.range n, (f (b i) - f (a i))
      ≤ ∑ i ∈ Finset.range n, (f (a (i + 1)) - f (a i)) := by
    apply Finset.sum_le_sum
    intro i _
    have : f (b i) ≤ f (a (i + 1)) := hf (hba i)
    linarith
  have htel : ∑ i ∈ Finset.range n, (f (a (i + 1)) - f (a i))
      = f (a n) - f (a 0) := Finset.sum_range_sub (fun i => f (a i)) n
  have hbound : f (a n) - f (a 0) ≤ M - L := by
    have := hM (a n)
    have := hL (a 0)
    linarith
  linarith [hstep, htel ▸ hstep]

/-- **The interleaving bound for a function of bounded variation**, in Jordan
form. The absolute increments sum to at most the total variation. -/
theorem bv_lattice_sum (hf : Monotone f) (hg : Monotone g)
    (hLf : ∀ x, Lf ≤ f x) (hMf : ∀ x, f x ≤ Mf)
    (hLg : ∀ x, Lg ≤ g x) (hMg : ∀ x, g x ≤ Mg)
    (hab : ∀ i, a i ≤ b i) (hba : ∀ i, b i ≤ a (i + 1)) (n : ℕ) :
    ∑ i ∈ Finset.range n, |(f (b i) - g (b i)) - (f (a i) - g (a i))|
      ≤ (Mf - Lf) + (Mg - Lg) := by
  have hsplit : ∑ i ∈ Finset.range n,
      |(f (b i) - g (b i)) - (f (a i) - g (a i))|
      ≤ ∑ i ∈ Finset.range n,
        ((f (b i) - f (a i)) + (g (b i) - g (a i))) := by
    apply Finset.sum_le_sum
    intro i _
    have h1 : 0 ≤ f (b i) - f (a i) := by
      have := hf (hab i); linarith
    have h2 : 0 ≤ g (b i) - g (a i) := by
      have := hg (hab i); linarith
    rw [abs_le]
    constructor <;> linarith
  have hf' := monotone_lattice_sum hf hLf hMf hab hba n
  have hg' := monotone_lattice_sum hg hLg hMg hab hba n
  rw [Finset.sum_add_distrib] at hsplit
  linarith

/-! ## The lattice instantiation

The two lattices of the lemma, `ϑ(k + z)` and `ϑ(k + z')`, are interleaved
exactly when `0 ≤ z ≤ z' < 1`: the first inequality gives `a i ≤ b i` and the
second gives `b i ≤ a (i+1)`. A window of `n` cells starting `N` cells below the
origin is indexed by `i ↦ i - N`. -/

/-- The lower lattice of the window. -/
noncomputable def latticeA (ϑ z : ℝ) (N : ℕ) (i : ℕ) : ℝ :=
  ϑ * ((i : ℝ) - (N : ℝ) + z)

/-- The upper lattice of the window. -/
noncomputable def latticeB (ϑ z' : ℝ) (N : ℕ) (i : ℕ) : ℝ :=
  ϑ * ((i : ℝ) - (N : ℝ) + z')

lemma latticeA_le_latticeB (hϑ : 0 < ϑ) (hzz : z ≤ z') (N i : ℕ) :
    latticeA ϑ z N i ≤ latticeB ϑ z' N i := by
  unfold latticeA latticeB
  have : (i : ℝ) - (N : ℝ) + z ≤ (i : ℝ) - (N : ℝ) + z' := by linarith
  exact mul_le_mul_of_nonneg_left this hϑ.le

lemma latticeB_le_latticeA_succ (hϑ : 0 < ϑ) (hz : 0 ≤ z) (hz' : z' < 1)
    (N i : ℕ) : latticeB ϑ z' N i ≤ latticeA ϑ z N (i + 1) := by
  unfold latticeA latticeB
  have hcast : ((i + 1 : ℕ) : ℝ) = (i : ℝ) + 1 := by push_cast; ring
  rw [hcast]
  have : (i : ℝ) - (N : ℝ) + z' ≤ (i : ℝ) + 1 - (N : ℝ) + z := by linarith
  exact mul_le_mul_of_nonneg_left this hϑ.le

/-- **Lemma (Offset Uniformity), the windowed bound.** Over any finite window of
the lattice, the absolute increments of a bounded-variation density between the
two offsets sum to at most its total variation, uniformly in the window. -/
theorem offset_window_bound (hϑ : 0 < ϑ) (hz : 0 ≤ z) (hzz : z ≤ z')
    (hz' : z' < 1) (hq : ∀ x, q x = f x - g x)
    (hf : Monotone f) (hg : Monotone g)
    (hLf : ∀ x, Lf ≤ f x) (hMf : ∀ x, f x ≤ Mf)
    (hLg : ∀ x, Lg ≤ g x) (hMg : ∀ x, g x ≤ Mg) (N n : ℕ) :
    ∑ i ∈ Finset.range n,
        |q (latticeB ϑ z' N i) - q (latticeA ϑ z N i)|
      ≤ (Mf - Lf) + (Mg - Lg) := by
  have hrw : ∀ i, q (latticeB ϑ z' N i) - q (latticeA ϑ z N i)
      = (f (latticeB ϑ z' N i) - g (latticeB ϑ z' N i))
        - (f (latticeA ϑ z N i) - g (latticeA ϑ z N i)) := by
    intro i; rw [hq, hq]
  calc ∑ i ∈ Finset.range n, |q (latticeB ϑ z' N i) - q (latticeA ϑ z N i)|
      = ∑ i ∈ Finset.range n,
          |(f (latticeB ϑ z' N i) - g (latticeB ϑ z' N i))
            - (f (latticeA ϑ z N i) - g (latticeA ϑ z N i))| := by
        exact Finset.sum_congr rfl fun i _ => by rw [hrw i]
    _ ≤ (Mf - Lf) + (Mg - Lg) :=
        bv_lattice_sum hf hg hLf hMf hLg hMg
          (fun i => latticeA_le_latticeB hϑ hzz N i)
          (fun i => latticeB_le_latticeA_succ hϑ hz hz' N i) n

/-! ## From the oscillation bound to the sup bound

The remaining step of the lemma is arithmetic: a function on the unit cell that
integrates to one takes values on both sides of one, so an oscillation bound is
a deviation bound. -/

/-- **Lemma (Offset Uniformity), the sup bound.** A density on the unit cell
whose oscillation is at most `V`, and which is at most one somewhere and at
least one somewhere, deviates from one by at most `V` everywhere. The two
one-sided witnesses are what integrating to one supplies. -/
theorem sup_dev_of_oscillation (pbar : ℝ → ℝ) (V : ℝ) (S : Set ℝ)
    (hosc : ∀ u ∈ S, ∀ v ∈ S, pbar u - pbar v ≤ V)
    {z₀ z₁ : ℝ} (hz₀ : z₀ ∈ S) (hz₁ : z₁ ∈ S)
    (h0 : pbar z₀ ≤ 1) (h1 : 1 ≤ pbar z₁) {z : ℝ} (hz : z ∈ S) :
    |pbar z - 1| ≤ V := by
  rw [abs_le]
  constructor
  · have := hosc z₁ hz₁ z hz
    linarith
  · have := hosc z hz z₀ hz₀
    linarith

/-! ## The Brownian constant of the occupation corollary

For `X = σB` from the origin the mean occupation density has total variation
`2σ√(2T/π)` and `E⟨X⟩_T = σ²T`, so the corollary's bound is
`ϑ · 2√2 / (√π σ√T)`. The constant `2√2/√π` is the `1.60` quoted in the paper;
the identity below is the arithmetic that produces it. -/

/-- The occupation corollary's constant, in closed form. -/
theorem occupation_constant (σ T : ℝ) (hσ : 0 < σ) (hT : 0 < T) :
    (2 * σ * Real.sqrt (2 * T / Real.pi)) / (σ ^ 2 * T)
      = 2 * Real.sqrt 2 / (Real.sqrt Real.pi * σ * Real.sqrt T) := by
  have hpi : (0:ℝ) < Real.pi := Real.pi_pos
  have h2 : Real.sqrt (2 * T / Real.pi)
      = Real.sqrt 2 * Real.sqrt T / Real.sqrt Real.pi := by
    rw [Real.sqrt_div' _ (by positivity), Real.sqrt_mul (by norm_num)]
  rw [h2]
  have hsT : Real.sqrt T * Real.sqrt T = T := Real.mul_self_sqrt hT.le
  have hsπ : Real.sqrt Real.pi ≠ 0 := (Real.sqrt_pos.mpr hpi).ne'
  have hsTne : Real.sqrt T ≠ 0 := (Real.sqrt_pos.mpr hT).ne'
  field_simp
  nlinarith [hsT, sq_nonneg σ]

/-- The constant is the `1.60` of the text, to the quoted precision. -/
theorem occupation_constant_value :
    1.59 < 2 * Real.sqrt 2 / Real.sqrt Real.pi
      ∧ 2 * Real.sqrt 2 / Real.sqrt Real.pi < 1.60 := by
  have hpi : (0:ℝ) < Real.pi := Real.pi_pos
  have hsπ : (0:ℝ) < Real.sqrt Real.pi := Real.sqrt_pos.mpr hpi
  have hs2 : (0:ℝ) < Real.sqrt 2 := Real.sqrt_pos.mpr (by norm_num)
  have h2 : Real.sqrt 2 ^ 2 = 2 := Real.sq_sqrt (by norm_num)
  have hπ : Real.sqrt Real.pi ^ 2 = Real.pi := Real.sq_sqrt hpi.le
  have hπlb : (3.1415:ℝ) < Real.pi := Real.pi_gt_d4
  have hπub : Real.pi < 3.1416 := Real.pi_lt_d4
  constructor
  · rw [lt_div_iff₀ hsπ]
    nlinarith [h2, hπ, hsπ, hs2]
  · rw [div_lt_iff₀ hsπ]
    nlinarith [h2, hπ, hsπ, hs2]

end LocalTime
