# BANKING77 additional experiment

A separate 77-intent banking-domain experiment. This does not evaluate the Bitext classifier on incompatible labels, fine-tune a second transformer, or change the deployed 27-intent model.

| Model | Test accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| naive_bayes | 0.7893 | 0.7741 | 0.7741 |
| logistic_regression | 0.8500 | 0.8482 | 0.8482 |

Training/validation/official test rows: 8493/1499/3080. Removed 11 normalized duplicate/overlap training rows. TF-IDF fits training text only. Selected by validation macro F1 with seed 42; no test-set tuning.

Source: https://github.com/PolyAI-LDN/task-specific-datasets/tree/57ec275d8078af65b7731c2a98be812d844a6d6b/banking_data. Attribution: PolyAI, Casanueva et al., Efficient Intent Detection with Dual Sentence Encoders (2020), https://arxiv.org/abs/2003.04807. Dataset license: CC BY 4.0. Raw examples are excluded from Git.