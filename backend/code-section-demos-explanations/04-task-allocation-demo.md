# 04. Task allocation: choosing a workshop and updating the preview queue

Automatic-allocation reference calculation recorded 19 October 2026. Section 9 describes notebook 06's historical per-row approval queues; the current application places manual destinations first and uses one batch approval.

This walkthrough explains automatic selection and temporary queues. Follow [02. Task verification demo](02-task-verification-demo.md) and [03. Processing files explanation](03-order-processing-files-explanation.md) first.

Verification answers: **"What is the current request, and is it clear enough to process?"**

Allocation answers: **"Which allowed workshop can fulfil that request, given its capacity and existing workload?"**

AI interprets the request during processing. Python checks eligibility, calculates delivery and cost, ranks workshops and builds the allocation preview. Allocation itself makes no model call.

## 1. Start with a verified request

For this example, the request is:

```text
Please allocate ORD-045 by April 9, 2026. Choose the fastest eligible workshop.
```

The relevant part of its verified record is:

```json
{
  "order_id": "ORD-045",
  "due_date": "2026-04-09",
  "preference": "fastest",
  "requested_workshop": null,
  "excluded_workshops": [],
  "information_sufficient": true
}
```

This is a shortened teaching record, not the complete task schema or a newly generated model answer. Assume no split, unsupported condition or unclear workshop reference.

The order CSV supplies the factory facts:

| Fact | Value |
|---|---|
| Order | ORD-045 |
| Product | Vest |
| Category | TOPS |
| Quantity | 150 pieces |
| Experiment dispatch date | 1 April 2026 |
| Delivery deadline | 9 April 2026 |
| Time available | 8 calendar days |

The quantity comes from the CSV. A conflicting written quantity must be clarified during verification; automatic processing does not replace the CSV quantity. The dispatcher can explicitly correct batch quantity during review. The deadline is the checked chat deadline when present, otherwise the order's CSV due date.

The calculations below treat this as the first planned task, using the original workshop queues. Earlier recommendations can change later tasks' estimates.

## 2. Route the task before comparing workshops

[route_verified_tasks.py](../task_routing/route_verified_tasks.py) decides what kind of work this is.

| Situation | Route |
|---|---|
| Allocation request with sufficient information | Allocation |
| Missing facts or an unresolved question | Needs clarification |
| Information question with no missing facts or open questions | Reference: recorded, not answered here |
| A ready allocation request shares an order with another verified allocation request | Duplicate-order review |

The duplicate check also counts allocation requests that are not ready. One ready task cannot silently allocate the order while another allocation request for the same order remains unclear.

Ready allocation tasks are planned earliest deadline first. Equal deadlines keep their existing order. This is a sequential, greedy plan: each recommendation changes the queue seen by later tasks. It is not a search for the best possible arrangement of every order together.

## 3. Apply hard rules first

[workshop_rules_and_estimates.py](../task_allocation_to_workshops/workshop_rules_and_estimates.py) checks whether each workshop is allowed to take the batch.

It checks request exclusions, ACTIVE status, product-category compatibility, maximum batch size and any requested destination. A destination requested in chat does not override these limits. A workshop explicitly chosen during dispatcher review is a separate authoritative human action whose overrides are recorded.

For this 150-piece TOPS batch:

| Workshop | Hard-rule result |
|---|---|
| W1 QuickStitch | Allowed |
| W2 SteadyHands | Allowed |
| W3 BudgetWorks | Allowed |
| W4 Little Loom | Rejected: makes ACCESSORIES, not TOPS |
| W5 GiantWeave | Allowed |
| W6 Nimble Needle | Allowed |
| W7 OldMill | Rejected: SUSPENDED |
| W8 FreshStart | Allowed: 150 pieces is within its 300-piece batch cap |

Passing these rules means the workshop may take the batch. It does not yet mean it can deliver on time.

## 4. Calculate delivery for every allowed workshop

