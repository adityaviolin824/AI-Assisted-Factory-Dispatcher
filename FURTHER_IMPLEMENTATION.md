# Further implementation

Updated: 28 October 2026.

This roadmap records proposed product improvements for SweaterCo Dispatch Copilot. It supports the dispatcher's three core checks: whether a workshop can make a batch, can take it given capacity and workload, and is allowed to take it. The items below are planned work, not implemented capabilities or measured improvements.

The current application reads fixed CSV order/workshop records, calculates tentative queues and saves reviewed dispatch tables. SQLite supports chat and workflow checkpoints; JSON files retain run evidence and plan versions. Saving a table does not book production capacity. Current priorities and evaluation requirements remain in the [project plan](docs/project-plan.md); [capabilities and evidence](FEATURES.md) separates implementation from historical results.

## 1. Shared operational data and workshop availability

### Purpose and proposed approach

Use PostgreSQL as the proposed shared operational store for order records, workshop profiles and availability. Give workshop staff an authenticated application screen for maintaining their own availability and permitted capacity information. Updates should pass through the backend API, rather than exposing database credentials or unrestricted table editing to workshop users.

For example, a workshop could record that it will be closed for one week. The planner should use that dated closure when checking whether it can accept a batch, rather than relying on a dispatcher to remember the closure or manually edit a CSV.

### Required behavior

- Record closure start/end dates, the applicable timezone/calendar, an optional operational reason, the actor, update time and record version. Keep temporary unavailability distinct from administrative suspension.
- Restrict workshop staff to their own permitted fields and records. Order details, other workshops' records, commercial terms and suspension decisions need separately defined permissions. PostgreSQL alone does not supply the application login or workshop interface.
- Check availability against the proposed production period, including the effect of the existing queue, rather than only checking whether the workshop is open today. Define date boundaries and reopening behavior before implementing calendar-aware delivery estimates. Until those estimates are supported, overlapping closures must prevent automatic recommendation rather than be ignored.
- Read a consistent planning snapshot and retain its record versions with the decision. Recheck relevant changes before approval; a closure or capacity update after preview must require refreshed calculations and visible review of changed results.
- Flag existing affected work for dispatcher attention. A closure update must not silently transfer work already accepted or started, or rewrite earlier saved decisions.
- Preserve the current distinction between automatic eligibility and explicit dispatcher overrides. Define permitted operational overrides and their authorization before enabling live commitments; a migration must not silently change the current review contract.

### Decisions, alternatives and expected effect

PostgreSQL is the proposed direction for shared access by workshop staff and dispatchers. Fixed CSVs remain simpler for the current reproducible prototype; SQLite remains a reasonable local relational alternative. Existing SQLite chat/checkpoint storage does not need to be replaced merely because operational records move to PostgreSQL.

The expected benefit is more current availability and fewer recommendations based on stale workshop facts. This depends on staff recording updates and on a defined data owner; a database does not make records automatically current. Database access adds latency that must be measured.

Keep the supplied CSV fixtures and simulator unchanged for historical evaluation. Introduce the operational data path separately and compare equivalent snapshots before changing the planner's data source. Do not claim that a database migration improves the recorded benchmark scores.

Live bookings require a separate assignment/reservation transaction, duplicate-submission protection and clear queue ownership. Work already included in a workshop's reported workload must not be counted again as an application reservation. These guarantees require explicit design and verification; storing rows in PostgreSQL is insufficient by itself.

### Acceptance checks

- A workshop user can update its own closure, but cannot alter another workshop, order records or its own administrative suspension.
- A one-week closure excludes overlapping automatic options; work after reopening is evaluated under the defined calendar and deadline policy.
- A closure added between preview and approval invalidates stale calculations and exposes the affected rows.
- Existing assignments remain recorded, affected work is visible, and repeated submissions cannot reserve the same batch twice once live bookings exist.
- Every availability change is attributable and earlier planning snapshots remain inspectable.

## 2. Local PII filtering

### Purpose and proposed approach

Reduce unnecessary personal information sent to language models and external tracing services. Detection must run locally, without a public detection API. Begin with a defined scope such as email addresses, phone numbers and specifically supported personal identifiers, using compiled patterns and consistent replacement aliases. Use known-value mappings for structured personal fields where available.

Names and addresses in free text may need local entity recognition. Presidio with a local NLP model is an option to evaluate if the initial scope requires it; it is not a selected dependency. Pattern matching alone must not be described as complete PII detection, and reversible aliases do not make the data anonymous.

### Integration requirements and verification

- Preserve order IDs, workshop IDs, quantities and dates needed for dispatch. Check ambiguous numeric patterns rather than masking every number.
- Create a consistent redacted processing snapshot before traceable graph execution and model calls. All stages must validate exact quotations against that same snapshot; masking only the outgoing prompt would conflict with current source-evidence checks.
- Keep any originals and alias mappings under restricted local access with a defined retention policy. Do not send mappings to models or external traces. Preserve the dispatcher's ability to inspect original evidence locally.
- Check all outbound paths, including LangSmith graph inputs, state and decisions. Trace suppression or redaction must be verified before using sensitive inputs; protecting the model request alone is insufficient.
- Include the redaction policy/version in cache identity and prevent reuse of unredacted cached content in the protected path.
- Use synthetic examples to check repeated aliases, names/contact details, legitimate order facts, exact-source validation and the absence of original PII in outbound traces and generated evidence exports.

