# Harness evaluation: our allocation policies against the supplied baselines

| | |
|---|---|
| **Run date** | 15 October 2026 |
| **Harness** | `harness/simulate.py`, unchanged (SHA-256 identical to the supplied `project-material/harness/simulate.py`) |
| **Data** | `backend/data/orders.csv` (120 orders, sent 1 January to 27 March 2026) and `backend/data/workshops.csv` (8 workshops, 7 active) |
| **Seed** | 5105 (the harness default), the same for every policy |
| **Scenarios** | Normal run, and shock run (`--shock`): W2 SteadyHands closed for days 30–44 (31 January to 14 February 2026) |
| **Our code** | `backend/eval_harness/run_harness_evaluation.py`, using the allocation rules in `backend/task_allocation_to_workshops/` |
| **Model calls** | None. The harness replay is deterministic: a rerun gives the same numbers. |

## Summary

- **Delivery time and lateness.** All six of our policies beat all three baselines on mean delivery days, p90 delivery days and percentage late, in both the normal and the shock run.
- **Our default policy** (minimize lateness) is late on 2 of 120 batches with a mean of 8.1 delivery days. The best baseline, `random`, is late on 41 batches with a mean of 21.5 days.
- **Cost.** A baseline wins: `cheapest` costs 85,960, against 101,005 for our cheapest policy. But 112 of its 120 batches are late. Our default costs 115,360, which is 3,580 more than `random`.
- **Defects.** Our default has 7 defective batches, against 5 for `random` and `greedy_biggest`. Our hybrid policy has the fewest of all policies (4). Defects are random draws, so differences of a few batches are small.
- **Shock.** Our default is unaffected: still 2 late batches, with a mean of 8.3 days. The three policies that spread work across workshops (concentration, robustness and hybrid) go from 6–8 to 15 late batches each. The policy named "robustness" is therefore not the most robust in this test.

## 1. What was evaluated

### 1.1 The harness

`simulate.py` replays the 120 historical orders in date order. For each batch it asks the allocator for one workshop, then simulates that workshop's queue, its production (pieces divided by daily capacity), a random defect (if the batch is defective, half of it is redone) and transport. Choosing a workshop that is suspended, cannot make the category or is over its batch cap stops the run with an error.

| Official metric | Definition in `simulate.py` |
|---|---|
| Mean days | Mean delivery time per batch: from the day it is sent to the day it is complete, including queue wait, production, rework and transport |
| p90 days | 90th-percentile delivery time (the 109th of the 120 sorted values) |
| % late | Share of batches whose completion date (rounded to a whole day) is after the due date |
| % defect | Share of batches that came back defective |
| Cost | Total of pieces × cost per piece |
| Max share | Largest share of all pieces sent to one workshop |

### 1.2 The policies

The three baselines are supplied with the harness. Our six policies use the app's allocation rules, one objective each.

| Name in the tables | Source | How it chooses |
|---|---|---|
| `random` | Baseline | A random eligible workshop |
| `greedy_biggest` | Baseline | The eligible workshop with the highest capacity |
| `cheapest` | Baseline | The eligible workshop with the lowest cost per piece |
| `tardiness` | Ours (**default**) | Lateness, then delivery days, then cost |
| `cost` | Ours | Cost, then delivery days, then defect rate |
| `defects` | Ours | Defect rate, then delivery days, then cost |
| `concentration` | Ours | Workload share, then delivery days, then defect rate |
| `robustness` | Ours | Workload share, then lateness, then defect rate |
| `hybrid` | Ours | 0.5 × lateness + 0.25 × cost + 0.25 × workload share, each scaled from 0 to 1 within the candidates |

`tardiness` is the app's default: a request with no stated preference is ranked this way.

### 1.3 How our policies decide each batch

For every batch, each of our policies follows the app's own steps:

1. **Hard rules first.** Remove workshops that are suspended, cannot make the category or are over their batch cap. These are the same rules as the harness's `eligible_workshops()`.
2. **Estimate delivery days** for each remaining workshop: current queue + production + expected rework + transport. Expected rework is production × defect rate × 0.5. The queue is the one the harness reports at that moment.
3. **Remove late workshops.** A workshop is late if its estimate is greater than the days between the batch's sent date and its due date.
4. **Rank the on-time workshops** by the policy's objective, and choose the first.

Decisions made for the harness (15 October 2026):

| Question | Decision | Reason |
|---|---|---|
| What if no workshop can deliver on time? | Choose the least-late workshop (lateness, then delivery days, then cost), whatever the policy | The harness requires a workshop for every batch, where the app would ask the dispatcher. Least-late keeps our first priority, avoiding lateness. |
| Should the on-time check round like the harness? | No: we keep the app's unrounded estimate | The harness then measures exactly the rule the app uses. Our check is slightly stricter: 10.3 estimated days with 10 available counts as late. |
| Which date counts as "today"? | Each batch's own sent date | The app's fixed 1 April 2026 snapshot does not apply to a replay that runs from January to March. |
| How is workload share counted? | Separately for each run of each policy | Runs must not affect each other. |

