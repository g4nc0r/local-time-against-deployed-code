#!/usr/bin/env python3
"""WS0 feasibility probe: the Uniswap V3 Base operator population.

Uniswap V3 event scan and class census on Base. Counts
candidate operators (tx senders for NFPM-mediated positions; vault
contracts for direct pool positions) with >= 30 reconstructable trigger
firings inside the census-aligned era window, on the top Uniswap V3
Base pools by rebalance activity, and estimates the finalist pools'
swap-stream density. The full-era event pass stores complete burn and
mint amounts, so the Tier-2 third-party identity evaluation reads the
same checkpoint with no re-scan.

The factory's PoolCreated surface is millions of events (token
launchers auto-deploy V3 pools), so pools are NOT enumerated. Candidate
pools come from two directions instead: direct factory.getPool lookups
over a major-pair token set (including every Aerodrome census token,
for the Tier-4 pairing readout), and sampled burn-activity discovery
across the era with factory verification of the survivors.

Transports: Alchemy RPC via the ALCHEMY_RPC env var for sparse or
call-shaped work (never hardcode the key); the SQD portal
(portal.sqd.dev, free, no key, same protocol as the Operator
Fingerprinting indexer's client) for the streaming era pass, which also
returns each log's transaction sender. No lake writes. Outputs land in
this folder:

  candidates.json      candidate pool set with pair metadata
  ranking.json         era-wide Burn counts on the candidates
  events_top.json.gz   full-era Mint/Burn logs + amounts + tx senders
  firings.json         per (pool, operator) firing counts
  swaps_sample.json    sampled swap counts on the finalist pools
  summary.md           captured numbers for the decision memo

Stages checkpoint to disk and are skipped when their output exists.
Run detached (session background tasks get group-killed here):

  systemd-run --user --unit=ws0-probe \
    --property=WorkingDirectory="$PWD" \
    --property=EnvironmentFile=<env file with ALCHEMY_RPC> \
    bash -lc 'python3 ws0_probe.py > ws0.log 2>&1'
"""
import gzip
import json
import os
import time
import urllib.error
import urllib.request

import requests

PORTAL = "https://portal.sqd.dev/datasets/base-mainnet"
RPC = os.environ.get("ALCHEMY_RPC", "https://mainnet.base.org")
OUT = os.path.dirname(os.path.abspath(__file__))

ERA_LO, ERA_HI = 44_000_000, 49_200_000  # census era, ~120 days at 2 s
FACTORY = "0x33128a8fc17869897dce68ed026d694621f6fdfd"
NFPM = "0x03a520b32c04bf3beef7beb72e919cf822ed34f1"

TOPIC_MINT = "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
TOPIC_BURN = "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"
TOPIC_SWAP = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"

FEES = [100, 500, 3000, 10000]
SCAN_N = 40         # pools carried into the full-era portal scan
TOP_N = 30          # pools reported in the summary table
FIRING_BAR = 30     # admission bar per the spec
DISC_WINDOWS = 26   # sampled discovery windows
DISC_WIDTH = 2_000
DISC_KEEP = 300     # sampled addresses carried to factory verification

# Major-pair token set: programme majors plus every token appearing in
# the Aerodrome census top-50 (aero_census_pairs.json, resolved earlier).
MAJOR_TOKENS = {
    "WETH": "0x4200000000000000000000000000000000000006",
    "USDC": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    "cbBTC": "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf",
    "USDbC": "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca",
    "DAI": "0x50c5725949a6f0c72e6c4a641f24049a917db0cb",
    "cbETH": "0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22",
    "wstETH": "0xc1cba3fcea344f92d9239c08c0568f6f2f0ee452",
    "AERO": "0x940181a94a35a4569e4529a3cdfb74e38fd98631",
    "USDT": "0xfde4c96c8593536e31f229ea8f37b2ada2699bb2",
    "weETH": "0x04c0599ae5a44757c0af6f9ec3b93da8976c150a",
    "EURC": "0x60a3e35cc302bfa44cb288bc5a4f316fdb1adb42",
    "LBTC": "0xecac9c5f704e954931349da37f60e39f515c11c1",
}
KNOWN_TOKENS = {v.lower(): k for k, v in MAJOR_TOKENS.items()}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def ckpt(name):
    return os.path.join(OUT, name)


# ---- RPC client (Alchemy; sparse and call-shaped work) ----------------------

class TooMany(Exception):
    pass


