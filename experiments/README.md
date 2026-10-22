# Experiments

These notebooks cover chat processing, workshop allocation, the combined LangGraph pipeline and the first dispatcher review screen. They are earlier stages of the backend. The current application is described in the [backend README](../backend/README.md).

The task stayed the same through these steps: read a dispatch request, check which workshops can make the batch and take the extra work, check their restrictions, and give the dispatcher a usable recommendation.

## Reading order

| Notebook | What to look at |
|---|---|
| [02: Chat processing](notebooks/02-order-processing-from-chat-v4.ipynb) | Separate requests from follow-ups, retain the original words and check each task against the CSV data. |
| [03: Allocation](notebooks/03-order-allocation-v5.ipynb) | Apply workshop rules, estimate delivery and cost, then build a shared plan in deadline order. Includes controlled checks C1-C14. |
| [05: Combined pipeline](notebooks/05-order-pipeline-mvp.ipynb) | Put processing and allocation in one LangGraph flow. This replaced the earlier disk handoff between stages. |
| [06: Dispatcher review](notebooks/06-dispatcher-workflow.ipynb) | Show recommendations and unresolved cases, try typed decisions, and use a small Gradio screen. Its per-row approval rules are historical. |

Notebook 04 was the first combined graph. Notebook 05 is included here because it carries that work forward with one execution path and simpler storage. The [timeline](timeline.md) records the intermediate steps.

The [development notes](development-notes.md) cover four problems in more detail: duplicate extraction, lost years in dates, follow-up detection, and requests that never reached verification. They include what was tried, the result and the limits of each fix. The [engineering log](../docs/engineering-log.md) and [model experiment record](../backend/docs/evaluation/PROMPT_TESTING_RESULTS.md) contain the longer records.

## About these copies

The sources remain in the local `backend/experimentation_notebooks/` folder. These copies were prepared on 22 October 2026. Comments and introductions were shortened, empty cells and saved outputs were removed, and paths were adjusted for this folder. Model prompts, calculations, validation rules and decision functions were retained. Each notebook records its source path and hash in its metadata.

The notebooks describe the rules at their own stage. For example, earlier processing held tasks when a follow-up was unresolved. The current backend instead shows provisional warnings. Notebook 06 also predates the current single **Approve all** submission. These differences are intentional history, not instructions to change the application back.

AI tools assisted with code, tests, investigations and documentation. The team made scope and workflow decisions and reviewed the test dataset. The notes distinguish recorded model runs, offline checks and remaining work.

## Before running anything

The files can be read on GitHub without running them. To execute cells, use the existing environment in `backend/`; the copies have no separate dependencies.

```sh
cd backend
uv run python -m jupyterlab ../experiments/notebooks
```

- Notebooks 02 and 05 can make paid model calls. A cache hit is free, but the public repository does not include the response cache. Do not use Run All as a free check.
- Notebook 03 makes no model calls. Its real-plan cells need the matching processing handoff. For its controlled checks, run the definitions, the Section 5 example cell that defines `check_task`, then Section 7. These do not need the handoff.
- Notebook 06 needs a saved local run containing `manifest.json`, `state.json` and `plan.json`. Its explanation cells can make paid calls. Its decision and Gradio sections make no model calls, but saving decisions writes into the selected run.
- The copies of 02, 03 and 05 write under `experiments/notebooks/output/`, which is ignored. Notebook 06 reads the backend's local runs and retains the historical save behavior described above.
- Optional LangSmith tracing can send chat and run data to an external service. Keep it off for offline checks.

Saved outputs, credentials, local databases, response caches and private paths are not included here. Results quoted in the notes are historical; preparing these copies did not repeat the model runs.

Reallocation, the optional review after it and approval after reallocation are still pending. No notebook 07 is included.
