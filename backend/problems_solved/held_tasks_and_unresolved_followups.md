# Held tasks and unresolved follow-ups

Recorded: 15 October 2026.

**Status: solution implemented on 15 October 2026 and verified offline; no paid run yet.** See the solution section at the end. No prompt change or new model experiment is recorded here.

Related backlog entries: [Pending Improvements, issues 1, 4, 5 and 12](../docs/Pending_Improvements.md).

## The historical problem in simple words

We need to distinguish understanding a request from allowing it to be allocated. Before the agreed preview policy, an unresolved follow-up could hold allocation. That hold also prevented verification of the request's existing evidence and left its useful details out of the plan summary. A stored hold could remain after its original blocking review was removed.

There is also the opposite failure: a follow-up mistakenly becomes a separate task, so its restriction does not block or update the original request.

The examples below are from [dispatch_requests_blocker_cases.txt](../data/dispatch_requests_blocker_cases.txt). Its R numbers are different from the R numbers in the original 30-request file. In this blocker file, R07 is message L0007, for example.

## Example 1: ORD-108 gets stuck

> R07 [08:28] Boss: ORD-108, 2000 scarves, Harbor Knits, Apr 03. Move it now.
>
> R08 [08:30] Ravi: Speed priority?
>
> R09 [08:31] Boss: Yes.

The development test expects R08 and R09 to belong to the ORD-108 conversation, establishing a fastest-workshop preference. That expected interpretation is not proof that every similar short reply is unambiguous.

What happened in saved run `2026-10-15_21-19-26`:

1. R07 became task `T:L0007:J1`.
2. R08 became a separate task, `T:L0008:J1`.
3. R09 was recognised as a follow-up, but linking refused to attach it. The saved reason says that "Yes." does not establish a clear relationship to a candidate task.
4. The unresolved R09 review names no order. The two-message hold rule therefore held the tasks associated with R07 and R08.
5. Holds ran before verification. Both tasks received `related_review` records and were skipped by verification. A hold clears any existing verification; these two tasks were never verified in this run.
6. ORD-108 received no allocation recommendation and reserved no capacity. Its summary row had no order ID and said: `Resolve related processing reviews before using this task: link:L0009:J1`.

The original request remains saved. The problem is not deletion of its evidence: the summary lacks a structured interpretation, and the hold has no automatic release path.

### Evidence checked without paid calls

- The actual R09 linking payload already contained R07 and R08 as separate candidates' original evidence, with R09 as the follow-up. It did not supply a separate continuous-chat block. Missing access to these three messages is therefore not the explanation for this particular refusal; whether presentation or the prompt's linking standard caused it still needs a controlled experiment.
- The saved verification requests contained eight task IDs; `T:L0007:J1` was absent.
- In a copy of the saved state, removing only R09's unresolved-link record and calling the current hold calculation left ORD-108's `related_review` in place. The verification batch builder still skipped it.
- This diagnostic changed no saved state, plan or application code. It did not simulate an implemented dispatcher resolution flow; that flow does not exist yet.

Sources: [saved state](../output/runs/2026-10-15_21-19-26/state.json), [saved plan](../output/runs/2026-10-15_21-19-26/plan.json), [verification and holds](../order_processing_into_tasks/verify_tasks.py).

## Example 2: ORD-024 proceeds without its exclusion

> R14 [08:49] Mei: ORD-024, 300 vests, Loom & Leaf, Apr 15. Quick turnaround needed.
>
> R15 [08:51] Chen: Fastest workshop excluding QuickStitch.

The development test expects R15 to modify R14. Intake instead labelled R15 a new request. New requests immediately become separate tasks and bypass follow-up linking.

Verification marked R14 ready with no exclusions. R15 retained the QuickStitch exclusion, but had no order ID and needed clarification. The current hold calculation does not use a successfully verified task needing clarification as a blocking source, so R15 did not hold R14.

The saved plan recommended FreshStart for ORD-024. It did not select QuickStitch in this run, but QuickStitch remained an allowed alternative. The restriction was therefore not enforced.

