#!/usr/bin/env python3
"""Tier M2 pool discovery: where does mainnet ALM rebalancing actually live?

The majors-only pool set of the first M2 run produced 2,450 firings over
120 days and four cells at the 30-firing bar, too thin for a census or a
scatter. Either mainnet ALM is far rarer than Base's, or it does not sit
in the majors. This decides which, by sampling Burn events across ALL
Uniswap V3 pools (topic filter, no address filter) and ranking by
rebalance-shaped activity: a burn and a mint of a CHANGED range in one
transaction, which is the census firing definition.
"""
import json, os, sys, time
from collections import defaultdict
import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "third-party"))
import t2_eval

PORTAL = "https://portal.sqd.dev/datasets/ethereum-mainnet/finalized-stream"
T_MINT = "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
T_BURN = "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"
NFPM = "0xc36442b4a4522e871399cd717abdd847ab11fe88"
ERA_LO, ERA_HI = 24_763_430, 25_626_973
WINDOWS, WIDTH = 24, 3_000


def to_int24(h):
    v = int(h, 16)
    return v - (1 << 256) if v >= (1 << 255) else v


def word(d, i):
    return int(d[64 * i:64 * (i + 1)], 16)


fire = defaultdict(int)
cells = defaultdict(set)
step = (ERA_HI - ERA_LO - WIDTH) // (WINDOWS - 1)
t0 = time.time()
for i in range(WINDOWS):
    lo = ERA_LO + i * step
    cur, hi = lo, lo + WIDTH - 1
    while cur <= hi:
        body = {"type": "evm", "fromBlock": cur, "toBlock": hi,
                "includeAllBlocks": False,
                "logs": [{"topic0": [T_MINT, T_BURN], "transaction": True}],
                "fields": {"block": {"number": True},
                           "log": {"address": True, "topics": True,
                                   "data": True, "transactionHash": True},
                           "transaction": {"hash": True, "from": True}}}
        r = requests.post(PORTAL, json=body, stream=True, timeout=180)
        r.raise_for_status()
        last = cur - 1
        for line in r.iter_lines():
            if not line:
                continue
            ch = json.loads(line)
            last = ch["header"]["number"]
            txs = {t.get("hash"): t for t in ch.get("transactions", [])}
            groups = defaultdict(list)
            for lg in ch.get("logs", []):
                d = lg["data"][2:]
                kind = "burn" if lg["topics"][0] == T_BURN else "mint"
                liq = word(d, 0) if kind == "burn" else word(d, 1)
                a0 = word(d, 1) if kind == "burn" else word(d, 2)
                a1 = word(d, 2) if kind == "burn" else word(d, 3)
                sender = (txs.get(lg["transactionHash"], {}).get("from")
                          or "").lower()
                groups[(lg["transactionHash"], lg["address"].lower())].append(
                    (("0x" + lg["topics"][1][-40:]).lower(),
                     to_int24(lg["topics"][2]), to_int24(lg["topics"][3]),
                     kind, liq, a0, a1, sender))
            for (tx, pool), g in groups.items():
                op = t2_eval.firing_of(g, NFPM)
                if op:
                    fire[pool] += 1
                    cells[pool].add(op)
        if last < cur:
            break
        cur = last + 1
    print(f"  window {i+1}/{WINDOWS}: {sum(fire.values())} firings, "
          f"{len(fire)} pools ({time.time()-t0:.0f}s)", flush=True)

top = sorted(fire.items(), key=lambda kv: -kv[1])[:60]
out = [{"pool": p, "sampled_firings": n, "sampled_operators": len(cells[p])}
       for p, n in top]
json.dump({"sampled_blocks": WINDOWS * WIDTH, "era": [ERA_LO, ERA_HI],
           "total_sampled_firings": sum(fire.values()),
           "distinct_pools": len(fire), "top": out},
          open("discovery.json", "w"), indent=1)
print(f"\ntotal {sum(fire.values())} firings across {len(fire)} pools; "
      f"top 15:")
for r in out[:15]:
    print(f"  {r['pool']} {r['sampled_firings']:>5} firings "
          f"{r['sampled_operators']:>3} operators")
