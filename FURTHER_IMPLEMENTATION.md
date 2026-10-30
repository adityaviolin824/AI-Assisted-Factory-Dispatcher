# Further implementation

**Current product priority, 31 October 2026:** deepen the workshop-update-to-dispatcher workflow and improve interface quality. Chinese/bilingual expansion, PII filtering and additional injection checks are deferred. Existing evaluation evidence is retained. This roadmap preserves earlier technical research; its previous PII-first and multilingual implementation sequence is superseded. The workshop extension remains proposed. Translation is disabled by default, with its implementation retained.

Updated: 29 October 2026. Multilingual research added after reviewing current publisher documentation. Later that day, the in-app model-usage view (section 4) and cloud voice input (section 5) were implemented, the first PII scope was set (section 2) and injection checks were kept as future work (section 3). On 30 October, local Chinese-to-English translation at Send was implemented (section 5). Historical results are unchanged.

This roadmap records proposed product improvements for SweaterCo Dispatch Copilot. It supports the dispatcher's three core checks: whether a workshop can make a batch, can take it given capacity and workload, and is allowed to take it. The items below are planned work, not implemented capabilities or measured improvements, except the parts marked as implemented in sections 4 and 5.

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

Reduce unnecessary personal information sent to language models and external tracing services. Detection must run locally, without a public detection API. Use consistent replacement aliases, and known-value mappings for structured personal fields where available.

**Scope decision (29 October 2026):** the first implementation targets names of people and addresses. Contact patterns such as email addresses and phone numbers can follow as compiled patterns.

Names and addresses in free text cannot be found reliably by compiled patterns, so this scope needs local entity recognition. Presidio with a local NLP model is the candidate to evaluate; adding it is a new dependency that needs approval, and it is not yet selected. Any masking changes the text the models receive, so validating it on the existing conversations needs a separately authorized paid run. Pattern matching alone must not be described as complete PII detection, and reversible aliases do not make the data anonymous.

Voice recordings are outside this text filter: a recording reaches the transcription model before any text exists to filter (section 5).

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

**Timing decision (29 October 2026):** these checks remain future work. The final presentation describes them as a planned control, not an implemented one.

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

**Implemented part: in-app usage view (29 October 2026).** `GET /runs/{run_id}/usage` and the Dispatcher's **Model usage and cost** panel show each saved run's calls, reused answers, tokens, model time and estimated cost per stage. The calculator above counts them from the run's call records with the stored price table, whose check date (14 October 2026) is shown. The response contains numbers and model names only. On the 19 October run it reports 192 calls, 37 of them paid, $0.0705 for this run and $0.1434 with no saved answers. This serves local inspection only: the 22 October experiment is not among the app's saved runs, and nothing is published. The sanitized public bundle below is still to be prepared.

### Evidence to retain and verify

- Publish selected usage-only records or a sanitized table with run identity, model, stage, calls, input/output tokens, provider-cached input, price-table date, timings and the calculation method. Exclude source conversations, personal identifiers, credentials and sensitive response contents.
- Distinguish locally reused model answers, which incur no new model call, from discounted provider-cached input within a paid API call. Do not bill reasoning tokens twice when they are already included in output tokens.
- Check the exported totals against the retained call records and keep the original historical report unchanged. Treat LangSmith as optional supporting evidence rather than a prerequisite for inspection.
- Report fresh runs, saved-answer replays and human-assisted review separately. Updating pricing assumptions must not silently rewrite historical estimates.

## 5. Chinese-English support, translation and optional dictation

### Purpose and research decision

Workers should be able to express requirements and understand clarification in a language they know. Plan typed Chinese and English, a labeled translation beside the original, and bilingual review information first. Add short, editable local voice dictation afterward. Singlish and Mandarin-English mixtures remain experimental until evaluated on representative speech and task meaning.

