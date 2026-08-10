"""Session E item 2: third-party Liquidity Book identity anchor.

Shaped like the V3-class anchor (mirrors t2_eval.py's event discipline): locate
isolated third-party burn+re-mint sequences on deployed LBPairs v2.2 on
Avalanche C-Chain from public events (WithdrawnFromBins /
DepositedToBins, schema read from lfj-gg/joe-v2 commit 067c6cc), and
reconstruct the Appendix H (app:lb) algebra on each from event payloads
plus one pre-state read per sequence. Sparse eth_getLogs only; no SQD,
no lake producer, no census.

Isolation criterion (the LB analogue of the Base Tier-2 "isolated
interior re-placement" discipline). A probe of 10k blocks found zero
same-transaction burn+mint pairs on these deployments (LB rebalancing
on Avalanche routes withdraw and redeposit as separate transactions),
so the sequence shape is the charter's block-window form:
  - one WithdrawnFromBins transaction followed by one DepositedToBins
    transaction on the SAME pair from the SAME transaction sender
    within WINDOW blocks (nearest deposit only);
  - each of the two transactions is the pair's only event-emitting
    transaction in its own block (same-block pairs allowed when the
    block holds exactly these two), so block-boundary state is exact
    pre-state for each leg;
  - no pair event of any kind (swaps included) from any other
    transaction in the closed block interval between them, and no
    same-pair Swap inside either transaction;
  - the pair is registered to the v2.2 factory (the deployment lineage
    of commit 067c6cc).
Sequences failing any clause are counted and excluded, never relaxed.

Per-sequence checks, all in exact integer arithmetic (the bin price
P(i) is replicated bit-exactly from Uint128x128Math.pow):
  W  (burn identity)   per bin: withdrawn amounts equal
                       floor(shares * reserve / supply) on both legs,
                       and the value form: withdrawn depth over bin
                       depth equals the burned share fraction,
                       residual r_W = |v_out*S - sh*L_bin| / (sh*L_bin).
  D  (mint identity)   per non-active bin: single-sidedness (base above
                       the active id, quote below) and the share-
                       potential form r_D = |sh*L_bin - L_in*S| /
                       (L_in*S); fresh bins (S=0) check shares =
                       isqrt(L_in) exactly.
  CF (composition fee) where a CompositionFees event fired: the fee
                       replicated through getSharesAndEffectiveAmountsIn
                       -> getCompositionFees -> eta(1+eta) at the
                       pair's updated parameters, residual relative on
                       the fee, plus the protocol split exact.

Author exclusion: the Base Tier-2 author/infra set is Base-specific;
the author operates nothing on Avalanche, so every sender here is
third-party by construction (the filter is retained vacuously).

Output: t5b_lb_avax.json (all residuals, classes, per-pair counts).
Run:  python3 lb_anchor.py
"""

import json
import math
import os
import sys
import time
import urllib.request

RPC = os.environ.get("RPC_AVAX_ALCHEMY")
if not RPC:
    sys.exit("RPC_AVAX_ALCHEMY not set")

PIN = 92_430_000          # the fork suite's pin: scan ends here
SPAN = int(os.environ.get("T5B_SPAN", 3_000_000))   # ~2 months at ~1.8 s
CHUNK = 2_000
FACTORY_V22 = "0xb43120c4745967fa9b93e79c149e66b0f2d6fe0c"

T_WITHDRAWN = "0xa32e146844d6144a22e94c586715a1317d58a8aa3581ec33d040113ddcb24350"
T_DEPOSITED = "0x87f1f9dcf5e8089a3e00811b6a008d8f30293a3da878cb1fe8c90ca376402f8a"
T_COMPFEES = "0x3f0b46725027bb418b2005f4683538eccdbcdf1de2b8649a29dbd9c507d16ff4"
T_TRANSFER = "0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb"
T_SWAP = "0xad7d6f97abf51ce18e17a38f4d70e975be9c0708474987bb3e26ad21bd93ca70"

SCALE = 1 << 128
PRECISION = 10**18
BASIS = 10_000

_rpc_id = 0


def rpc(method, params, retries=5):
    global _rpc_id
    _rpc_id += 1
    body = json.dumps({"jsonrpc": "2.0", "id": _rpc_id, "method": method,
                       "params": params}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                RPC, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                out = json.loads(r.read())
            if "error" in out:
                msg = str(out["error"])
                if "execution reverted" in msg:
                    raise RuntimeError(msg)
                time.sleep(1.5 * (attempt + 1))
                continue
            return out["result"]
        except RuntimeError:
            raise
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"rpc failed: {method}")


