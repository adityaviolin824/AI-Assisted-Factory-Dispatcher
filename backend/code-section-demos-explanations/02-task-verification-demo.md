# 02. Task verification: consolidating the current request

Prepared: 13 October 2026.

Checked against the current Python modules: 19 October 2026. This version includes the current date rules, written-quantity check and provisional-warning behaviour.

The main code is [verify_tasks.py](../order_processing_into_tasks/verify_tasks.py). Its key steps are `verification_payload`, `finish_verification_batch`, `finish_verification` and `resolve_scheduling`.

This walkthrough follows [01. Task linking demo](01-task-linking-demo.md). Here, consolidation means working out the current requirements from the messages already connected to one task. AI interprets those requirements, and code checks its answer against the evidence and known factory records.

The messages, proposed answers and saved records below are illustrative. They are not results from a notebook or model run. The readable records explain the relevant information rather than reproducing the complete response or saved-file format.

**Verification turns the linked messages into one checked, current request.**

Linking answered: **"Which messages belong together?"**

Verification answers: **"What is this person asking for now, and do we have enough reliable information to process it?"**

AI interprets the messages. Code checks that interpretation against the saved evidence and known factory records.

This walkthrough continues Elena's example from the linking demo.

## 1. What verification starts with

Elena's task is now at **version 7**. Its seven messages are:

| Message | Original instruction |
|---|---|
| `L0001` | Please allocate ORD-092 by November 20, 2026, at the lowest cost. |
| `L0002` | For the allocation I just sent, avoid BudgetWorks. |
| `L0004` | For my ORD-092 request, use November 22, 2026, instead of November 20, 2026. |
| `L0005` | For that same ORD-092 allocation, choose the fastest delivery instead of the cheapest option. |
| `L0006` | Update to my ORD-092 request: BudgetWorks is allowed again. |
| `L0007` | Confirming that same allocation: earliest delivery is my main priority. |
| `L0008` | Final deadline for my ORD-092 request: November 21, 2026, replacing November 22, 2026. |

The table shortens the saved lines by leaving out their times and sender names. Verification receives the full saved quotations.

At this point, linking has connected the messages. **It has not yet established the final deadline, preference or workshop restrictions.**

Verification normally starts after all messages have been read and linked. That allows it to consider the corrections together.

## 2. Code gives each quotation an evidence ID

Before asking AI to interpret the task, code labels its quotations.

For this task, the evidence IDs look like:

| Evidence ID | Source message | What it contains |
|---|---|---|
| `T:L0001:J1:E1` | `L0001` | Original request, November 20 deadline, lowest cost |
| `T:L0001:J1:E2` | `L0002` | Avoid BudgetWorks |
| `T:L0001:J1:E3` | `L0004` | Change deadline to November 22 |
| `T:L0001:J1:E4` | `L0005` | Change preference to fastest delivery |
| `T:L0001:J1:E5` | `L0006` | Allow BudgetWorks again |
| `T:L0001:J1:E6` | `L0007` | Confirm earliest delivery |
| `T:L0001:J1:E7` | `L0008` | Final deadline: November 21 |

These are called **E1 through E7** below to keep the explanation readable.

These IDs let AI say:

> "The deadline comes from E7."

Code can then retrieve the exact original quotation behind E7. AI does not need to retype it, and code can reject an evidence ID that does not belong to this task.

**The evidence ID identifies a quotation. It does not mean the quotation is the current instruction.** Deciding that still requires interpretation.

## 3. Code adds the known factory facts

Code reads the order IDs appearing in the task's evidence and looks them up in the order data.

For Elena's task, that means looking up `ORD-092`.

If it exists, code supplies its actual order record to AI. If it does not exist, that absence is recorded.

Code also identifies recognised workshop names or IDs in the evidence. Here, BudgetWorks appears in two different instructions.

So AI receives:

- The task ID and current version.
- All seven original evidence entries.
- The evidence IDs.
- The order lookup result.
- The order IDs in the task's first item, so a task that still combines multiple orders can be identified.
- The recognised workshop mentions.

**AI does not invent the order's quantity, category or other recorded facts. Code supplies those facts.**

For the rest of this example, assume `ORD-092` exists in the order data and BudgetWorks is a recognised workshop.

