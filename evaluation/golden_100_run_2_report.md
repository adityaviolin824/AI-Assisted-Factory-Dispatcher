# Run report: dispatch_requests_extended_conversation_and_edge_cases_100.txt

- Run folder: `output/extended_dispatch_100_repeat/runs/2026-10-21_23-43-53`
- Plan made 2026-10-21T23:53:51; dispatch date 2026-04-01; objective: each request's own preference.
- Message date: 2026-04-01. Processing complete: yes.
- Written by `make_run_report.py` from the saved run files, with no model call.

## Settings

| Stage | Model | Reasoning effort |
|---|---|---|
| intake | gpt-5.6-luna | high |
| link | gpt-5.6-luna | medium |
| verify | gpt-5.6-luna | medium |

Batches: 3 target and 2 context messages per extraction call; up to 3 tasks per verification call; payload limit 24,000 characters.

## Processing

- Chat messages: 149. No request found: 5; intake review: 0.
- Items extracted: 146. Tasks: 103, of which 102 verified at their current version and 1 in processing review.
- Follow-ups in link review: 8. Inputs without an outcome: 0.
- Tasks marked provisional by review warnings: 15.

## Score against the key

- Key: `docs/evaluation/extended_dispatch_100_human_team_golden.json`, version 2, SHA-256 `e8d861875b08cd9a...`; 100 cases in 149 messages.
- Key's own description: Human team golden set: extended dispatch conversation and edge cases, 100 tasks. Human-reviewed expected interpretations and offline allocation feasibility; no model-accuracy measurement or paid processing result on this set.
- Review recorded with the key: Comprehensive manual, line-by-line review by human team members, not AI. Reviewers: 3 human team members. Draft author: Codex (AI assistant). Confirmation source: Project owner confirmation in chat.
- The key's own plan is calculated by the app's routing and allocation rules from `data/extended_dispatch_100`.
- A case is matched to the app task created from its first message; with two jobs in that message, to the task whose excerpts name its order. Not allocating an exception is correct, whatever the route.

### Decisions

| Decision | Cases |
|---|---|
| Should allocate (key: recommendation) | 85 |
| - allocated, obeying the key's requested and excluded workshops | 80 |
| - not allocated (missed) | 5 |
| - allocated against the key's workshop rules (unsafe) | 0 |
| Should not allocate (key: exception) | 15 |
| - not allocated (correct) | 14 |
| - allocated anyway (unsafe) | 1 |

Provisional recommendations, counted as allocations above: 15 (CASE-016, CASE-017, CASE-018, CASE-019, CASE-021, CASE-022, CASE-023, CASE-024, CASE-025, CASE-026, CASE-027, CASE-028, CASE-029, CASE-059, CASE-060).

**Unsafe allocations**

| Case | Order | Key outcome | App workshop | Scenario |
|---|---|---|---|---|
| CASE-097 | ORD-297 | needs_clarification | W1 | Confirmed cancellation must not become an allocation |

### Missed allocations and other workshops, by cause

| Cause | Missed | Other workshop than the key's plan | Meaning |
|---|---|---|---|
| intake | 3 | 0 | intake made a follow-up its own task, read a case message as no task or could not read it |
| link | 0 | 5 | a follow-up stayed in link review or joined another task |
| verification | 2 | 0 | verification blocked the task or read a field differently from the key |
| allocation | 0 | 14 | every field matches the key, but the plan differs: earlier tasks took the queue time, or another task names the same order |