The current estimate is:

```text
Production days = pieces / daily capacity
Expected rework days = production days × defect rate × 0.5
Delivery days = existing queue + production + expected rework + transport lead time
```

The rework factor is an assumption in the current estimator. Expected rework is an average allowance, not a guarantee of the actual delay.

For W6 Nimble Needle:

```text
Existing queue       = 1 day
Production           = 150 / 130 = 1.153846 days
Expected rework      = 1.153846 × 0.05 × 0.5 = 0.028846 days
Transport lead time  = 1 day

Estimated delivery   = 1 + 1.153846 + 0.028846 + 1
                     = 3.182692 days after dispatch
```

The same calculation for every allowed workshop gives:

| Workshop | Delivery days, rounded | Batch cost, CSV units | Defect rate | Within 8 days? |
|---|---:|---:|---:|---|
| W1 QuickStitch | 5.530 | 225 | 12% | Yes |
| W2 SteadyHands | 5.396 | 195 | 3% | Yes |
| W3 BudgetWorks | 8.682 | 120 | 9% | No |
| W5 GiantWeave | 7.386 | 165 | 6% | Yes |
| W6 Nimble Needle | 3.183 | 180 | 5% | Yes |
| W8 FreshStart | 3.530 | 150 | 4% | Yes |

Code compares the unrounded estimates with the available calendar days. Rounding is for display. The current experiment does not add a working-day or holiday calendar.

W3 passes the factory rules but misses the deadline, so the normal allocation policy removes it before ranking.

## 5. Rank the on-time choices using the preference

[rank_workshops.py](../task_allocation_to_workshops/rank_workshops.py) contains the ranking rules. With no experiment-wide objective override:

| Request preference | Comparison order | Winner here |
|---|---|---|
| Fastest, or no preference | Lateness, then delivery days, then cost | W6 |
| Cheapest | Cost, then delivery days, then defect rate | W8 |
| Quality | Defect rate, then delivery days, then cost | W2 |

Every ranked workshop is already on time, so its lateness is zero. The default ranking therefore picks the shortest delivery, then uses cost to break a tie.

For the example's fastest preference, W6 wins with delivery in about 3.18 of the 8 available days and a batch cost of 180.

W3 cannot win the cheapest on-time comparison despite costing 120, because it is late. W8 is the cheapest remaining choice at 150.

Other experimental objectives and a hybrid exist in the code. They are separate policy comparisons; this example uses the normal request preferences.

## 6. Reserve production time for the next task

[allocation_plan.py](../task_allocation_to_workshops/allocation_plan.py) adds the chosen batch's production and expected rework to the workshop's temporary queue:

```text
W6 queue before this order = 1 day
New work                  = 1.153846 + 0.028846 = 1.182692 days
W6 queue after this order = 2.182692 days
```

The next task considered for W6 sees approximately 2.18 days already occupied.

**The queue becomes 2.18 days; the order's delivery estimate is 3.18 days.** The extra day is transport. Transport affects delivery but does not occupy the workshop's production capacity, so it is not added to the production queue.

These are planning copies. The calculation does not change the workshop CSV or commit an assignment. Recalculating starts from the original queues and rebuilds reservations, so displaying the plan twice does not add the work twice.

## 7. When allocation returns no recommendation

[recommend_one_task.py](../task_allocation_to_workshops/recommend_one_task.py) records a reason rather than inventing a workable assignment.

| Situation | Result | Adds queue time? |
|---|---|---|
| Facts are missing or verification failed | Clarification or processing review | No |
| Deadline is on or before dispatch | `deadline_passed`; no estimates or least-late option | No |
| No workshop passes the hard rules | Review with rejection reasons | No |
| Deadline is in the future, but every allowed workshop is late | Review, with the closest late option as information | No |
| Requested workshop cannot fulfil the request, but another can | Review may show an alternative that needs dispatcher approval | No |
| Split or another unsupported condition | Review | No |
| Winning workshop was mentioned only as an unclear reference | Review to confirm the instruction | No |
| A ready, feasible task may be affected by a separately unresolved input | Provisional recommendation, with a warning | Yes |

