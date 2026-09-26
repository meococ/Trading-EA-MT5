# CENSUS - outcome-blind signal census (DESIGN only)

No P/L is computed here or anywhere above this file.

```
   sym        cfg family  signals  sig_wk  long  short  at_sr_share  thru_share  e2_removed  sparse
EURUSD       F0_J     F0     1055    2.02   507    548          0.0       0.420           0   False
EURUSD   F1_W2whq     F1      209    0.40   105    104          1.0       0.421           0    True
EURUSD F1_W2swing     F1      156    0.30    65     91          1.0       0.449           0    True
EURUSD      F1_W3     F1      448    0.86   209    239          0.0       1.000           0   False
EURUSD     F1_W4a     F1       28    0.05    12     16          0.0       0.286           0    True
EURUSD     F1_W4b     F1        0    0.00     0      0          NaN         NaN           0    True
EURUSD     F1_R1b     F1     1047    2.00   499    548          0.0       0.415           3   False
EURUSD     F1_R2a     F1      801    1.53   389    412          0.0       0.414           0   False
EURUSD     F1_R2b     F1      337    0.64   168    169          0.0       0.386           0   False
EURUSD      F1_PV     F1       23    0.04    12     11          0.0       0.696           0    True
EURUSD    F1_FULL     F1        0    0.00     0      0          NaN         NaN           0    True
EURUSD F1_FULL_RE     F1        0    0.00     0      0          NaN         NaN           0    True
EURUSD    F2_NH_a     F2     3764    7.20  1894   1870          0.0       0.000           0   False
EURUSD    F2_NH_b     F2     3480    6.65  1749   1731          0.0       0.000          13   False
EURUSD  F3_LUCY_a     F3    10591   20.25  5030   5561          0.0       0.000          18   False
EURUSD  F3_LUCY_b     F3     7916   15.13  3756   4160          0.0       0.000          17   False
EURUSD   F4_BAI14     F4     8995   17.20  4338   4657          0.0       0.000           0   False
XAUUSD       F0_J     F0     1027    1.96   507    520          0.0       0.449           2   False
XAUUSD   F1_W2whq     F1      346    0.66   178    168          1.0       0.451           1   False
XAUUSD F1_W2swing     F1       92    0.18    47     45          1.0       0.511           0    True
XAUUSD      F1_W3     F1      470    0.90   232    238          0.0       1.000           0   False
XAUUSD     F1_W4a     F1       27    0.05    11     16          0.0       0.333           0    True
XAUUSD     F1_W4b     F1        0    0.00     0      0          NaN         NaN           0    True
XAUUSD     F1_R1b     F1     1007    1.93   499    508          0.0       0.449           3   False
XAUUSD     F1_R2a     F1      821    1.57   399    422          0.0       0.442           2   False
XAUUSD     F1_R2b     F1      153    0.29    70     83          0.0       0.386           1    True
XAUUSD      F1_PV     F1       21    0.04    15      6          0.0       0.667           0    True
XAUUSD    F1_FULL     F1        0    0.00     0      0          NaN         NaN           0    True
XAUUSD F1_FULL_RE     F1        0    0.00     0      0          NaN         NaN           0    True
XAUUSD    F2_NH_a     F2     4142    7.92  2007   2135          0.0       0.000         759   False
XAUUSD    F2_NH_b     F2     3853    7.37  1855   1998          0.0       0.000          42   False
XAUUSD  F3_LUCY_a     F3    10964   20.96  5747   5217          0.0       0.000        6866   False
XAUUSD  F3_LUCY_b     F3     8622   16.48  4463   4159          0.0       0.000        5507   False
XAUUSD   F4_BAI14     F4     9254   17.69  4834   4420          0.0       0.000         665   False
```

## Pairwise signal-bar overlap (same t and dir)