| Case | Order | Scenario | App task | App outcome | App workshop (key plan) | Cause | App reason |
|---|---|---|---|---|---|---|---|
| CASE-014 | ORD-214 | Complete request with varied wording | T:L0015:J1 | recommendation | W1 (W5) | allocation | W1 (QuickStitch) ranks first under minimize_tardiness (order: W1, W6, W2, W5, W8, W3): delivery in 8.39 of 16 available days, cost 450.0. |
| CASE-019 | ORD-219 | Request completed by a clear follow-up | T:L0023:J1 | provisional_recommendation | W5 (W3) | link | W5 (GiantWeave) ranks first under minimize_tardiness (order: W5, W1, W6, W2, W8, W3): delivery in 8.39 of 15 available days, cost 330.0. Provisional: L0024:J1 may modify this request. Please confirm whether it applies; the result may need recalculation. |
| CASE-021 | ORD-221 | Request completed by a clear follow-up | T:L0028:J1 | provisional_recommendation | W2 (W1) | link | W2 (SteadyHands) ranks first under minimize_tardiness (order: W2, W6, W5, W8, W1, W3): delivery in 8.08 of 16 available days, cost 156.0. Provisional: L0029:J1 may modify this request. Please confirm whether it applies; the result may need recalculation. |
| CASE-022 | ORD-222 | Request completed by a clear follow-up | T:L0030:J1 | provisional_recommendation | W6 (W2) | allocation | W6 (Nimble Needle) ranks first under minimize_tardiness (order: W6, W2, W5, W8, W1, W3): delivery in 9.10 of 17 available days, cost 216.0. Provisional: L0033:J1 may modify this request. Please confirm whether it applies; the result may need recalculation. |
| CASE-023 | ORD-223 | Request completed by a clear follow-up | T:L0032:J1 | provisional_recommendation | W2 (W3) | link | W2 (SteadyHands) ranks first under minimize_tardiness (order: W2, W8, W5, W1, W6, W3): delivery in 9.52 of 18 available days, cost 312.0. Provisional: L0033:J1 may modify this request. Please confirm whether it applies; the result may need recalculation. |
| CASE-026 | ORD-226 | Request completed by a clear follow-up | T:L0039:J1 | provisional_recommendation | W8 (W6) | allocation | W8 (FreshStart) ranks first under minimize_tardiness (order: W8, W6, W1, W5, W2, W3): delivery in 8.73 of 18 available days, cost 120.0. Provisional: L0042:J1 may modify this request. Please confirm whether it applies; the result may need recalculation. |
| CASE-027 | ORD-227 | Request completed by a clear follow-up | T:L0041:J1 | provisional_recommendation | W5 (W3) | link | W5 (GiantWeave) ranks first under minimize_tardiness (order: W5, W1, W6, W2, W8, W3): delivery in 8.85 of 16 available days, cost 198.0. Provisional: L0042:J1 may modify this request. Please confirm whether it applies; the result may need recalculation. |
| CASE-029 | ORD-229 | Request completed by a clear follow-up | T:L0045:J1 | provisional_recommendation | W5 (W1) | link | W5 (GiantWeave) ranks first under minimize_tardiness (order: W5, W1, W2, W6, W8, W3): delivery in 10.55 of 18 available days, cost 330.0. Provisional: L0046:J1 may modify this request. Please confirm whether it applies; the result may need recalculation. |
| CASE-033 | ORD-233 | Confirmed preference, exclusion or delivery-date correction | T:L0054:J1 | recommendation | W1 (W2) | allocation | W1 (QuickStitch) ranks first under minimize_tardiness (order: W1, W2, W6, W5, W8): delivery in 10.51 of 18 available days, cost 360.0. |
| CASE-038 | ORD-238 | Confirmed preference, exclusion or delivery-date correction | T:L0064:J1 | recommendation | W6 (W5) | allocation | W6 (Nimble Needle) ranks first under minimize_tardiness (order: W6, W5, W1, W8, W3, W2): delivery in 10.99 of 20 available days, cost 288.0. |
| CASE-041 | ORD-241 | Confirmed preference, exclusion or delivery-date correction | T:L0070:J1 | recommendation | W5 (W6) | allocation | W5 (GiantWeave) ranks first under minimize_tardiness (order: W5, W6, W1, W8, W3, W2): delivery in 11.33 of 22 available days, cost 132.0. |
| CASE-042 | ORD-242 | Confirmed preference, exclusion or delivery-date correction | T:L0072:J1 | recommendation | W5 (W6) | allocation | W5 (GiantWeave) ranks first under minimize_tardiness (order: W5, W1, W6, W8, W2): delivery in 11.02 of 20 available days, cost 198.0. |
| CASE-045 | ORD-245 | Confirmed preference, exclusion or delivery-date correction | T:L0078:J1 | recommendation | W1 (W5) | allocation | W1 (QuickStitch) ranks first under minimize_tardiness (order: W1, W5, W6, W2): delivery in 11.78 of 20 available days, cost 540.0. |
| CASE-046 | ORD-246 | Interleaved requests with separate follow-ups | T:L0080:J1 | review_required | - | intake | Allocation requests T:L0080:J1, T:L0082:J1 all name ORD-246; clarify the intended batches. |
| CASE-047 | ORD-247 | Interleaved requests with separate follow-ups | T:L0081:J1 | review_required | - | intake | Allocation requests T:L0081:J1, T:L0083:J1 all name ORD-247; clarify the intended batches. |
| CASE-049 | ORD-249 | Interleaved requests with separate follow-ups | T:L0085:J1 | processing_review | - | verification | Selected evidence must belong to this task's supplied catalog. |
| CASE-051 | ORD-251 | Interleaved requests with separate follow-ups | T:L0089:J1 | review_required | - | intake | Allocation requests T:L0089:J1, T:L0091:J1 all name ORD-251; clarify the intended batches. |
| CASE-053 | ORD-253 | Interleaved requests with separate follow-ups | T:L0093:J1 | recommendation | W5 (W8) | allocation | W5 (GiantWeave) ranks first under minimize_tardiness (order: W5, W1, W8, W6, W3, W2): delivery in 13.49 of 24 available days, cost 264.0. |
| CASE-054 | ORD-254 | Interleaved requests with separate follow-ups | T:L0096:J1 | recommendation | W1 (W5) | allocation | W1 (QuickStitch) ranks first under minimize_tardiness (order: W1, W5, W6, W8, W3, W2): delivery in 12.84 of 22 available days, cost 450.0. |
| CASE-057 | ORD-257 | Interleaved requests with separate follow-ups | T:L0101:J1 | recommendation | W6 (W1) | allocation | W6 (Nimble Needle) ranks first under minimize_tardiness (order: W6, W5, W1, W8, W3, W2): delivery in 12.41 of 22 available days, cost 216.0. |
| CASE-058 | ORD-258 | Interleaved requests with separate follow-ups | T:L0104:J1 | recommendation | W5 (W6) | allocation | W5 (GiantWeave) ranks first under minimize_tardiness (order: W5, W1, W8, W6, W3, W2): delivery in 12.87 of 23 available days, cost 264.0. |
| CASE-066 | ORD-266 | Relative delivery deadline resolved from 1 April 2026 | T:L0115:J1 | recommendation | W1 (W6) | allocation | W1 (QuickStitch) ranks first under minimize_tardiness (order: W1, W5, W6, W3, W2, W8): delivery in 13.69 of 29 available days, cost 180.0. |
| CASE-070 | ORD-270 | Dispatch timing leaves the CSV delivery deadline intact | T:L0119:J1 | needs_clarification | - | verification | Confirm which written date is the current deadline. |
| CASE-073 | ORD-273 | Explicit eligible destination or exclusion | T:L0122:J1 | recommendation | W6 (W5) | allocation | W6 (Nimble Needle) ranks first under minimize_tardiness (order: W6, W5, W8, W2): delivery in 14.30 of 27 available days, cost 288.0. |