## 4. AI works out the current request

AI now needs to read the messages together.

For the deadline, it should understand:

```text
E1: November 20
E3: November 22 replaces November 20
E7: November 21 replaces November 22

Current deadline: November 21, 2026
```

For the preference:

```text
E1: Lowest cost
E4: Fastest delivery replaces cheapest
E6: Earliest delivery is confirmed

Current preference: Fastest delivery
```

For BudgetWorks:

```text
E2: Avoid BudgetWorks
E5: BudgetWorks is allowed again

Current restriction: BudgetWorks is no longer excluded
```

Allowing BudgetWorks again does **not** mean Elena specifically requested that workshop. It means the earlier exclusion has been withdrawn. Workshop selection still comes later.

AI also identifies the kind of task:

```text
This is an allocation request.
It is not an information question.
```

And it checks whether the messages leave anything unresolved: an unclear deadline, unclear order, unsupported condition, or a question that needs answering.

## 5. What AI should propose

In readable form, the proposed interpretation would be:

| Field | Proposed result | Supporting evidence |
|---|---|---|
| Task | `T:L0001:J1` | Task supplied by code |
| Task version | 7 | Version supplied by code |
| Intent | Allocation | E1 |
| Order | `ORD-092` | E1 and later explicit references |
| Current deadline | November 21, 2026 | E7 |
| Current preference | Fastest delivery | E4 and E6 |
| Requested workshop | None | No current instruction requires a particular workshop |
| Current workshop exclusions | None | E5 withdraws the earlier BudgetWorks exclusion |
| Missing details or clarification questions | None, under our example assumptions | All evidence considered |

This table explains the intended answer; it is not an exact copy of the model's response format.

**AI must also account for the old instructions.** It cannot simply ignore BudgetWorks because the final exclusions are empty. Its interpretation must explain that the earlier exclusion was replaced by later evidence.

## 6. Code checks the proposed interpretation

The AI answer is a proposal. Code checks it before accepting it.

| Check | What it prevents |
|---|---|
| The task ID and version match the requested task | Applying an answer to the wrong task or an older version |
| The selected evidence IDs belong to this task | Using another task's messages or invented evidence |
| The order ID is written in the task's evidence | Inventing an order ID |
| The order lookup establishes whether that order exists | Treating an unknown order as a known factory order |
| The first item identifies one allocation job, rather than several unresolved orders | Treating a combined source as one clearly identified batch |
| The proposed deadline agrees with a date in the selected evidence, including its year | Returning a date unsupported by the cited text |
| A recognised written piece count agrees with the identified order's CSV quantity | Silently allocating the CSV quantity when the chat asks for a different amount |
| Recognised workshop mentions have an explanation | Dropping an exclusion or destination instruction |
| An instruction marked as replaced has later supporting evidence | Discarding an earlier requirement without support |
| Preferences and constraints have supporting evidence | Adding requirements that nobody asked for |
| Missing details and unresolved questions are accounted for | Marking an incomplete request as ready |

For example, if AI returns:

```text
Deadline: November 21, 2027
Evidence: E7
```

Code can reject that: E7 says **2026**.

But there is an important limit. If AI chooses November 22 even though Elena said it was being replaced, checking that the date appears in the text does not, by itself, prove that AI understood the sentence.

**Code checks specific consistency rules. AI still has to understand the meaning correctly.**

**Dates are calculated by Python.** AI identifies the current deadline evidence and copies its date words. Python reads an explicit date, or resolves supported relative delivery words from `message_date` in `config.toml`. With the current message date of **1 April 2026**:

| Source wording | Current handling |
|---|---|
| "Deliver tomorrow" | The supported relative deadline resolves to 2 April 2026 |
| "By the end of next week" | Resolves to Friday, 10 April 2026 |
| "By the end of this month" | Resolves to 30 April 2026 |
| "Next Friday" | Asks for an explicit calendar date; this wording is not in the supported list |
| "Send out today", with no delivery instruction | Dispatch timing alone does not set a delivery deadline; the CSV due date can apply |
| AI selects no deadline, but the evidence says "Deliver tomorrow" | Python adds a blocker asking which written date is the current deadline |

