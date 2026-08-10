"""Shared loaders and estimators for the third act's overshoot probes.

Ported from the probe scripts of the empirical companion paper
(`overshoot_probe.py`, `overshoot_fast.py`, `overshoot_localsigma.py`);
the port is this paper's own regression surface, the companion's
artefacts remaining inputs only. Function bodies are kept identical to
the originals so that the ported probes reproduce the captured numbers
exactly. Any change here is a manuscript-level event, OUTPUT.md having
been captured.

Three inputs, all external, path-parameterised through the
environment, and none of them copied into this tree.

  sender-layer.db   the sender-keyed operator layer; env SENDER_LAKE
  tick cache        per-pool tick streams as npz, built by the
                    companion paper's indexer; env LT_TICKCACHE
  sender census     the census-clean (sender, pool, phi) cells, also
                    the companion's; env LT_CENSUS

The census and the operator layer carry third-party addresses, so
distributing either alongside this code is a separate decision from
distributing the code.
"""
from __future__ import annotations

import glob
import json
import math
import os

import numpy as np

# The sender-keyed operator layer is the companion paper's artefact and is
# not vendored here. Point SENDER_LAKE at the directory holding it.
LAKE = os.environ.get("SENDER_LAKE", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sender-lake"))
DB = os.path.join(LAKE, "sender-layer.db")

# The tick cache and the census are the companion paper's artefacts and
# are not vendored here. Point LT_TICKCACHE and LT_CENSUS at them, or set
# LT_COMPANION to the directory holding both. The older P3_ names are
# still honoured. Without one of these the population probes cannot run.
_COMPANION = os.environ.get(
    "LT_COMPANION",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "companion"))


def _path_env(new, old, default):
    return os.environ.get(new) or os.environ.get(old) or default


CACHE = _path_env("LT_TICKCACHE", "P3_TICKCACHE", _COMPANION + "/data/tickcache")
CENSUS = _path_env("LT_CENSUS", "P3_CENSUS",
                   _COMPANION + "/results/sender-census.json")

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")

STALE_GUARD = 450
LOOKBACK = 20_000          # blocks searched for the crossing (~11 h on Base)
FAST_DELAY = 5             # blocks; "no room for diffusion" threshold
FAT_MULT = 3.0             # x cell median = a fat overshoot
HALF_NORMAL = {"q90_q50": 2.44, "q99_q50": 3.82}
EXPONENTIAL = {"q90_q50": 3.32, "q99_q50": 6.64}
FOLDED_NORMAL = {"median": 0.674, "q99": 2.576}

REBALANCE_SQL = """
    SELECT block, prev_lower, prev_upper, firing_tick, u, tick_gap_blocks
    FROM rebalances
    WHERE sender = ? AND pool = ? AND firing_tick IS NOT NULL
      AND tick_gap_blocks <= ? AND u IS NOT NULL
      AND prev_upper > prev_lower
    ORDER BY block"""


def _require(path, what, envs):
    """Exit with an instruction rather than a traceback when an input the
    population probes need is not on this machine. These three inputs are
    the companion paper's and are deliberately not vendored, so a missing
    one is the normal state of a fresh clone, not a fault."""
    if os.path.exists(path):
        return path
    raise SystemExit(
        "missing input: %s\n"
        "  looked in: %s\n"
        "  set %s to its location.\n"
        "  These probes read an event lake that is not vendored in this\n"
        "  repository; see verification/README.md for what they need."
        % (what, path, " or ".join(envs)))


def load_census_cells():
    census = json.load(open(_require(CENSUS, "the operator census",
                                     ("LT_CENSUS", "LT_COMPANION"))))
    return [(s, c["pool"], c["phi"])
            for s, o in census["operators"].items() for c in o["cells"]]


def load_cache(pool):
    _require(CACHE, "the per-pool tick cache", ("LT_TICKCACHE", "LT_COMPANION"))
    hits = sorted(glob.glob(f"{CACHE}/{pool}-*.npz"))
    if not hits:
        return None, None
    z = np.load(hits[-1])
    return z["blocks"], z["ticks"]


def crossing_delay(cb, ck, blk, line, direction):
    """Blocks between the first tick-stream crossing of `line` in the current
    excursion and the mint at `blk`. None if the whole lookback window sits
    outside the line (censored) or no data."""
    hi = int(np.searchsorted(cb, blk))          # ticks strictly before blk
    lo = int(np.searchsorted(cb, blk - LOOKBACK))
    if hi <= lo:
        return None
    w_t = ck[lo:hi]
    inside = w_t >= line if direction == "dn" else w_t <= line
    nz = np.nonzero(inside)[0]
    if len(nz) == 0:
        return None                              # censored: crossed earlier
    k = nz[-1]                                   # last sample inside
    if k + 1 >= hi - lo:
        return int(blk - cb[lo + k])             # crossed between k and mint
    return int(blk - cb[lo + k + 1])             # first outside sample


def classify_event(phi, u, plo, phi_u):
    """Trigger-side classification of one rebalance event.

    Returns (direction, line, over_w) for a trigger firing, or None for a
    convention (interior) firing. Caller validates u."""
    if phi < u < 1 - phi:
        return None
    W = phi_u - plo
    if u <= phi:
        return "dn", plo + phi * W, phi - u
    return "up", phi_u - phi * W, u - (1 - phi)


def pool_sigma(cb, ck):
    """Full-era realised per-block tick volatility: sqrt(sum dt^2 / span)."""
    if cb is None or len(cb) < 100:
        return None
    dt = np.diff(ck.astype(float))
    span = float(cb[-1] - cb[0])
    if span <= 0:
        return None
    return math.sqrt(float(np.sum(dt * dt)) / span)


MIN_SAMPLES = 30


def local_sigma(cb, ck, end_block, trail):
    """Per-block tick volatility over [end_block - trail, end_block)."""
    hi = int(np.searchsorted(cb, end_block))
    lo = int(np.searchsorted(cb, end_block - trail))
    if hi - lo < MIN_SAMPLES:
        return None
    span = float(cb[hi - 1] - cb[lo])
    if span < trail / 2:
        return None
    dt = np.diff(ck[lo:hi].astype(float))
    return math.sqrt(float(np.sum(dt * dt)) / span)


def q(xs, p):
    return float(np.quantile(xs, p)) if len(xs) else None


def connect():
    import duckdb
    _require(DB, "the sender-keyed operator layer", ("SENDER_LAKE",))
    con = duckdb.connect(DB, read_only=True)
    con.execute("PRAGMA memory_limit='3GB'")
    con.execute("PRAGMA threads=2")
    return con
