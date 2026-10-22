# Development notes

These examples come from the existing investigations and run records. The results below were recorded during development; they are not new model runs made for these notes.

## 1. Thirty messages became 48 records

**Observed:** an early parser read overlapping groups of messages. Across those groups, the 30 source messages appeared 48 times. A later model deduplication step returned all 48, and the application accepted them. Copies of one request could then receive different verification results.

**Cause established:** the application had no acceptance rule that prevented a source message from being extracted again. The saved files did not establish which edited prompt had produced every result, so the investigation could not attribute the problem to one prompt version.

**Approach tried:** deduplication after extraction. It did not remove the repeated records in the inspected run.

**Change:** each intake call owned a small set of target messages. Earlier messages could be supplied as context but could not create new extracted items. Python checked coverage of the target set before accepting an answer. Different jobs inside one message still kept separate item IDs.

**Check:** the later processing and module checks cover ownership, repeated inputs and input accounting. This prevents repeated extraction of the same message. It does not prove that two differently worded messages describe the same task.

The useful distinction was between message identity and task identity. A shared order ID alone was not enough to merge requests.

Sources: [the original diagnosis in the project explanation](../docs/project-explanation.md#why-duplicate-counts-were-a-real-engineering-problem), [processing notebook](notebooks/02-order-processing-from-chat-v4.ipynb).

## 2. A deadline lost its written year

**Observed:** the earlier date pattern could read `April 2` from `April 2, 2027`. That discarded the explicit year and allowed the default year to be used.

**Cause established:** the match could end before the year. This was a Python parsing problem, separate from whether the model understood the request.

**Change:** the date pattern read complete month-first, day-first and ISO dates, including the year. A proposed date had to match the written evidence. Empty input was repaired separately so it returned without creating a run.

**Check:** the date repair was checked against 12 controlled examples. The old and new patterns also found the same spans in the supplied 30-message chat, whose dates were yearless. The record says the repair checks failed before the fix and passed afterwards.

**Limit:** reading a date correctly does not decide what the date means. Later work distinguished delivery deadlines from phrases such as "send out today" and added checks for supported relative dates. Those are separate rules.

Sources: [engineering log, 13 October](../docs/engineering-log.md#2026-10-13-simplify-notebook-05s-storage-repair-i03-and-i04-and-document-it), [combined pipeline notebook](notebooks/05-order-pipeline-mvp.ipynb).

## 3. Follow-ups became separate jobs

**Observed:** a seven-message development chat contained one request followed by corrections and additions. Intake labelled several follow-ups as new requests and discarded the message containing the deadline. Linking could not repair those labels because only items already labelled `follow_up` reached it.

**Evidence:** with `gpt-4.1-mini` intake, 3/7 labels matched the development key. Changing only intake to `gpt-5.6-luna` with high reasoning effort gave 7/7 in the recorded comparison. Linking and verification retained their earlier model settings in that comparison.

**Other attempts:** two rewritten intake prompts also reached 7/7 with Luna on this chat. Neither showed an advantage over the existing prompt. One introduced a wrong attachment on the separate 30-request input. Increasing linking effort did not solve the remaining attachment problem and was reverted.

**Result:** intake retained the deadline and recognised all four expected follow-ups. Three attached to the task; the quality instruction still remained unresolved at linking. The task was held under the policy used then, so this run did not reach verification or demonstrate a successful allocation.

**Limit:** 7/7 on a small development chat is a result for that example. It does not establish reliable interpretation of new conversations. Replaying its cache reproduces the saved answers, not a new model attempt.

Sources: [detailed intake comparison](../backend/problems_solved/followup_detection_fixed_with_luna.md), [model test record](../backend/docs/evaluation/PROMPT_TESTING_RESULTS.md).

## 4. Unresolved messages prevented useful verification

**Observed:** in a blocker-case run, six held tasks never reached verification. A request for ORD-108 was followed by a speed question and a short answer. The question became a separate task, and the answer could not be linked. The unresolved answer held nearby tasks before verification, leaving useful request details absent from their plan rows.

**Cause established:** holds were applied before verification and stored in processing state. In a diagnostic copy, removing the original unresolved-link record did not remove the old `related_review` hold. The affected task still could not reach verification.

**Initial approach considered:** verify held tasks but keep their allocations held. That would recover the structured facts while still withholding a recommendation. The chosen policy instead allowed previews with explicit provisional warnings.

**Change:** verification used the task's established evidence. Allocation separately calculated which unresolved rows might affect it. A usable recommendation could reserve tentative queue time and carry a warning naming the unresolved evidence. Missing facts and failed verification still prevented allocation. The code did not guess a link or treat a possible link as confirmed.

**Check:** the implementation was checked offline against saved states and controlled warning cases. The record distinguishes these checks from a fresh paid run on the blocker chat. Historical runs still containing unverified held tasks did not acquire missing verification just by being replanned.

**Limit:** a provisional recommendation can still be unsuitable to approve. In later 100-case testing, a cancelled order was recommended unsafely. Removing stale holds did not solve cancellation interpretation or dispatcher resolution.

Sources: [investigation and implementation steps](../backend/debugging/held-tasks-never-verified.md), [problem and solution record](../backend/problems_solved/held_tasks_and_unresolved_followups.md), [later golden-set results](../backend/docs/evaluation/GOLDEN_100_RUN_REPORT.md).

## What these checks establish

Controlled checks test particular code rules. Cached replays compare behavior using recorded interpretations. Fresh model runs test the language stages under the recorded settings. The human-reviewed answer key supplies expected results for the separate 100-case dataset. These forms of evidence answer different questions and are kept separate in the records.

The current backend also has intentional differences from these notebooks, including provisional warnings, the graph review pause and one-batch final approval. See the [backend README](../backend/README.md) for those contracts. Reallocation and its optional review/approval flow remain pending.
