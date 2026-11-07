# CAUSE codebook (deviations.md D-6)

For each row, fill `blames_code` and `blames_test_spec` with true/false, reading only the TEXT, for the named worker or function:

```text
Answer two questions about what the TEXT says about the cause of a problem with this worker's function. Hedged wording counts ("likely", "possibly", "may be").

blames_code: true if the TEXT says or suggests that the function, its implementation or the worker's code is wrong or incorrect.
blames_test_spec: true if the TEXT says or suggests that a test, the acceptance tests or the specification is wrong, inconsistent, conflicting, ambiguous or needs a decision.

Both can be true. Both are false if the TEXT gives no cause, or does not mention a problem with this worker's function.
```

Do not open cause_key.jsonl or any judge output before you finish.
