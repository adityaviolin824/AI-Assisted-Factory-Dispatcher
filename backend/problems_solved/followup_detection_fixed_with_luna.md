# Follow-up detection fixed with GPT-5.6 Luna in the recorded demo

Recorded: 15 October 2026. Original diagnosis and model experiments: 14 October 2026.

**Status: fixed for the recorded intake examples; downstream linking remains incomplete.** The results below are historical observations, not a claim that all future follow-ups will be classified correctly.

## What the problem was

One conversation was being broken into several separate tasks. The intake model failed to recognise corrections, answers and additional requirements as follow-ups. One message containing the only deadline was discarded as non-task text.

This prevented the linking stage from doing its job: code sends only items labelled `follow_up` to linking. A `request` immediately becomes a separate task, and a non-task message creates no item to link.

## The exact conversation

From [dispatch_requests_chat_demo.txt](../data/dispatch_requests_chat_demo.txt):

> R02 [11:02] Adi: So I thought we need to dispatch the sweaterco order really quick.
>
> R03 [11:03] Adi: I think it is order number, oh sorry I mean we need to dispatch the Harbor Knit Hoodie. Which order number is that?
>
> R04 [11:04] Zhang: I think its order number 52.
>
> R05 [11:05] Zhang: Yes it is 52. And the deadline for that is 30th October.
>
> R07 [11:05] Adi: For that we should focus a bit more on quality. It is pretty expensive.

R01 is a greeting; R06 is "Oh ok cool." Those two messages are non-task text. The development key expects R02 to start one task, followed by corrections or additions from R03, R04, R05 and R07.

The conversation suggests order 52, but the application still requires confirmation of a full order reference such as `ORD-052`. Recognising a follow-up does not authorise guessing that identity.

## What happened before the fix

Saved run: 2026-10-14_11-16-34, with intake on `gpt-4.1-mini`.

| Message | Expected label | Recorded label |
|---|---|---|
| R03: correction and order question | follow_up | request |
| R04: proposed order number | follow_up | request |
| R05: confirmation and deadline | follow_up | non-task |
| R07: quality preference | follow_up | request |

The result was four separate tasks, no linking calls, and no ready task. The deadline in R05 never entered a task. The quality preference was separated from the request it was intended to modify.

Only three of the seven message labels matched the development key: the original request and the two non-task messages.

## Established root cause

The saved intake responses contained the incorrect labels, and the application followed those labels as designed. This was not a modularization regression. The original request was already visible when R03 and R04 were classified, so lack of access to that request did not explain those mistakes.

The smaller model's interpretation under the existing prompt was the failing component. The experiments did not isolate the internal reason for each model decision or establish a universal model limitation.

## SOLUTION TO THIS PROBLEM

Use `gpt-5.6-luna` with reasoning effort `high` for intake, retaining the current intake prompt and batch sizes: three target messages with two earlier context messages.

The client supports the selected reasoning effort and omits temperature for this reasoning-model configuration. These settings are included in the recorded request and response-cache identity. No application rule was relaxed to force a link.

In the comparison run, only intake's model configuration changed; linking and verification stayed on `gpt-4.1-mini`. This made it possible to identify the improvement at intake rather than attributing the result to a rewritten link prompt.

## Verification and observed result

Saved run: 2026-10-14_13-10-07.

| Measure | Before: mini intake | After: Luna intake, high |
|---|---|---|
| Correct labels across the seven messages | 3/7 | 7/7 |
| Four expected follow-ups recognised | 0/4 | 4/4 |
| R05's deadline evidence | Discarded as non-task | Retained and attached |
| Link calls | 0 | 4 |
| Tasks | Four separate fragments | One task at version 4, plus the unresolved R07 follow-up |

R03, R04 and R05 attached to `T:L0002:J1`. R07 reached linking but was refused there and remained in review. The single task was held, so verification did not run. The fix restored detection and preservation of the follow-ups; it did not complete the dispatch journey.

The original 30-request file provided a separate check. With the current prompt, intake labelling improved from 29/30 to 30/30 in Test 2. The previously dropped information question, "Which workshop did we use for the Harbor Knits batch last October?", was retained. That file contains no follow-ups, so this result does not measure linking accuracy.

## Alternatives tested and remaining limits

- Two rewritten intake prompts also achieved 7/7 on the demo with Luna. Neither demonstrated an advantage over the current prompt. Prompt 1 introduced a wrong attachment on the separate 30-request file, so it was not adopted.
- Switching linking to Luna at `medium` still refused the demo's R07 quality instruction. Raising linking to `high` also refused R03 and was reverted. Increasing reasoning effort did not solve the downstream issue.
- The bare order number `52` and unsupported ordinal date form `30th October` remain separate hurdles. The demo did not reach verification, so it did not demonstrate that these were resolved.
- These are small development examples with limited fresh repetition. Cached replays reproduce saved answers; they do not establish model consistency on new samples or unseen conversations.

## Supporting records

- Original diagnosis and the controlled intake comparison, section 13.
- [Prompt and model testing results: Tests 1, 2 and 3](../docs/evaluation/PROMPT_TESTING_RESULTS.md).
- [Request and follow-up routing](../order_processing_into_tasks/create_and_link_tasks.py).
- [Current unresolved hold and linking problem](held_tasks_and_unresolved_followups.md).
