/-
Shared definitions for the Lean formalisation of "Local Time Against Deployed
Code".

The concentrated liquidity primitives that every theorem file consumes: the
per-liquidity token amounts of a V3 range, the per-liquidity value coefficient
φ, the holdings shares ω₀ and ω₁ of §The central law, the binding-side mint
minimum, and the retained fraction and mint kerf of eq. (kdef).

Setting: in the sqrt-price coordinate a position with liquidity L at price s in
range [sa, sb], with 0 < sa < s < sb, holds token amounts x = L(1/s - 1/sb) and
y = L(s - sa); its value in token1 units is V = x s² + y = L φ(s, sa, sb).

The φ and mint-minimum definitions are a copy of the corresponding surface in
the Geometric Siphon formalisation, generalised from that paper's isolated
single-pool case to an arbitrary admissible target range. That repository owns
the original. Programme convention is to share by copy, not by symlink.
-/
import Mathlib

set_option linter.style.header false

namespace LocalTime

/-! ## Range geometry -/

/-- Per-liquidity token0 amount of a range with upper bound `sb` at price `s`. -/
noncomputable def amt0 (s sb : ℝ) : ℝ := 1 / s - 1 / sb

/-- Per-liquidity token1 amount of a range with lower bound `sa` at price `s`. -/
def amt1 (s sa : ℝ) : ℝ := s - sa

/-- Per-liquidity value coefficient `φ(s, sa, sb) = 2s - s²/sb - sa`, in
token1 units. -/
noncomputable def phi (s sa sb : ℝ) : ℝ := 2 * s - s ^ 2 / sb - sa

/-- φ decomposes over the token amounts: `φ = s² x_u + y_u`. -/
lemma phi_eq_amounts {s sa sb : ℝ} (hs : s ≠ 0) (hsb : sb ≠ 0) :
    phi s sa sb = s ^ 2 * amt0 s sb + amt1 s sa := by
  unfold phi amt0 amt1; field_simp; ring

/-- Strict interiority gives a positive token0 amount. -/
lemma amt0_pos {s sb : ℝ} (hs : 0 < s) (h : s < sb) : 0 < amt0 s sb :=
  sub_pos.mpr (one_div_lt_one_div_of_lt hs h)

/-- Strict interiority gives a positive token1 amount. -/
lemma amt1_pos {s sa : ℝ} (h : sa < s) : 0 < amt1 s sa := sub_pos.mpr h

/-- A position holding both tokens has positive value. -/
lemma phi_pos {s sa sb : ℝ} (h0 : 0 < sa) (h1 : sa < s) (h2 : s < sb) :
    0 < phi s sa sb := by
  have hs : (0:ℝ) < s := h0.trans h1
  have hsb : (0:ℝ) < sb := hs.trans h2
  rw [phi_eq_amounts hs.ne' hsb.ne']
  have := amt0_pos hs h2
  have := amt1_pos h1
  positivity

/-! ## Holdings shares

The state variable of the second act. `share0` is the token0 value share of the
withdrawn position, `share1` its token1 share; they sum to one. -/

/-- Token0 value share `ω₀ = x s² / V`. -/
noncomputable def share0 (s sa sb : ℝ) : ℝ := s ^ 2 * amt0 s sb / phi s sa sb

/-- Token1 value share `ω₁ = y / V`. -/
noncomputable def share1 (s sa sb : ℝ) : ℝ := amt1 s sa / phi s sa sb

/-- The two shares sum to one. -/
lemma share_add_eq_one {s sa sb : ℝ} (h0 : 0 < sa) (h1 : sa < s) (h2 : s < sb) :
    share0 s sa sb + share1 s sa sb = 1 := by
  have hs : (0:ℝ) < s := h0.trans h1
  have hsb : (0:ℝ) < sb := hs.trans h2
  have hphi : phi s sa sb ≠ 0 := (phi_pos h0 h1 h2).ne'
  unfold share0 share1
  rw [← add_div, ← phi_eq_amounts hs.ne' hsb.ne', div_self hphi]

lemma share0_pos {s sa sb : ℝ} (h0 : 0 < sa) (h1 : sa < s) (h2 : s < sb) :
    0 < share0 s sa sb := by
  have hs : (0:ℝ) < s := h0.trans h1
  have := amt0_pos hs h2
  have := phi_pos h0 h1 h2
  unfold share0; positivity

lemma share1_pos {s sa sb : ℝ} (h0 : 0 < sa) (h1 : sa < s) (h2 : s < sb) :
    0 < share1 s sa sb := by
  have := amt1_pos h1
  have := phi_pos h0 h1 h2
  unfold share1; positivity

/-! ## The isolated re-placement

An isolated re-placement withdraws the position at price `s` and re-mints into
an admissible range `[sa', sb']` containing `s` through the binding-side
minimum, emitting the non-binding surplus. -/

/-- Liquidity minted by the binding-side minimum `L' = min(x/x_u, y/y_u)`. -/
noncomputable def Lnew (L s sa sb sa' sb' : ℝ) : ℝ :=
  min (L * amt0 s sb / amt0 s sb') (L * amt1 s sa / amt1 s sa')

/-- The retained value fraction `V'/V` of an isolated re-placement. -/
noncomputable def retained (L s sa sb sa' sb' : ℝ) : ℝ :=
  Lnew L s sa sb sa' sb' * phi s sa' sb' / (L * phi s sa sb)

/-- The mint kerf `k = -ln(V'/V)` of eq. (kdef), the per-event log-cost. -/
noncomputable def kerf (L s sa sb sa' sb' : ℝ) : ℝ :=
  -Real.log (retained L s sa sb sa' sb')

end LocalTime
