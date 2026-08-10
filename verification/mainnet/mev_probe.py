#!/usr/bin/env python3
"""The MEV probe: does the extraction regime change what the
instrument reads?

Everything the programme has measured sits on Base, a single sequencer
with no contested mempool. Ethereum mainnet has proposer-builder
separation and an extraction industry. Before the mainnet arm's
census-scale tiers are worth running, four numbers decide whether the
instrument is reading the same object on both chains. This probe
measures them on matched pairs in a matched wall-clock window.

  A  firing position u in the operator's previous range, the primitive
     the census recovers phi from. Phi-free, so no census is needed and
     the two chains are directly comparable.
  B  exit delay: blocks, and seconds, between the price leaving the old
     range and the re-placement. The mass at zero is the quantity
     §5.1 says can break the delay-cut equivalence test.
  C  same-block adjacency: for each firing, external swaps in the same
     pool and block ordered before and after the operator's own logs.
     A backrun is an external swap after; a sandwich shape is both.
     This is the direct MEV read and needs neither ticks nor phi.

     Raw shares here are NOT evidence on their own: in a busy block,
     swaps sit on both sides of anything. The test is against a
     within-block null. Conditioning on the block's own external swap
     count s, a firing inserted uniformly at random into one of the
     s + 1 gaps has P(before) = P(after) = s / (s + 1) and
     P(both) = (s - 1) / (s + 1) for s >= 1. Summing those per firing
     gives the expected counts under "the operator's position in the
     block is arbitrary". Excess over the null is placement, which is
     what a builder controls and what extraction looks like; agreement
     with the null means the adjacency is ambient traffic.
  D  just-in-time share: positions minted and burned inside one block,
     which mimic an implausibly fast operator to the census gate.

Chains are streamed identically, so any difference in the readings is a
difference in the chains, not in the code. Wall-clock windows are
matched: 12 s against 2.000 s means one mainnet block per six Base
blocks.

Ungated: Uniswap V3 on two public chains, no census join, no lake
writes, no OF sender-layer number.

Run:  python3 mev_probe.py --chain ethereum
      python3 mev_probe.py --chain base
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import defaultdict

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "third-party"))
import t2_eval  # noqa: E402

TOPIC_MINT = ("0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae"
              "16239d0bde")
TOPIC_BURN = ("0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd5"
              "68da98982c")
TOPIC_SWAP = ("0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e"
              "115fbcca67")

# Matched pairs. Same token pair, same fee tier, one pool per chain.
# Base's BTC leg is cbBTC and mainnet's is WBTC: the same underlying
# read through different wrappers, which is stated, not hidden.
CHAINS = {
    "ethereum": {
        "dataset": "ethereum-mainnet",
        "block_seconds": 12.0,
        "nfpm": "0xc36442b4a4522e871399cd717abdd847ab11fe88",
        # the full era pin. Mainnet ALM firings on these pools are
        # sparse (order 6 per 10,000 blocks in the smoke window), so
        # the long window is needed for power, and it is cheap: the
        # position and swap volumes here are a fraction of Base's.
        "lo": 24_763_430, "hi": 25_626_973,
        "pools": {
            "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640": "WETH/USDC 500",
            "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8": "WETH/USDC 3000",
            "0xcbcdf9626bc03e24f779434178a73a0b4bad62ed": "WBTC/WETH 3000",
        },
    },
    "base": {
        "dataset": "base-mainnet",
        "block_seconds": 2.0,
        "nfpm": "0x03a520b32c04bf3beef7beb72e919cf822ed34f1",
        # the full census era, the same wall-clock window as the
        # mainnet pin. Both chains therefore run one code path over
        # one era; the local-layer reading (base_local_ab.py) is NOT
        # the comparison basis, because the layer's rebalances table
        # includes same-range re-mints, which are interior by
        # construction and are not trigger firings.
        "lo": 44_000_000, "hi": 49_200_000,
        "pools": {
            "0xd0b53d9277642d899df5c87a3966a349a798f224": "WETH/USDC 500",
            "0x6c561b446416e1a00e8e93e221854d6ea4171372": "WETH/USDC 3000",
            "0x8c7080564b5a792a33ef2fd473fba6364d5495e5": "WETH/cbBTC 3000",
        },
    },
}
PORTAL = "https://portal.sqd.dev/datasets"
LOOKBACK = 20_000          # the Base census's crossing lookback, in blocks
CKPT_EVERY = 50_000


def word(data_hex, i, signed=False):
    v = int(data_hex[64 * i:64 * (i + 1)], 16)
    if signed and v >= (1 << 255):
        v -= 1 << 256
    return v


def to_int24(word_hex):
    v = int(word_hex, 16)
    return v - (1 << 256) if v >= (1 << 255) else v


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def post(dataset, body, retries=8):
    url = f"{PORTAL}/{dataset}/finalized-stream"
    for i in range(retries):
        try:
            r = requests.post(url, json=body, stream=True, timeout=180)
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


def q(v, p):
    v = sorted(v)
    return v[min(int(p * len(v)), len(v) - 1)] if v else float("nan")


class Probe:
    """Accumulates the four readings over one chain's stream."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.nfpm = cfg["nfpm"]
        self.ticks = defaultdict(list)      # pool -> [(block, tick)]
        self.last_range = {}                # (pool, op) -> (tl, tu)
        self.us = []                        # firing positions
        self.delays = []                    # exit delay in blocks
        self.adj = {"firings": 0, "backrun": 0, "frontrun": 0,
                    "sandwich": 0, "own_swap": 0, "any_ext": 0}
        # expected counts under the uniform within-block insertion null
        self.null = {"backrun": 0.0, "frontrun": 0.0, "sandwich": 0.0,
                     "n_with_swaps": 0, "ext_swaps": 0}
        self.jit = {"positions": 0, "blocks_with_jit": 0,
                    "same_range_remints": 0}
        self.n_pos_events = 0
        self.n_firings = 0
        self.per_pool = defaultdict(lambda: {"firings": 0, "backrun": 0,
                                             "sandwich": 0, "jit": 0})

    def tick_before(self, pool, blk):
        arr = self.ticks[pool]
        lo, hi = 0, len(arr)
        while lo < hi:
            mid = (lo + hi) // 2
            if arr[mid][0] < blk:
                lo = mid + 1
            else:
                hi = mid
        return arr[lo - 1][1] if lo else None

    def exit_delay(self, pool, blk, tl, tu):
        """Blocks since the tick was last inside the old range. Zero
        means the price left the range and the operator re-placed in
        the same block. The cache holds one tick per block over the
        lookback, so the backward scan is bounded by it."""
        arr = self.ticks[pool]
        lo, hi = 0, len(arr)
        while lo < hi:
            mid = (lo + hi) // 2
            if arr[mid][0] < blk:
                lo = mid + 1
            else:
                hi = mid
        for j in range(lo - 1, -1, -1):
            b, t = arr[j]
            if b < blk - LOOKBACK:
                return None
            if tl <= t <= tu:
                return blk - b
        return None

    def on_block(self, blk, logs):
        """One block's logs across all pools, in log order."""
        by_pool = defaultdict(list)
        for lg in logs:
            by_pool[lg["address"].lower()].append(lg)
        for pool, lgs in by_pool.items():
            lgs.sort(key=lambda l: l["logIndex"])
            swaps = [l for l in lgs if l["topics"][0] == TOPIC_SWAP]
            pos = [l for l in lgs if l["topics"][0] != TOPIC_SWAP]
            self.n_pos_events += len(pos)
            # D: same (owner, range) minted and burned inside one block.
            # ORDER SEPARATES TWO DIFFERENT THINGS, and conflating them
            # was wrong: mint-then-burn is just-in-time liquidity, a
            # position that exists only to straddle a swap; burn-then-
            # mint is an operator closing and reopening the same range,
            # which is fee compounding or a top-up and is the ordinary
            # `same_range` class. Both are counted, separately.
            seen = defaultdict(list)
            for l in pos:
                key = (l["topics"][1], to_int24(l["topics"][2]),
                       to_int24(l["topics"][3]))
                seen[key].append(
                    (l["logIndex"],
                     "mint" if l["topics"][0] == TOPIC_MINT else "burn"))
            n_jit = n_re = 0
            for evs in seen.values():
                evs.sort()
                kinds = [k for _, k in evs]
                if "mint" in kinds and "burn" in kinds:
                    if kinds[0] == "mint":
                        n_jit += 1
                    else:
                        n_re += 1
            if n_jit:
                self.jit["positions"] += n_jit
                self.jit["blocks_with_jit"] += 1
                self.per_pool[pool]["jit"] += n_jit
            self.jit["same_range_remints"] += n_re
            # firings, grouped by transaction
            by_tx = defaultdict(list)
            for l in pos:
                by_tx[l["transactionHash"]].append(l)
            for tx, group in by_tx.items():
                decoded = []
                for l in group:
                    kind = ("burn" if l["topics"][0] == TOPIC_BURN
                            else "mint")
                    d = l["data"][2:]
                    if kind == "burn":
                        liq, a0, a1 = (word(d, 0), word(d, 1), word(d, 2))
                    else:
                        liq, a0, a1 = (word(d, 1), word(d, 2), word(d, 3))
                    decoded.append((
                        ("0x" + l["topics"][1][-40:]).lower(),
                        to_int24(l["topics"][2]), to_int24(l["topics"][3]),
                        kind, liq, a0, a1,
                        (l.get("_from") or "").lower()))
                op = t2_eval.firing_of(decoded, self.nfpm)
                if not op:
                    continue
                self.n_firings += 1
                self.adj["firings"] += 1
                self.per_pool[pool]["firings"] += 1
                idxs = [l["logIndex"] for l in group]
                lo_i, hi_i = min(idxs), max(idxs)
                own = [s for s in swaps
                       if s["transactionHash"] == tx]
                ext = [s for s in swaps
                       if s["transactionHash"] != tx]
                before = any(s["logIndex"] < lo_i for s in ext)
                after = any(s["logIndex"] > hi_i for s in ext)
                if own:
                    self.adj["own_swap"] += 1
                if before or after:
                    self.adj["any_ext"] += 1
                if after:
                    self.adj["backrun"] += 1
                    self.per_pool[pool]["backrun"] += 1
                if before:
                    self.adj["frontrun"] += 1
                if before and after:
                    self.adj["sandwich"] += 1
                    self.per_pool[pool]["sandwich"] += 1
                s = len(ext)
                if s:
                    self.null["n_with_swaps"] += 1
                    self.null["ext_swaps"] += s
                    self.null["backrun"] += s / (s + 1)
                    self.null["frontrun"] += s / (s + 1)
                    self.null["sandwich"] += (s - 1) / (s + 1)
                # A and B need the operator's previous range
                mints = [e for e in decoded
                         if e[3] == "mint" and e[4] > 0]
                new_range = (mints[0][1], mints[0][2]) if mints else None
                prev = self.last_range.get((pool, op))
                if prev and prev[1] > prev[0]:
                    ft = self.tick_before(pool, blk)
                    if ft is not None:
                        plo, phi_u = prev
                        self.us.append((ft - plo) / (phi_u - plo))
                        d = self.exit_delay(pool, blk, plo, phi_u)
                        if d is not None:
                            self.delays.append(d)
                if new_range:
                    self.last_range[(pool, op)] = new_range
            # swap ticks last, so a firing reads the pre-block state.
            # One entry per block, the block's last Swap tick, which is
            # the layer's own swap_ticks semantics; pruned to the
            # lookback so memory and the scan above stay bounded.
            if swaps:
                arr = self.ticks[pool]
                arr.append((blk, word(swaps[-1]["data"][2:], 4,
                                      signed=True)))
                if len(arr) > 4 * LOOKBACK:
                    cut = blk - LOOKBACK
                    self.ticks[pool] = [e for e in arr if e[0] >= cut]

    def summary(self):
        bs = self.cfg["block_seconds"]
        a = self.adj
        f = max(a["firings"], 1)
        interior = sum(1 for u in self.us if 0 < u < 1)
        d0 = sum(1 for d in self.delays if d == 0)
        d1 = sum(1 for d in self.delays if d <= 1)
        nd = max(len(self.delays), 1)
        return {
            "block_seconds": bs,
            "window_blocks": self.cfg["hi"] - self.cfg["lo"],
            "window_days": (self.cfg["hi"] - self.cfg["lo"]) * bs / 86400,
            "n_position_events": self.n_pos_events,
            "n_firings": self.n_firings,
            "A_firing_position": {
                "n": len(self.us),
                "interior_fraction": round(interior / max(len(self.us), 1), 4),
                "q10": round(q(self.us, .10), 4),
                "q50": round(q(self.us, .50), 4),
                "q90": round(q(self.us, .90), 4),
            },
            "B_exit_delay_blocks": {
                "n": len(self.delays),
                "_note": "delay >= 1 by construction (the tick cache "
                         "holds one entry per block, searched strictly "
                         "before the firing block), identically on both "
                         "chains. Same-block correction is reading C.",
                "mass_at_0_structural_zero": round(d0 / nd, 4),
                "mass_le_1": round(d1 / nd, 4),
                "q50": q(self.delays, .5), "q90": q(self.delays, .9),
                "q50_seconds": q(self.delays, .5) * bs
                if self.delays else None,
                "q90_seconds": q(self.delays, .9) * bs
                if self.delays else None,
            },
            "C_same_block_adjacency": {
                "firings": a["firings"],
                "own_swap_share": round(a["own_swap"] / f, 4),
                "external_swap_share": round(a["any_ext"] / f, 4),
                "backrun_share": round(a["backrun"] / f, 4),
                "frontrun_share": round(a["frontrun"] / f, 4),
                "sandwich_share": round(a["sandwich"] / f, 4),
                "null": {
                    "_what": "expected counts if the firing sat at a "
                             "uniformly random position among the "
                             "block's external swaps; excess over this "
                             "is placement, agreement is ambient "
                             "traffic",
                    "firings_with_external_swaps":
                        self.null["n_with_swaps"],
                    "mean_external_swaps_in_those_blocks": round(
                        self.null["ext_swaps"]
                        / max(self.null["n_with_swaps"], 1), 2),
                    "expected_backrun": round(self.null["backrun"], 1),
                    "observed_backrun": a["backrun"],
                    "expected_frontrun": round(self.null["frontrun"], 1),
                    "observed_frontrun": a["frontrun"],
                    "expected_sandwich": round(self.null["sandwich"], 1),
                    "observed_sandwich": a["sandwich"],
                    "backrun_excess_ratio": round(
                        a["backrun"] / self.null["backrun"], 3)
                    if self.null["backrun"] > 0 else None,
                    "sandwich_excess_ratio": round(
                        a["sandwich"] / self.null["sandwich"], 3)
                    if self.null["sandwich"] > 0 else None,
                },
            },
            "D_jit": {
                "_what": "mint-then-burn inside one block is JIT; "
                         "burn-then-mint of the same range is fee "
                         "compounding, counted apart",
                "jit_positions": self.jit["positions"],
                "jit_share_of_position_events":
                    round(2 * self.jit["positions"]
                          / max(self.n_pos_events, 1), 4),
                "same_range_remints": self.jit["same_range_remints"],
                "remint_share_of_position_events":
                    round(2 * self.jit["same_range_remints"]
                          / max(self.n_pos_events, 1), 4),
            },
            "per_pool": {self.cfg["pools"].get(p, p): dict(v)
                         for p, v in self.per_pool.items()},
        }


