/-
Proposition (Retention Collapse), §The retention collapse.

In the retention architecture the surplus is credited back to a ledger rather
than emitted. The system value, position plus ledger at the impulse price, is
then conserved at every swap-free impulse, so the impulse leg carries no term
of the floors' order: the floors are deleted, not lowered.

The arithmetic is the ledger-inclusive mint identity of the Master Equation
paper, restated here in the value coordinate. No verification function is
needed, which is why this file has no analysis in it.
-/
import Mathlib

set_option linter.style.header false
set_option linter.unusedVariables false

namespace LocalTime

variable {xhat yhat xu yu s : ℝ}

/-- The liquidity minted from the available amounts through the binding-side
minimum. -/
noncomputable def LnewLedger (xhat yhat xu yu : ℝ) : ℝ :=
  min (xhat / xu) (yhat / yu)

/-- **Proposition (Retention Collapse), swap-free half.** At a swap-free
impulse the system value, minted position plus credited ledger, equals the
available value: nothing is surrendered. -/
theorem system_value_conserved (L' : ℝ) :
    L' * (xu * s ^ 2 + yu) + ((xhat - L' * xu) * s ^ 2 + (yhat - L' * yu))
      = xhat * s ^ 2 + yhat := by
  ring

/-- Token-by-token conservation, of which the value statement is the
price-weighted sum. -/
theorem token_conserved (L' : ℝ) :
    (L' * xu + (xhat - L' * xu) = xhat) ∧ (L' * yu + (yhat - L' * yu) = yhat) :=
  ⟨by ring, by ring⟩

/-- **Proposition (Retention Collapse), swap-corrected half.** With a corrective
swap the system value falls by exactly the swap's execution cost, and by nothing
else. -/
theorem system_value_loss_eq_swap_cost (L' swapLoss : ℝ) :
    (xhat * s ^ 2 + yhat)
        - (L' * (xu * s ^ 2 + yu)
            + ((xhat - L' * xu) * s ^ 2 + (yhat - L' * yu) - swapLoss))
      = swapLoss := by
  ring

end LocalTime
