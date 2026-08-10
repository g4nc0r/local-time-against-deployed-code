"""Probe 10 -- independent-provenance cross-check of the tick cache.

The per-pool tick caches were
built by the OF indexer from the SQD portal; the position-manager lake's
pools-swaps extension parquets were indexed independently (Alchemy
eth_getLogs path). For census pools covered by both inside the
census era, this probe compares the per-block last tick of the two
sources on every shared block. Agreement answers the tick-stream
provenance question at zero incremental risk; disagreement flags an
indexing defect on one side.

Deterministic: no RNG. Reads both sources read-only.

Run:  python3 probe_provenance.py
      (writes results/provenance-crosscheck.json)
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

import duckdb
import numpy as np

from common import RESULTS, load_cache, load_census_cells

def _lake():
    """Resolve the event lake and its file naming.

    The lake is a private dataset of recorded position-manager events. It is
    not vendored here, and neither is its file naming: point LAKE_DIR at the
    directory and LAKE_LAYOUT at a JSON file naming the members, or place
    `lake-layout.json` under verification/. Absent either, the surfaces that
    read the lake cannot run; the captured OUTPUT.md files are the answer
    they produced.
    """
    d = os.environ.get("LAKE_DIR")
    here = os.path.dirname(os.path.abspath(__file__))
    lay = os.environ.get("LAKE_LAYOUT") or os.path.join(here, "..", "lake-layout.json")
    if not d or not os.path.exists(lay):
        raise SystemExit(
            "missing input: the position-manager event lake\n"
            "  set LAKE_DIR to the lake directory, and LAKE_LAYOUT to a JSON\n"
            "  naming its members (db, amounts, swap_extensions); see\n"
            "  verification/README.md.")
    with open(lay) as f:
        return d, json.load(f)


LAKE, _L = _lake()
EXT = [os.path.join(LAKE, f) for f in _L["swap_extensions"]
       if os.path.exists(os.path.join(LAKE, f))]
ERA_LO = 43_990_000


def main():
    census_pools = sorted({p for _, p, _ in load_census_cells()})
    con = duckdb.connect()
    con.execute("PRAGMA memory_limit='4GB'")
    files = ",".join(f"'{f}'" for f in EXT)
    ext_pools = {r[0] for r in con.execute(
        f"SELECT DISTINCT pool FROM read_parquet([{files}])").fetchall()}
    shared = [p for p in census_pools if p in ext_pools]

    out = {"census_pools": len(census_pools),
           "extension_pools": len(ext_pools),
           "shared_pools": len(shared), "pools": {}}
    for pool in shared:
        cb, ck = load_cache(pool)
        if cb is None:
            out["pools"][pool] = {"skipped": "no tick cache"}
            continue
        rows = con.execute(f"""
            SELECT block, arg_max(tick, log_index) AS last_tick
            FROM read_parquet([{files}])
            WHERE pool = '{pool}' AND block >= {ERA_LO}
            GROUP BY block ORDER BY block
        """).fetchall()
        if not rows:
            out["pools"][pool] = {"skipped": "no census-era extension rows"}
            continue
        eb = np.array([r[0] for r in rows], dtype=np.int64)
        et = np.array([r[1] for r in rows], dtype=np.int64)
        # cache samples at exactly these blocks
        idx = np.searchsorted(cb, eb)
        ok = (idx < len(cb)) & (cb[np.minimum(idx, len(cb) - 1)] == eb)
        n = int(ok.sum())
        if n == 0:
            out["pools"][pool] = {"skipped": "no shared blocks"}
            continue
        diff = np.abs(ck[idx[ok]].astype(np.int64) - et[ok])
        out["pools"][pool] = {
            "shared_blocks": n,
            "exact_match": round(float(np.mean(diff == 0)), 4),
            "within_1_tick": round(float(np.mean(diff <= 1)), 4),
            "max_abs_diff_ticks": int(diff.max()),
            "extension_block_range": [int(eb[0]), int(eb[-1])]}

    checked = [v for v in out["pools"].values() if "exact_match" in v]
    if checked:
        out["summary"] = {
            "pools_checked": len(checked),
            "total_shared_blocks": sum(v["shared_blocks"] for v in checked),
            "min_exact_match": min(v["exact_match"] for v in checked),
            "min_within_1_tick": min(v["within_1_tick"] for v in checked),
            "max_abs_diff_ticks": max(v["max_abs_diff_ticks"]
                                      for v in checked)}
    os.makedirs(RESULTS, exist_ok=True)
    with open(RESULTS + "/provenance-crosscheck.json", "w") as f:
        json.dump(out, f, indent=1)
    print("=== probe 10: independent-provenance cross-check ===")
    print(json.dumps(out, indent=1))
    print("wrote results/provenance-crosscheck.json", flush=True)


if __name__ == "__main__":
    main()