Sources: [request/link handling](../order_processing_into_tasks/create_and_link_tasks.py), the saved state and plan above, and [Test 6](../docs/evaluation/PROMPT_TESTING_RESULTS.md#test-6-the-blocker-cases-file-with-the-narrower-hold-rule-15-oct-2026).

## Related boundaries the eventual fix must respect

- **Cancellation:** R02 requests ORD-095; R21 says, "ORD-095 has been cancelled by the customer. Do not allocate." The saved run safely held R02 through R21's rejected intake batch. However, the current same-order conflict check counts only verified tasks with intent `allocation`. A separate cancellation task verified as `unclear` would not participate in that check. This is a coverage gap, not an observed allocation of a cancelled order in this run.
- **False association:** R20, "Put 005 somewhere sensible. Cost matters more than shaving off a day.", holds the ORD-036 task through nearby R18. The bare `005` is not a recognised full order reference, so the rule falls back to nearby messages. ORD-036 was already paused; this example does not demonstrate damage to an otherwise ready unrelated task.
- **Saved holds:** stored hold records can outlive the review that created them. Holds are applied before verification and again at final save. Partial planning also applies them to a state copy. Removing an original review alone does not remove an existing `related_review`.
- **Current model limits:** these short-reply failures occurred with the recorded Luna settings. Earlier improvements from switching models should be documented separately with their specific evidence; the switch did not solve all linking failures.

## SOLUTION TO THIS PROBLEM: allocation previews with provisional warnings

Decided by Aditya and implemented on 15 October 2026. The step-by-step plan and its evidence are in [debugging/held-tasks-never-verified.md](../debugging/held-tasks-never-verified.md).

### The decision

Allocation previews are allowed while follow-up links need review.

- An unresolved input that *might* affect a task no longer holds it. The task is verified and planned from its established instructions.
- The input stays in review, with its original text and candidate task IDs. A candidate is never presented as a confirmed link.
- The plan marks each affected task provisional in `summary_rows`. A recommendation becomes `provisional_recommendation` there and still reserves tentative queue time. The raw `decisions` status remains `recommendation`, so a consumer must also read `review_warnings` or the summary. Its reason ends: "Provisional: L0009:J1 may modify this request. Please confirm whether it applies; the result may need recalculation."
- Enforced rules do not change. An incomplete or invalid request is still not allocatable, and confirmed restrictions and linked corrections are still enforced.
- No new machinery is added: no model stage, no automatic linking, no graph branch and no reallocation. Reallocation comes later; `plan["review_warnings"]` keeps the evidence it will need.

### What changed

- `possibly_affected_tasks(state)` in `verify_tasks.py` replaces `hold_reviewed_requests`. It returns {task ID: [IDs of the plan rows that may modify it]} and changes nothing.
  - Its sources are the same as before (intake reviews, link reviews and failed task reviews), plus two kinds of verified task:
    - **R15 rule:** an allocation task with no order ID that requests or excludes a workshop warns the tasks of the 2 messages before it. This covers Example 2.
    - **Unclear rule:** a task verified as `unclear` that names an order warns the other tasks of that order. This covers the cancellation boundary.
  - The same-order spread is unchanged. A task never warns itself.
- Only allocation calls it, on the state being planned. Warnings are recomputed for each plan and saved as `review_warnings` in that plan; they are not stored as holds in processing state. Partial plans no longer need a state copy or a second hold call.
- Every task is verified. `run_verification` and `save_run_outputs` no longer hold anything, and `pipeline_complete` no longer checks `held_task_ids`. Reviews no longer store `held_task_ids`, and task reviews no longer store `blocking_review_ids`.
- Runs saved before this change still plan with no special code. Their held tasks are unverified, so they keep their `processing_review` rows. Their old `related_review` records are skipped as warning sources, because they were holds, not failures.

### Alternatives considered

- **Keep holds, but verify held tasks and give them a `held` plan outcome.** This was the first plan. It fixed the dead end but still gave no recommendation for ORD-108. Aditya chose provisional previews instead.
- **Warn every link candidate.** This would flag 10 of Test 6's 14 tasks, against 6 for the hold rule's targets. Rejected as too broad.
- **Any not-ready allocation task with no order affects the 2 messages before it.** On the original 30 requests this flagged 3 to 5 ready, independent tasks. For example, R10 "New rush coming in" would flag ORD-073 and urgent ORD-045. Rejected. Requiring a requested or excluded workshop narrows it to R14 across all 14 saved runs.
- **Make a cancellation block its order** through the duplicate-order check. Not chosen: a review or task that names an order only warns, like every other source.

### Verification (offline, no paid calls)

- **Tests:** `uv run python -W default -m unittest discover -s tests` ran 69 tests OK, with no warnings and none skipped. The new tests failed first, for their stated reasons.
- **Replay of all 14 saved runs:**
  - In Test 6 (`2026-10-15_15-28-46` and `2026-10-15_21-19-26`), the warned tasks are exactly the 6 old holds plus T:L0014:J1.
  - The only changed plan row in any run is T:L0014:J1 (R14). It becomes `provisional_recommendation`, naming T:L0015:J1 (R15). Every other decision is unchanged.
  - Runs with no holds are unchanged.
- **Mutation check:** each change, switched off in memory, makes at least one test fail. The six breaks were: no R15 rule, no unclear rule, a task warning itself, old `related_review` records counted, no warnings in the plan, and verification skipping affected tasks.
- **Unchanged:** notebook 05, `data/`, `config.toml`, the prompts, response formats and `output/runs/`.

### Remaining limitations

- **Saved runs are not re-verified.** ORD-108 (Example 1) and the other formerly held tasks of Test 6 stay unverified in the saved runs. The next run of the blocker file verifies them. That needs about 5 new verification calls, which is a paid run awaiting approval. Intake and link answers stay cached.
- **A warning is not enforcement.** R14's recommendation still allows QuickStitch until the dispatcher confirms R15. A cancellation warns R02 but does not block it. Dispatcher resolution and reallocation are planned in [system design section 6](../../docs/system-design.md#6-planned-dispatcher-review-and-reallocation).
- **Warnings come from text rules.** The two-message window still links R20 to ORD-036 (false association). It still misses a correction more than two messages back (Pending Improvements, issue 5).
- **Root causes are unchanged.** Intake still labels R15 a request (issue 1), linking still refuses "Yes." (issue 2), and intake can still reject R21's batch (issue 4). Those need prompt work and paid runs.
