# Baselines versus DistilBERT

All models use the same hashed splits. Model/checkpoint selection uses validation macro F1; test scores are descriptive final results.

| Model | Test accuracy | Test macro F1 | Test weighted F1 |
| --- | ---: | ---: | ---: |
| logistic_regression | 0.9896 | 0.9885 | 0.9895 |
| naive_bayes | 0.9849 | 0.9836 | 0.9849 |
| distilbert | 0.9986 | 0.9983 | 0.9986 |

DistilBERT warm single-message latency on cpu: mean 35.62 ms, p95 43.30 ms (200 messages).
Logistic Regression measured in the same evaluation process on CPU: mean 1.53 ms, p95 1.99 ms, using the same 200 messages. These are local warm timings, not API load-test results.

Scores cover a deduplicated random split of synthetic Bitext data. Shared templates may inflate performance. Real-ticket robustness and confidence calibration remain untested.
