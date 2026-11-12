
**English questions**, n=44

| Mode | hit@1 | hit@3 | hit@5 | MRR@10 |
|---|---|---|---|---|
| vector | 41/44 | 44/44 | 44/44 | 0.962 |
| keyword | 28/44 | 35/44 | 38/44 | 0.742 |
| hybrid | 37/44 | 42/44 | 44/44 | 0.905 |

**Hindi/Spanish/French questions**, n=6

| Mode | hit@1 | hit@3 | hit@5 | MRR@10 |
|---|---|---|---|---|
| vector | 5/6 | 6/6 | 6/6 | 0.917 |
| keyword | 0/6 | 0/6 | 1/6 | 0.042 |
| hybrid | 5/6 | 6/6 | 6/6 | 0.917 |

**Best cosine similarity: covered vs not covered by the books**

| Set | n | min | median | max |
|---|---|---|---|---|
| covered | 50 | 0.653 | 0.715 | 0.764 |
| not covered | 10 | 0.539 | 0.579 | 0.634 |

**What a MIN_SCORE gate would do**

| Threshold | covered questions kept | not-covered questions rejected |
|---|---|---|
| 0.55 | 50/50 | 1/10 |
| 0.60 | 50/50 | 9/10 |
| 0.62 | 50/50 | 9/10 |
| 0.64 | 50/50 | 10/10 |
| 0.66 | 47/50 | 10/10 |
| 0.68 | 45/50 | 10/10 |
| 0.70 | 36/50 | 10/10 |
| 0.72 | 21/50 | 10/10 |

**Vector misses at k=5** (question -> top results)


No-corpus questions skipped retrieval: 2/2
