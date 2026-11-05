# Raw model score diagnostics

Measured on the fixed synthetic Bitext test split. No score transformation, calibration fitting or threshold selection was performed.

| Model | Accuracy | ECE (10 bins) | Brier sum | Log loss | Score < 0.8 |
| --- | ---: | ---: | ---: | ---: | ---: |
| logistic_regression | 0.9896 | 0.1238 | 0.0466 | 0.1710 | 0.2054 |
| distilbert | 0.9986 | 0.0012 | 0.0022 | 0.0072 | 0.0014 |

ECE is the support-weighted absolute gap between top-score averages and empirical accuracy in ten equal-width bins. Brier sum is the mean sum of squared probability errors over all classes (not divided by class count). Empty bins have null accuracy and score. These measures depend on the test distribution and do not establish calibration for real tickets or out-of-domain inputs.

Raw scores stay marked uncalibrated in the API. Proper post-hoc calibration would need fitting on validation data and an untouched evaluation protocol; that is a future experiment.
