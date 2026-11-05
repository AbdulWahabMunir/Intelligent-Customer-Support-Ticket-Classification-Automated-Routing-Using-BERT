# Baseline error analysis

Validation errors guide analysis. Test errors are descriptive only; do not use them to tune models or author evaluation examples.

## Validation: 50 errors / 3641 messages

| Actual intent | Predicted intent | Count |
| --- | --- | ---: |
| get_invoice | check_invoice | 7 |
| cancel_order | change_order | 6 |
| edit_account | delete_account | 6 |
| get_refund | track_refund | 5 |
| registration_problems | create_account | 4 |
| create_account | delete_account | 3 |
| change_order | place_order | 3 |
| cancel_order | delete_account | 3 |
| cancel_order | place_order | 2 |
| track_order | change_order | 2 |

## Test: 38 errors / 3642 messages

| Actual intent | Predicted intent | Count |
| --- | --- | ---: |
| get_invoice | check_invoice | 6 |
| cancel_order | change_order | 5 |
| payment_issue | registration_problems | 3 |
| contact_customer_service | contact_human_agent | 3 |
| change_order | edit_account | 3 |
| get_refund | track_refund | 2 |
| create_account | delete_account | 2 |
| edit_account | delete_account | 2 |
| track_order | change_order | 2 |
| cancel_order | place_order | 1 |

## Interpretation

Manual inspection of validation errors found misspellings (such as cancle and dfownload), joined words (such as trackorder), and related-intent ambiguity (registration problems versus account creation, invoice retrieval versus invoice checking). Some short messages lack enough context to establish a unique intent. These are qualitative observations, not mutually exclusive or quantified linguistic annotations. No automatic spelling fixes or relabeling are applied.

The DistilBERT experiment retains the same split and a fixed configuration. Its outcome is unknown until training and held-out evaluation finish. A separate human-reviewed robustness set remains future work.
