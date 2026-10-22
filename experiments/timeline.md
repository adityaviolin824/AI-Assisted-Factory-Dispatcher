# Development timeline

This is a short route through the dated records. Test counts and run results refer to the work recorded on that date.

| Date | Work | What changed or was learned |
|---|---|---|
| 6 October 2026 | Investigated repeated extraction | Thirty source messages appeared 48 times in overlapping groups. The next processing design gave each target message one owner and used earlier messages only as context. |
| 9-10 October | Separated processing and allocation experiments | Processing retained tasks, corrections and reviews. Allocation checked workshop rules and reported why a request could not be assigned. Early runs exposed lost questions and workshop restrictions. |
| 12 October | Reviewed the first combined LangGraph notebook | Identified empty-input handling, date parsing and storage/run-identity problems. Notebook 05 first reproduced the earlier graph with saved answers before changes were made. |
| 13 October | Simplified notebook 05 and moved code into modules | Used one graph execution path and passed processing state directly to allocation. Fixed empty input and dates whose written year was lost. Module checks compared behavior with the notebook. |
| 14 October | Compared intake models and prompts | On the seven-message development chat, changing intake from `gpt-4.1-mini` to `gpt-5.6-luna` improved labels from 3/7 to 7/7 in the recorded comparison. One follow-up still failed at linking. |
| 15 October | Changed how unresolved follow-ups affect other tasks | Removed persistent holds that could prevent verification. Usable requests could produce provisional recommendations, with the unresolved evidence still shown. This did not fix the language interpretation errors. |
| 18-19 October | Added dispatcher views and decision experiments | Notebook 06 showed recommendations, problems and source messages. Typed decisions and a Gradio screen exercised recalculation. Date and quantity checks were also tightened. |
| 20 October | Added the graph review pause and FastAPI routes | A review could wait in a checkpoint and be answered through Python or the API. The dispatcher's workshop choices were given priority over automatic selection. |
| 21 October | Added one-batch final approval | The frontend could keep choices locally and submit the complete set once. The backend calculated and saved the result, with changed rows returned for inspection. This did not complete reallocation. |
| 21 October | Reviewed and ran the extended dataset | Three team members divided the manual review of 100 cases in 149 messages. Two subsequent model runs exposed remaining linking, interpretation and date-handling errors, including an unsafe cancelled-order recommendation. Both runs are in the evaluation record. |
| 22 October | Prepared the public experiment copies | Retained the original notebooks, shortened explanations and removed saved output and local metadata from the copies. Reallocation remains separate work. |

## Records

- [Development notes](development-notes.md): selected investigations with causes, attempted fixes and checks.
- [Engineering log](../docs/engineering-log.md): the detailed dated record, including scope decisions and verification.
- [Prompt and model tests](../backend/docs/evaluation/PROMPT_TESTING_RESULTS.md): settings, keys, costs and recorded outcomes.
- [Evaluation guide](../evaluation/README.md): datasets, the reviewed key and measured results.
- [Current implementation](../backend/README.md): the code used by the application now.