```
   sym          a          b  overlap
EURUSD       F0_J   F1_W2whq      205
EURUSD       F0_J F1_W2swing      153
EURUSD       F0_J      F1_W3      443
EURUSD       F0_J     F1_W4a       27
EURUSD       F0_J     F1_R1b     1042
EURUSD       F0_J     F1_R2a      797
EURUSD       F0_J     F1_R2b      330
EURUSD       F0_J      F1_PV       23
EURUSD       F0_J    F2_NH_a      570
EURUSD       F0_J    F2_NH_b      524
EURUSD       F0_J  F3_LUCY_a        7
EURUSD       F0_J  F3_LUCY_b        6
EURUSD       F0_J   F4_BAI14      580
EURUSD   F1_W2whq F1_W2swing       29
EURUSD   F1_W2whq      F1_W3       88
EURUSD   F1_W2whq     F1_W4a        5
EURUSD   F1_W2whq     F1_R1b      203
EURUSD   F1_W2whq     F1_R2a      152
EURUSD   F1_W2whq     F1_R2b       46
EURUSD   F1_W2whq      F1_PV        6
EURUSD   F1_W2whq    F2_NH_a      109
EURUSD   F1_W2whq    F2_NH_b      100
EURUSD   F1_W2whq  F3_LUCY_a        1
EURUSD   F1_W2whq  F3_LUCY_b        1
EURUSD   F1_W2whq   F4_BAI14      127
EURUSD F1_W2swing      F1_W3       70
EURUSD F1_W2swing     F1_W4a        2
EURUSD F1_W2swing     F1_R1b      153
EURUSD F1_W2swing     F1_R2a      100
EURUSD F1_W2swing     F1_R2b       41
EURUSD F1_W2swing      F1_PV        9
EURUSD F1_W2swing    F2_NH_a       77
EURUSD F1_W2swing    F2_NH_b       71
EURUSD F1_W2swing  F3_LUCY_a        3
EURUSD F1_W2swing  F3_LUCY_b        2
EURUSD F1_W2swing   F4_BAI14       84
EURUSD      F1_W3     F1_W4a        8
EURUSD      F1_W3     F1_R1b      434
EURUSD      F1_W3     F1_R2a      332
EURUSD      F1_W3     F1_R2b      130
EURUSD      F1_W3      F1_PV       16
EURUSD      F1_W3    F2_NH_a      245
EURUSD      F1_W3    F2_NH_b      222
EURUSD      F1_W3  F3_LUCY_a        2
EURUSD      F1_W3  F3_LUCY_b        1
EURUSD      F1_W3   F4_BAI14      247
EURUSD     F1_W4a     F1_R1b       28
EURUSD     F1_W4a     F1_R2a       20
EURUSD     F1_W4a     F1_R2b        4
EURUSD     F1_W4a    F2_NH_a       15
EURUSD     F1_W4a    F2_NH_b       14
EURUSD     F1_W4a   F4_BAI14       17
EURUSD     F1_R1b     F1_R2a      786
EURUSD     F1_R1b     F1_R2b      324
EURUSD     F1_R1b      F1_PV       23
EURUSD     F1_R1b    F2_NH_a      563
EURUSD     F1_R1b    F2_NH_b      525
EURUSD     F1_R1b  F3_LUCY_a        7
EURUSD     F1_R1b  F3_LUCY_b        6
EURUSD     F1_R1b   F4_BAI14      579
EURUSD     F1_R2a     F1_R2b      260
EURUSD     F1_R2a      F1_PV       16
EURUSD     F1_R2a    F2_NH_a      529
EURUSD     F1_R2a    F2_NH_b      513
EURUSD     F1_R2a  F3_LUCY_a        7
EURUSD     F1_R2a  F3_LUCY_b        6
EURUSD     F1_R2a   F4_BAI14      357
EURUSD     F1_R2b      F1_PV        6
EURUSD     F1_R2b    F2_NH_a      194
EURUSD     F1_R2b    F2_NH_b      177
EURUSD     F1_R2b  F3_LUCY_a        3
EURUSD     F1_R2b  F3_LUCY_b        3
EURUSD     F1_R2b   F4_BAI14      189
EURUSD      F1_PV    F2_NH_a       12
EURUSD      F1_PV    F2_NH_b       11
EURUSD      F1_PV   F4_BAI14       11
EURUSD    F2_NH_a    F2_NH_b     3411
EURUSD    F2_NH_a  F3_LUCY_a       23
EURUSD    F2_NH_a  F3_LUCY_b       19
EURUSD    F2_NH_a   F4_BAI14     1605
EURUSD    F2_NH_b  F3_LUCY_a       21
EURUSD    F2_NH_b  F3_LUCY_b       18
EURUSD    F2_NH_b   F4_BAI14     1358
EURUSD  F3_LUCY_a  F3_LUCY_b     7916
EURUSD  F3_LUCY_a   F4_BAI14       68
EURUSD  F3_LUCY_b   F4_BAI14       49
XAUUSD       F0_J   F1_W2whq      342
XAUUSD       F0_J F1_W2swing       91
XAUUSD       F0_J      F1_W3      461
XAUUSD       F0_J     F1_W4a       27
XAUUSD       F0_J     F1_R1b     1004
XAUUSD       F0_J     F1_R2a      818
XAUUSD       F0_J     F1_R2b      151
XAUUSD       F0_J      F1_PV       21
XAUUSD       F0_J    F2_NH_a      578
XAUUSD       F0_J    F2_NH_b      530
XAUUSD       F0_J  F3_LUCY_a        5
XAUUSD       F0_J  F3_LUCY_b        3
XAUUSD       F0_J   F4_BAI14      617
XAUUSD   F1_W2whq F1_W2swing       26
XAUUSD   F1_W2whq      F1_W3      156
XAUUSD   F1_W2whq     F1_W4a       12
XAUUSD   F1_W2whq     F1_R1b      335
XAUUSD   F1_W2whq     F1_R2a      271
XAUUSD   F1_W2whq     F1_R2b       35
XAUUSD   F1_W2whq      F1_PV       10
XAUUSD   F1_W2whq    F2_NH_a      183
XAUUSD   F1_W2whq    F2_NH_b      165
XAUUSD   F1_W2whq  F3_LUCY_a        2
XAUUSD   F1_W2whq  F3_LUCY_b        1
XAUUSD   F1_W2whq   F4_BAI14      199
XAUUSD F1_W2swing      F1_W3       47
XAUUSD F1_W2swing     F1_W4a        2
XAUUSD F1_W2swing     F1_R1b       90
XAUUSD F1_W2swing     F1_R2a       62
XAUUSD F1_W2swing     F1_R2b        8
XAUUSD F1_W2swing      F1_PV        4
XAUUSD F1_W2swing    F2_NH_a       53
XAUUSD F1_W2swing    F2_NH_b       45
XAUUSD F1_W2swing   F4_BAI14       63
XAUUSD      F1_W3     F1_W4a        9
XAUUSD      F1_W3     F1_R1b      450
XAUUSD      F1_W3     F1_R2a      363
XAUUSD      F1_W3     F1_R2b       59
XAUUSD      F1_W3      F1_PV       14
XAUUSD      F1_W3    F2_NH_a      257
XAUUSD      F1_W3    F2_NH_b      237
XAUUSD      F1_W3  F3_LUCY_a        1
XAUUSD      F1_W3  F3_LUCY_b        1
XAUUSD      F1_W3   F4_BAI14      290
XAUUSD     F1_W4a     F1_R1b       27
XAUUSD     F1_W4a     F1_R2a       23
XAUUSD     F1_W4a     F1_R2b        2
XAUUSD     F1_W4a    F2_NH_a       15
XAUUSD     F1_W4a    F2_NH_b       15
XAUUSD     F1_W4a   F4_BAI14       12
XAUUSD     F1_R1b     F1_R2a      804
XAUUSD     F1_R1b     F1_R2b      149
XAUUSD     F1_R1b      F1_PV       20
XAUUSD     F1_R1b    F2_NH_a      567
XAUUSD     F1_R1b    F2_NH_b      532
XAUUSD     F1_R1b  F3_LUCY_a        5
XAUUSD     F1_R1b  F3_LUCY_b        3
XAUUSD     F1_R1b   F4_BAI14      600
XAUUSD     F1_R2a     F1_R2b      127
XAUUSD     F1_R2a      F1_PV       13
XAUUSD     F1_R2a    F2_NH_a      549
XAUUSD     F1_R2a    F2_NH_b      525
XAUUSD     F1_R2a  F3_LUCY_a        3
XAUUSD     F1_R2a  F3_LUCY_b        3
XAUUSD     F1_R2a   F4_BAI14      421
XAUUSD     F1_R2b      F1_PV        2
XAUUSD     F1_R2b    F2_NH_a       91
XAUUSD     F1_R2b    F2_NH_b       82
XAUUSD     F1_R2b  F3_LUCY_a        2
XAUUSD     F1_R2b  F3_LUCY_b        1
XAUUSD     F1_R2b   F4_BAI14      100
XAUUSD      F1_PV    F2_NH_a        8
XAUUSD      F1_PV    F2_NH_b        7
XAUUSD      F1_PV   F4_BAI14       12
XAUUSD    F2_NH_a    F2_NH_b     3760
XAUUSD    F2_NH_a  F3_LUCY_a       25
XAUUSD    F2_NH_a  F3_LUCY_b       20
XAUUSD    F2_NH_a   F4_BAI14     1862
XAUUSD    F2_NH_b  F3_LUCY_a       25
XAUUSD    F2_NH_b  F3_LUCY_b       20
XAUUSD    F2_NH_b   F4_BAI14     1606
XAUUSD  F3_LUCY_a  F3_LUCY_b     8622
XAUUSD  F3_LUCY_a   F4_BAI14       56
XAUUSD  F3_LUCY_b   F4_BAI14       41
```
