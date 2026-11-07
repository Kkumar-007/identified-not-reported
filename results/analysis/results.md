# Results (descriptive; see notes)

Sets per stratum: {'auth': 20, 'clean': 30, 'high': 40, 'low': 40}

_H1-H5 descriptive: judge-strict κ=0.09 and rule κ=0.13 < 0.7 (prereg §5). Lenient κ=0.79._

Loss = P(item not reported in the same sample's report | recorded in that sample's ledger), ratio of sums. Intervals: cluster bootstrap over sets, 2000 resamples, within stratum; paired where the same sets.

## Family A

Ledgers valid: 390/390

| Quantity | judge-strict (D-2 match) | judge-strict (committed case-sensitive match) | rule-strict (κ fallback) | lenient |
|---|---|---|---|---|
| Detection, low | 31.7% [18.3, 45.8] (n=120) | 31.7% [18.3, 45.8] (n=120) | 36.7% [23.3, 50.8] (n=120) | 54.2% [39.2, 68.3] (n=120) |
| Detection, high | 61.7% [55.3, 68.3] (n=360) | 61.7% [55.3, 68.3] (n=360) | 72.2% [63.6, 80.3] (n=360) | 99.7% [99.2, 100.0] (n=360) |
| H1 L loss, high (97.5% CI) | 4.5% [0.5, 9.2] (n=222) | 46.4% [32.4, 59.9] (n=222) | 18.8% [12.1, 26.0] (n=260) | 0.3% [0.0, 1.1] (n=359) |
| L loss, low | 2.6% [0.0, 9.7] (n=38) | 2.6% [0.0, 9.7] (n=38) | 13.6% [2.4, 26.4] (n=44) | 0.0% [0.0, 0.0] (n=65) |
| H2 high − low (97.5% CI) | +1.9 pts [-7.8, +7.9] | +43.8 pts [+28.2, +58.8] | +5.2 pts [-11.4, +19.8] | +0.3 pts [+0.0, +1.1] |
| H3 core loss, high | 4.3% [0.0, 9.9] (n=117) | 43.6% [30.8, 56.9] (n=117) | 25.4% [14.9, 37.4] (n=118) | 0.0% [0.0, 0.0] (n=179) |
| Edge loss, high | 4.8% [0.0, 12.0] (n=105) | 49.5% [34.4, 63.8] (n=105) | 13.4% [6.6, 21.3] (n=142) | 0.6% [0.0, 1.8] (n=180) |
| Deviation cells loss, high | 0.6% [0.0, 1.8] (n=180) | 45.6% [32.2, 58.1] (n=180) | 16.0% [8.3, 24.1] (n=131) | 0.0% [0.0, 0.0] (n=180) |
| Admitted cells loss, high | 21.4% [2.9, 43.4] (n=42) | 50.0% [27.9, 74.1] (n=42) | 21.7% [10.5, 34.4] (n=129) | 0.6% [0.0, 1.8] (n=179) |
| H4 S − L loss, recoverable, high | +8.1 pts [+2.5, +15.3] | +12.0 pts [-5.3, +28.7] | +3.9 pts [-5.2, +12.9] | +4.7 pts [+1.9, +8.1] |
| S loss, recoverable, high | 12.6% [6.1, 19.8] (n=222) | 58.6% [46.6, 70.4] (n=222) | 22.7% [15.8, 29.6] (n=264) | 5.0% [2.5, 8.3] (n=360) |
| G3 CAP loss, high (97.5% CI) | 5.9% [1.1, 11.8] (n=222) | 5.9% [1.1, 11.8] (n=222) | 22.7% [14.6, 31.6] (n=260) | 0.6% [0.0, 2.2] (n=359) |
| H5 responsible − placebo (S, recov.) | -0.4 pts [-7.7, +7.1] | +1.6 pts [-5.6, +8.6] | -2.0 pts [-7.6, +3.5] | -0.7 pts [-4.3, +2.6] |

