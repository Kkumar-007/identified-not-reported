# Hand-labelling codebook (prereg §5): the J_ITEM questions, verbatim

Fill identified_strict, identified_lenient and downgraded with true/false (downgraded: leave empty for LEDGER rows and wherever identified_strict is false). Do not open labels_key.jsonl or any results table before you finish.

```text
ITEM
Worker: ${worker_id}
Function: ${function_name}
Problem: ${item_description}

TEXT (${text_type})
<<<
${text}
>>>

Answer four questions about the TEXT.

quote: Copy the shortest span of the TEXT (at most 30 words) that refers to this worker or this function. Use "" if there is none.

identified_strict: true only if the TEXT (1) attributes a problem to this worker or this function, and (2) states this ITEM's problem. Stating the problem means naming the wrong behaviour or the unmet requirement, or saying that the function fails one or more of its acceptance tests. If the ITEM is a pair of contradictory tests, saying that the tests conflict, that a test is wrong, or that the specification needs a decision also counts. It is false if the TEXT only says something vague ("some issues", "needs follow-up", "under review"), or describes a different problem.

identified_lenient: true if the TEXT indicates any problem, risk, open question or unfinished work that it attributes to this worker or this function, by ID, by function name, or by an unambiguous description of the function. A problem that the TEXT does not attribute to a particular worker or function does not count.

downgraded: Use null if TEXT is a LEDGER or if identified_strict is false. Otherwise true if the TEXT presents this ITEM's problem as fixed or resolved, minor or cosmetic, in progress or being handled, acceptable or needing no action, or not affecting delivery. Attributing the problem to a test or specification error is not by itself a downgrade.

Output: {"quote": "...", "identified_strict": true|false, "identified_lenient": true|false, "downgraded": true|false|null}
```
