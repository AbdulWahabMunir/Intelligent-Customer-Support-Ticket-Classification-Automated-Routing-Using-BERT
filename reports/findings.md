# Initial Bitext audit

Source revision: `430d1a89bd93bd1fa23c16f29dd53e73f0087443`.
Generated from the actual downloaded CSV using `python -m src.data.inspect`.

| Check | Result |
| --- | ---: |
| Rows | 26,872 |
| Categories | 11 |
| Intents | 27 |
| Missing values across all columns | 0 |
| Fully duplicated rows | 0 |
| Repeated exact input messages beyond first occurrence | 2,237 |
| Repeated normalized input messages beyond first occurrence | 2,598 |
| Normalized message groups with conflicting targets | 0 |
| Median / maximum message length in whitespace words | 9 / 16 |

ACCOUNT is the largest category (5,986 rows); CANCEL is the smallest (950). Intent counts are comparatively balanced (950–1,000 rows per intent). Category and intent balance are different because categories group different numbers of intents.

Full rows are unique while input messages repeat, so dropping only full-row duplicates would leave input overlap. Normalize case and whitespace for duplicate detection before splitting. The resulting 24,274 unique message keys have consistent category and intent labels. Each intent maps to a single category in this revision.

Do not infer real-world model performance from this audit. Generated phrasing and shared templates may still overlap after deduplication. Future work needs a template/near-duplicate audit and a separate robustness set. No model metrics are available yet.

The notebook is provided for interactive exploration; the command-line inspection and two unit tests were executed. Jupyter has not been installed or launched.