The first implementation should avoid another network call. Measure detection misses, unnecessary masking and added median/p95 latency on representative conversations. If a local NLP model is added, load it once and report startup separately from steady-state processing. No latency result has been established yet.

## 3. Basic prompt-injection checks

### Purpose and proposed approach

Add a local detection layer for attempts to change the model's role, bypass its task or expose unrelated information. Current prompts already treat source evidence as data, and Python checks response structure, source membership and scheduling rules. These controls do not establish complete resistance to manipulated interpretations.

Start with a small, explainable signature set and a normalized detection copy of the text. Preserve the original evidence. Simple matching or regular expressions are sufficient for an initial small list; Aho-Corasick becomes an option when many fixed phrases must be scanned efficiently. It accelerates matching, not understanding of malicious intent.

A small local encoder classifier, such as Prompt Guard 2 22M, is a later candidate if signatures miss important cases. Evaluate its model/license requirements, context limits, false positives and latency on the intended hardware before adoption. Encoding text as Base64 or another representation is not an injection defense.

### Required behavior and verification

- Route flagged input to visible review without silently deleting the message, its order references or a potentially important correction. Account for requests that the flagged update could affect under the existing uncertainty/review policy.
- Include legitimate corrections such as "ignore my earlier deadline" in the benign checks. Matching a suspicious phrase alone does not prove an attack.
- Test direct role changes, attempts to bypass workshop rules, paraphrases, unusual Unicode and encoded content alongside ordinary dispatch requests. Preserve source coverage and the automatic workshop constraints.
- Keep schema validation separate from semantic correctness: an injected preference or wrong follow-up can still fit a valid response schema.
- Report missed attacks, benign messages incorrectly flagged, effects on useful allocation coverage and added latency. Keep measured protection limited to the tested cases.

No signature list or classifier should be presented as complete prompt-injection protection. Stronger model-independent controls and human review remain necessary, and any policy change requires its own evaluation.

## 4. Public cost and reproducibility evidence

### Purpose and proposed approach

Prepare a small sanitized evidence bundle so a reader can inspect recorded usage and reproduce the model-cost calculation without accessing a private tracing account or publishing full run contents.

The 22 October 2026 end-to-end experiment has 128 saved paid call records for 100 cases across 149 messages. Recalculating their recorded token usage with the repository's historical price table gives $0.07569878, rounded to $0.0757. This is the recorded model-usage estimate for that experiment, not a guaranteed cost for future runs or a provider invoice. Hosting and human review time are excluded.

The [experiment record](backend/docs/evaluation/END_TO_END_TEST_2026-10-22.md#8-cost-and-time) retains the public summary. The [calculator](backend/eval_run_report/run_summary.py) applies the stored prices to token usage. Detailed run reports and call records exist locally under the ignored output directory; publication of this roadmap does not publish those raw records.

### Evidence to retain and verify

- Publish selected usage-only records or a sanitized table with run identity, model, stage, calls, input/output tokens, provider-cached input, price-table date, timings and the calculation method. Exclude source conversations, personal identifiers, credentials and sensitive response contents.
- Distinguish locally reused model answers, which incur no new model call, from discounted provider-cached input within a paid API call. Do not bill reasoning tokens twice when they are already included in output tokens.
- Check the exported totals against the retained call records and keep the original historical report unchanged. Treat LangSmith as optional supporting evidence rather than a prerequisite for inspection.
- Report fresh runs, saved-answer replays and human-assisted review separately. Updating pricing assumptions must not silently rewrite historical estimates.

## 5. Implementation sequence and presentation scope

The immediate priorities remain known correctness gaps, integrated workflow verification and the required final evaluation. Plan the extensions in bounded increments:

1. Specify the PII scope, operational permissions, closure/calendar rules and measurable acceptance criteria.
2. Prepare the sanitized cost evidence from existing records without a new model run.
3. Add and verify local PII filtering, then basic injection checks, preserving interpretation and source-evidence behavior. Evaluate an encoder only if the measured benefit justifies it.
4. Prototype workshop availability and operational data changes in the experiment notebook workflow before integrating a shared store and workshop interface. Validate equivalent snapshots before introducing live updates or bookings.
5. Address operational transactions, concurrency and permissions before live use. Containerization and deployment remain the final phase.

For the final presentation, describe these as future improvements: workshop-maintained availability in a shared operational store, local privacy filtering, measured injection checks and independently inspectable cost records. Do not imply that PostgreSQL, a workshop portal, PII redaction, an injection classifier or live production bookings are already implemented.

## Technical references

- [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html): possible additional enforcement for workshop-specific data access; policies and application identity still require configuration.
- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html): concurrency behavior to consider for consistent reads and future reservations.
- [Presidio](https://presidio.dataprivacystack.org/): local PII recognition/anonymization options and detection limitations.
- [OWASP prompt-injection guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html): layered defenses, encoding attacks and evaluation boundaries.
- [Aho-Corasick implementation documentation](https://pyahocorasick.readthedocs.io/en/latest/): efficient matching of predefined strings.
- [Prompt Guard 2 22M model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M): local encoder-classifier candidate and its stated scope and limits.