Workshop choice: 61 of 80 correct allocations chose the workshop of the key's own plan.

### Fields of verified matched tasks

| Field | Matches key | Tasks compared |
|---|---|---|
| order_id | 99 | 99 |
| due_date | 99 | 99 |
| preference | 93 | 99 |
| requested_workshop | 99 | 99 |
| excluded_workshops | 99 | 99 |
| wants_split | 99 | 99 |

| Case | Field | App | Key |
|---|---|---|---|
| CASE-019 | preference | none | cheapest |
| CASE-023 | preference | none | cheapest |
| CASE-027 | preference | none | cheapest |
| CASE-046 | preference | none | fastest |
| CASE-047 | preference | none | cheapest |
| CASE-051 | preference | none | cheapest |

### Message labels

145 of 149 messages have the key's label.

| Key label | App label | Messages |
|---|---|---|
| follow_up | follow_up | 42 |
| follow_up | request | 3 |
| non_task | follow_up | 1 |
| non_task | non_task | 5 |
| request | request | 98 |

Messages with another label: L0082, L0083, L0091, L0109.

### Follow-up links

35 of 45 follow-ups joined their case's task.

| Case | Follow-up | Where it went |
|---|---|---|
| CASE-017 | L0020 | link review |
| CASE-019 | L0024 | link review |
| CASE-021 | L0029 | link review |
| CASE-023 | L0033 | link review |
| CASE-025 | L0037 | link review |
| CASE-027 | L0042 | link review |
| CASE-029 | L0046 | link review |
| CASE-046 | L0082 | task T:L0082:J1 |
| CASE-047 | L0083 | task T:L0083:J1 |
| CASE-051 | L0091 | task T:L0091:J1 |

