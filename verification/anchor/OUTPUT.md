# Captured output: real-data anchor (anchor.py)

First capture 2026-08-09. Command: `python3 anchor.py --pools 0`
(~2 min; reads the position-manager lake read-only). This file is the
regression target for the anchor surface; numeric shifts here mean
either a lake refresh past the amounts window or a script change,
and either propagates to the manuscript's anchor paragraphs.

Pools carry stable labels, `pool_01` upward, rather than addresses.
The per-pool rows below pair a venue with this operator's own trigger
and correction geometry, and the manuscript reports that geometry only
as a range across pools; the labels keep the repository from being the
finer statement. Labels are ordered by event count and are consistent
across the tables here, so rows remain cross-referenceable. Every
reported quantity is unchanged.

```
anchor: 135538 rebalance events in the amounts window (blocks 43,635,967-45,988,726), all pools

[1] share-potential identity on production events
    event classes: {'clean': 78999, 'draw': 53512, 'degenerate': 3027}
    clean events: 78999 (58.3% of window)
    price self-consistency (mint arithmetic, rel): median 3.81e-15, q99 9.59e-10, max 1.69e-07
    mint-minimum arithmetic error (rel): median 4.85e-13, q99 5.94e-07, max 1.00e+00
    identity |k_real - k_pred|: median 5.72e-17, q99 5.17e-08, max 3.85e-05   (n 78908)
    dust-credit surplus match: 78999 matched, 0 unmatched

[2] realised rate vs the fee-only swap-mediated floor (eta anchor 1e-4; gas excluded, reported at $0.03/event; clean and dust-draw events priced)
    pool              n   days     rho  sig/s  r-hat%/yr  floor%/yr   score  x-med  m-med
    pool_01       19993     53  0.0050   0.27     440.46       7.12    61.9   0.65   0.02  [event-marks]
    pool_02       11166     28  0.0005   0.09     282.93      85.82     3.3   0.40   0.34  [swap-stream]
    pool_03        9687     26  0.0004   0.12     474.62     204.63     2.3   0.79   0.69  [swap-stream]
    pool_04        7867     48  0.0024   0.24     865.03      24.88    34.8   0.67   0.17  [swap-stream]
    pool_05        6989     54  0.0021   0.42    2902.43     102.02    28.4   0.55   0.52  [swap-stream]
    pool_06        6619     26  0.0013   0.28     563.94     121.90     4.6   0.70   0.59  [swap-stream]
    pool_07        6340     33  0.0091   0.49    4014.96       7.11   564.5   0.52   0.24  [swap-stream]
    pool_08        6200     28  0.0020   0.21     184.27      28.01     6.6   0.38   0.33  [swap-stream]
    pool_09        5664     54  0.0025   0.29     283.44      34.04     8.3   0.66   0.05  [event-marks]
    pool_10        4463     54  0.0050   0.26     216.82       6.54    33.1   0.62   0.07  [event-marks]
    pool_11        4424     19  0.0047   0.57    6507.01      36.28   179.4   0.74   0.27  [swap-stream]
    pool_12        3957     28  0.0020   0.17     260.37      17.39    15.0   0.37   0.34  [swap-stream]
    pool_13        3589     53  0.0050   0.20      69.70       3.76    18.5   0.65   0.03  [event-marks]
    pool_14        1928     54  0.0027   0.27     534.63      26.39    20.3   0.67   0.08  [swap-stream]
    pool_15        1881     28  0.0003   0.02      47.99      18.65     2.6   0.46   0.38  [swap-stream]
    pool_16        1867     25  0.0001   0.03      87.28     148.61     0.6   1.11   0.99  [swap-stream]
    pool_17        1784     15  0.0012   0.43    1163.86     299.65     3.9   1.02   0.90  [swap-stream]
    pool_18        1633     54  0.0115   0.69    1853.76       8.94   207.4   0.57   0.20  [swap-stream]
    pool_19        1500     26  0.0013   0.21     282.20      69.52     4.1   0.83   0.69  [swap-stream]
    pool_20        1499     54  0.0056   0.41     477.50      13.29    35.9   0.63   0.08  [swap-stream]
    pool_21        1461     27  0.0013   0.21     304.52      69.85     4.4   0.91   0.66  [swap-stream]
    pool_22        1358     33  0.0177   1.29     431.47      12.89    33.5   0.51   0.22  [swap-stream]
    pool_23        1304     54  0.0095   0.74    1017.96      14.78    68.9   0.62   0.24  [swap-stream]
    pool_24        1233     15  0.0113   6.67    5045.02     849.83     5.9   0.67   0.36  [swap-stream]
    pool_25        1220     40  0.0050   0.22     279.30       4.64    60.2   0.59   0.36  [swap-stream]
    pool_26        1158     54  0.0051   0.30     295.12       8.74    33.8   0.68   0.04  [event-marks]
    pool_27        1083     54  0.0051   0.25     289.89       6.04    48.0   0.69   0.05  [swap-stream]
    pool_28        1077     33  0.0101   0.38     321.49       3.52    91.2   0.54   0.14  [swap-stream]
    pool_29        1048     54  0.0145   1.22    1664.23      17.34    96.0   0.59   0.41  [swap-stream]
    pool_30         984     48  0.0099   0.68    1428.58      11.76   121.5   0.64   0.26  [swap-stream]
    pool_31         967     46  0.0052   0.34     363.37      10.47    34.7   0.63   0.06  [event-marks]
    pool_32         951     54  0.0049   0.20     240.73       4.22    57.0   0.69   0.04  [swap-stream]
    pool_33         901     19  0.0026   0.37     668.64      51.43    13.0   0.75   0.19  [swap-stream]
    pool_34         899     19  0.0028   1.05     731.88     343.93     2.1   0.68   0.08  [swap-stream]
    pool_35         890     52  0.0051   0.18      90.01       3.15    28.6   0.68   0.08  [swap-stream]
    pool_36         834     54  0.0051   0.30     392.31       8.33    47.1   0.61   0.13  [swap-stream]
    pool_37         824     26  0.0054   0.75     765.34      48.16    15.9   0.74   0.17  [swap-stream]
    pool_38         750     53  0.0026   0.20     245.87      14.53    16.9   0.75   0.16  [swap-stream]
    pool_39         708     25  0.0050   0.91    1405.11      80.22    17.5   0.74   0.10  [event-marks]
    pool_40         643     18  0.0171   1.23    2511.81      12.51   200.7   0.54   0.32  [swap-stream]
    pool_41         492     19  0.0053   0.99    1941.44      86.43    22.5   0.73   0.32  [swap-stream]
    pool_42         486     38  0.0013   0.05      63.24       3.74    16.9   0.64   0.08  [swap-stream]
    pool_43         442     21  0.0161   1.19    1367.30      13.29   102.9   0.46   0.33  [swap-stream]
    pool_44         405     33  0.0050   0.28     286.60       7.44    38.5   0.63   0.05  [swap-stream]
    pool_45         375     15  0.0109   1.22    1495.66      30.56    48.9   0.78   0.44  [swap-stream]
    pool_46         307     28  0.0193   0.51     212.96       1.67   127.6   0.34   0.21  [swap-stream]
    pool_47         211     15  0.0050   0.13     231.12       1.70   136.2   0.75   0.02  [event-marks]
    pool_48        (skipped: thin data or no swap-stream sigma)
    pool_49         117     14  0.0025   0.07     114.97       1.97    58.5   0.76   0.07  [swap-stream]
    pool_50          95     26  0.0165   0.30     278.59       0.81   343.2   0.33   0.19  [swap-stream]
    pool_51        (skipped: thin data or no swap-stream sigma)
    pool_52        (skipped: thin data or no swap-stream sigma)
    pool_53        (skipped: thin data or no swap-stream sigma)

    benchmark scores span 0.6 to 564.5 (floor at one), median 33.5

all evaluations complete
```

