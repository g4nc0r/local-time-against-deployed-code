#!/usr/bin/env python3
"""Tier M2: third-party identity and the two-sided floor scatter on
Uniswap V3, Ethereum mainnet.

This is the reading Base cannot give. There, pool Swap logs outnumber
position events by two orders of magnitude and cannot be restricted to
rebalance transactions, so the corrective swap is unobserved, the mark
has to be taken at the mint's own post-swap price, and the realised
cost comes out as a lower bound (`e3-floor-scatter/OUTPUT.md`). On
mainnet the volumes invert: majors carry about 0.12 position events and
2.25 swaps per block, so one stream fits the whole era and the swap is
in hand.

With it the event is priced exactly as the production anchor prices its
own (`verification/anchor/anchor.py`, evaluation [2]):

  holdings after the burn and the in-transaction swap
      h = (b + c) - s          s pool-signed, c the collected fee leg
  pre-swap mark, from the swap's own constant-liquidity arithmetic
      s_mark = s_post - amount1 / L_swap
  realised cost of the event
      k = -log( v_land / v_burn )   at s_mark, v_land componentwise max(m, h)

Marking pre-swap is the whole point: marking at the post-swap price
credits the swap with its own impact, which is what made the Base
reading one-sided. The fee leg is on the input side because a V3
rebalance collects accrued fees in the same transaction, and on Base
that term was the same order as the cost itself.

Also accumulated, for the M3 tier and the floor: per-pool last Swap tick
per block (the tick cache, no second pass needed), the Tier-2 identity
class, firing positions and exit delays.

Era: the mainnet arm's pin, blocks 24,763,430-25,626,973, wall-clock
aligned to the Base census era. Six pools, factory-verified 2026-08-10.

Ungated: Uniswap V3 mainnet only, no census join, no lake writes.

Run detached:
  systemd-run --user --unit=lt-m2 --property=WorkingDirectory="$PWD" \
    bash -lc 'python3 m2_stream.py > m2.log 2>&1'
"""
import gzip
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "third-party"))
sys.path.insert(0, os.path.join(HERE, "..", "e3-floor-scatter"))
import t2_eval  # noqa: E402
import requests  # noqa: E402

PORTAL = "https://portal.sqd.dev/datasets/ethereum-mainnet/finalized-stream"
TOPIC_MINT = ("0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae"
              "16239d0bde")
TOPIC_BURN = ("0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd5"
              "68da98982c")
TOPIC_SWAP = ("0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e"
              "115fbcca67")
TOPIC_COLLECT = ("0x70935338e69775456a85ddef226c395fb668b63fa0115f5f2061"
                 "0b388e6ca9c0")
NFPM = "0xc36442b4a4522e871399cd717abdd847ab11fe88"
ERA_LO, ERA_HI = 24_763_430, 25_626_973
def _load_pools():
    """The pool set is the discovery pass's factory-verified Uniswap V3
    pools (`m2_pools_uni.json`, 47 of the 55 busiest by the census firing
    definition; the other 8 carry V3 event signatures but are not in the
    Uniswap factory and are excluded rather than silently mixed in, the
    mistake the Base census made). Falls back to the six majors."""
    here = os.path.dirname(os.path.abspath(__file__))
    vf = os.path.join(here, "pool_verification.json")
    pf = os.path.join(here, "m2_pools_uni.json")
    if os.path.exists(pf) and os.path.exists(vf):
        keep = set(json.load(open(pf)))
        meta = {v["pool"]: (f"{v['token0'][:6]}/{v['token1'][:6]}",
                            v["fee"])
                for v in json.load(open(vf))["verified"]}
        return {p: meta.get(p, ("?", 500)) for p in keep}
    return {
        "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640": ("USDC/WETH", 500),
        "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8": ("USDC/WETH", 3000),
        "0x11b815efb8f581194ae79006d24e0d814b7697f6": ("WETH/USDT", 500),
        "0x4e68ccd3e89f51c3074ca5072bbac773960dfa36": ("WETH/USDT", 3000),
        "0xcbcdf9626bc03e24f779434178a73a0b4bad62ed": ("WBTC/WETH", 3000),
        "0x99ac8ca7087fa4a2a1fb6357269965a2014abc35": ("WBTC/USDC", 3000),
    }


POOLS = _load_pools()
OUT_CELLS = os.path.join(HERE, "m2_cells.json.gz")
OUT_TICKS = os.path.join(HERE, "m2_ticks.json.gz")
OUT_SUMMARY = os.path.join(HERE, "m2_summary.json")
RESUME = os.path.join(HERE, "m2_resume.json.gz")


def word(d, i, signed=False):
    v = int(d[64 * i:64 * (i + 1)], 16)
    if signed and v >= (1 << 255):
        v -= 1 << 256
    return v