### Exception cases

| Case | Order | Scenario | Key outcome | App outcome | Decision |
|---|---|---|---|---|---|
| CASE-086 | ORD-286 | Delivery deadline already passed | deadline_passed | deadline_passed | correct non-allocation |
| CASE-087 | ORD-287 | Delivery due on the dispatch date | deadline_passed | deadline_passed | correct non-allocation |
| CASE-088 | ORD-288 | Future deadline cannot be met even before new allocations | review_required | review_required | correct non-allocation |
| CASE-089 | ORD-289 | Requested workshop is suspended | review_required | review_required | correct non-allocation |
| CASE-090 | ORD-290 | Requested workshop cannot make TOPS | review_required | review_required | correct non-allocation |
| CASE-091 | ORD-291 | Requested workshop batch cap exceeded | review_required | review_required | correct non-allocation |
| CASE-092 | ORD-292 | Splitting a full order across workshops is unsupported | review_required | review_required | correct non-allocation |
| CASE-093 | ORD-293 | Numeric budget is not a supported allocation field | needs_clarification | needs_clarification | correct non-allocation |
| CASE-094 | ORD-294 | Explicit piece count contradicts the order CSV | needs_clarification | needs_clarification | correct non-allocation |
| CASE-095 | ORD-295 | Proposed delivery-date change is not confirmed | needs_clarification | needs_clarification | correct non-allocation |
| CASE-096 | ORD-296 | Written order ID does not exist in this fixture | needs_clarification | needs_clarification | correct non-allocation |
| CASE-097 | ORD-297 | Confirmed cancellation must not become an allocation | needs_clarification | recommendation | unsafe allocation |
| CASE-098 | ORD-298 | Production approval is paused | needs_clarification | needs_clarification | correct non-allocation |
| CASE-099 | ORD-299 | Vague request has no order identity | needs_clarification | needs_clarification | correct non-allocation |
| CASE-100 | ORD-300 | Historical workshop assignment is not supplied | reference | needs_clarification | correct non-allocation |

## Plan outcomes

| Outcome | Rows | Meaning |
|---|---|---|
| recommendation | 66 | a workshop is recommended (a preview, not an assignment) |
| provisional_recommendation | 15 | recommended, but an unresolved message may modify the request |
| review_required | 11 | the rules found no acceptable workshop, or another request names the same order |
| deadline_passed | 2 | the deadline is on or before the dispatch date |
| needs_clarification | 8 | a fact is missing or conflicts; the reason is the question to ask |
| processing_review | 1 | the model's check of this task could not be trusted |
| link_review | 8 | a follow-up whose task is uncertain |
| non_task | 5 | no request or question found |
| total | 116 | one row per task, follow-up or message |

### Recommendations