The supported week convention ends on Friday. Week expressions ask for clarification when the message date is a weekend. A copied explicit date such as "due Apr 13" is accepted when its one readable date agrees with the selected evidence. These are the project's date conventions, not a factory working-day calendar.

**Written quantities also have a Python check.** Suppose the chat says "ORD-105, 1300 vests" but `orders.csv` records 200 pieces. `stated_piece_counts` finds the written count, and `finish_verification` adds:

```text
The chat states 1300 pieces for ORD-105, but orders.csv records 200; confirm the quantity.
```

The task is not ready, even if AI overlooked the mismatch. Code never changes the CSV quantity to 1300. This check covers recognised number-and-product wording such as "1,250 cardigan pieces" or "400 pcs"; it does not prove that every possible quantity phrase, customer or product description was understood correctly. If no quantity is written, code uses the identified order's recorded quantity rather than estimating one.

Verification is batched, currently up to three tasks within the payload limit. Code first checks that the answers identify every requested task and version exactly once. If they cannot be matched, the whole requested batch goes to review. Once matched, each assessment is checked on a copy of its task: one failed interpretation does not prevent the other valid assessments from being accepted. A task too large to verify alone goes to review with its evidence intact.

## 7. What gets saved after acceptance

The original evidence stays saved. The checked interpretation is stored separately on the task.

Conceptually, the saved task now contains:

```text
Task ID: T:L0001:J1
Current task version: 7
Verified version: 7

Saved original evidence:
    All seven connected messages

Checked current request:
    Allocation for ORD-092
    Deadline: November 21, 2026
    Preference: fastest delivery
    No requested workshop
    BudgetWorks exclusion withdrawn

Missing details or questions:
    None under the example assumptions
```

The distinction matters:

- **Evidence** preserves what was said, including old instructions.
- **Current request fields** describe what later processing should act on.
- **Verified version** records which version of the task was checked.

Later allocation should use the checked current deadline. It should not scan the historical text and accidentally reuse November 20.

The updated task is saved in the run's processing state. The model request and answer are also recorded for inspection.

## 8. Acceptance and readiness are different

A verification answer can be accepted while the request still needs clarification.

For example:

| Situation | Verification outcome |
|---|---|
| Known order, clear deadline, supported requirements, no unresolved questions | Ready for allocation checks |
| Clearly written order ID, but that order does not exist in the data | Accepted interpretation with a clarification blocker |
| Chat contains a deadline, but its current date is not identified or cannot be read | Accepted interpretation with a missing-detail blocker |
| Request includes a condition the current system cannot handle | Recorded condition; readiness is blocked |
| A recognised written quantity differs from the CSV | Accepted interpretation with a quantity-confirmation blocker |
| AI cites invented evidence or produces an inconsistent interpretation | Interpretation review |
| The task is an information question | Recorded as a question; it does not enter allocation |

If the chat has no deadline override and there are no remaining blockers, later allocation can use the due date recorded for the order. **A deadline missing from the chat alone does not automatically block the task.** If a date was written in the chat but left unresolved, the system asks which date applies instead of silently falling back to the order's date.

If a follow-up could not be linked and might change this task, the task is **still verified** from its established evidence. `possibly_affected_tasks` identifies the possible impact. Allocation then records a warning in `plan["review_warnings"]` and marks the task's summary row provisional. It does not invent a link or automatically hold an otherwise ready task. A provisional recommendation still reserves tentative queue time; the unresolved follow-up itself reserves nothing.

This warning does not remove a task's own blockers. A task missing essential facts still needs clarification, and an interpretation that fails a consistency check still goes to processing review.

A clear request can also be ready for allocation checks even when its deadline is already past. The allocator applies the separate `deadline_passed` gate for deadlines on or before the dispatch date. Readiness is about a usable interpretation; it is not a promise that delivery is feasible.

## 9. What verification does not decide

Verification does not calculate which workshop can finish on time, compare costs, rank workshops, or reserve queue time.

Those are later allocation responsibilities.

For Elena, verification establishes:

> "This is a sufficiently clear request to allocate ORD-092 by November 21, prioritising fastest delivery."

Allocation must still establish whether an allowed workshop can actually fulfil it.

**Ready for allocation checks does not mean a workshop has been selected or the order has been assigned.**