def to_int24(h):
    v = int(h, 16)
    return v - (1 << 256) if v >= (1 << 255) else v


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def post(body, retries=8):
    for i in range(retries):
        try:
            r = requests.post(PORTAL, json=body, stream=True, timeout=180)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 502, 503, 504):
                time.sleep(min(60, 2 ** i))
                continue
            r.raise_for_status()
        except requests.exceptions.RequestException:
            if i == retries - 1:
                raise
            time.sleep(min(60, 2 ** i))
    raise RuntimeError("portal unreachable")


def decode(lg, txs):
    t0 = lg["topics"][0]
    d = lg["data"][2:]
    sender = (txs.get(lg["transactionHash"], {}).get("from") or "").lower()
    if t0 == TOPIC_SWAP:
        return {"kind": "swap", "pool": lg["address"].lower(),
                "tx": lg["transactionHash"],
                "a0": word(d, 0, True), "a1": word(d, 1, True),
                "sqrt": word(d, 2), "liq": word(d, 3),
                "tick": word(d, 4, True)}
    if t0 == TOPIC_COLLECT:
        return {"kind": "collect", "pool": lg["address"].lower(),
                "tx": lg["transactionHash"],
                "owner": ("0x" + lg["topics"][1][-40:]).lower(),
                "tl": to_int24(lg["topics"][2]),
                "tu": to_int24(lg["topics"][3]),
                "a0": word(d, 1), "a1": word(d, 2), "sender": sender}
    kind = "burn" if t0 == TOPIC_BURN else "mint"
    liq = word(d, 0) if kind == "burn" else word(d, 1)
    a0 = word(d, 1) if kind == "burn" else word(d, 2)
    a1 = word(d, 2) if kind == "burn" else word(d, 3)
    return {"kind": kind, "pool": lg["address"].lower(),
            "tx": lg["transactionHash"],
            "owner": ("0x" + lg["topics"][1][-40:]).lower(),
            "tl": to_int24(lg["topics"][2]),
            "tu": to_int24(lg["topics"][3]),
            "liq": liq, "a0": a0, "a1": a1, "sender": sender}


def tsqrt(t):
    return 1.0001 ** (t / 2.0)


def price_event(evs):
    """The anchor's evaluation [2] on one third-party rebalance."""
    burns = [e for e in evs if e["kind"] == "burn" and e["liq"] > 0]
    mints = [e for e in evs if e["kind"] == "mint" and e["liq"] > 0]
    cols = [e for e in evs if e["kind"] == "collect"]
    swaps = [e for e in evs if e["kind"] == "swap"]
    if len(burns) != 1 or len(mints) != 1:
        return None
    b, m = burns[0], mints[0]
    if m["liq"] <= 0:
        return None
    sa, sb = tsqrt(m["tl"]), tsqrt(m["tu"])
    s = sa + m["a1"] / m["liq"]
    if not (sa < s < sb):
        return None
    # fee leg: a full burn's collect returns principal plus fees
    c0 = max(sum(e["a0"] for e in cols) - b["a0"], 0)
    c1 = max(sum(e["a1"] for e in cols) - b["a1"], 0)
    s0 = sum(e["a0"] for e in swaps)
    s1 = sum(e["a1"] for e in swaps)
    h0 = b["a0"] + c0 - s0
    h1 = b["a1"] + c1 - s1
    if h0 < 0 or h1 < 0:
        return None
    # pre-swap mark from the swap's own constant-liquidity arithmetic
    s_mark = s
    if len(swaps) == 1 and swaps[0]["liq"] > 0:
        s_pre = s - s1 / swaps[0]["liq"]
        if s_pre > 0 and abs(s_pre / s - 1) < 0.2:
            s_mark = s_pre
    v_burn = (b["a0"] + c0) * s_mark ** 2 + (b["a1"] + c1)
    v_land = max(m["a0"], h0) * s_mark ** 2 + max(m["a1"], h1)
    if v_burn <= 0 or v_land <= 0:
        return None
    return {"k": -math.log(v_land / v_burn), "u": (sb - sa) / 2.0,
            "s": s, "had_swap": bool(swaps),
            "fee_frac": ((c0 * s_mark ** 2 + c1) / v_burn)
            if v_burn > 0 else 0.0}


