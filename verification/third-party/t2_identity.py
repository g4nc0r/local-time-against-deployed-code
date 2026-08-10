#!/usr/bin/env python3
"""Tier 2: the share-potential identity on third-party rebalances.

Replicates the production anchor's methodology (verification/
anchor.py, evaluation [1]) on operators other than the one it records,
reconstructed from public pool events on either venue. Input is an
events checkpoint in the WS0 tuple format: (block, tx, pool, owner,
tick_lower, tick_upper, kind, liquidity, amount0, amount1, sender).

Event classification per (tx, pool) group, mirroring the anchor's
discipline:
  multi        more than one live burn or more than one mint
  degenerate   unpriceable (mint arithmetic inconsistent, or holdings
               negative)
  topup        the mint draws tokens beyond the burn's holdings (fee
               compounding, external funds, or an in-tx swap); priced
               out of the identity subsample, tabulated
  partial      neither side of the holdings is consumed to sub-unit
               slack (the operator re-minted only part of the
               withdrawal); excluded, tabulated
  clean        isolated full re-placement; the identity is evaluated

For clean events: the price is recovered from the mint's own
arithmetic two ways (consistency reported), the mint-minimum
L' = min(h0/x_u, h1/y_u) is checked against the actual mint liquidity,
and |k_real - k_pred| is reported with k_pred the max-log share form.
Author events are excluded by sender/owner address.

Usage:
  python3 t2_identity.py --events <events.json.gz> --venue <name> \
      [--exclude 0x...,0x...] [--out results.json]
"""
import argparse
import gzip
import json
import math
from collections import defaultdict


def tick_to_sqrt(t):
    return 1.0001 ** (t / 2.0)


def load_events(path):
    with gzip.open(path, "rt") as f:
        return json.load(f)


def evaluate(events, exclude):
    groups = defaultdict(list)
    for blk, tx, pool, owner, tl, tu, kind, liq, a0, a1, sender in events:
        groups[(tx, pool)].append(
            (owner.lower(), tl, tu, kind, int(liq), int(a0), int(a1),
             sender.lower())
        )

    classes = defaultdict(int)
    id_errs, mint_errs, price_errs, slacks = [], [], [], []
    per_op = defaultdict(int)
    n_author = 0

    for (tx, pool), evs in groups.items():
        burns = [e for e in evs if e[3] == "burn" and e[4] > 0]
        mints = [e for e in evs if e[3] == "mint" and e[4] > 0]
        if not burns or not mints:
            continue
        senders = {e[7] for e in evs if e[7]}
        owners = {e[0] for e in evs}
        if (senders | owners) & exclude:
            n_author += 1
            continue
        if len(burns) != 1 or len(mints) != 1:
            classes["multi"] += 1
            continue
        _, _, _, _, _, h0, h1, _ = burns[0]
        _, tl, tu, _, liq, m0, m1, sender = mints[0]
        if (tl, tu) == (burns[0][1], burns[0][2]):
            classes["same_range"] += 1
            continue
        if m0 > h0 + 2 or m1 > h1 + 2:
            classes["topup"] += 1
            continue
        # price from the mint's own arithmetic
        sa, sb = tick_to_sqrt(tl), tick_to_sqrt(tu)
        if liq <= 0:
            classes["degenerate"] += 1
            continue
        s_from1 = sa + m1 / liq
        inv_s = m0 / liq + 1.0 / sb
        s_from0 = 1.0 / inv_s if inv_s > 0 else float("nan")
        if not (sa < s_from1 < sb):
            classes["degenerate"] += 1
            continue
        s = s_from1
        price_consist = abs(s_from0 - s_from1) / s_from1
        # binding-side slack: one side must be consumed to sub-unit slack
        xu = 1.0 / s - 1.0 / sb
        yu = s - sa
        unit0 = xu  # token0 per unit liquidity
        unit1 = yu
        slack0 = h0 - m0
        slack1 = h1 - m1
        bind0 = slack0 <= unit0 + 4
        bind1 = slack1 <= unit1 + 4
        if not (bind0 or bind1):
            classes["partial"] += 1
            continue
        classes["clean"] += 1
        per_op[sender] += 1
        # mint-minimum arithmetic, value-weighted error
        lp = min(h0 / xu if xu > 0 else float("inf"),
                 h1 / yu if yu > 0 else float("inf"))
        v_mint = m0 * s * s + m1
        mint_err = (abs(m0 - (lp * xu if xu > 0 else 0)) * s * s
                    + abs(m1 - lp * yu)) / max(v_mint, 1)
        # identity
        v_before = h0 * s * s + h1
        v_after = m0 * s * s + m1
        if v_before <= 0 or v_after <= 0:
            classes["clean"] -= 1
            classes["degenerate"] += 1
            continue
        k_real = -math.log(v_after / v_before)
        w0 = h0 * s * s / v_before
        w1 = h1 / v_before
        w0p = m0 * s * s / v_after
        w1p = m1 / v_after
        if w0 > 0 and w1 > 0 and w0p > 0 and w1p > 0:
            k_pred = max(math.log(w0p / w0), math.log(w1p / w1))
        elif (w0 == 0 and w0p == 0) or (w1 == 0 and w1p == 0):
            k_pred = k_real
        else:
            classes["clean"] -= 1
            classes["degenerate"] += 1
            continue
        id_errs.append(abs(k_real - k_pred))
        mint_errs.append(mint_err)
        price_errs.append(price_consist)
        slacks.append(min(slack0 / unit0 if unit0 > 0 else 0,
                          slack1 / unit1 if unit1 > 0 else 0))

    return classes, id_errs, mint_errs, price_errs, slacks, per_op, n_author


