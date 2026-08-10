# Synthetic calibration

The paper's seventh verification surface. Where the first six assert
identities against arithmetic or against deployed code, this one
measures the instrument and stress-tests the floors on synthetic ground
truth at simulation scale.

Executed 2026-08-10 on two AMD Radeon AI PRO R9700 cards under PyTorch
with ROCm, with CPU-exact companions on the workstation for every
result that a single core can reach. `RUN-LOG.md` records the hardware,
the supervisor pattern, the precision and determinism decisions, and
the incidents.

## Stance

Simulation plays one role here: controlled synthetic ground truth
against which the paper's own laws, floors, and estimators are tested.
No price model enters as an assumption, and no equilibrium,
agent-based, or benchmark-loss modelling appears anywhere on this
surface. Worlds are diffusion plus explicitly planted jump measures,
and every recovery is reported against the planted truth.

The census-derived geometry mix for the spectrometer item is not wired
in. `item1_spectrometer/config_census_STUB.json` marks the slot, and no
census-derived number appears in any artefact in this folder.

## Contents

| Path | What it is | State |
|---|---|---|
| `item1_spectrometer/` | the spectrometer calibration harness | built and toy-validated; the production run awaits the census draw |
| `item2_sharp_constant/` | the search behind the sharpness result | executed; `OUTPUT.md` captured, a regression target |
| `item3_stress_maps/` | small-delay and surcharge stress maps | executed; `OUTPUT.md` captured, a regression target |
| `output/` | result JSONs copied back from the GPU machine | artefacts |
| `RUN-LOG.md` | the session run log | log |

## Provenance

Geometry and estimator code is shared by copy, with the owner named in
each file's header, per the programme's rule against symlinking between
surfaces. The exact re-placement mint arithmetic comes from
[`../verification/act2-floor/verify_floor.py`](../verification/act2-floor/verify_floor.py);
the operator scan, the bipower estimator, and the estimator formulas
come from
[`../verification/act3-instrument/mc_harness.py`](../verification/act3-instrument/mc_harness.py)
and the manuscript's estimator appendix.

Every simulator was validated against the owning surface's captured
numbers, or event-exactly against the owning code, before any large run
was launched. The validation transcripts are in `RUN-LOG.md`.

The four standard-library harnesses under
[`../verification/`](../verification/) remain the paper's shipped
reference implementations. Artefacts here are an evidence surface, not
a replacement for them.

## Regression rule

The captured `OUTPUT.md` files in `item2_sharp_constant/` and
`item3_stress_maps/` are regression targets from the moment of capture.
A numeric shift in either is a manuscript-level event.
