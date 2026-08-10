# Calibration run log: 2026-08-10

## Hardware and stack

- Remote GPU host (ssh), 2x AMD Radeon AI PRO R9700 32 GB,
  PyTorch 2.13.0 with `torch.cuda` via ROCm (3 CUDA devices
  enumerated; jobs pinned with `HIP_VISIBLE_DEVICES`).  `nvidia-smi`
  does not exist; minimal non-login PATH; invoke via absolute
  `/usr/bin/python3`.
- Local workstation: AMD RX 7800 XT (ROCm torch available), used for
  development and CPU-exact companions.  One local ROCm runtime
  assertion (AqlPacket) occurred after a GPU validation run; local
  validation therefore runs with `--cpu`.  No such fault observed on
  the GPU host.

## Supervisor pattern

```
ssh <gpu-host> 'systemd-run --user --unit=<name> \
  --working-directory="$HOME/local-time-calibration/<item>" \
  --setenv=HIP_VISIBLE_DEVICES=<0|1> \
  /usr/bin/python3 <script>.py --out <results>.json'
# poll:    journalctl --user -u <name> -n 8 -o cat
# status:  systemctl --user is-active <name>
# collect: rsync <gpu-host>:<workdir>/... calibration/output/
```

Code is authored locally under `calibration/`, rsynced to
a working directory on the GPU host, run detached under transient
systemd user units, and result JSONs are rsynced back into
`calibration/output/`.

## Precision and determinism decisions

- float64 THROUGHOUT on GPU, including the R9700s.  Rationale: all
  three simulators run small per-step tensors (10^3-10^4 elements),
  so wall time is kernel-launch-bound and the weak consumer-AMD FP64
  ALU rate is immaterial; measured wall times confirm (see below).
  The float32-plus-companion alternative was not needed.
- `torch.manual_seed` + `torch.use_deterministic_algorithms(True)`
  accepted on both machines; per-run generators are explicitly
  seeded (`torch.Generator(device).manual_seed(seed)`).  Seeds:
  qvi_solver deterministic (no RNG), zoo 20260810, stress 20260811,
  spectrometer toy 20260812.  Captured numbers in the OUTPUT.md
  files state Monte Carlo standard errors; bitwise reproducibility
  on ROCm was not certified, so regression comparisons use the
  stated seed and tolerance convention.

## Validation before GPU burn (spec requirement)

- `qvi_solver.py --validate`: reproduces verify_floor.py's captured
  corridor constants c_min(0.05/0.02/0.005) = 1.9522/1.9804/1.9950,
  the narrow-limit c(0.5) = 2.7726 and c(0.7153) = 2.4554 through
  the cycle algebra, and the exact three-parameter renewal grid
  minimum 2.397 at the symmetric point; exact-vs-narrow kernel
  deviation scales O(rho) (9.0e-3 at rho 0.005, 9.0e-4 at 0.0005).
  Passed.
- `mc_policy_zoo.py --validate` (CPU-scale): classic renewal MC vs
  analytic c(x): x = 0.7153 dev 0.1 %, x = 0.5 dev 3.1 %, x = 0.9
  dev 7.0 % (known near-edge discretisation overshoot, cf. the
  paper's own 14 % note); chattering members biased up 6-14 % at
  coarse step, as expected from overshoot at eps ~ step.  Passed.
- Independent stdlib MC (seeded, verify_floor-style, exact mint
  arithmetic, wandering price): classic x = 0.72 measured c = 2.398
  (analytic 2.397); x = 0.5 measured 2.711 (2.700); chattering
  a = 0.5h members measured 2.02-2.06 at coarse steps.  The
  first two calibrate the machinery; the third confirms the kill
  under a third independent implementation.
- `stress_maps.py --validate`: vectorised operator scan agrees
  EVENT-EXACTLY with the stdlib scan of
  verification/act3-instrument/mc_harness.py on a common seeded
  world at periods 1/5/40 (496/461/336 events, exact match);
  quick bracket check holds; Hill read carries the known upward
  finite-o_ref bias; surcharge premium matches the narrow potential
  form to 4.2e-3 mean absolute and respects the lower bound.
  Passed.
- `spectrometer.py config_toy.json`: 6/6 pools recover the planted
  jump share inside the Theorem 6 bracket; within-component
  agreement test passes in every pool; per-component exceedance
  spread (the multiscale signal) visible; Hill alpha_hat mean 2.94
  vs planted 2.5 (documented upward finite-o_ref kernel bias; the
  harness's own check-3 sees +0.21 at a smaller delay cut).

## Incidents and their fixes

1. First zoo launch (unit e4-item2-zoo): NaN at rho 0.2.  Cause:
   unbanded wandering price over long horizons left the domain
   (sigma_s sqrt(T) exceeded S0).  Fix: per-path horizon capped at
   T ~ 0.9 (sigma_s sqrt(T) ~ 0.15 S0), precision moved to
   replicas (96), per-replica minimum-price exclusion (threshold
   0.4 S0, counts reported), rho = 0.2 kept QVI-only since any
   usable wander there violates the standing h/s_- <= 1/5
   hypothesis.  Same treatment applied to stress part B.
2. Jump arms: beyond-range straddle landings have L2 = 0 in the
   isolated class (one-sided holdings cannot mint a price-containing
   equal-width range), hence INFINITE log-cost.  This is a genuine
   structural fact, the beyond-range clause of Proposition 17 in its
   sharpest form: any jump law with support beyond h(1-x) gives
   every band-maintaining policy an infinite isolated-class
   log-dissipation rate.  Numerics cap per-event k at 10 (e^-10
   residual value, de facto total loss) and count capped events;
   the cap is stated wherever jump numbers land.  Flagged for the
   synthesiser as a possible scope note on Proposition 17.
3. First stress/zoo drafts had no burn-in; the centred start biased
   chattering rates low (~8 %).  Burn-in of n_steps/5 added before
   accounting.

## Runs

- e4-item2-zoo-v3 (GPU0) and e4-item3-stress-v3 (GPU1), launched
  2026-08-10 ~01:50 EEST, detached; results
  `zoo_results.json` / `stress_results.json` copied to
  `calibration/output/`.
- `qvi_solver.py` full run on the local workstation (CPU float64,
  deterministic); stdout captured to
  `item2_sharp_constant/qvi_captured_stdout.txt` and folded into
  `item2_sharp_constant/OUTPUT.md`.
- Wall-time note (FP64-on-GPU decision): the v2 zoo's rho 0.05
  fine-step cell (1.2M steps, 13.3k float64 columns) ran in 215 s on
  one R9700, launch-bound as predicted.
- Final runs: e4-item2-zoo-v4 completed in 18.8 min wall (GPU0;
  horizons re-derived per regime after the v3 launch showed the
  rho 0.005 fine cell at 57M steps); e4-item3-stress-v3 completed in
  9.1 min wall (GPU1).  Results in `output/`.
- Determinism spot-check on the GPU host: two identical seeded
  torch.randn(1e5, float64, cuda) draws are BITWISE identical
  (sum 302.0571161139111 reproduced exactly).  Full-run bitwise
  reproducibility remains uncertified; the seed + tolerance
  convention stands.

## The spectrometer calibration, production run

The Uniswap V3 census on Base landed while the other two items were
running, so the census draw was wired in and run.  `production_sweep.py`
run locally (stdlib CPU, 62 s, seed 20260813): 2 planted worlds x
12 pools x 32 census-drawn operators, sweeps over population size,
era length, delay cut.  Captured in `item1_spectrometer/OUTPUT.md`.
Disclosure: draw reads the census artefact by path at runtime; no
census numbers restated in any artefact here.