def q(v, p):
    v = sorted(v)
    return v[min(int(p * len(v)), len(v) - 1)] if v else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", required=True)
    ap.add_argument("--venue", required=True)
    ap.add_argument("--exclude", default="",
                    help="comma-separated author/infra addresses to exclude")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    exclude = {a.strip().lower() for a in args.exclude.split(",") if a.strip()}
    events = load_events(args.events)
    (classes, id_errs, mint_errs, price_errs, slacks, per_op,
     n_author) = evaluate(events, exclude)

    n_ops = len(per_op)
    ops10 = sum(1 for v in per_op.values() if v >= 10)
    print(f"t2_identity [{args.venue}]: {len(events)} events, "
          f"{sum(classes.values())} rebalance groups after author exclusion "
          f"({n_author} author/infra groups excluded)")
    print(f"  classes: {dict(classes)}")
    print(f"  clean third-party rebalances: {classes['clean']} across "
          f"{n_ops} operators ({ops10} with >= 10)")
    print(f"  identity |k_real - k_pred|: median {q(id_errs, .5):.2e}, "
          f"q99 {q(id_errs, .99):.2e}, max {q(id_errs, 1):.2e}")
    print(f"  mint-minimum error (value-weighted): median "
          f"{q(mint_errs, .5):.2e}, q99 {q(mint_errs, .99):.2e}, "
          f"max {q(mint_errs, 1):.2e}")
    print(f"  price self-consistency: median {q(price_errs, .5):.2e}, "
          f"q99 {q(price_errs, .99):.2e}")
    print(f"  binding-side slack (liquidity units): median "
          f"{q(slacks, .5):.2e}, q99 {q(slacks, .99):.2e}")

    if args.out:
        json.dump(
            {"venue": args.venue, "n_events": len(events),
             "classes": dict(classes), "n_author_excluded": n_author,
             "n_operators": n_ops, "n_ops_ge10": ops10,
             "id_err": {"median": q(id_errs, .5), "q99": q(id_errs, .99),
                        "max": q(id_errs, 1), "n": len(id_errs)},
             "mint_err": {"median": q(mint_errs, .5),
                          "q99": q(mint_errs, .99), "max": q(mint_errs, 1)},
             "price_consist": {"median": q(price_errs, .5),
                               "q99": q(price_errs, .99)}},
            open(args.out, "w"), indent=1)
        print(f"  written: {args.out}")


if __name__ == "__main__":
    main()