A provisional recommendation is still a preview reservation. The unresolved input remains visible for checking. Raw decision status stays `recommendation`; the summary shows `provisional_recommendation` and the plan records `review_warnings`.

Historical completed orders remain allowed with a warning in this experiment. That is not a live-order status policy.

## 8. What the saved plan contains

The normal allocation runner writes `plan.json` and a timestamped copy in `plan-history/`. It records the planning order, selected workshop, candidate estimates, ranking, hard-rule rejections, reasons, source-message links and queues before and after planning. It also accounts for clarification, review, reference and non-task inputs.

A review row can show an informational workshop option without selecting it or reserving time. Read the outcome and selected fields, not just whether a workshop name appears in the table.

Notebook 06 builds the dispatcher preview from those source records and the dispatcher's current decisions. Its screen recalculates without a model call. Displaying that screen does not save decisions; the notebook's explicit save steps do that.

## 9. Reading notebook 06's Queues table

Each row is a **workshop**, not an order. Each number is that workshop's modeled production backlog in days.

| Column | Meaning |
|---|---|
| Queue days at start | Existing queue loaded from the workshop data |
| After approved work | Starting queue plus valid approved allocations, placed first in approval order |
| After the plan | That queue plus the remaining recommendations, eligible dispatcher choices and explicitly accepted late allocations |

The last column already includes approved work. Do not add the three columns together.

These are three calculation snapshots, not three dates. Time does not pass between them, so existing queues do not drain. The screen rounds values to two decimal places.

The historical notebook queue table is reproduced by saved run `2026-10-14_14-40-08` with no dispatcher decisions:

| Workshop | At start | After approved work | After the plan | Added work in this preview |
|---|---:|---:|---:|---|
| W1 QuickStitch | 4 | 4 | 5.77 | ORD-109: 500 pieces, about 1.77 production/rework days |
| W2 SteadyHands | 2.5 | 2.5 | 2.5 | None |
| W3 BudgetWorks | 5 | 5 | 5 | None |
| W4 Little Loom | 0.5 | 0.5 | 0.5 | None |
| W5 GiantWeave | 3 | 3 | 6.86 | ORD-081: 1,500 pieces, about 3.86 production/rework days |
| W6 Nimble Needle | 1 | 1 | 2.18 | ORD-045: 150 pieces, about 1.18 production/rework days |
| W7 OldMill | 0 | 0 | 0 | None; suspended |
| W8 FreshStart | 0 | 0 | 0 | None |

There are no valid approved reservations in this reproduced calculation, so the middle column equals the starting column. Three recommendations add work in the last column. The remaining workshops receive no new reservation in this preview, so their queues stay unchanged. An unchanged queue does not by itself mean a workshop is ineligible for every order.

For example, W8 can take ORD-045 on time, but W6 wins that request's fastest preference. W8 therefore gains no queue time from that order.

Approval is not another copy of the batch. An approved task is placed in the approved group and excluded from the remaining-task group, so it reserves once. Approval can change planning order and therefore affect other estimates; it does not necessarily increase the final total queue.

## 10. Recorded verification and ranking consequence

The example metrics and all eight screenshot queue rows were recalculated from the actual Python functions and notebook 06's Part 8 calculation, with network connections refused and a blank API key. No model call or Gradio server was started. The notebook, source run, configuration, original CSVs and supplied simulator were unchanged by hash.

For a cheapest preference, W8 wins because W3 misses the deadline and is removed before cost ranking.

Continue with [05. LangGraph implementation](05-langgraph-implementation-demo.md), which explains the current processing, allocation and dispatcher review graph. The current application implements dispatch-table reallocation through Approve all and Review again. Operational assignments and transfers of real production remain future work.