class RpcError(Exception):
    """Definitive JSON-RPC error (e.g. execution reverted): do not retry."""


def rpc(method, params):
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode()
    for a in range(6):
        try:
            req = urllib.request.Request(
                RPC, data=payload,
                headers={"Content-Type": "application/json",
                         "User-Agent": "curl/8.8.0"},
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    out = json.loads(r.read())
            except urllib.error.HTTPError as he:
                body = he.read()
                try:
                    out = json.loads(body)
                except Exception:  # noqa: BLE001
                    raise he from None
            if "error" in out:
                m = str(out["error"].get("message", ""))
                low = m.lower()
                if ("10,000" in m or "10000" in m or "block range" in low
                        or "response size" in low or "larger" in low
                        or "query timeout" in low):
                    raise TooMany(m)
                raise RpcError(m)
            return out["result"]
        except (TooMany, RpcError):
            raise
        except Exception:  # noqa: BLE001
            time.sleep(2 * (a + 1))
    raise RuntimeError(f"rpc failed: {method}")


def rpc_get_logs(flt, cb=None):
    """Adaptive eth_getLogs: split the block range on result-size
    errors. With cb, each leaf's logs go to cb and are discarded
    (bounded memory); without, the concatenated list is returned."""
    lo, hi = int(flt["fromBlock"], 16), int(flt["toBlock"], 16)
    try:
        out = rpc("eth_getLogs", [flt])
        if cb is not None:
            cb(out)
            return None
        return out
    except TooMany:
        if hi <= lo:
            raise
        mid = (lo + hi) // 2
        a = rpc_get_logs({**flt, "toBlock": hex(mid)}, cb)
        b = rpc_get_logs({**flt, "fromBlock": hex(mid + 1)}, cb)
        return None if cb is not None else a + b


def eth_call(to, data):
    return rpc("eth_call", [{"to": to, "data": data}, "latest"])


# ---- SQD Portal streaming client (heavy era passes) -------------------------

def _post_stream(body, retries=8):
    last = None
    for attempt in range(retries):
        try:
            r = requests.post(PORTAL + "/finalized-stream", json=body,
                              timeout=180, stream=True)
            if r.status_code == 200:
                return r
            last = f"{r.status_code} {r.text[:100]}"
            r.close()
        except requests.RequestException as e:  # noqa: BLE001
            last = str(e)[:120]
        time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"SQD portal failed after {retries} retries: {last}")


def walk_logs(from_block, to_block, log_filter, fields, on_chunk,
              progress_every=None):
    cur = from_block
    last_report = time.time()
    while cur <= to_block:
        body = {"type": "evm", "fromBlock": cur, "toBlock": to_block,
                "includeAllBlocks": False, "logs": [log_filter],
                "fields": fields}
        r = _post_stream(body)
        last = cur - 1
        for line in r.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            hdr = chunk["header"]
            last = hdr["number"]
            txs = {t.get("hash"): t for t in chunk.get("transactions", [])}
            on_chunk(hdr, chunk.get("logs", []), txs)
            if progress_every and time.time() - last_report > progress_every:
                log(f"  ...at block {last:,}")
                last_report = time.time()
        if last < cur:
            break
        cur = last + 1


def to_int24(word_hex):
    v = int(word_hex, 16)
    return v - (1 << 256) if v >= (1 << 255) else v


def word(data_hex, i, signed=False):
    v = int(data_hex[64 * i : 64 * (i + 1)], 16)
    if signed and v >= (1 << 255):
        v -= 1 << 256
    return v


# ---- stage 1: candidate pools -----------------------------------------------

def _pool_meta(pool):
    """token0/token1/fee of a claimed V3 pool, and whether the factory
    confirms it. Returns None when any call fails or the factory denies."""
    try:
        t0 = "0x" + eth_call(pool, "0x0dfe1681")[-40:]
        t1 = "0x" + eth_call(pool, "0xd21220a7")[-40:]
        fee = int(eth_call(pool, "0xddca3f43"), 16)
        got = eth_call(
            FACTORY,
            "0x1698ee82"
            + t0[2:].rjust(64, "0")
            + t1[2:].rjust(64, "0")
            + hex(fee)[2:].rjust(64, "0"),
        )
        if ("0x" + got[-40:]).lower() != pool.lower():
            return None
        return {"token0": t0, "token1": t1, "fee": fee}
    except Exception:  # noqa: BLE001
        return None