| Row | Order | Outcome | Workshop | Delivery days | Days available | Messages |
|---|---|---|---|---|---|---|
| T:L0002:J1 | ORD-201 | recommendation | W2 | 5.22 | 13 | L0002 |
| T:L0003:J1 | ORD-202 | recommendation | W6 | 6.26 | 14 | L0003 |
| T:L0004:J1 | ORD-203 | recommendation | W3 | 9.09 | 12 | L0004 |
| T:L0005:J1 | ORD-204 | recommendation | W4 | 4.10 | 13 | L0005 |
| T:L0006:J1 | ORD-205 | recommendation | W2 | 7.37 | 14 | L0006 |
| T:L0007:J1 | ORD-206 | recommendation | W8 | 5.06 | 12 | L0007 |
| T:L0008:J1 | ORD-207 | recommendation | W3 | 9.91 | 13 | L0008 |
| T:L0009:J1 | ORD-208 | recommendation | W4 | 5.83 | 14 | L0009 |
| T:L0010:J1 | ORD-209 | recommendation | W1 | 6.06 | 12 | L0010 |
| T:L0011:J1 | ORD-210 | recommendation | W1 | 7.33 | 13 | L0011 |
| T:L0012:J1 | ORD-211 | recommendation | W3 | 12.09 | 16 | L0012 |
| T:L0013:J1 | ORD-212 | recommendation | W4 | 7.99 | 14 | L0013 |
| T:L0014:J1 | ORD-213 | recommendation | W5 | 7.62 | 15 | L0014 |
| T:L0015:J1 | ORD-214 | recommendation | W1 | 8.39 | 16 | L0015 |
| T:L0016:J1 | ORD-215 | recommendation | W3 | 11.54 | 14 | L0016 |
| T:L0017:J1 | ORD-216 | provisional_recommendation | W4 | 8.86 | 15 | L0017, L0018 |
| T:L0019:J1 | ORD-217 | provisional_recommendation | W6 | 7.68 | 16 | L0019 |
| T:L0021:J1 | ORD-218 | provisional_recommendation | W8 | 7.51 | 14 | L0021, L0022 |
| T:L0023:J1 | ORD-219 | provisional_recommendation | W5 | 8.39 | 15 | L0023 |
| T:L0025:J1 | ORD-220 | recommendation | W4 | 10.16 | 16 | L0025, L0026 |
| T:L0028:J1 | ORD-221 | provisional_recommendation | W2 | 8.08 | 16 | L0028 |
| T:L0030:J1 | ORD-222 | provisional_recommendation | W6 | 9.10 | 17 | L0030, L0031 |
| T:L0032:J1 | ORD-223 | provisional_recommendation | W2 | 9.52 | 18 | L0032 |
| T:L0034:J1 | ORD-224 | provisional_recommendation | W4 | 11.89 | 16 | L0034, L0035 |
| T:L0036:J1 | ORD-225 | provisional_recommendation | W5 | 9.78 | 17 | L0036 |
| T:L0039:J1 | ORD-226 | provisional_recommendation | W8 | 8.73 | 18 | L0039, L0040 |
| T:L0041:J1 | ORD-227 | provisional_recommendation | W5 | 8.85 | 16 | L0041 |
| T:L0043:J1 | ORD-228 | provisional_recommendation | W4 | 14.05 | 17 | L0043, L0044 |
| T:L0045:J1 | ORD-229 | provisional_recommendation | W5 | 10.55 | 18 | L0045 |
| T:L0047:J1 | ORD-230 | recommendation | W1 | 9.66 | 16 | L0047, L0048 |
| T:L0050:J1 | ORD-231 | recommendation | W2 | 10.77 | 19 | L0050, L0051 |
| T:L0052:J1 | ORD-232 | recommendation | W4 | 16.65 | 20 | L0052, L0053 |
| T:L0054:J1 | ORD-233 | recommendation | W1 | 10.51 | 18 | L0054, L0055 |
| T:L0056:J1 | ORD-234 | recommendation | W2 | 12.56 | 19 | L0056, L0057 |
| T:L0058:J1 | ORD-235 | recommendation | W3 | 13.72 | 20 | L0058, L0059 |
| T:L0060:J1 | ORD-236 | recommendation | W2 | 10.05 | 18 | L0060, L0061 |
| T:L0062:J1 | ORD-237 | recommendation | W2 | 13.63 | 19 | L0062, L0063 |
| T:L0064:J1 | ORD-238 | recommendation | W6 | 10.99 | 20 | L0064, L0065 |
| T:L0066:J1 | ORD-239 | recommendation | W8 | 11.79 | 18 | L0066, L0067 |
| T:L0068:J1 | ORD-240 | recommendation | W4 | 15.78 | 19 | L0068, L0069 |
| T:L0070:J1 | ORD-241 | recommendation | W5 | 11.33 | 22 | L0070, L0071 |
| T:L0072:J1 | ORD-242 | recommendation | W5 | 11.02 | 20 | L0072, L0073 |
| T:L0074:J1 | ORD-243 | recommendation | W2 | 15.07 | 21 | L0074, L0075 |
| T:L0076:J1 | ORD-244 | recommendation | W4 | 19.68 | 22 | L0076, L0077 |
| T:L0078:J1 | ORD-245 | recommendation | W1 | 11.78 | 20 | L0078, L0079 |
| T:L0084:J1 | ORD-248 | recommendation | W4 | 17.52 | 20 | L0084, L0086 |
| T:L0088:J1 | ORD-250 | recommendation | W5 | 12.25 | 22 | L0088, L0090 |
| T:L0092:J1 | ORD-252 | recommendation | W2 | 15.61 | 23 | L0092, L0094 |
| T:L0093:J1 | ORD-253 | recommendation | W5 | 13.49 | 24 | L0093, L0095 |
| T:L0096:J1 | ORD-254 | recommendation | W1 | 12.84 | 22 | L0096, L0098 |
| T:L0097:J1 | ORD-255 | recommendation | W3 | 15.36 | 23 | L0097, L0099 |
| T:L0100:J1 | ORD-256 | recommendation | W4 | 23.58 | 24 | L0100, L0102 |
| T:L0101:J1 | ORD-257 | recommendation | W6 | 12.41 | 22 | L0101, L0103 |
| T:L0104:J1 | ORD-258 | recommendation | W5 | 12.87 | 23 | L0104, L0106 |
| T:L0105:J1 | ORD-259 | provisional_recommendation | W3 | 16.72 | 24 | L0105, L0107 |
| T:L0108:J1 | ORD-260 | provisional_recommendation | W4 | 21.84 | 22 | L0108 |
| T:L0110:J1 | ORD-261 | recommendation | W6 | 2.95 | 9 | L0110 |
| T:L0111:J1 | ORD-262 | recommendation | W8 | 3.84 | 9 | L0111 |
| T:L0112:J1 | ORD-263 | recommendation | W6 | 4.84 | 9 | L0112 |
| T:L0113:J1 | ORD-264 | recommendation | W4 | 2.80 | 9 | L0113 |
| T:L0114:J1 | ORD-265 | recommendation | W4 | 1.93 | 2 | L0114 |
| T:L0115:J1 | ORD-266 | recommendation | W1 | 13.69 | 29 | L0115 |
| T:L0116:J1 | ORD-267 | recommendation | W3 | 17.54 | 29 | L0116 |
| T:L0117:J1 | ORD-268 | recommendation | W4 | 27.90 | 29 | L0117 |
| T:L0118:J1 | ORD-269 | recommendation | W5 | 15.34 | 60 | L0118 |
| T:L0120:J1 | ORD-271 | recommendation | W8 | 17.91 | 28 | L0120 |
| T:L0121:J1 | ORD-272 | recommendation | W4 | 25.31 | 26 | L0121 |
| T:L0122:J1 | ORD-273 | recommendation | W6 | 14.30 | 27 | L0122 |
| T:L0123:J1 | ORD-274 | recommendation | W2 | 18.29 | 28 | L0123 |
| T:L0124:J1 | ORD-275 | recommendation | W8 | 13.63 | 26 | L0124 |
| T:L0125:J1 | ORD-276 | recommendation | W2 | 16.50 | 27 | L0125 |
| T:L0126:J1 | ORD-277 | recommendation | W5 | 14.57 | 28 | L0126 |
| T:L0127:J1 | ORD-278 | recommendation | W5 | 14.11 | 26 | L0127 |
| T:L0128:J1 | ORD-279 | recommendation | W8 | 16.69 | 27 | L0128 |
| T:L0129:J1 | ORD-280 | recommendation | W6 | 14.77 | 28 | L0129 |
| T:L0130:J1 | ORD-281 | recommendation | W1 | 13.27 | 28 | L0130 |
| T:L0130:J2 | ORD-282 | recommendation | W1 | 14.33 | 29 | L0130 |
| T:L0131:J1 | ORD-283 | recommendation | W3 | 18.63 | 30 | L0131 |
| T:L0131:J2 | ORD-284 | recommendation | W4 | 26.61 | 28 | L0131 |
| T:L0132:J1 | ORD-285 | recommendation | W2 | 20.44 | 29 | L0132, L0133 |
| T:L0145:J1 | ORD-297 | recommendation | W1 | 14.96 | 31 | L0145 |