## 2. Results: normal run

### 2.1 Official metrics (as printed by `simulate.py`)

| Policy | Mean days | p90 days | % late | % defect | Cost | Max share |
|---|---:|---:|---:|---:|---:|---:|
| `random` (baseline) | 21.5 | 45.6 | 34% | 4% | 111,780 | 23% |
| `greedy_biggest` (baseline) | 49.0 | 80.6 | 84% | 4% | 108,430 | 70% |
| `cheapest` (baseline) | 105.1 | 192.9 | 93% | 8% | **85,960** | 70% |
| **`tardiness` (our default)** | **8.1** | **13.7** | **2%** | 6% | 115,360 | 25% |
| `cost` | 16.5 | 27.8 | **2%** | 4% | 101,005 | 37% |
| `defects` | 20.2 | 31.8 | 19% | 5% | 108,980 | 40% |
| `concentration` | 12.2 | 24.4 | 6% | 5% | 113,275 | **21%** |
| `robustness` | 12.4 | 26.0 | 5% | 4% | 112,920 | **21%** |
| `hybrid` | 12.8 | 25.9 | 7% | **3%** | 111,850 | 22% |

Bold marks the best value in each column.

### 2.2 External lateness measures (not official harness metrics)

Days late for one batch = max(0, completion date − due date), taken from the same replay outcomes.

| Policy | Late batches (of 120) | Mean days late, all batches | Mean days late, late batches only | p90 days late | Total days late |
|---|---:|---:|---:|---:|---:|
| `random` (baseline) | 41 | 5.9 | 17.2 | 24 | 704 |
| `greedy_biggest` (baseline) | 101 | 25.3 | 30.0 | 58 | 3,034 |
| `cheapest` (baseline) | 112 | 80.8 | 86.6 | 169 | 9,697 |
| **`tardiness` (our default)** | **2** | **0.2** | 10.0 | **0** | **20** |
| `cost` | **2** | **0.2** | 10.0 | **0** | **20** |
| `defects` | 23 | 1.5 | 7.8 | 5 | 180 |
| `concentration` | 7 | 0.5 | 9.0 | **0** | 63 |
| `robustness` | 6 | 0.5 | 10.2 | **0** | 61 |
| `hybrid` | 8 | 0.5 | **8.1** | **0** | 65 |

## 3. Results: shock run (W2 SteadyHands closed, days 30–44)

The closed workshop is chosen at random by the harness (seed 5105) and is the same for every policy. Work that would start at W2 during the closure waits until it reopens. The allocators are not told about the closure.

### 3.1 Official metrics (as printed by `simulate.py`)

| Policy | Mean days | p90 days | % late | % defect | Cost | Max share |
|---|---:|---:|---:|---:|---:|---:|
| `random` (baseline) | 23.4 | 48.4 | 39% | 4% | 111,780 | 23% |
| `greedy_biggest` (baseline) | 51.0 | 81.2 | 87% | 4% | 108,430 | 70% |
| `cheapest` (baseline) | 103.9 | 190.0 | 92% | 5% | **85,960** | 70% |
| **`tardiness` (our default)** | **8.3** | **15.4** | **2%** | 6% | 115,665 | 27% |
| `cost` | 16.3 | 26.9 | 3% | 4% | 101,700 | 37% |
| `defects` | 19.2 | 32.7 | 17% | **2%** | 108,490 | 41% |
| `concentration` | 13.2 | 29.6 | 12% | 3% | 112,650 | **19%** |
| `robustness` | 13.7 | 30.8 | 12% | 3% | 112,795 | **19%** |
| `hybrid` | 13.4 | 28.3 | 12% | **2%** | 111,850 | **19%** |

### 3.2 External lateness measures (not official harness metrics)

| Policy | Late batches (of 120) | Mean days late, all batches | Mean days late, late batches only | p90 days late | Total days late |
|---|---:|---:|---:|---:|---:|
| `random` (baseline) | 47 | 7.1 | 18.2 | 26 | 857 |
| `greedy_biggest` (baseline) | 104 | 27.1 | 31.3 | 58 | 3,258 |
| `cheapest` (baseline) | 110 | 79.6 | 86.9 | 167 | 9,556 |
| **`tardiness` (our default)** | **2** | **0.2** | 10.0 | **0** | **20** |
| `cost` | 4 | **0.2** | 6.8 | **0** | 27 |
| `defects` | 20 | 1.5 | 8.9 | 7 | 179 |
| `concentration` | 15 | 1.0 | 7.9 | 4 | 118 |
| `robustness` | 15 | 1.0 | 8.1 | 2 | 122 |
| `hybrid` | 15 | 0.8 | **6.7** | 2 | 101 |

