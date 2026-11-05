# Baseline comparison

Selection: validation macro F1, before examining test results.

| Model | Validation macro F1 | Test accuracy | Test macro F1 | Test weighted F1 |
| --- | ---: | ---: | ---: | ---: |
| logistic_regression | 0.9841 | 0.9896 | 0.9885 | 0.9895 |
| naive_bayes | 0.9837 | 0.9849 | 0.9836 | 0.9849 |

Selected model: **logistic_regression**.

Both models use word unigram/bigram TF-IDF fitted on training messages only. Category is derived from the training intent-to-category map. Per-class precision/recall/F1 and category accuracy are in metrics.json; confusion matrices have actual labels in rows and predicted labels in columns.

These scores describe a deduplicated random split of synthetic Bitext data. Shared templates and paraphrases may inflate scores; real customer performance and linguistic robustness are not established. Confidence calibration has not been evaluated. Do not tune against the test results.