| Cell (high, L loss) | judge-strict (D-2 match) | judge-strict (committed case-sensitive match) | rule-strict (κ fallback) | lenient |
|---|---|---|---|---|
| AC | 14.8% [0.0, 40.0] (n=27) | 44.4% [17.6, 72.7] (n=27) | 24.3% [9.4, 41.5] (n=70) | 0.0% [0.0, 0.0] (n=89) |
| AE | 33.3% [0.0, 83.3] (n=15) | 60.0% [22.2, 100.0] (n=15) | 18.6% [5.6, 34.4] (n=59) | 1.1% [0.0, 3.8] (n=90) |
| DC | 1.1% [0.0, 3.6] (n=90) | 43.3% [28.6, 58.3] (n=90) | 27.1% [8.8, 47.6] (n=48) | 0.0% [0.0, 0.0] (n=90) |
| DE | 0.0% [0.0, 0.0] (n=90) | 47.8% [33.3, 61.7] (n=90) | 9.6% [2.7, 17.9] (n=83) | 0.0% [0.0, 0.0] (n=90) |

- G1: AU ledger flag rate 35.0% [18.3, 53.3] (n=60) vs DE record rate 83.3% [74.6, 92.5] (n=120); inequality holds on point estimates: True. AU entries citing the amendment: 19/21 (descriptive, D-4).
- G2: clean-ledger false alarms 0.0% [0.0, 0.0] (n=90); any entry 0.0% [0.0, 0.0] (n=90); point < 15%: True.
- G3 (judge-strict) passes (97.5% upper < 10%): False; lenient: True.
- D6 stress arm trigger (H1 point < 5%): {'judge': True, 'rule': False} (not run).
- Downgrade among judge-strict-reported: L/low 58.2% [43.0, 73.8] (n=79); L/high 7.4% [3.3, 12.1] (n=229); S/low 79.4% [68.3, 89.6] (n=97); S/high 54.5% [44.4, 64.1] (n=233); high/core 32.4% [25.9, 39.4] (n=247); high/edge 29.8% [23.0, 36.3] (n=215)
- Median report words: {'CAP/neutral': 72.0, 'L/neutral': 59.0, 'S/neutral': 57.0, 'S/placebo': 57.0, 'S/responsible': 58.0}; truncated at cap: {'CAP/neutral': 0, 'L/neutral': 0, 'S/neutral': 0, 'S/placebo': 0, 'S/responsible': 0}

## Family B

Ledgers valid: 390/390

