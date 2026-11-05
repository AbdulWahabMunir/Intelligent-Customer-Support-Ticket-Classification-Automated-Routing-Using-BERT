# DistilBERT experiment

## Question and fixed protocol

Can DistilBERT improve on the validation-selected TF-IDF Logistic Regression baseline on the same 27-intent task?

- Official model: `distilbert/distilbert-base-uncased`, revision `12040accade4e8a0f71eabdb258fecc2e7e948be`.
- Same hashed, deduplicated 70/15/15 splits and seed 42 as the baselines.
- Input is `instruction` only. Categories are derived from the training intent-to-category map.
- Maximum length 64 subword tokens, dynamic batch padding.
- Three epochs, learning rate 2e-5, batch size 16, AdamW, weight decay 0.01, 10% warmup.
- Choose checkpoint by validation macro F1; evaluate the test set only in a separate explicit command after training.
- No tuning against inspected test errors. Shared templates still limit conclusions about generalization.

Design follows Hugging Face's [sequence classification guide](https://huggingface.co/docs/transformers/v4.57.6/en/tasks/sequence_classification). This implementation uses PyTorch datasets directly, so the Hugging Face `datasets` package is unnecessary.

## Local environment and smoke check

Hardware discovery found Intel UHD Graphics 620; no NVIDIA GPU was detected. Full training subsequently completed locally on CPU; Colab remains an optional alternative. Windows Python 3.14 wheels resolved for the dependencies listed below.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m src.analyze_errors
.venv\Scripts\python.exe -m src.train_distilbert --smoke --cpu
```

Smoke mode trains for two steps on two examples per intent from each of the train and validation splits. It then evaluates validation, saves the checkpoint, reloads it and checks finite inference logits. It never reads the test CSV. Its metrics are not benchmark results. Smoke models and reports have separate directories from full runs.

Verified locally: dependency checks passed, seven unit tests passed, and the pretrained CPU smoke run completed successfully with saved-model reload and finite inference logits. The smoke run used 54 training and 54 validation examples. See `reports/distilbert-smoke/training.json` for its versions and provenance.

The complete three-epoch CPU run also succeeded on all 16,991 training and 3,641 validation messages. Training, final validation and export took 3,309.88 seconds (about 55 minutes). Validation macro F1 increased from 0.9940 to 0.9959 to 0.9971, selecting epoch three. The final checkpoint was reloaded and produced finite inference logits. Full-run details are in `reports/distilbert/training.json`; Colab has not been executed.

The first run downloads pretrained weights into `.cache/huggingface`. Network access is required. A new classification head is initialized randomly, which is expected. Existing experiment directories are protected against accidental overwrites; choose a new `--output` directory for another run.

## Full training in Colab

1. Run `.venv\Scripts\python.exe -m src.package_colab` locally.
2. Open `notebooks/02_distilbert_colab.ipynb` in Colab and select a GPU runtime.
3. Run the notebook, upload the generated `artifacts/distilbert-colab.zip`, then train. The archive includes the exact existing splits and baseline provenance. It excludes raw data, caches and unrelated files. Keep it private and follow the dataset license terms.
4. Inspect validation output. Run the separate test evaluation cell only after training completes.
5. Download the final artifact ZIP before the Colab runtime ends. GPU access and training time depend on the selected Colab runtime; none is provisioned automatically here.

Colab retains its preinstalled GPU-compatible PyTorch. The notebook installs the same scikit-learn and Transformers/Accelerate versions and records all installed versions with the result. Windows and Colab lockfiles differ by platform.

Local full-run equivalents (CPU is supported but may be slow):

```powershell
.venv\Scripts\python.exe -m src.train_distilbert
.venv\Scripts\python.exe -m src.train_distilbert --evaluate-only
```

Full-run metadata and validation results are in `reports/distilbert/training.json`. Test evaluation adds per-class scores, a confusion matrix, baseline test macro F1 and warm single-message latency measurements. See `reports/distilbert/test_metrics.json` and `reports/distilbert/comparison.md` after evaluation completes. Confidence calibration and an API load test remain future work.

## Completed held-out evaluation

The CPU test evaluation completed on all 3,642 held-out messages after checkpoint selection was fixed. DistilBERT achieved 99.8627% intent accuracy, macro F1 0.998328 and weighted F1 0.998624. Five intent predictions were incorrect, compared with 38 for Logistic Regression; derived category accuracy was 100% on this test split.

Warm single-message tokenization and inference averaged 35.62 ms (p95 43.30 ms) for DistilBERT and 1.53 ms (p95 1.99 ms) for Logistic Regression on the same 200 messages, measured sequentially in the same CPU process. This is a local timing comparison rather than a concurrency or API load test. DistilBERT contains 66,974,235 parameters.

The experiment establishes an improvement on this synthetic dataset split, at additional inference cost. It does not establish real-world reliability. Near-duplicate/template overlap, linguistic challenge-set performance and calibration still require investigation.