### Every other row, by outcome

**review_required** (11)

| Row | Order | Reason |
|---|---|---|
| T:L0080:J1 | ORD-246 | Allocation requests T:L0080:J1, T:L0082:J1 all name ORD-246; clarify the intended batches. |
| T:L0081:J1 | ORD-247 | Allocation requests T:L0081:J1, T:L0083:J1 all name ORD-247; clarify the intended batches. |
| T:L0082:J1 | ORD-246 | Allocation requests T:L0080:J1, T:L0082:J1 all name ORD-246; clarify the intended batches. |
| T:L0083:J1 | ORD-247 | Allocation requests T:L0081:J1, T:L0083:J1 all name ORD-247; clarify the intended batches. |
| T:L0089:J1 | ORD-251 | Allocation requests T:L0089:J1, T:L0091:J1 all name ORD-251; clarify the intended batches. |
| T:L0091:J1 | ORD-251 | Allocation requests T:L0089:J1, T:L0091:J1 all name ORD-251; clarify the intended batches. |
| T:L0136:J1 | ORD-288 | No workshop allowed for this request meets the deadline 2026-04-02 (1 days available). Closest option: W6 (Nimble Needle), delivery in 2.95 days, 1.95 days late. |
| T:L0137:J1 | ORD-289 | Requested W7 (OldMill) cannot take this batch: status=SUSPENDED. Without the request, the best on-time option is W5 (GiantWeave), delivery in 15.34 of 30 available days; using it needs the dispatcher's approval. |
| T:L0138:J1 | ORD-290 | Requested W4 (Little Loom) cannot take this batch: cannot_make_category=TOPS. Without the request, the best on-time option is W1 (QuickStitch), delivery in 14.54 of 28 available days; using it needs the dispatcher's approval. |
| T:L0139:J1 | ORD-291 | Requested W8 (FreshStart) cannot take this batch: exceeds_batch_cap=500>300. Without the request, the best on-time option is W5 (GiantWeave), delivery in 15.86 of 31 available days; using it needs the dispatcher's approval. |
| T:L0140:J1 | ORD-292 | Not supported by this plan, so the dispatcher must decide: split requested. |