def run(chain):
    cfg = CHAINS[chain]
    pools = list(cfg["pools"])
    probe = Probe(cfg)
    out = os.path.join(HERE, f"mev_probe_{chain}.json")
    log(f"{chain}: blocks {cfg['lo']:,}-{cfg['hi']:,} "
        f"({(cfg['hi'] - cfg['lo']) * cfg['block_seconds'] / 86400:.1f} "
        f"days) on {len(pools)} pools")
    cur = cfg["lo"]
    t0 = last_report = time.time()
    while cur <= cfg["hi"]:
        body = {"type": "evm", "fromBlock": cur, "toBlock": cfg["hi"],
                "includeAllBlocks": False,
                "logs": [{"address": pools,
                          "topic0": [TOPIC_MINT, TOPIC_BURN, TOPIC_SWAP],
                          "transaction": True}],
                "fields": {"block": {"number": True, "timestamp": True},
                           "log": {"address": True, "topics": True,
                                   "data": True, "logIndex": True,
                                   "transactionHash": True},
                           "transaction": {"hash": True, "from": True}}}
        last = cur - 1
        try:
            r = post(cfg["dataset"], body)
            for line in r.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                last = chunk["header"]["number"]
                txs = {t.get("hash"): t
                       for t in chunk.get("transactions", [])}
                lgs = chunk.get("logs", [])
                for lg in lgs:
                    tx = txs.get(lg.get("transactionHash"), {})
                    lg["_from"] = tx.get("from") or ""
                if lgs:
                    probe.on_block(last, lgs)
                if time.time() - last_report > 120:
                    log(f"  ...at block {last:,} "
                        f"({probe.n_firings:,} firings)")
                    last_report = time.time()
        except (requests.exceptions.RequestException,
                json.JSONDecodeError) as exc:
            log(f"  transport error at {last:,} ({type(exc).__name__}); "
                f"resuming")
            if last < cur:
                time.sleep(5)
                continue
        if last < cur:
            break
        cur = last + 1
    s = probe.summary()
    json.dump(s, open(out, "w"), indent=1)
    log(f"{chain} done in {time.time() - t0:.0f} s; wrote {out}")
    print(json.dumps(s, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", required=True, choices=sorted(CHAINS))
    run(ap.parse_args().chain)


if __name__ == "__main__":
    main()