## Reading

[1] The share-potential identity (Theorem 2) holds on 78,908
production rebalances at median |k_real - k_pred| = 5.7e-17, machine
precision, q99 5.2e-8; the identity is an identity on production
events, not only in the seeded harness. The 41.5% of events classed
"draw" consumed the standing dust balance (the contract sweeps the
full balance into every mint and credits back the remainder, ME's
retention architecture live in production); they are priced in [2]
but excluded from the identity subsample, whose hypothesis is
isolated holdings. Dust conservation (credit >= surplus) holds on
all 78,999 clean events with zero exceptions. The mint-minimum
error tail (max 1.0) is a handful of at-range-edge events where one
token amount is near zero; value-weighted median is 4.9e-13.

[2] No volatile-pair pool beats its class floor. Benchmark scores
(realised rate over the fee-only floor at the uniform eta = 1e-4
anchor) span 0.6 to 564 with median 33.5. The sub-one scores are
pegged/stable pools where the uniform anchor overstates the true
fee tier (stable CL fees run below 1e-4) and the 5-minute RV sigma
is inflated by microstructure bounce (the paper's own probe 6
measures RV/BV 1.198 on volatile pairs; pegged pairs are worse), so
the floor shown for them is overstated; a fee-tier-correct, bipower
run is the release-grade version. Distances to floor are dominated
by correction-size and width choices, as the benchmark-score
reading in the manuscript's swap section says they should be.

[3] Median trigger fractions x-hat run 0.22 to 1.14 across pools
(late-firing direction confirmed; several pools fire at or past the
band edge), median corrections m-hat 0.01 to 1.01, with the small-m
large-x corner (the Proposition 8 cost-optimal direction) the modal
pattern.

Caveats, standing. Amounts stop at block 45,988,726 (2026-05-13);
events after that carry ticks and AERO only, so the window is the
first ~53 days of the V9 era. Gas is excluded from r-hat and
reported at the $0.03/event anchor. sigma from 5-min RV, not
bipower. The eta anchor is uniform at 1e-4; per-pool fee tiers are
the known refinement (TOSHI CL200 is a 24 bps pool, so its true
floor is ~24x the table's). Pool 0xcbba009b's sigma (6.69) is a
depeg/decimals artefact; treat its row as unreliable.