**deadline_passed** (2)

| Row | Order | Reason |
|---|---|---|
| T:L0134:J1 | ORD-286 | The delivery deadline 2026-03-31 is on or before the dispatch date 2026-04-01, so no workshop can meet it. Nothing is estimated or reserved; only a revised deadline confirmed by the dispatcher can return this request to allocation, and the original date stays on record. |
| T:L0135:J1 | ORD-287 | The delivery deadline 2026-04-01 is on or before the dispatch date 2026-04-01, so no workshop can meet it. Nothing is estimated or reserved; only a revised deadline confirmed by the dispatcher can return this request to allocation, and the original date stays on record. |

**needs_clarification** (8)

| Row | Order | Reason |
|---|---|---|
| T:L0119:J1 | ORD-270 | Confirm which written date is the current deadline. |
| T:L0141:J1 | ORD-293 | Total production cost must not exceed 100. |
| T:L0142:J1 | ORD-294 | Confirm whether the allocation quantity is 1,250 pieces or the order-record quantity of 250 pieces.; The chat states 1250 pieces for ORD-294, but orders.csv records 250; confirm the quantity.; The stated quantity of 1,250 is explicitly not a confirmed change to the order record. |
| T:L0143:J1 | ORD-295 | The Apr 10 delivery change has not been approved. Which deadline applies? |
| T:L0144:J1 | ORD-9999 | ORD-9999 was not found. What is the correct order ID? |
| T:L0146:J1 | ORD-298 | Confirmation that the fabric has been released before allocation; Fabric is not approved; allocation must wait until release is confirmed |
| T:L0147:J1 | - | What is the order ID? |
| T:L0148:J1 | ORD-300 | Historical workshop assignment for ORD-300 last year |