## 4. Response to the shock

| Policy | Late batches, normal → shock | Mean days, normal → shock | p90 days, normal → shock |
|---|---|---|---|
| `random` (baseline) | 41 → 47 | 21.5 → 23.4 | 45.6 → 48.4 |
| `greedy_biggest` (baseline) | 101 → 104 | 49.0 → 51.0 | 80.6 → 81.2 |
| `cheapest` (baseline) | 112 → 110 | 105.1 → 103.9 | 192.9 → 190.0 |
| **`tardiness` (our default)** | **2 → 2** | 8.1 → 8.3 | 13.7 → 15.4 |
| `cost` | 2 → 4 | 16.5 → 16.3 | 27.8 → 26.9 |
| `defects` | 23 → 20 | 20.2 → 19.2 | 31.8 → 32.7 |
| `concentration` | 7 → 15 | 12.2 → 13.2 | 24.4 → 29.6 |
| `robustness` | 6 → 15 | 12.4 → 13.7 | 26.0 → 30.8 |
| `hybrid` | 8 → 15 | 12.8 → 13.4 | 25.9 → 28.3 |

Our default keeps the same 2 late batches under the shock. The three policies that spread work across workshops (`concentration`, `robustness` and `hybrid`) about double their late batches. A policy's name does not show how robust it is: here `robustness` responds worse than the default. We have not yet analysed why the spreading policies are hit harder.

## 5. Where a baseline wins

| Metric | Baseline result | Our closest result | Trade-off |
|---|---|---|---|
| Cost | `cheapest`: 85,960 | `cost`: 101,005 (15,045 more) | `cheapest` is late on 112 of 120 batches; our `cost` policy on 2 |
| Cost, against our default | `random` 111,780 and `greedy_biggest` 108,430 | `tardiness`: 115,360 | Our default pays 3,580 more than `random` and is late on 2 batches instead of 41 |
| Defects, against our default | `random` and `greedy_biggest`: 5 defective batches | `tardiness`: 7 | Our `cost` and `robustness` policies match 5; `hybrid` has 4 |
| Max share, against our default | `random`: 23% | `tardiness`: 25% | `concentration`, `robustness` (21%) and `hybrid` (22%) are below `random` |

Everywhere else (mean days, p90 days, % late and every lateness measure), every one of our six policies beats every baseline, in both runs.

## 6. How to read these numbers

- **Scope.** This replay scores the allocation rules only. It does not test how the app reads chat messages; the 30 chat requests are evaluated separately. Harness batches carry no requested or excluded workshops, so those request rules are not exercised here.
- **Historical replay.** The 120 orders include orders that are already complete. The replay is separate from live dispatch.
- **Forced choices.** When no workshop can be on time, the app would send the request to the dispatcher. The harness forces a choice, so our policies take the least-late workshop.
- **Estimates and outcomes differ.** Our policies plan with expected rework. The harness draws each defect at random and rounds completion days, so a batch we estimate as on time can still finish late.
- **Defects are random draws.** With 120 batches, one batch is about 0.8 percentage points. Differences of one to three defective batches between policies are small.
- **Compare % defect within a run, not across runs.** Before the replay, the shock run uses one random draw to choose the closed workshop, so every later defect draw is different. For example, `cheapest` makes the same choices in both runs (cost 85,960 both times), but has 9 defective batches in the normal run and 6 in the shock run.
- **One seed.** All results use seed 5105, as every team's results do.

## 7. How to reproduce

From `backend/`:

```
uv run python -m eval_harness.run_harness_evaluation
```

The script prints the official `simulate.py` report and the external lateness table for both runs. It needs no API key and makes no model calls. `simulate.py` is imported unchanged; only its data folder is pointed at `backend/data/`, because the folder it expects (`DSS-Project-CODES/data/`) does not exist in this project.

## 8. Checks behind these numbers

The offline tests in `backend/tests/test_harness_evaluation.py` (14 tests, all passing on 15 October 2026) check that:

- `simulate.py` is byte-for-byte identical to the supplied copy, and it reads the app's data: the same 120 orders and 8 workshops as the app;
- the decision rules give the hand-worked answers on made-up workshops: hard rules first, late workshops removed, days counted from each batch's sent date, the least-late choice when none is on time, the harness's queues used, and workload counted separately for each run;
- for all 120 orders under all six policies, our harness choice equals the app's own recommendation (or its least-late option when every allowed workshop is late);
- both replays finish for every policy (the harness stops with an error on any ineligible choice);
- the rebuilt days late agree with the harness's own late flag for every batch of every run.

Each rule was also broken on purpose, in memory, to confirm the tests catch it: days counted from the wrong date, late workshops ranked by the objective, queues ignored, workload counts shared between runs, and completion days truncated instead of rounded. Every break made at least one test fail.