**Implemented part: cloud voice input (29 October 2026).** Ahead of this sequence, an approved increment added short editable dictation through OpenAI instead of a local recognizer. **Record** sends one recording to `POST /chat/transcriptions`, which uses `gpt-transcribe` with English and Mandarin language hints, and the transcript appears in the message box for the worker to check before **Send**. It follows the dictation rules below: an editable original-language transcript, text fallback, and no automatic sending, processing or approval. It departs from the local-execution rule: audio leaves the host for OpenAI, which is why the route is refused unless the API runs with `ALLOW_PAID_PROCESSING=1`, and why nothing is stored. English is the supported language. Mandarin is experimental because the cancellation, date and quantity checks read English only. Accuracy, latency and cost on real speech are unmeasured; OpenAI listed $0.0045 per minute when checked on 29 October 2026. The [system design](docs/system-design.md#voice-input-decision-29-october-2026) records the alternatives. Local recognition remains the planned replacement behind the same editable flow.

**Implemented part: local translation at Send (30 October 2026).** With `[translation]` on in `backend/config.toml`, **Send** translates a message containing Chinese characters into English with the research's first candidate, Hy-MT2-1.8B, converted to 8 bits and run on the host through MLX, and saves the English. A translation that loses, changes or adds an order or workshop ID is refused. It follows the local-execution rule and has no per-message charge. It departs from the first rule below: the English replaces the original instead of sitting beside it. Quantities, dates, negation and intent are not validated after translation; it was checked on 12 made-up messages. The [system design](docs/system-design.md#local-translation-decision-30-october-2026) records the decision.

The [multilingual research](MULTILINGUAL_INPUT_RESEARCH.md) compares local translation and speech models, regional alternatives, licenses, runtime evidence and evaluation limitations. Its initial trial shortlist is Hy-MT2-1.8B for translation and Qwen3-ASR-0.6B for later dictation, with larger/regional comparisons only when measured failures justify them. Hy-MT2-1.8B is now installed for the translation above; no speech model is installed.

### Required behavior and acceptance boundaries

- Preserve original messages and source IDs. Keep machine translations as derived information; a translated sentence is not an exact quotation from the source. Redacted processing snapshots must remain consistent with source validation and tracing protection.
- Compare direct Chinese interpretation against translation-assisted interpretation before choosing the processing path. Translation may support the interface without becoming an obligatory semantic conversion before allocation.
- Extend the English-oriented date, quantity and cancellation checks explicitly. Preserve negation, workshop exclusions, corrections and follow-up ownership; possible cancellation asks for review and never automatically cancels work.
- Provide bilingual structured facts, clarification and stable warning templates. A worker must not need English fluency to verify their Chinese request. Python retains all scheduling calculations, and dispatcher-only corrections/overrides retain their existing authority.
- Later dictation must produce an editable original-language transcript before **Send**, with text fallback. Sending, processing and approval stay separate; a voice or sender label does not confer permissions.
- Keep ASR/translation local to the chosen application host (the cloud voice increment above is the recorded exception), protect original and translated PII before external calls/traces, and evaluate injection checks in both languages. English classifier performance does not establish Mandarin protection.
- Evaluate operational-field accuracy, unsafe automatic actions, unnecessary reviews, explanation faithfulness, worker correction/review effort and median/p95 latency. Use independent bilingual review and unseen speakers; do not relabel existing English golden-set scores as multilingual results.

The research defines a phased workflow and a proposed test suite; it contains no measured Singlish or voice result, and translation is measured only on the 12 made-up messages above. These extensions remain deferred under the current product priorities.

## 6. Implementation sequence and presentation scope

The immediate priorities remain known correctness gaps, integrated workflow verification and the required final evaluation. Plan the extensions in bounded increments:

1. Specify operational permissions, closure/calendar rules and measurable acceptance criteria. The first PII scope, names of people and addresses, was set on 29 October 2026.
2. Prepare the sanitized cost evidence from existing records without a new model run. The in-app usage view is implemented; the public bundle remains.
3. Add and verify local PII filtering for names and addresses, preserving interpretation and source-evidence behavior. Basic injection checks follow later; evaluate an encoder only if the measured benefit justifies it.
4. Prototype workshop availability and operational data changes in the experiment notebook workflow before integrating a shared store and workshop interface. Validate equivalent snapshots before introducing live updates or bookings.
5. Use the multilingual research to scope bilingual review with the original kept beside the existing local translation, then local dictation in place of the current cloud transcription. Verify original evidence, language-aware guards and outbound privacy before enabling Chinese automatic processing; evaluate Singlish separately.
6. Address operational transactions, concurrency and permissions before live use. Containerization and deployment remain the final phase.

For the final presentation, the in-app usage view, cloud voice input and local translation can be shown as implemented, with their limits: cost figures are estimates from a stored price table, voice sends audio to OpenAI and is unmeasured on real speech, and translation keeps only the English and checks only order and workshop IDs. Describe these as future improvements: workshop-maintained availability in a shared operational store, local privacy filtering, injection checks, a public cost evidence bundle and Chinese-English communication with local dictation. Do not imply that PostgreSQL, a workshop portal, PII redaction, an injection classifier, evaluated multilingual support, bilingual review, local speech recognition or live production bookings are already implemented.

## Technical references

- [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html): possible additional enforcement for workshop-specific data access; policies and application identity still require configuration.
- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html): concurrency behavior to consider for consistent reads and future reservations.
- [Presidio](https://presidio.dataprivacystack.org/): local PII recognition/anonymization options and detection limitations.
- [OWASP prompt-injection guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html): layered defenses, encoding attacks and evaluation boundaries.
- [Aho-Corasick implementation documentation](https://pyahocorasick.readthedocs.io/en/latest/): efficient matching of predefined strings.
- [Prompt Guard 2 22M model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M): local encoder-classifier candidate and its stated scope and limits.