def stage_candidates():
    path = ckpt("candidates.json")
    if os.path.exists(path):
        return json.load(open(path))
    cands = {}

    log("stage 1a: factory.getPool over the major-pair token set")
    toks = sorted(MAJOR_TOKENS.values())
    for i, ta in enumerate(toks):
        for tb in toks[i + 1 :]:
            t0, t1 = (ta, tb) if ta.lower() < tb.lower() else (tb, ta)
            for fee in FEES:
                got = eth_call(
                    FACTORY,
                    "0x1698ee82"
                    + t0[2:].rjust(64, "0")
                    + t1[2:].rjust(64, "0")
                    + hex(fee)[2:].rjust(64, "0"),
                )
                pool = ("0x" + got[-40:]).lower()
                if int(got, 16) != 0:
                    cands[pool] = {"token0": t0.lower(), "token1": t1.lower(),
                                   "fee": fee, "source": "majors"}
    log(f"stage 1a done: {len(cands)} major-pair pools")

    log("stage 1b: sampled burn-activity discovery (portal)")
    counts = {}
    step = (ERA_HI - ERA_LO - DISC_WIDTH) // (DISC_WINDOWS - 1)
    for w in range(DISC_WINDOWS):
        lo = ERA_LO + w * step

        def on_chunk(hdr, logs, txs):
            for lg in logs:
                a = lg["address"].lower()
                counts[a] = counts.get(a, 0) + 1

        walk_logs(
            lo, lo + DISC_WIDTH - 1,
            {"topic0": [TOPIC_BURN]},
            {"block": {"number": True},
             "log": {"address": True, "topics": True}},
            on_chunk,
        )
        log(f"  window {w + 1}/{DISC_WINDOWS}: {len(counts)} distinct "
            f"burn-emitting addresses so far")

    sampled = sorted(counts.items(), key=lambda kv: -kv[1])[:DISC_KEEP]
    log(f"stage 1c: factory-verifying {len(sampled)} sampled candidates")
    kept = 0
    for addr, n in sampled:
        if addr in cands:
            cands[addr]["sampled_burns"] = n
            continue
        meta = _pool_meta(addr)
        if meta:
            meta["source"] = "sampled"
            meta["sampled_burns"] = n
            cands[addr] = meta
            kept += 1
    log(f"stage 1c done: {kept} sampled pools verified; "
        f"{len(cands)} candidates total")
    json.dump(cands, open(path, "w"), indent=1)
    return cands


# ---- stage 2: era-wide Burn ranking on the candidates -----------------------

def stage_ranking(cands):
    path = ckpt("ranking.json")
    if os.path.exists(path):
        return json.load(open(path))
    log("stage 2: era-wide Burn ranking via RPC")
    addrs = sorted(cands)
    counts = {}

    def tally(logs):
        for lg in logs:
            a = lg["address"].lower()
            counts[a] = counts.get(a, 0) + 1

    for bi in range(0, len(addrs), 500):
        batch = addrs[bi : bi + 500]
        rpc_get_logs(
            {"fromBlock": hex(ERA_LO), "toBlock": hex(ERA_HI),
             "address": batch, "topics": [TOPIC_BURN]},
            cb=tally,
        )
        log(f"  batch {bi // 500 + 1}: {sum(counts.values())} burns so far")
    ranking = sorted(counts.items(), key=lambda kv: -kv[1])
    json.dump(ranking, open(path, "w"), indent=1)
    log(f"stage 2 done: {len(ranking)} candidate pools with era burns")
    return ranking


# ---- stage 3: streaming era pass (firings census + Tier-2 identity) ---------
# One portal walk over the finalist pools. Groups close within a block
# (a transaction never spans blocks), so both the firing census and the
# Tier-2 identity evaluation run inline with bounded memory; only
# aggregates survive.

def decode_log(lg, txs):
    t0 = lg["topics"][0]
    kind = "burn" if t0 == TOPIC_BURN else "mint"
    data = lg["data"][2:]
    if kind == "burn":
        liq, a0, a1 = word(data, 0), word(data, 1), word(data, 2)
    else:
        liq, a0, a1 = word(data, 1), word(data, 2), word(data, 3)
    tx = txs.get(lg["transactionHash"], {})
    return (
        ("0x" + lg["topics"][1][-40:]).lower(),   # owner
        to_int24(lg["topics"][2]),
        to_int24(lg["topics"][3]),
        kind,
        liq,
        a0,
        a1,
        (tx.get("from") or "").lower(),
        lg["transactionHash"],
        lg["address"].lower(),
    )