def call(to, data, block):
    return rpc("eth_call", [{"to": to, "data": data}, hex(block)])


def rpc_batch(calls, retries=5):
    """calls: list of (method, params); returns results in order."""
    global _rpc_id
    payload = []
    for m, p in calls:
        _rpc_id += 1
        payload.append({"jsonrpc": "2.0", "id": _rpc_id, "method": m,
                        "params": p})
    body = json.dumps(payload).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                RPC, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                out = json.loads(r.read())
            by_id = {o["id"]: o for o in out}
            return [by_id[p["id"]].get("result",
                                       by_id[p["id"]].get("error"))
                    for p in payload]
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("rpc batch failed")


# ---- bit-exact replication of Uint128x128Math.pow (commit 067c6cc) ------

def lb_base(bin_step):
    return SCALE + ((bin_step << 128) // BASIS)


def lb_pow(x, y):
    """base**y in 128.128, replicating the contract's squaring loop."""
    if y == 0:
        return SCALE
    invert = False
    abs_y = y
    if y < 0:
        abs_y = -y
        invert = True
    if abs_y >= 0x100000:
        raise ValueError("exponent out of range")
    result = SCALE
    squared = x
    if x > (SCALE - 1):
        squared = ((1 << 256) - 1) // squared
        invert = not invert
    for bit in range(20):
        if abs_y & (1 << bit):
            result = (result * squared) >> 128
        squared = (squared * squared) >> 128
    if result == 0:
        raise ValueError("pow underflow")
    return ((1 << 256) - 1) // result if invert else result


def price_of(bin_id, bin_step):
    return lb_pow(lb_base(bin_step), bin_id - (1 << 23))


def isqrt_contract(x):
    """Uint256x256Math.sqrt: seven Newton steps from a msb seed, capped."""
    if x == 0:
        return 0
    s = 1 << (x.bit_length() - 1) // 2
    for _ in range(7):
        s = (s + x // s) >> 1
    return min(s, x // s)


def liquidity(x, y, price):
    return price * x + (y << 128)


# ---- decoding helpers ---------------------------------------------------

def dec_amounts(b32):
    v = int(b32, 16)
    return v & (SCALE - 1), v >> 128       # (amountX, amountY)


def dec_arrays(data_hex):
    """abi-decode (uint256[] ids, bytes32[] amounts) from event data."""
    d = bytes.fromhex(data_hex[2:])
    w = lambda i: int.from_bytes(d[32 * i:32 * (i + 1)], "big")
    off_ids, off_am = w(0) // 32, w(1) // 32
    n = w(off_ids)
    ids = [w(off_ids + 1 + i) for i in range(n)]
    ams = ["0x" + d[32 * (off_am + 1 + i):32 * (off_am + 2 + i)].hex()
           for i in range(w(off_am))]
    return ids, ams


# ---- phase 1: chain-wide sparse scan ------------------------------------

WINDOW = int(os.environ.get("T5B_WINDOW", 50))
# max blocks from withdraw to redeposit (~100 s). The isolation clauses
# below (sole tx per block, empty closed interval) carry the correctness
# burden; the window only bounds what counts as one sequence.

CKPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "scan_events.jsonl")


def scan():
    """Per-pair event streams: pair -> sorted [(block, kind, txhash)].
    Chunk results checkpoint to scan_events.jsonl; a rerun resumes."""
    lo = PIN - SPAN
    done_from = lo
    streams = {}
    nw = nd = 0

    def add(pair, blk, kind, txh):
        nonlocal nw, nd
        streams.setdefault(pair, []).append((blk, kind, txh))
        if kind == "W":
            nw += 1
        else:
            nd += 1

    if os.path.exists(CKPT):
        pending = []
        with open(CKPT) as f:
            for line in f:
                rec = json.loads(line)
                if rec[0] == "chunk":
                    done_from = max(done_from, rec[1] + 1)
                    for p in pending:
                        add(p[1], p[2], p[3], p[4])
                    pending = []
                else:
                    pending.append(rec)
        # trailing events with no chunk marker (crash mid-chunk) are
        # dropped; their chunk re-scans
    for start in range(done_from, PIN, CHUNK):
        end = min(start + CHUNK - 1, PIN - 1)
        rows = []
        for topic, kind in ((T_WITHDRAWN, "W"), (T_DEPOSITED, "D")):
            logs = rpc("eth_getLogs", [{
                "fromBlock": hex(start), "toBlock": hex(end),
                "topics": [topic]}])
            for lg in logs:
                pair = lg["address"].lower()
                blk = int(lg["blockNumber"], 16)
                add(pair, blk, kind, lg["transactionHash"])
                rows.append(["ev", pair, blk, kind, lg["transactionHash"]])
        with open(CKPT, "a") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
            f.write(json.dumps(["chunk", end]) + "\n")
        if (start - lo) % 100_000 < CHUNK:
            print(f"  scan at block {start:,} ({nw} W / {nd} D)", flush=True)
    for v in streams.values():
        v.sort()
    return streams, nw, nd


def window_candidates(streams):
    """(pair, wtx, wblock, dtx, dblock): each withdraw tx paired with the
    nearest following deposit tx on the same pair within WINDOW blocks."""
    out = []
    for pair, evs in streams.items():
        w_seen, d_seen = set(), set()
        for i, (blk, kind, txh) in enumerate(evs):
            if kind != "W" or txh in w_seen:
                continue
            w_seen.add(txh)
            for blk2, kind2, txh2 in evs[i:]:
                if blk2 > blk + WINDOW:
                    break
                if kind2 == "D" and txh2 != txh and txh2 not in d_seen:
                    d_seen.add(txh2)
                    out.append((pair, txh, blk, txh2, blk2))
                    break
    return sorted(out, key=lambda c: c[2])


# ---- phase 2/3: receipts, factory filter, isolation ---------------------

FACT_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "factory_cache.json")
_factory_cache = {}
if os.path.exists(FACT_CACHE):
    _factory_cache = json.load(open(FACT_CACHE))


def prefetch_factories(pairs):
    todo = [p for p in pairs if p not in _factory_cache]
    for lo in range(0, len(todo), 100):
        batch = todo[lo:lo + 100]
        outs = rpc_batch([("eth_call",
                           [{"to": p, "data": "0x88cc58e4"}, hex(PIN)])
                          for p in batch])
        for p, out in zip(batch, outs):
            _factory_cache[p] = ("0x" + out[-40:]) \
                if isinstance(out, str) and len(out) >= 42 else "none"
    with open(FACT_CACHE, "w") as f:
        json.dump(_factory_cache, f)


def factory_of(pair):
    if pair not in _factory_cache:
        prefetch_factories([pair])
    return _factory_cache[pair]


def pair_logs_in_block(pair, block):
    return rpc("eth_getLogs", [{
        "fromBlock": hex(block), "toBlock": hex(block),
        "address": pair}])


# ---- phase 4/5: pre-state and evaluation --------------------------------

def prestate(pair, bin_ids, block):
    """getBin + totalSupply per bin, active id, bin step, fee params at
    the block before the sequence."""
    b = block - 1
    st = {"bins": {}, "supply": {}}
    st["active"] = int(call(pair, "0xdbe65edc", b), 16)
    st["bin_step"] = int(call(pair, "0x17f11ecc", b), 16)
    for bid in sorted(bin_ids):
        out = call(pair, "0x0abe9688" + hex(bid)[2:].zfill(64), b)
        raw = out[2:]
        st["bins"][bid] = (int(raw[0:64], 16), int(raw[64:128], 16))
        sup = call(pair, "0xbd85b039" + hex(bid)[2:].zfill(64), b)
        st["supply"][bid] = int(sup, 16)
    raw = call(pair, "0x7ca0de30", b)[2:]
    st["static"] = [int(raw[64 * i:64 * (i + 1)], 16) for i in range(7)]
    raw = call(pair, "0x8d7024e5", b)[2:]
    st["variable"] = [int(raw[64 * i:64 * (i + 1)], 16) for i in range(4)]
    return st


def total_fee(st, ts):
    """updateReferences + updateVolatilityAccumulator at the active id,
    then getTotalFee, replicated from PairParameterHelper."""
    base_factor, filter_p, decay_p, reduction, var_ctrl, _, max_vol = st["static"]
    vol_acc, vol_ref, id_ref, t_last = st["variable"]
    dt = ts - t_last
    if dt >= filter_p:
        id_ref = st["active"]
        vol_ref = (vol_acc * reduction // BASIS) if dt < decay_p else 0
    delta = abs(st["active"] - id_ref)
    vol_acc = min(vol_ref + delta * BASIS, max_vol)
    base_fee = base_factor * st["bin_step"] * 10**10
    var_fee = 0
    if var_ctrl:
        prod = vol_acc * st["bin_step"]
        var_fee = (prod * prod * var_ctrl + 99) // 100
    return base_fee + var_fee


def get_composition_fee(amount, f):
    return amount * f * (f + PRECISION) // (PRECISION * PRECISION)


def evaluate(seq, st, ts):
    """Apply the tx's pair events in log order against the pre-state and
    emit per-bin residuals."""
    bins = {b: list(v) for b, v in st["bins"].items()}
    supply = dict(st["supply"])
    active = st["active"]
    bstep = st["bin_step"]
    res = {"rW": [], "rD": [], "rCF": [], "cf_commit_gap": [],
           "exactW": 0, "inexactW": 0,
           "sided_ok": 0, "sided_bad": 0, "fresh_ok": 0, "fresh_bad": 0,
           "cf_events": 0, "cf_matched": 0, "cf_shares_exact": 0,
           "notes": []}
    pending_burn_shares = None
    pending_mint_shares = None
    cf_by_id = {}
    for ev in seq:
        kind = ev["kind"]
        if kind == "tb_burn":
            pending_burn_shares = dict(zip(ev["ids"], ev["shares"]))
        elif kind == "tb_mint":
            pending_mint_shares = dict(zip(ev["ids"], ev["shares"]))
        elif kind == "cf":
            res["cf_events"] += 1
            cf_by_id[ev["id"]] = ev
        elif kind == "withdraw":
            for bid, am in zip(ev["ids"], ev["amounts"]):
                sh = pending_burn_shares[bid]
                X, Y = bins[bid]
                S = supply[bid]
                x_out, y_out = dec_amounts(am)
                xp, yp = sh * X // S, sh * Y // S
                if (x_out, y_out) == (xp, yp):
                    res["exactW"] += 1
                else:
                    res["inexactW"] += 1
                P = price_of(bid, bstep)
                v_out = liquidity(x_out, y_out, P)
                l_bin = liquidity(X, Y, P)
                if sh * l_bin:
                    res["rW"].append(abs(v_out * S - sh * l_bin) / (sh * l_bin))
                bins[bid] = [X - x_out, Y - y_out]
                supply[bid] = S - sh
        elif kind == "deposit":
            for bid, am in zip(ev["ids"], ev["amounts"]):
                sh = pending_mint_shares[bid]
                X, Y = bins.get(bid, [0, 0])
                S = supply.get(bid, 0)
                x_in, y_in = dec_amounts(am)
                P = price_of(bid, bstep)
                if bid != active:
                    ok = (y_in == 0) if bid > active else (x_in == 0)
                    res["sided_ok" if ok else "sided_bad"] += 1
                l_in = liquidity(x_in, y_in, P)
                if S == 0 or liquidity(X, Y, P) == 0:
                    ok = sh == isqrt_contract(l_in)
                    res["fresh_ok" if ok else "fresh_bad"] += 1
                elif bid == active and bid in cf_by_id:
                    cf = cf_by_id[bid]
                    fee_x, fee_y = dec_amounts(cf["total"])
                    pf_x, pf_y = dec_amounts(cf["protocol"])
                    # amountsIn as getCompositionFees saw them
                    ax, ay = x_in + pf_x, y_in + pf_y
                    l_bin = liquidity(X, Y, P)
                    sh_pre = liquidity(ax, ay, P) * S // l_bin
                    rx = (sh_pre * (X + ax)) // (S + sh_pre)
                    ry = (sh_pre * (Y + ay)) // (S + sh_pre)
                    f = total_fee(st, ts)
                    if rx > ax:
                        fee_pred = get_composition_fee(ay - ry, f)
                        fee_evt, pf_evt, share = fee_y, pf_y, "y"
                    elif ry > ay:
                        fee_pred = get_composition_fee(ax - rx, f)
                        fee_evt, pf_evt, share = fee_x, pf_x, "x"
                    else:
                        fee_pred, fee_evt, pf_evt, share = 0, 0, 0, "-"
                    if fee_evt:
                        res["rCF"].append(abs(fee_pred - fee_evt) / fee_evt)
                        proto_share = st["static"][5]
                        if pf_evt == fee_evt * proto_share // BASIS:
                            res["cf_matched"] += 1
                    # Final-shares identity. The Avalanche v2.2
                    # implementation predates joe-v2 commit 7e5b0b4
                    # ("Fix the composition fee calculation", 2024-07-04,
                    # an ancestor of 067c6cc): deployed code divides by
                    # the ORIGINAL bin liquidity; the commit divides by
                    # bin + net fee. We assert the deployed law and
                    # record the commit-form gap as the measured
                    # divergence per event.
                    ux, uy = ax - fee_x, ay - fee_y
                    u_l = liquidity(ux, uy, P)
                    b_dep = liquidity(X, Y, P)
                    b_com = liquidity(X + fee_x - pf_x, Y + fee_y - pf_y, P)
                    if u_l * S:
                        if sh == u_l * S // b_dep:
                            res["cf_shares_exact"] += 1
                        res["rD"].append(
                            abs(sh * b_dep - u_l * S) / (u_l * S))
                        res["cf_commit_gap"].append(
                            abs(sh * b_com - u_l * S) / (u_l * S))
                else:
                    l_bin = liquidity(X, Y, P)
                    if l_in * S:
                        res["rD"].append(abs(sh * l_bin - l_in * S) / (l_in * S))
                bins[bid] = [X + x_in, Y + y_in]
                supply[bid] = S + sh
        elif kind == "swap":
            res["notes"].append("swap")   # should have been excluded
    return res


_receipt_cache = {}


def receipt(txh):
    if txh not in _receipt_cache:
        _receipt_cache[txh] = rpc("eth_getTransactionReceipt", [txh])
    return _receipt_cache[txh]


def tx_seq(rec, pair):
    """(seq, touched_bins, has_swap) for one tx's events on one pair."""
    seq, touched, has_swap = [], set(), False
    for lg in rec["logs"]:
        if lg["address"].lower() != pair:
            continue
        t = lg["topics"][0]
        if t == T_SWAP:
            has_swap = True
        elif t == T_TRANSFER:
            ids, raw = dec_arrays(lg["data"])
            shares = [int(a, 16) for a in raw]
            frm = "0x" + lg["topics"][2][-40:]
            to = "0x" + lg["topics"][3][-40:]
            if to == "0x" + "0" * 40:
                seq.append({"kind": "tb_burn", "ids": ids, "shares": shares})
            elif frm == "0x" + "0" * 40:
                seq.append({"kind": "tb_mint", "ids": ids, "shares": shares})
        elif t == T_WITHDRAWN:
            ids, ams = dec_arrays(lg["data"])
            touched.update(ids)
            seq.append({"kind": "withdraw", "ids": ids, "amounts": ams})
        elif t == T_DEPOSITED:
            ids, ams = dec_arrays(lg["data"])
            touched.update(ids)
            seq.append({"kind": "deposit", "ids": ids, "amounts": ams})
        elif t == T_COMPFEES:
            d = lg["data"][2:]
            seq.append({"kind": "cf",
                        "id": int(d[0:64], 16),
                        "total": "0x" + d[64:128],
                        "protocol": "0x" + d[128:192]})
    return seq, touched, has_swap


def merge_res(a, b):
    for k, v in b.items():
        a[k] = a[k] + v
    return a


def main():
    t0 = time.time()
    print(f"scan: blocks {PIN - SPAN:,} .. {PIN:,}", flush=True)
    streams, nw, nd = scan()
    # factory filter first: only pairs registered to the v2.2 factory
    # (the commit's deployment lineage) enter pairing at all
    prefetch_factories(list(streams))
    v22_streams = {p: v for p, v in streams.items()
                   if factory_of(p) == FACTORY_V22}
    other_pairs = len(streams) - len(v22_streams)
    cands = window_candidates(v22_streams)
    print(f"raw: {nw} withdraw events, {nd} deposit events, "
          f"{len(streams)} pairs ({len(v22_streams)} v2.2, "
          f"{other_pairs} other-factory excluded), "
          f"{len(cands)} v2.2 window candidates "
          f"(<= {WINDOW} blocks; {time.time() - t0:.0f}s)", flush=True)

    counts = {"window_candidates": len(cands),
              "pairs_other_factory": other_pairs,
              "sender_mismatch": 0, "swap_in_tx": 0,
              "interleaved": 0, "receipt_missing": 0, "isolated": 0}
    per_pair = {}
    all_rW, all_rD, all_rCF, all_cfgap = [], [], [], []
    agg = {"exactW": 0, "inexactW": 0, "sided_ok": 0, "sided_bad": 0,
           "fresh_ok": 0, "fresh_bad": 0, "cf_events": 0, "cf_matched": 0,
           "cf_shares_exact": 0}
    sequences = []
    senders = set()
    ts_cache = {}
    gaps = []

    def block_ts(n):
        if n not in ts_cache:
            blk = rpc("eth_getBlockByNumber", [hex(n), False])
            ts_cache[n] = int(blk["timestamp"], 16)
        return ts_cache[n]

    for (pair, wtx, wblk, dtx, dblk) in cands:
        wrec, drec = receipt(wtx), receipt(dtx)
        if not wrec or not drec:
            counts["receipt_missing"] += 1
            continue
        if wrec["from"].lower() != drec["from"].lower():
            counts["sender_mismatch"] += 1
            continue
        wseq, wtouched, wswap = tx_seq(wrec, pair)
        dseq, dtouched, dswap = tx_seq(drec, pair)
        if wswap or dswap:
            counts["swap_in_tx"] += 1
            continue
        # closed-interval interleave check: nothing but these two txs
        interval = rpc("eth_getLogs", [{
            "fromBlock": hex(wblk), "toBlock": hex(dblk), "address": pair}])
        if {lg["transactionHash"] for lg in interval} != {wtx, dtx}:
            counts["interleaved"] += 1
            continue

        if wblk == dblk:
            if int(wrec["transactionIndex"], 16) > int(drec["transactionIndex"], 16):
                # deposit precedes withdraw: not a burn+re-mint sequence
                counts["d_before_w"] = counts.get("d_before_w", 0) + 1
                continue
            st = prestate(pair, wtouched | dtouched, wblk)
            r = evaluate(wseq + dseq, st, block_ts(wblk))
        else:
            st_w = prestate(pair, wtouched, wblk)
            st_d = prestate(pair, dtouched, dblk)
            r = merge_res(evaluate(wseq, st_w, block_ts(wblk)),
                          evaluate(dseq, st_d, block_ts(dblk)))

        counts["isolated"] += 1
        senders.add(wrec["from"].lower())
        per_pair[pair] = per_pair.get(pair, 0) + 1
        gaps.append(dblk - wblk)
        all_rW += r["rW"]
        all_rD += r["rD"]
        all_rCF += r["rCF"]
        all_cfgap += r["cf_commit_gap"]
        for k in agg:
            agg[k] += r[k]
        sequences.append({
            "w_tx": wtx, "d_tx": dtx, "pair": pair,
            "blocks": [wblk, dblk],
            "sender": wrec["from"].lower(),
            "bins": len(wtouched | dtouched),
            "same_bins": sorted(wtouched) == sorted(dtouched),
            "rW_max": max(r["rW"], default=None),
            "rD_max": max(r["rD"], default=None),
            "rCF": r["rCF"]})

    def stats(v):
        if not v:
            return None
        s = sorted(v)
        n = len(s)
        return {"n": n, "median": s[n // 2], "q99": s[min(int(0.99 * n), n - 1)],
                "max": s[-1]}

    out = {
        "scan": {"chain": "avalanche-c", "from_block": PIN - SPAN,
                 "to_block": PIN, "factory": FACTORY_V22,
                 "source_commit": "067c6cc", "window_blocks": WINDOW,
                 "raw_withdraw_events": nw, "raw_deposit_events": nd,
                 "pairs_seen": len(streams)},
        "gap_blocks": sorted(gaps),
        "counts": counts,
        "n_senders": len(senders),
        "per_pair": per_pair,
        "checks": agg,
        "residuals": {"rW": stats(all_rW), "rD": stats(all_rD),
                      "rCF": stats(all_rCF),
                      "cf_commit_gap": stats(all_cfgap)},
        "sequences": sequences,
    }
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "t5b_lb_avax.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in
                      ("counts", "n_senders", "checks", "residuals")}, indent=1))
    print(f"done in {time.time() - t0:.0f}s; "
          f"{len(sequences)} isolated sequences written", flush=True)


if __name__ == "__main__":
    main()