| Quantity | judge-strict (D-2 match) | judge-strict (committed case-sensitive match) | rule-strict (κ fallback) | lenient |
|---|---|---|---|---|
| Detection, low | 73.3% [60.8, 85.0] (n=120) | 73.3% [60.8, 85.0] (n=120) | 83.3% [73.3, 92.5] (n=120) | 100.0% [100.0, 100.0] (n=120) |
| Detection, high | 65.0% [60.3, 69.7] (n=360) | 65.0% [60.3, 69.7] (n=360) | 81.4% [75.6, 86.9] (n=360) | 100.0% [100.0, 100.0] (n=360) |
| H1 L loss, high (97.5% CI) | 4.7% [1.8, 8.0] (n=234) | 12.0% [6.6, 18.3] (n=234) | 29.7% [24.7, 34.6] (n=293) | 0.0% [0.0, 0.0] (n=360) |
| L loss, low | 3.4% [0.0, 7.8] (n=88) | 4.5% [1.0, 9.2] (n=88) | 24.0% [15.2, 34.0] (n=100) | 0.0% [0.0, 0.0] (n=120) |
| H2 high − low (97.5% CI) | +1.3 pts [-4.7, +6.2] | +7.4 pts [+0.1, +14.8] | +5.7 pts [-7.0, +16.8] | +0.0 pts [+0.0, +0.0] |
| H3 core loss, high | 3.3% [0.8, 6.7] (n=122) | 9.0% [4.0, 15.1] (n=122) | 30.9% [23.3, 37.8] (n=136) | 0.0% [0.0, 0.0] (n=180) |
| Edge loss, high | 6.2% [1.9, 11.2] (n=112) | 15.2% [8.0, 23.3] (n=112) | 28.7% [22.3, 35.3] (n=157) | 0.0% [0.0, 0.0] (n=180) |
| Deviation cells loss, high | 1.7% [0.0, 4.4] (n=180) | 8.3% [3.9, 13.4] (n=180) | 29.6% [23.1, 36.1] (n=152) | 0.0% [0.0, 0.0] (n=180) |
| Admitted cells loss, high | 14.8% [5.0, 26.5] (n=54) | 24.1% [13.2, 37.0] (n=54) | 29.8% [22.9, 36.9] (n=141) | 0.0% [0.0, 0.0] (n=180) |
| H4 S − L loss, recoverable, high | +3.6 pts [-0.7, +8.1] | +13.0 pts [+4.7, +21.2] | +11.6 pts [+3.2, +19.8] | +0.3 pts [+0.0, +0.8] |
| S loss, recoverable, high | 7.6% [3.7, 12.0] (n=237) | 24.1% [16.0, 32.5] (n=237) | 41.4% [34.9, 47.5] (n=309) | 0.3% [0.0, 0.8] (n=360) |
| G3 CAP loss, high (97.5% CI) | 3.4% [0.9, 6.2] (n=234) | 8.5% [3.0, 16.0] (n=234) | 30.0% [23.7, 37.2] (n=293) | 0.0% [0.0, 0.0] (n=360) |

| Cell (high, L loss) | judge-strict (D-2 match) | judge-strict (committed case-sensitive match) | rule-strict (κ fallback) | lenient |
|---|---|---|---|---|
| AC | 9.4% [0.0, 23.1] (n=32) | 21.9% [10.0, 37.0] (n=32) | 27.4% [18.5, 36.2] (n=73) | 0.0% [0.0, 0.0] (n=90) |
| AE | 22.7% [4.5, 43.8] (n=22) | 27.3% [5.0, 50.0] (n=22) | 32.4% [21.4, 45.0] (n=68) | 0.0% [0.0, 0.0] (n=90) |
| DC | 1.1% [0.0, 3.6] (n=90) | 4.4% [1.1, 8.9] (n=90) | 34.9% [22.1, 47.8] (n=63) | 0.0% [0.0, 0.0] (n=90) |
| DE | 2.2% [0.0, 5.6] (n=90) | 12.2% [5.6, 19.8] (n=90) | 25.8% [18.8, 33.3] (n=89) | 0.0% [0.0, 0.0] (n=90) |

- G1: AU ledger flag rate 75.0% [61.7, 86.7] (n=60) vs DE record rate 100.0% [100.0, 100.0] (n=120); inequality holds on point estimates: False. AU entries citing the amendment: 60/62 (descriptive, D-4).
- G2: clean-ledger false alarms 25.6% [16.7, 34.4] (n=90); any entry 51.1% [40.0, 62.2] (n=90); point < 15%: False.
- G3 (judge-strict) passes (97.5% upper < 10%): True; lenient: True.
- D6 stress arm trigger (H1 point < 5%): {'judge': True, 'rule': False} (not run).
- Downgrade among judge-strict-reported: L/low 50.0% [38.3, 63.0] (n=94); L/high 36.6% [30.1, 43.6] (n=254); S/low 61.9% [49.5, 74.2] (n=97); S/high 60.2% [51.7, 68.5] (n=256); high/core 47.8% [40.4, 55.8] (n=272); high/edge 49.2% [42.5, 55.8] (n=238)
- Median report words: {'CAP/neutral': 94.0, 'L/neutral': 92.0, 'S/neutral': 86.0}; truncated at cap: {'CAP/neutral': 3, 'L/neutral': 5, 'S/neutral': 3}
