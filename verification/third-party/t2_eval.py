"""Shared per-transaction evaluation for the third-party scans.

Two evaluators over one (tx, pool) group of live pool events:

  firing_of(group)      trigger-firing detection for the operator census
                        (burn + mint with a changed range; operator =
                        vault owner, else tx sender)
  identity_of(group)    the share-potential identity on an
                        isolated third-party re-placement, mirroring
                        the production anchor's event discipline
                        (verification/anchor/anchor.py)

A group is a list of tuples (owner, tick_lower, tick_upper, kind,
liquidity, amount0, amount1, sender), integers decoded, addresses
lowercase. Both evaluators are pure; the scanners stream blocks and
keep aggregates only.
"""
import json
import math
import os

# Author and infrastructure exclusion for the third-party subsample: the
# position-manager contract, the corrective router, and the operator's
# depositor wallets. The captured results in this folder were produced with
# that list loaded. It is not published here; point AUTHOR_ADDRS_FILE at a
# JSON file with an "addresses" array to reproduce the captured class split.
# Without it the scan still runs, but the author's own re-placements fall
# into the third-party classes instead of the "author" class, so the counts
# will not match OUTPUT.md.
_AUTHOR_FILE = os.environ.get("AUTHOR_ADDRS_FILE")
AUTHOR_ADDRS = set()
if _AUTHOR_FILE and os.path.exists(_AUTHOR_FILE):
    with open(_AUTHOR_FILE) as _f:
        AUTHOR_ADDRS = {a.lower() for a in json.load(_f)["addresses"]}


def tick_to_sqrt(t):
    return 1.0001 ** (t / 2.0)


def firing_of(group, nfpm):
    """Returns the operator key for one reconstructed trigger firing,
    or None. A firing is a live burn plus a live mint on a changed
    range in one transaction; the operator is the non-custodial owner
    when there is one, else the transaction sender."""
    burns = [e for e in group if e[3] == "burn" and e[4] > 0]
    mints = [e for e in group if e[3] == "mint" and e[4] > 0]
    if not burns or not mints:
        return None
    burn_ranges = {(e[1], e[2]) for e in burns}
    if not any((e[1], e[2]) not in burn_ranges for e in mints):
        return None
    owners = {e[0] for e in burns + mints}
    vaults = sorted(owners - {nfpm})
    if vaults:
        return vaults[0]
    return next((e[7] for e in group if e[7]), None)


def identity_of(group):
    """Classify one group per the anchor's discipline and, when clean,
    evaluate the identity. Returns (cls, metrics_or_None). Classes:
    author, multi, same_range, topup, partial, degenerate, clean."""
    senders = {e[7] for e in group if e[7]}
    owners = {e[0] for e in group}
    if (senders | owners) & AUTHOR_ADDRS:
        return "author", None
    burns = [e for e in group if e[3] == "burn" and e[4] > 0]
    mints = [e for e in group if e[3] == "mint" and e[4] > 0]
    if not burns or not mints:
        return None, None
    if len(burns) != 1 or len(mints) != 1:
        return "multi", None
    _, btl, btu, _, _, h0, h1, _ = burns[0]
    _, tl, tu, _, liq, m0, m1, sender = mints[0]
    if (tl, tu) == (btl, btu):
        return "same_range", None
    if m0 > h0 + 2 or m1 > h1 + 2:
        return "topup", None
    if liq <= 0:
        return "degenerate", None
    sa, sb = tick_to_sqrt(tl), tick_to_sqrt(tu)
    s_from1 = sa + m1 / liq
    inv_s = m0 / liq + 1.0 / sb
    s_from0 = 1.0 / inv_s if inv_s > 0 else float("nan")
    if not (sa < s_from1 < sb):
        return "degenerate", None
    s = s_from1
    price_consist = abs(s_from0 - s_from1) / s_from1
    if m0 <= 2 or m1 <= 2:
        # single-sided limit-order placement (ALM base/limit split);
        # the identity is trivial there (k = 0 with one share at zero)
        return "single_sided", None
    xu = 1.0 / s - 1.0 / sb
    yu = s - sa
    slack0, slack1 = h0 - m0, h1 - m1
    bind0 = slack0 <= xu + 4
    bind1 = slack1 <= yu + 4
    if not (bind0 or bind1):
        return "partial", None
    lp = min(h0 / xu if xu > 0 else float("inf"),
             h1 / yu if yu > 0 else float("inf"))
    v_mint = m0 * s * s + m1
    mint_err = (abs(m0 - (lp * xu if xu > 0 else 0)) * s * s
                + abs(m1 - lp * yu)) / max(v_mint, 1)
    v_before = h0 * s * s + h1
    v_after = m0 * s * s + m1
    if v_before <= 0 or v_after <= 0:
        return "degenerate", None
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
        return "degenerate", None
    return "clean", {
        "id_err": abs(k_real - k_pred),
        "mint_err": mint_err,
        "price_consist": price_consist,
        "operator": sender,
    }


def q(v, p):
    v = sorted(v)
    return v[min(int(p * len(v)), len(v) - 1)] if v else float("nan")
