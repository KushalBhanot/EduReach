q01 answerable   cited
q02 answerable   cited
q03 answerable   cited
q04 answerable   cited
q05 answerable   cited
q06 answerable   cited
q07 answerable   cited
q08 answerable   cited
q09 answerable   cited
q10 answerable   cited
q11 answerable   cited
q12 answerable   cited
q13 answerable   cited
q14 answerable   cited
q15 answerable   cited
q16 answerable   cited
q17 answerable   cited
q18 answerable   cited
q19 answerable   cited
q20 answerable   cited
q21 answerable   cited
q22 answerable   cited
q23 answerable   cited
q24 answerable   cited
q25 answerable   cited
q26 answerable   cited
q27 answerable   cited
q28 answerable   cited
q29 answerable   cited
q30 answerable   cited
q31 answerable   cited
q32 answerable   cited
q33 answerable   cited
q34 answerable   cited
q35 answerable   cited
q36 answerable   cited
q37 answerable   cited
q38 answerable   cited
q39 answerable   cited
q40 answerable   cited
q41 answerable   cited
q42 answerable   cited
q43 answerable   cited
q44 answerable   cited
q45 multilingual cited
q46 multilingual cited
q47 multilingual cited
q48 multilingual cited
q49 multilingual cited
q50 multilingual cited
q51 unsupported  out_of_scope
q52 unsupported  out_of_scope
q53 unsupported  out_of_scope
q54 unsupported  out_of_scope
q55 unsupported  out_of_scope
q56 unsupported  out_of_scope
q57 unsupported  insufficient
q58 unsupported  out_of_scope
q59 unsupported  out_of_scope
q60 unsupported  out_of_scope
q61 no_corpus    out_of_scope
q62 no_corpus    out_of_scope

**Grounding outcome (RAG run) by question kind**

| Kind | n | cited | uncited | insufficient | out_of_scope | error |
|---|---|---|---|---|---|---|
| answerable | 44 | 44 | 0 | 0 | 0 | 0 |
| multilingual | 6 | 6 | 0 | 0 | 0 | 0 |
| unsupported | 10 | 0 | 0 | 1 | 9 | 0 |
| no_corpus | 2 | 0 | 0 | 0 | 2 | 0 |

Cited answers that cite at least one gold section: 50/50

**Per-request cost and latency** (median / p95)

| Measure | RAG | Prompt-only |
|---|---|---|
| End-to-end latency (ms) | 1792 / 3602 | 1458 / 1734 |
| Query embedding (ms) | 216 / 488 | n/a |
| Vector search (ms) | 24.9 / 40.6 | n/a |
| Generation (ms) | 1511 / 3154 | 1456 / 1733 |
| Prompt tokens | 2022 / 2789 | 152 / 163 |
| Output tokens | 262 / 833 | 254 / 285 |
| Cost per request (USD, x1000) | 0.875 / 1.888 | 0.419 / 0.466 |

Models that served: {'gemini-3.1-flash-lite': 124}
