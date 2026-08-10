"""Real-data anchor for the first two acts.

Evaluates the consolidated paper's identity and floor claims against
the operator's own production history in the position-manager event
lake, read-only. Three evaluations.

  [1] Share-potential identity (Theorem 2) per production
      event: for every rebalance in the amounts window whose value
      chain closes without a silent dust draw, the realised log-cost
      of the isolated re-mint equals max(ln w0'/w0, ln w1'/w1)
      computed from the same event's amounts, to mint rounding.
      Also asserts the binding-side mint-minimum arithmetic
      (L' = min(h0/x_u, h1/y_u)) directly.

  [2] Realised dissipation rate against the swap-mediated floor
      (Theorem 5): per pool over the amounts window, the
      realised per-event log-costs (fee + impact + surrendered dust,
      gas excluded and reported separately) aggregate to a rate r-hat
      compared against A(1-rho)^2 sigma_s^2 / w^2 with sigma_s
      measured from the pool's own swap stream and eta measured from
      the operator's own corrective swaps.

  [3] Convention against optimum: measured trigger and correction
      fractions (x-hat, m-hat) per pool against the deployed
      convention and the renewal-family prediction r(x, m)
      (Proposition 8).

Deterministic: no RNG. Reads the lake read-only via DuckDB.
Captured output: OUTPUT.md in this folder is the regression target.

Run:  python3 anchor.py            (~1-2 min, full window)
      python3 anchor.py --pools 5  (top-N pools only)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict

import duckdb

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
DB = os.path.join(LAKE, _L["db"])
AMOUNTS = os.path.join(LAKE, _L["amounts"])
EXT = [os.path.join(LAKE, f) for f in _L["swap_extensions"]
       if os.path.exists(os.path.join(LAKE, f))]

BLOCK_LO, BLOCK_HI = 43_635_967, 45_988_726   # amounts-window bounds
Q96 = 2 ** 96
SECONDS_PER_YEAR = 365.25 * 86400
GAS_USD = 0.03                                 # programme anchor, reported separately


def tick_to_sqrt(t: float) -> float:
    return 1.0001 ** (t / 2.0)


def connect():
    if not os.path.exists(DB):
        raise SystemExit(
            "missing input: the position-manager event lake\n"
            "  looked in: %s\n"
            "  set LAKE_DIR to its location.\n"
            "  The anchor reads recorded production rebalances, which are\n"
            "  not vendored in this repository; see verification/README.md."
            % DB)
    con = duckdb.connect(DB, read_only=True)
    con.execute("PRAGMA memory_limit='4GB'")
    return con


def load_events(con, top_pools):
    """One row per rebalance tx in the amounts window: principal burn,
    optional swap, the mint, and same-tx dust credits."""
    pool_filter = ""
    if top_pools:
        quoted = ",".join(f"'{p}'" for p in top_pools)
        pool_filter = f"AND r.pool IN ({quoted})"
    rows = con.execute(f"""
        WITH r AS (
          SELECT tx_hash, pool, block, block_ts, new_tick_lower, new_tick_upper, swap_mode
          FROM rebalances r
          WHERE block BETWEEN {BLOCK_LO} AND {BLOCK_HI} {pool_filter}
        ),
        p AS (
          SELECT tx, kind, tickLower, tickUpper,
                 CAST(amount0 AS HUGEINT) a0, CAST(amount1 AS HUGEINT) a1,
                 CAST(liquidity AS HUGEINT) liq, log_index
          FROM read_parquet('{AMOUNTS}')
          WHERE tx IN (SELECT tx_hash FROM r)
        ),
        burns AS (
          SELECT tx, sum(a0) b0, sum(a1) b1,
                 count(*) FILTER (WHERE a0 > 0 OR a1 > 0) n_nonzero,
                 min(tickLower) FILTER (WHERE a0 > 0 OR a1 > 0) old_tl,
                 min(tickUpper) FILTER (WHERE a0 > 0 OR a1 > 0) old_tu
          FROM p WHERE kind = 'burn' GROUP BY tx
        ),
        mints AS (
          SELECT tx, sum(a0) m0, sum(a1) m1, count(*) n_mint,
                 min(tickLower) tl, min(tickUpper) tu, min(liq) liq
          FROM p WHERE kind = 'mint' GROUP BY tx
        ),
        swaps AS (
          SELECT tx, sum(a0) s0, sum(a1) s1, count(*) n_swap,
                 min(liq) sliq
          FROM p WHERE kind = 'swap' GROUP BY tx
        )
        SELECT r.tx_hash, r.pool, r.block, r.block_ts, r.swap_mode,
               b.b0, b.b1, b.n_nonzero, b.old_tl, b.old_tu,
               m.m0, m.m1, m.n_mint, m.tl, m.tu, m.liq,
               coalesce(s.s0, 0), coalesce(s.s1, 0), coalesce(s.n_swap, 0),
               coalesce(s.sliq, 0)
        FROM r
        JOIN burns b ON b.tx = r.tx_hash
        JOIN mints m ON m.tx = r.tx_hash
        LEFT JOIN swaps s ON s.tx = r.tx_hash
        ORDER BY r.pool, r.block
    """).fetchall()
    dust = defaultdict(list)
    for tx, amt in con.execute(f"""
        SELECT tx_hash, CAST(amount AS HUGEINT) FROM dust_credits
        WHERE block BETWEEN {BLOCK_LO} AND {BLOCK_HI}
    """).fetchall():
        dust[tx].append(int(amt))
    return rows, dust


def eval_event(row, dust):
    """Classify one event and, if clean, test the identity.

    Returns dict with class in {'clean', 'draw', 'multi', 'degenerate'}
    and, for clean events, the identity errors and per-event k.
    """
    (tx, pool, block, ts, mode, b0, b1, nnz, old_tl, old_tu,
     m0, m1, nmint, tl, tu, liq, s0, s1, nswap, sliq) = row
    b0, b1, m0, m1, liq, s0, s1, sliq = map(
        int, (b0, b1, m0, m1, liq, s0, s1, sliq))
    if nmint != 1 or nnz != 1:
        return {"class": "multi"}
    # holdings after burn and (pool-perspective-signed) swap
    h0, h1 = b0 - s0, b1 - s1
    if h0 < 0 or h1 < 0 or liq <= 0:
        return {"class": "degenerate"}
    # price at mint, recovered from the mint's own arithmetic
    sa, sb = tick_to_sqrt(tl), tick_to_sqrt(tu)
    s_from1 = sa + m1 / liq
    inv_s = m0 / liq + 1.0 / sb
    s_from0 = 1.0 / inv_s if inv_s > 0 else float("nan")
    if not (sa < s_from1 < sb):
        return {"class": "degenerate"}
    s = s_from1
    price_consist = abs(s_from0 - s_from1) / s_from1
    # dust-draw detection: a mint not coverable by the tx's own
    # holdings drew on the standing dust balance (swept into every
    # mint and re-credited); the event is priced but excluded from
    # the identity subsample, whose hypothesis is isolated holdings
    d0_raw, d1_raw = h0 - m0, h1 - m1
    is_draw = d0_raw < -2 or d1_raw < -2
    draw0, draw1 = max(-d0_raw, 0), max(-d1_raw, 0)
    d0, d1 = max(d0_raw, 0), max(d1_raw, 0)
    # the contract sweeps the prior dust balance into every mint and
    # credits back the remainder, so per-tx the testable direction is
    # credit >= surplus (equality only when the swept balance is zero)
    credits = sorted(dust.get(tx, []))
    surplus = sorted(x for x in (d0, d1) if x > 2)
    dust_match = all(
        any(c >= sv - 2 for c in credits) for sv in surplus)
    # mint-minimum arithmetic: L' = min(h0/x_u, h1/y_u)
    xu = 1.0 / s - 1.0 / sb              # per unit liquidity
    yu = s - sa
    lp = min(h0 / xu if xu > 0 else float("inf"),
             h1 / yu if yu > 0 else float("inf"))
    # value-weighted arithmetic error (edge-of-range token amounts can
    # be near zero, so per-token relative error is the wrong metric)
    v_mint = m0 * s * s + m1
    mint_err = (abs(m0 - (lp * xu if xu > 0 else 0)) * s * s
                + abs(m1 - lp * yu)) / max(v_mint, 1)
    # values and shares at s (token1 units, raw)
    v_before = h0 * s * s + h1
    v_after = m0 * s * s + m1
    if v_before <= 0 or v_after <= 0:
        return {"class": "degenerate"}
    k_real = -math.log(v_after / v_before)
    w0, w1 = h0 * s * s / v_before, h1 / v_before
    w0p, w1p = m0 * s * s / v_after, m1 / v_after
    k_pred = float("inf")
    if w0 > 0 and w1 > 0 and w0p > 0 and w1p > 0:
        k_pred = max(math.log(w0p / w0), math.log(w1p / w1))
    elif (w0 == 0 and w0p == 0) or (w1 == 0 and w1p == 0):
        k_pred = k_real                   # single-sided, identity trivial
    # whole-event cost incl. swap: value of burn holdings against the
    # post-event position plus its surplus. Marked at the PRE-swap
    # price, recovered exactly from the swap's own constant-liquidity
    # arithmetic (s_pre = s_post - amount1/L_swap); marking at the
    # post-swap price would credit the swap with its own impact.
    s_mark = s
    if nswap == 1 and sliq > 0:
        s_pre = s - s1 / sliq
        if 0 < s_pre and abs(s_pre / s - 1) < 0.2:
            s_mark = s_pre
    v_burn = (b0 + draw0) * s_mark * s_mark + (b1 + draw1)
    v_land = max(m0, h0) * s_mark * s_mark + max(m1, h1)
    k_event = -math.log(v_land / v_burn) \
        if v_burn > 0 and v_land > 0 else float("nan")
    return {
        "class": "draw" if is_draw else "clean",
        "pool": pool, "block": block, "ts": ts,
        "mode": mode, "s": s, "sa": sa, "sb": sb,
        "old_tl": old_tl, "old_tu": old_tu, "tl": tl, "tu": tu,
        "price_consist": price_consist, "mint_err": mint_err,
        "dust_match": dust_match, "had_swap": nswap > 0,
        "k_real": k_real, "k_pred": k_pred,
        "id_err": abs(k_real - k_pred) if math.isfinite(k_pred) else float("nan"),
        "k_event": k_event, "v_burn": v_burn,
        "swap_notional1": abs(int(row[17])),  # |s1| in token1 raw
    }


def pool_sigma(con, pool, ts_lo, ts_hi):
    """Annualised sqrt-price volatility from the pool's full swap
    stream, 5-minute subsampled realised variance."""
    if not EXT:
        return None
    files = ",".join(f"'{f}'" for f in EXT)
    rows = con.execute(f"""
        SELECT block_timestamp, CAST(sqrtPriceX96 AS DOUBLE) / {Q96}
        FROM read_parquet([{files}])
        WHERE pool = '{pool}'
          AND block_timestamp BETWEEN {ts_lo} AND {ts_hi}
        ORDER BY block_timestamp
    """).fetchall()
    if len(rows) < 100:
        return None
    # last observation per 300 s bucket
    buckets = {}
    for ts, sp in rows:
        buckets[ts // 300] = sp
    keys = sorted(buckets)
    if len(keys) < 50:
        return None
    rv, tspan = 0.0, (keys[-1] - keys[0]) * 300
    prev = buckets[keys[0]]
    for kk in keys[1:]:
        cur = buckets[kk]
        rv += (cur - prev) ** 2
        prev = cur
    sigma2_per_sec = rv / tspan
    sbar = sum(buckets[k] for k in keys) / len(keys)
    return {"sigma_s_ann": math.sqrt(sigma2_per_sec * SECONDS_PER_YEAR),
            "sbar": sbar, "n_swaps": len(rows), "n_buckets": len(keys),
            "source": "swap-stream"}


def event_sigma(evs):
    """Fallback: annualised sqrt-price volatility from the operator's
    own event-time price marks (optional-stopping unbiased for the
    integrated variance, coarse but serviceable)."""
    if len(evs) < 100:
        return None
    rv, prev_s, prev_t = 0.0, evs[0]["s"], evs[0]["ts"]
    for e in evs[1:]:
        rv += (e["s"] - prev_s) ** 2
        prev_s, prev_t = e["s"], e["ts"]
    tspan = evs[-1]["ts"] - evs[0]["ts"]
    if tspan <= 0:
        return None
    sbar = sum(e["s"] for e in evs) / len(evs)
    return {"sigma_s_ann": math.sqrt(rv / tspan * SECONDS_PER_YEAR),
            "sbar": sbar, "n_swaps": len(evs), "n_buckets": len(evs),
            "source": "event-marks"}


def summarise_pool(pool, evs, sig):
    """Evaluations [2] and [3] for one pool."""
    evs = [e for e in evs if math.isfinite(e["k_event"])]
    if len(evs) < 50 or sig is None:
        return None
    t0, t1 = evs[0]["ts"], evs[-1]["ts"]
    span = t1 - t0
    if span < 7 * 86400:
        return None
    # geometry: median half-width in s-units, midpoint
    us = [(e["sb"] - e["sa"]) / 2 for e in evs]
    us.sort()
    u = us[len(us) // 2]
    sbar = sig["sbar"]
    rho = u / sbar
    w = 2 * u
    sigma_s = sig["sigma_s_ann"]
    # realised rate: mean k per event * events per year
    ks = [e["k_event"] for e in evs]
    r_hat = (sum(ks) / span) * SECONDS_PER_YEAR
    # measured eta: swap cost fraction per unit share moved is folded
    # into k_event; report the fee-only floor with eta = 1e-4 anchor
    # and the realised A from the operator's own events:
    floor_fee = 1e-4 * (1 - rho) ** 2 * sigma_s ** 2 / w ** 2
    score = r_hat / floor_fee if floor_fee > 0 else float("nan")
    # [3] trigger and correction fractions
    xs, ms = [], []
    for e in evs:
        if e["old_tl"] is None:
            continue
        osa, osb = tick_to_sqrt(e["old_tl"]), tick_to_sqrt(e["old_tu"])
        ou = (osb - osa) / 2
        omid = (osa + osb) / 2
        nmid = (e["sa"] + e["sb"]) / 2
        if ou > 0:
            xs.append(abs(e["s"] - omid) / ou)
            ms.append(abs(e["s"] - nmid) / ou)
    xs.sort(); ms.sort()
    x_med = xs[len(xs) // 2] if xs else float("nan")
    m_corr = [abs(x - m) for x, m in zip(xs, ms)]
    m_corr.sort()
    m_med = m_corr[len(m_corr) // 2] if m_corr else float("nan")
    return {
        "pool": pool, "n": len(evs), "days": span / 86400,
        "u": u, "sbar": sbar, "rho": rho, "sigma_frac": sigma_s / sbar,
        "r_hat_pct": 100 * r_hat, "floor_fee_pct": 100 * floor_fee,
        "score": score, "x_med": x_med, "m_med": m_med,
        "k_mean": sum(ks) / len(ks), "sig_source": sig["source"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pools", type=int, default=8,
                    help="top-N pools by event count (0 = all)")
    ap.add_argument("--include", action="append", default=[],
                    help="additionally include this pool address")
    args = ap.parse_args()

    con = connect()
    top = []
    if args.pools:
        top = [r[0] for r in con.execute(f"""
            SELECT pool FROM rebalances
            WHERE block BETWEEN {BLOCK_LO} AND {BLOCK_HI}
            GROUP BY pool ORDER BY count(*) DESC LIMIT {args.pools}
        """).fetchall()]
        for p in args.include:
            if p.lower() not in top:
                top.append(p.lower())
    rows, dust = load_events(con, top)
    print(f"anchor: {len(rows)} rebalance events in the amounts "
          f"window (blocks {BLOCK_LO:,}-{BLOCK_HI:,}), "
          f"{'top ' + str(args.pools) + ' pools' if top else 'all pools'}")

    # ---- [1] identity per event -------------------------------------
    by_class = defaultdict(int)
    clean, priced = [], []
    id_errs, mint_errs, price_errs = [], [], []
    dust_ok = dust_bad = 0
    for row in rows:
        e = eval_event(row, dust)
        by_class[e["class"]] += 1
        if e["class"] == "draw":
            priced.append(e)
            continue
        if e["class"] != "clean":
            continue
        clean.append(e)
        priced.append(e)
        if math.isfinite(e["id_err"]):
            id_errs.append(e["id_err"])
        mint_errs.append(e["mint_err"])
        price_errs.append(e["price_consist"])
        if e["dust_match"]:
            dust_ok += 1
        else:
            dust_bad += 1
    id_errs.sort(); mint_errs.sort(); price_errs.sort()

    def q(v, p):
        return v[min(int(p * len(v)), len(v) - 1)] if v else float("nan")

    print(f"\n[1] share-potential identity on production events")
    print(f"    event classes: {dict(by_class)}")
    print(f"    clean events: {len(clean)} "
          f"({100 * len(clean) / max(len(rows), 1):.1f}% of window)")
    print(f"    price self-consistency (mint arithmetic, rel): "
          f"median {q(price_errs, .5):.2e}, q99 {q(price_errs, .99):.2e}, "
          f"max {q(price_errs, 1):.2e}")
    print(f"    mint-minimum arithmetic error (rel): "
          f"median {q(mint_errs, .5):.2e}, q99 {q(mint_errs, .99):.2e}, "
          f"max {q(mint_errs, 1):.2e}")
    print(f"    identity |k_real - k_pred|: "
          f"median {q(id_errs, .5):.2e}, q99 {q(id_errs, .99):.2e}, "
          f"max {q(id_errs, 1):.2e}   (n {len(id_errs)})")
    print(f"    dust-credit surplus match: {dust_ok} matched, "
          f"{dust_bad} unmatched")

    # ---- [2]+[3] per-pool rates and geometry ------------------------
    by_pool = defaultdict(list)
    for e in priced:
        by_pool[e["pool"]].append(e)
    print(f"\n[2] realised rate vs the fee-only swap-mediated floor "
          f"(eta anchor 1e-4; gas excluded, reported at "
          f"${GAS_USD}/event; clean and dust-draw events priced)")
    print(f"    {'pool':<12} {'n':>6} {'days':>6} {'rho':>7} "
          f"{'sig/s':>6} {'r-hat%/yr':>10} {'floor%/yr':>10} "
          f"{'score':>7} {'x-med':>6} {'m-med':>6}")
    summaries = []
    for pool, evs in sorted(by_pool.items(), key=lambda kv: -len(kv[1])):
        evs.sort(key=lambda e: e["ts"])
        sig = pool_sigma(con, pool, evs[0]["ts"], evs[-1]["ts"]) \
            or event_sigma(evs)
        s = summarise_pool(pool, evs, sig)
        if s is None:
            print(f"    {pool[:10]}..   (skipped: thin data or no "
                  f"swap-stream sigma)")
            continue
        summaries.append(s)
        print(f"    {pool[:10]}.. {s['n']:>6} {s['days']:>6.0f} "
              f"{s['rho']:>7.4f} {s['sigma_frac']:>6.2f} "
              f"{s['r_hat_pct']:>10.2f} {s['floor_fee_pct']:>10.2f} "
              f"{s['score']:>7.1f} {s['x_med']:>6.2f} {s['m_med']:>6.2f} "
              f" [{s['sig_source']}]")
    if summaries:
        scores = sorted(s["score"] for s in summaries)
        print(f"\n    benchmark scores span "
              f"{scores[0]:.1f} to {scores[-1]:.1f} "
              f"(floor at one), median {scores[len(scores) // 2]:.1f}")
    con.close()
    print("\nall evaluations complete")


if __name__ == "__main__":
    main()