def main():
    if os.path.exists(OUT_CELLS):
        print("checkpoint exists; nothing to do")
        return
    state = {"done_to": ERA_LO - 1, "cells": {}, "ticks": {},
             "classes": {},
             "tally": {"firings": 0, "priced": 0, "unpriceable": 0,
                       "with_swap": 0, "clean": 0, "k_negative": 0},
             "id_errs": []}
    if os.path.exists(RESUME):
        with gzip.open(RESUME, "rt") as fp:
            state = json.load(fp)
        log(f"resuming from block {state['done_to']:,}")
    cells, ticks = state["cells"], state["ticks"]
    tally, classes = state["tally"], state["classes"]

    def checkpoint(st):
        tmp = RESUME + ".tmp"
        with gzip.open(tmp, "wt") as fp:
            json.dump(st, fp)
        os.replace(tmp, RESUME)
        log(f"  checkpoint at {st['done_to']:,} "
            f"({st['tally']['firings']:,} firings)")

    log(f"M2: era {ERA_LO:,}-{ERA_HI:,} on {len(POOLS)} mainnet pools")
    cur = state["done_to"] + 1
    last_report = last_ckpt = time.time()
    fails = 0
    while cur <= ERA_HI:
        body = {"type": "evm", "fromBlock": cur, "toBlock": ERA_HI,
                "includeAllBlocks": False,
                "logs": [{"address": list(POOLS),
                          "topic0": [TOPIC_MINT, TOPIC_BURN,
                                     TOPIC_COLLECT, TOPIC_SWAP],
                          "transaction": True}],
                "fields": {"block": {"number": True, "timestamp": True},
                           "log": {"address": True, "topics": True,
                                   "data": True, "logIndex": True,
                                   "transactionHash": True},
                           "transaction": {"hash": True, "from": True}}}
        last = cur - 1
        try:
            r = post(body)
            for line in r.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                last = chunk["header"]["number"]
                txs = {t.get("hash"): t
                       for t in chunk.get("transactions", [])}
                groups = {}
                for lg in chunk.get("logs", []):
                    d = decode(lg, txs)
                    groups.setdefault((d["tx"], d["pool"]), []).append(d)
                for (tx, pool), evs in groups.items():
                    sw = [e for e in evs if e["kind"] == "swap"]
                    if sw:
                        ticks.setdefault(pool, []).append(
                            [last, sw[-1]["tick"]])
                    pos = [e for e in evs if e["kind"] in ("burn", "mint")]
                    if not pos:
                        continue
                    tup = [(e["owner"], e["tl"], e["tu"], e["kind"],
                            e["liq"], e["a0"], e["a1"], e["sender"])
                           for e in pos]
                    op = t2_eval.firing_of(tup, NFPM)
                    if not op:
                        continue
                    tally["firings"] += 1
                    cls, met = t2_eval.identity_of(tup)
                    if cls:
                        classes[cls] = classes.get(cls, 0) + 1
                    if cls == "clean":
                        tally["clean"] += 1
                        state["id_errs"].append(met["id_err"])
                    r2 = price_event(evs)
                    if r2 is None:
                        tally["unpriceable"] += 1
                        continue
                    tally["priced"] += 1
                    if r2["had_swap"]:
                        tally["with_swap"] += 1
                    if r2["k"] < 0:
                        tally["k_negative"] += 1
                    c = cells.setdefault(f"{pool}|{op}",
                                         {"blk": [], "k": [], "u": [],
                                          "fee": [], "sw": []})
                    c["blk"].append(last)
                    c["k"].append(r2["k"])
                    c["u"].append(r2["u"])
                    c["fee"].append(r2["fee_frac"])
                    c["sw"].append(1 if r2["had_swap"] else 0)
                if time.time() - last_report > 120:
                    log(f"  ...at block {last:,} "
                        f"({tally['firings']:,} firings)")
                    last_report = time.time()
                if last - state["done_to"] > 100_000 and \
                        time.time() - last_ckpt > 120:
                    state["done_to"] = last
                    checkpoint(state)
                    last_ckpt = time.time()
            fails = 0
        except (requests.exceptions.RequestException,
                json.JSONDecodeError) as exc:
            fails += 1
            log(f"  transport error at {last:,} "
                f"({type(exc).__name__}); retry {fails}")
            if fails > 20:
                raise
            time.sleep(min(60, 2 ** fails))
        if last < cur:
            if fails:
                continue
            break
        cur = last + 1
        state["done_to"] = last
    ie = sorted(state["id_errs"])
    summary = {
        "era": [ERA_LO, ERA_HI], "pools": POOLS,
        "classes": classes, "tally": tally,
        "n_cells": len(cells),
        "cells_ge30": sum(1 for c in cells.values() if len(c["k"]) >= 30),
        "identity": {"n": len(ie), "median": t2_eval.q(ie, .5),
                     "q99": t2_eval.q(ie, .99), "max": t2_eval.q(ie, 1)},
    }
    with gzip.open(OUT_CELLS, "wt") as fp:
        json.dump(cells, fp)
    with gzip.open(OUT_TICKS, "wt") as fp:
        json.dump(ticks, fp)
    json.dump(summary, open(OUT_SUMMARY, "w"), indent=1)
    log("M2 done: " + json.dumps(summary))


if __name__ == "__main__":
    main()