**processing_review** (1)

| Row | Order | Reason |
|---|---|---|
| T:L0085:J1 | - | Selected evidence must belong to this task's supplied catalog. |

**link_review** (8)

| Row | Order | Reason |
|---|---|---|
| L0020:J1 | - | The follow-up does not identify which batch or task it refers to, and multiple candidate tasks are present. |
| L0024:J1 | - | The follow-up does not explicitly identify which allocation task “that batch” refers to. Multiple candidate tasks are present, and the shared author or batch context is insufficient to link it uniquely. |
| L0029:J1 | - | The follow-up does not identify which candidate task or batch it refers to; multiple allocation tasks are provided, and shared context alone is insufficient to link it. |
| L0033:J1 | - | The follow-up does not explicitly identify which prior task or batch it refers to, so the intended task is ambiguous. |
| L0037:J1 | - | The follow-up does not identify an order, customer, product, or explicit source task, so its intended task is ambiguous among the candidates. |
| L0042:J1 | - | The follow-up does not explicitly identify which existing batch or task it refers to, so the intended task is ambiguous. |
| L0046:J1 | - | The follow-up does not identify which batch or task it refers to, so the intended task cannot be determined from the supplied evidence. |
| L0109:J1 | - | The follow-up confirms an instruction but does not identify which of the four candidate allocation tasks it refers to. |

**non_task** (5)

| Row | Order | Reason |
|---|---|---|
| L0001 | - | Processing found no request or question: R001 [08:01] Chen: Morning team. Please keep each batch tied to its order number. |
| L0027 | - | Processing found no request or question: R027 [08:27] Ravi: Thanks, noted. |
| L0038 | - | Processing found no request or question: R038 [08:38] Mei: Thanks, noted. |
| L0049 | - | Processing found no request or question: R049 [08:49] Anika: Thanks, noted. |
| L0149 | - | Processing found no request or question: R149 [10:29] Mei: End of this dispatch review. Thanks everyone. |

## Model calls, cost and time

| Stage | Model | Calls | Paid in this run | Failed | Paid input tokens (cached) | Paid output tokens (reasoning) | Cost in this run | Cost of a fresh run | Model seconds in this run (fresh) |
|---|---|---|---|---|---|---|---|---|---|
| intake | gpt-5.6-luna | 50 | 50 | 0 | 38,889 (0) | 13,734 (4,973) | $0.0243 | $0.0243 | 197 (197) |
| link | gpt-5.6-luna | 43 | 43 | 0 | 28,799 (0) | 5,039 (1,769) | $0.0118 | $0.0118 | 108 (108) |
| verify | gpt-5.6-luna | 35 | 35 | 0 | 86,305 (68,839) | 24,190 (9,021) | $0.0339 | $0.0339 | 292 (292) |
| total | gpt-5.6-luna | 128 | 128 | 0 | 153,993 (68,839) | 42,963 (15,763) | $0.0700 | $0.0700 | 597 (597) |

A reused call was answered from the saved-answer cache, so this run paid nothing for it. A fresh run prices every answered call at its recorded tokens. Model seconds add up the recorded call times; they exclude Python time.

Prices per million tokens (checked 14 Oct 2026): `gpt-5.6-luna` $0.20 input, $0.02 cached input, $1.20 output; `gpt-4.1-mini` $0.40 input, $0.10 cached input, $1.60 output. Reasoning tokens are billed as output.