def stream_pass(scan_pools, from_block, to_block, firings, t2, nfpm):
    """Walk [from_block, to_block] on scan_pools, updating the firing
    census dict and the Tier-2 aggregate dict in place."""
    import t2_eval

    def on_chunk(hdr, logs, txs):
        groups = {}
        for lg in logs:
            d = decode_log(lg, txs)
            groups.setdefault((d[8], d[9]), []).append(d[:8])
        for (tx, pool), group in groups.items():
            op = t2_eval.firing_of(group, nfpm)
            if op:
                key = f"{pool}|{op}"
                firings[key] = firings.get(key, 0) + 1
            cls, metrics = t2_eval.identity_of(group)
            if cls:
                t2["classes"][cls] = t2["classes"].get(cls, 0) + 1
            if metrics:
                t2["id_errs"].append(metrics["id_err"])
                t2["mint_errs"].append(metrics["mint_err"])
                t2["price_errs"].append(metrics["price_consist"])
                t2["ops"][metrics["operator"]] = (
                    t2["ops"].get(metrics["operator"], 0) + 1
                )

    walk_logs(
        from_block, to_block,
        {"address": scan_pools, "topic0": [TOPIC_MINT, TOPIC_BURN],
         "transaction": True},
        {"block": {"number": True, "timestamp": True},
         "log": {"address": True, "topics": True, "data": True,
                 "transactionHash": True},
         "transaction": {"hash": True, "from": True}},
        on_chunk,
        progress_every=60,
    )


def stage_stream(scan_pools):
    fpath, tpath = ckpt("firings.json"), ckpt("t2_univ3.json")
    if os.path.exists(fpath) and os.path.exists(tpath):
        return json.load(open(fpath)), json.load(open(tpath))
    log(f"stage 3: streaming era pass on {len(scan_pools)} pools")
    firings = {}
    t2 = {"classes": {}, "id_errs": [], "mint_errs": [],
          "price_errs": [], "ops": {}}
    stream_pass(scan_pools, ERA_LO, ERA_HI, firings, t2, NFPM)
    json.dump(firings, open(fpath, "w"), indent=1)
    json.dump(t2, open(tpath, "w"), indent=1)
    log(f"stage 3 done: {sum(firings.values())} firings across "
        f"{len(firings)} (pool, operator) cells; "
        f"{len(t2['id_errs'])} clean third-party identity events")
    return firings, t2


# ---- stage 5: swap-stream density sample on finalists -----------------------

def stage_swaps(top_pools):
    path = ckpt("swaps_sample.json")
    if os.path.exists(path):
        return json.load(open(path))
    log("stage 5: sampled swap counts on finalist pools (RPC)")
    windows, width = 12, 2_000
    step = (ERA_HI - ERA_LO - width) // (windows - 1)
    counts = {}
    for w in range(windows):
        lo = ERA_LO + w * step
        logs = rpc_get_logs(
            {"fromBlock": hex(lo), "toBlock": hex(lo + width - 1),
             "address": top_pools, "topics": [TOPIC_SWAP]}
        )
        for lg in logs:
            a = lg["address"].lower()
            counts[a] = counts.get(a, 0) + 1
    sampled_blocks = windows * width
    out = {p: {"sampled_swaps": c,
               "est_swaps_per_day": round(c / sampled_blocks * 43_200)}
           for p, c in counts.items()}
    json.dump(out, open(path, "w"), indent=1)
    log("stage 5 done")
    return out


# ---- token symbols ----------------------------------------------------------

def symbol(addr, cache={}):
    addr = addr.lower()
    if addr in KNOWN_TOKENS:
        return KNOWN_TOKENS[addr]
    if addr in cache:
        return cache[addr]
    try:
        h = eth_call(addr, "0x95d89b41")[2:]
        if len(h) >= 128:
            n = int(h[64:128], 16)
            s = bytes.fromhex(h[128 : 128 + 2 * n]).decode("utf-8", "replace")
        else:
            s = bytes.fromhex(h).rstrip(b"\x00").decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        s = addr[:8]
    s = s.strip() or addr[:8]
    cache[addr] = s
    return s


def block_ts(n):
    b = rpc("eth_getBlockByNumber", [hex(n), False])
    return int(b["timestamp"], 16)


# ---- summary ----------------------------------------------------------------

def main():
    cands = stage_candidates()
    scan_pools = sorted(cands)
    firings, t2 = stage_stream(scan_pools)

    per_pool = {}
    for key, n in firings.items():
        pool, op = key.split("|")
        d = per_pool.setdefault(pool, {"firings": 0, "ops": {}})
        d["firings"] += n
        d["ops"][op] = n

    ranked = sorted(per_pool.items(), key=lambda kv: -kv[1]["firings"])
    top = [p for p, _ in ranked[:TOP_N]]
    swaps = stage_swaps(top)

    ts_lo, ts_hi = block_ts(ERA_LO), block_ts(ERA_HI)
    days = (ts_hi - ts_lo) / 86_400

    lines = []
    lines.append("# WS0 probe: Uniswap V3 Base operator population\n")
    lines.append(f"Era window: blocks {ERA_LO:,}-{ERA_HI:,} "
                 f"({time.strftime('%Y-%m-%d', time.gmtime(ts_lo))} to "
                 f"{time.strftime('%Y-%m-%d', time.gmtime(ts_hi))}, "
                 f"{days:.1f} days), aligned with the Aerodrome census era.\n")
    lines.append(f"Candidate pools: {len(cands)} (major-pair lookups plus "
                 f"sampled discovery, factory-verified), all scanned in "
                 f"full over the era.\n")
    lines.append("| pool | pair | fee | firings (era) | operators | ops>=30 | ops>=10 | max op | est swaps/day |")
    lines.append("|---|---|---|---|---|---|---|---|---|")

    clearing = 0
    total_admitted = 0
    for pool, d in ranked[:TOP_N]:
        meta = cands.get(pool, {})
        pair = f"{symbol(meta.get('token0', '?'))}/{symbol(meta.get('token1', '?'))}"
        ops = d["ops"]
        ge30 = sum(1 for v in ops.values() if v >= FIRING_BAR)
        ge10 = sum(1 for v in ops.values() if v >= 10)
        mx = max(ops.values()) if ops else 0
        sw = swaps.get(pool, {}).get("est_swaps_per_day", 0)
        if ge30 >= 1:
            clearing += 1
        total_admitted += ge30
        lines.append(
            f"| {pool[:10]}.. | {pair} | {meta.get('fee', '?')} | "
            f"{d['firings']} | {len(ops)} | {ge30} | {ge10} | {mx} | {sw} |"
        )

    all_ge30 = sum(
        1 for d in per_pool.values() for v in d["ops"].values() if v >= FIRING_BAR
    )
    pools_clearing_all = sum(
        1 for d in per_pool.values()
        if any(v >= FIRING_BAR for v in d["ops"].values())
    )

    lines.append("")
    lines.append(f"Top-{TOP_N} pools clearing the >= {FIRING_BAR}-firing bar "
                 f"with at least one operator: **{clearing}**.")
    lines.append(f"All scanned pools clearing the bar: "
                 f"**{pools_clearing_all}**; total admitted (pool, operator) "
                 f"cells: **{all_ge30}**.")
    lines.append("\nGate per the spec: fewer than ~8 clearing pools shrinks "
                 "Tier 3 to the Tier-4 paired pools only.\n")

    import t2_eval
    ie = t2["id_errs"]
    ops10 = sum(1 for v in t2["ops"].values() if v >= 10)
    lines.append("## Tier-2 identity on third-party rebalances (Uniswap V3)\n")
    lines.append(f"Event classes: {t2['classes']}.")
    lines.append(f"Clean isolated third-party re-placements: {len(ie)} "
                 f"across {len(t2['ops'])} operators ({ops10} with >= 10).")
    if ie:
        lines.append(
            f"Identity |k_real - k_pred|: median {t2_eval.q(ie, .5):.2e}, "
            f"q99 {t2_eval.q(ie, .99):.2e}, max {t2_eval.q(ie, 1):.2e}.")
        lines.append(
            f"Mint-minimum error (value-weighted): median "
            f"{t2_eval.q(t2['mint_errs'], .5):.2e}, "
            f"q99 {t2_eval.q(t2['mint_errs'], .99):.2e}.")
        lines.append(
            f"Price self-consistency: median "
            f"{t2_eval.q(t2['price_errs'], .5):.2e}, "
            f"q99 {t2_eval.q(t2['price_errs'], .99):.2e}.")

    with open(ckpt("summary.md"), "w") as f:
        f.write("\n".join(lines))
    log("summary.md written")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
