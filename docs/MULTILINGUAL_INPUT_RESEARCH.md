# Chinese, bilingual review and voice input research

Research date: 29 October 2026. Status: proposed extension; no model installation, inference experiment or application implementation has been performed for this research. Later on 29 October, a separate cloud dictation increment was implemented; see [Implemented cloud dictation](#implemented-cloud-dictation-29-october-2026). On 30 October, local Chinese-to-English translation at Send was implemented with this research's first translation candidate; see [Implemented local translation](#implemented-local-translation-30-october-2026). The other local recommendations below are unchanged and unmeasured.

## Recommendation and product purpose

Support workers who can describe production requirements more accurately in Chinese than in English. Start with typed Chinese and English, an optional translation beside the original message, and bilingual clarification/review information. Add short, editable voice dictation after the text path is verified. Treat Singlish and Mandarin-English code-switching as explicitly tested experimental capabilities until their results justify a stronger claim.

The extension should improve the facts used to decide whether a workshop can make a batch, can take it given capacity and queue, and is allowed to take it. It must preserve Python's scheduling authority and the dispatcher's final decision. A fluent translation alone does not establish any of these three checks.

The initial model shortlist is:

- **Text translation:** evaluate Tencent Hy-MT2-1.8B first, with TranslateGemma-4B as a comparison. Use translation for comprehension and bilingual display; do not silently replace the source conversation.
- **Voice:** evaluate Qwen3-ASR-0.6B first and compare its 1.7B variant if operational-field accuracy is inadequate. Compare a regional candidate when Singapore speech is a measured weakness.
- **Regional comparisons:** Polyglot-Lion-1.7B-v1.5 is a compact Singapore-language candidate; MERaLiON-3-3B-ASR has more explicit published evidence for local code-switching and Singlish, with a heavier documented serving path.
- **Interpretation:** compare the existing interpreter reading the original language directly against interpretation assisted by a local translation. Prefer direct source interpretation if it meets the frozen Chinese accuracy criteria; the translation can remain a display aid. Do not assume that another generative stage improves correctness.

These are candidates for measurement, not selected production dependencies or claims of performance on this project. Primary sources and restrictions appear below.

## Scope and terms

| Capability | Initial scope | Important distinction |
|---|---|---|
| Typed input | English and Mandarin written in simplified Chinese; retain Latin order/workshop identifiers. | Check traditional Chinese separately before claiming script coverage. |
| Translation | Chinese to English and English to Chinese for messages and supported free-text explanations. | Translation changes language; it does not allocate work or resolve an ambiguous deadline. |
| Voice dictation | One worker records a short request, inspects the transcript and edits it before sending. | ASR transcribes speech; speaker identification and voice authorization are separate problems. |
| Singapore English | Include local pronunciation in the voice evaluation. | Accent recognition does not establish understanding of Singlish grammar or implied intent. |
| Singlish | Test task meaning in typed and spoken examples, including particles, ellipsis and local expressions. | Avoid mechanically removing words such as "lah" when context could matter. |
| Code-switching | Mandarin and English within a sentence or conversation. | Separate monolingual accuracy from mixed-language accuracy. |
| Other dialects/languages | Record failures and allow manual text correction. | A model's language list is not a commitment to support every dialect in the application. |

Use a language preference with an override for display and clarification. Do not force a mixed utterance into English-only recognition merely because the application UI is English. Language detection is a hint, not proof of meaning or authority.

## Speech recognition candidates

Published results below belong to the model authors. Their datasets, quantization and hardware differ; no table position is a project benchmark ranking.

| Model | Evidence and license recorded at research time | Proposed role and limitation |
|---|---|---|
| **Qwen3-ASR-0.6B / 1.7B** | Apache 2.0. The publisher documents 30 languages and 22 Chinese dialects, with offline and streaming inference. [Model card](https://huggingface.co/Qwen/Qwen3-ASR-0.6B), [official runtime](https://github.com/QwenLM/Qwen3-ASR). | First general bilingual ASR comparison. Start with the smaller variant; measure identifiers, negation and deadlines before increasing size. Published batched throughput does not establish single-request Mac latency. |
| **Polyglot-Lion-1.7B-v1.5** | MIT. Qwen3-ASR fine-tune for English, Mandarin, Tamil and Malay using public corpora. The v1.5 card records retraining without punctuation removal. [Publisher card](https://huggingface.co/knoveleng/polyglot-lion-1.7b-v1.5), [paper](https://arxiv.org/abs/2603.16184). | Regional challenger if Singapore pronunciation is weak. Its four-language results do not alone establish conversational code-switching quality. Published NVIDIA timing is not an Apple Silicon result. Verify the exact checkpoint; examples on the card can reference an earlier revision. |
| **MERaLiON-3-3B-ASR** | A*STAR I2R model with a custom MERaLiON public license. Its card explicitly discusses Singlish and natural English mixed with Mandarin and other regional languages. It distinguishes open weights from a hosted API. [Publisher card](https://huggingface.co/MERaLiON/MERaLiON-3-3B-ASR). | Strong regional comparison for mixed speech. The card documents self-hosting on one 80 GB GPU; that is an example, not an established minimum. Apple deployment is unverified here. Do not attribute the hosted API's quality or latency to the open model. |
| **Whisper large-v3-turbo** | Approximately 809M parameters; MIT, multilingual ASR. The model card warns of hallucinations and uneven language/accent performance. [Publisher card](https://huggingface.co/openai/whisper-large-v3-turbo). | Familiar independent ASR baseline. Use original-language transcription for source evidence; benchmark translation separately. General multilingual support does not prove local factory vocabulary accuracy. |
| **NVIDIA Parakeet-TDT-0.6B-v3** | Approximately 600M parameters; CC BY 4.0. The published language list covers 25 European languages and excludes Mandarin. [Publisher card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3). | Possible English-only comparison. It cannot be the sole recognizer for this bilingual requirement. |

For this arm64 Mac, [MLX-Audio](https://github.com/Blaizzy/mlx-audio) documents Apple Silicon inference and community MLX conversions of Qwen3-ASR, Whisper and Parakeet. This makes Qwen a practical first trial, not a verified installation plan. A derivative that shares the Qwen architecture still needs conversion/runtime compatibility checks; compatibility must not be assumed for Polyglot-Lion or MERaLiON.

## Translation and interpretation candidates

| Model or option | Evidence and license recorded at research time | Decision for this project |
|---|---|---|
| **Tencent Hy-MT2-1.8B** | Apache 2.0; specialized translation family covering 33 languages. The publisher supplies terminology/context instructions and official GGUF variants. Released 21 May 2026, after HY-MT1.5. [Model card](https://huggingface.co/tencent/Hy-MT2-1.8B), [official GGUF](https://huggingface.co/tencent/Hy-MT2-1.8B-GGUF). | First local MT candidate: compact, bilingual terminology support and a documented local format. Begin with a moderate quantization; very small advertised storage sizes are not peak RAM requirements or proof of preserved operational facts. |
| **Google TranslateGemma-4B** | Dedicated translation across 55 languages; Gemma terms and access acceptance apply. Its card specifies a 2K-token input limit and a special source/target-language template, without a system role. [Model card](https://huggingface.co/google/translategemma-4b-it), [Google introduction](https://blog.google/innovation-and-ai/technology/developers-tools/translategemma/). | Comparison if the first candidate loses meaning or constraints. Translate bounded messages/segments; do not assume the base model's larger context or an ordinary chat prompt applies. |
| **MADLAD-400-3B-MT** | Apache 2.0; T5-based text translation across 400+ languages. The card flags general-domain training and unassessed production use; the published conversion/card has separate contributor provenance. [Model card](https://huggingface.co/google/madlad400-3b-mt), [original paper](https://arxiv.org/abs/2309.04662). | Optional older multilingual baseline. Additional language breadth is less valuable here than fact preservation. Its encoder-decoder runtime differs from a causal chat model. |
| **NLLB-200-distilled-600M** | CC BY-NC 4.0. The card calls it a research model, excludes production deployment, and warns about inputs beyond its 512-token training lengths. [Model card](https://huggingface.co/facebook/nllb-200-distilled-600M). | Small research comparison only; do not choose it as the product default or infer commercial suitability from downloadable weights. |
| **Gemma-SEA-LION-v4.5-E2B-IT** | AI Singapore regional instruction model, MIT per card; 2.3B effective parameters and 5.1B including embeddings. The card lists SEA adaptation, general/translation evaluation and adversarial robustness limits. [Model card](https://huggingface.co/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT). | Optional regional meaning comparison, not a dedicated translation or injection detector. The reviewed card does not establish this checkpoint's Singlish or Mandarin dispatch accuracy. "E2B" is not the full resident parameter count. |
| **Existing interpreter with original Chinese** | No new interpretation model is selected. Current extraction and verification contracts are documented in the [backend guide](backend/README.md). | Measure this path first against translation-assisted input. It can avoid an extra semantic conversion, but existing English-oriented validation must be extended and tested before Chinese processing is enabled. |
| **Tencent Hy-SimulMT-30B-A3B** | Released 26 October 2026 for bidirectional Chinese-English simultaneous speech translation; translated speech needs a configured TTS service. [Publisher card](https://huggingface.co/tencent/Hy-SimulMT-30B-A3B). | Defer. Continuous interpretation and speech output exceed editable dictation. A3B denotes active MoE capacity, not a model with only 3B total weights. |

Do not deploy every candidate. Start with one MT model and the existing interpreter; add the ASR pair later. Recheck current licenses, templates, revisions and library APIs when implementation starts. Downloads, custom model code and local services require a deliberate project-local setup step; none is authorized by this document alone.

## Recommended workflow

### 1. Establish the bilingual text path

1. The worker types in the language they understand. Preserve the original text, sender, message order, timestamp and source ID. A translation must be labeled as machine-generated and associated with that original message.
2. Local protection prepares the processing view before external interpretation or tracing: supported PII aliases, integrity checks for operational identifiers, and injection screening. The restricted original remains available to the dispatcher. An original local message and a redacted processing snapshot are distinct records.
3. Generate an optional local translation with a small, reviewed manufacturing glossary and bounded conversation context. Keep order IDs, workshop IDs and other protected tokens unchanged; validate their counts and correspondence. Dates and quantities expressed in Chinese need an explicit supported normalization policy rather than unrestricted rewriting.
4. Interpret the original processing text, with translation as optional derived context. Compare this against the direct bilingual baseline during evaluation. Preserve source references for each original segment; translated words must never be presented as exact quotations from a Chinese source.
5. Validate the extracted facts against trusted records and the source. The worker can correct their message; quantity overrides and final allocation authority remain with the dispatcher under the existing contract. Missing or conflicting facts remain visible for clarification.
6. Python performs the existing eligibility, capacity, queue, date, cost and ranking calculations. No translator computes a new delivery date or overrides workshop status.
7. Show the dispatcher the original, translation, structured request and calculated explanation. Provide supported clarification and warning text in the user's chosen language. Existing explicit processing, preview, approval and Review again remain separate actions.

The bilingual interface should use human-reviewed labels and deterministic templates for stable warnings/reasons, dates, quantities and costs. Translate free-form explanations on demand and cache them by source/version/language. Translating the input while leaving every clarification in English would not fully serve the intended worker.

### 2. Add short voice dictation

Use a push-to-talk interaction for one request at a time. A local recognizer creates an editable transcript in the spoken language. Show it before **Send**, preserve meaningful corrections, and make text entry a fallback. Sending still saves a message; it must not automatically trigger processing, approve a plan or commit an assignment.

Ask the speaker to verify key facts in a language they understand. A Chinese-speaking worker should not need English fluency to approve an English rendering. Speaking an order ID must not silently select a nearby valid ID: uncertain digits need correction or explicit confirmation.

The current chat sender is a display name, not an authenticated identity. Neither an ASR label nor the sound of a voice grants dispatcher/workshop permissions. Multi-speaker recordings, diarization, wake words, live interpretation and speech synthesis remain outside the first increment.

Keep recordings local to the chosen deployment, with a defined consent, access and retention policy. "Local" means on that application's host; on a later remote deployment, audio would travel to that host. Avoid browser speech services with unspecified remote processing. Do not send recordings to an external provider by default.

### 3. Preserve meaning across the whole pipeline

The current verification code contains English-oriented cancellation, date and quantity checks. Translation cannot be inserted ahead of it and treated as proof that equivalent checks now exist in Chinese.

- Check possible cancellation/hold language in the original and derived view. A translation that drops a cancellation must not enable automatic readiness. As today, a possible cancellation requests review; only the dispatcher's explicit action cancels work.
- Distinguish cancelling an order from excluding a workshop. Handle negation, correction and supersession at the correct message/order scope. A signature may trigger clarification without establishing the final intent.
- Normalize only explicitly supported numbers/date expressions using the run's declared reference date and calendar. Do not invent a day for "next week" or silently resolve ambiguous "next Saturday" wording.
- Treat workshop names, product categories and manufacturing terms as controlled vocabulary. A short bilingual glossary can include workshop/车间, rework/返工 and hold/暂停, with terms reviewed for the actual operational context.
- Preserve the supported subset of original-language evidence in exact-source validation. If translations are retained as separate evidence, give them derived identities and an explicit validation contract; do not relabel them as source quotations.
- A successful identifier or number check does not prove that negation, intent or follow-up ownership survived. These need separate examples and bilingual review.

These synthetic examples illustrate proposed checks; they are not a reviewed test dataset or model results:

| Input | Required treatment |
|---|---|
| `ORD-045，150件，不要用W7。` | Retain the order, quantity and W7 exclusion; no inferred cancellation. |
| `ORD-045 暂停安排，等我确认。` | Possible hold blocks automatic readiness pending review. |
| `ORD-045 不要取消，照原计划。` | Do not silently cancel; preserve the negation and relevant earlier context. A conservative guard may still ask for review. |
| `ORD-045 next Saturday 要到，不是这个 Saturday。` | Keep the correction and distinguish delivery from dispatch; resolve or clarify the relative date under the declared reference date. |
| `W7 cannot lah, use W6 for ORD-045.` | Preserve the exclusion and requested destination, subject to normal automatic checks and dispatcher authority. |
| `Can make it or not?` | A question needing context; do not manufacture an allocation request or a workshop commitment. |

## Privacy and injection checks

The [local protection roadmap](FURTHER_IMPLEMENTATION.md#2-local-pii-filtering) still applies. Extend its scope explicitly for Chinese text and mixed-language messages:

- Cover original text, translations, transcripts, structured fields, errors, graph state and external traces. Test whether a translation expands or restores a masked value; preserve stable aliases and protect the mapping locally.
- English entity recognition is insufficient evidence for Chinese names/addresses. Presidio's default models/recognizers are English; additional languages require NLP and recognizer/context configuration. [Presidio multilingual documentation](https://github.com/data-privacy-stack/presidio/blob/main/docs/analyzer/languages.md).
- Screen normalized copies of both original input and translated text for task/role overrides; preserve the originals. A translation can carry, hide or paraphrase an injection. Source text and glossary/context remain untrusted data, and model output remains untrusted until validated.
- Start with explicit English/Chinese attack signatures and benign correction cases. Do not flag ordinary words such as "ignore", "cancel" or "不要" by themselves as proof of injection. Aho-Corasick only accelerates fixed phrase matching.
- Prompt Guard 2 22M remains an optional local English-focused classifier, not established Mandarin protection. Meta describes the 86M variant as trained on non-English attacks and a 512-token context; multilingual branding does not establish Chinese coverage. Compare both false positives and misses on the project's languages before adoption. [Meta documentation](https://dev.meta.ai/llama/docs/model-cards-and-prompt-formats/prompt-guard).
- Classification is separate from ASR, translation and PII recognition. Adding a recent guard model does not establish protection or justify sending raw personal information to another external service.

Flagged material must remain visible and attributable, including updates that could affect an existing order. No detector should silently delete evidence or authorize an otherwise forbidden automatic destination. Measure any protection claim on the actual bilingual workflow.

## Local execution, latency and cost

The host architecture was confirmed as arm64; available RAM and model fit were not established. There is no measured local latency, memory footprint or translation quality from this research.

For a future trial, use a verified MLX-Audio conversion for ASR. For MT, Tencent's official GGUF is a candidate for a project-local runtime; [llama.cpp](https://github.com/ggml-org/llama.cpp) documents Apple Silicon acceleration through Metal/Accelerate. Model-format availability and general runtime support do not prove that a specific revision, template and quantization work together.

Load the selected models once, bound recording/message lengths, and measure cold startup separately from warm requests. Preserve complete clauses when segmenting text; splitting around a negation or dropping an earlier correction can change the request. Version any segment overlap/deduplication policy.

Record model revision, weight format, quantization, runtime version, decoding settings, glossary version and protection policy. Include those identities in derived-output/cache keys. Test a moderate quantization against the reference before adopting more aggressive compression. Do not assume deterministic decoding means every environment produces identical output.

Report median and p95 ASR time, translation time, existing interpretation time, total completion time, peak memory and concurrency. Separate automatic processing latency from worker correction/review time. Local inference can remove per-call API charges for ASR/MT but still consumes hardware, memory, energy and maintenance effort. Existing external interpretation calls remain billable; bilingual context may increase tokens. The historic $0.0757 experiment does not price this proposed workflow.

## Evaluation before claiming support

### Proposed development and held-out material

Build a small bilingual task suite before selecting the final model. A starting scope is 60 typed conversation cases and 60 distinct short audio utterances, with declared coverage across English, Mandarin, Mandarin-English mixtures and Singlish. These are proposed counts, not completed evaluation. Agree latency/review budgets and supported language claims before testing.

Use bilingual human reviewers for independent source meaning and translation checks. Author a development subset and a separate frozen unseen subset; keep audio speakers separated between them. Do not tune on the unseen split or create every Chinese reference by translating the existing English answer key with the model being assessed. Use real consented speakers for accent/noise/code-switch checks; synthetic speech is supplementary.

Cover identifiers spoken as letters/digits, workshop names, Chinese numerals, exact/relative dates, delivery versus dispatch, corrections, cancellation/hold/negation, exclusions, multiple orders, task/follow-up/question distinctions, fillers, background noise, silence, supported PII, injection attempts and legitimate instructions that resemble attacks. Preserve message ownership and ordering.

### Comparisons and measures

| Question | Proposed measurement |
|---|---|
| Does translation help interpretation? | Same frozen inputs and planner: original-language interpretation versus local translation-assisted interpretation. Score operational fields and final decisions, with costs/latency reported separately. |
| What is lost through voice? | Compare the same intended request as reviewed source text, unedited ASR text and worker-corrected text. Report corrections and downstream errors for each path. |
| Are the words accurate? | English WER, Mandarin CER and an explicitly defined mixed error rate/tokenization for code-switching. Record simplified/traditional normalization; do not let normalization hide a wrong number. |
| Are dispatch facts preserved? | Exact order/workshop IDs; quantities and date values under declared rules; preferences, exclusions, negation, cancellation state and follow-up ownership. Score misses separately from unsupported additions. |
| Is the translation faithful? | Bilingual human judgments for omissions, additions, wrong referents, wrong intent and readability. A high general MT score or a model judge alone is insufficient. |
| Does the application remain useful? | Automatic correct coverage, unsafe automatic recommendations, unnecessary reviews, time to enter/correct/review, and explanation faithfulness. A system sending everything to review is not equivalent to useful automation. |
| Is it practical locally? | Cold/warm median/p95 latency, memory, concurrency and full pipeline cost under recorded hardware/settings. |
| Do protections work? | PII misses/unnecessary masking and injection misses/false positives in each language, including effects on source validation and coverage. |

Acceptance should require that critical supported identifiers, quantities, dates and exclusions either remain correct or visibly block automatic action on the acceptance suite. A known critical mistranslation must be fixed or routed to review before enabling that case. Passing a finite suite is not a guarantee for all future messages. Freeze numeric targets and the sample/review protocol before the comparison rather than choosing them after results are known.

The unchanged 120-order scheduler replay, existing 100-case results and required 30-request evaluation remain distinct. Report new multilingual tests as a separate versioned dataset. Translation does not by itself demonstrate a better scheduling policy.

### Useful regional evaluation references

- [AudioBench](https://github.com/AudioLLMs/AudioBench) lists English-Chinese SEAME subsets and Singapore speech tasks. Check each underlying dataset's access, license and redistribution terms before use; an evaluation repository license does not license all recordings.
- [SEA-HELM Audio, published 23 October 2026](https://sea-lion.ai/blog/introducing-sea-helm-audio-measuring-the-speech-gap-in-southeast-asian-voice-agents/) compares text and spoken versions using task-level checks, including Chinese. Its first release uses synthetic speech and explicitly lacks real accent/noise/code-switching coverage. Adapt the paired text/audio method; do not use its scores as proof of this project's Singlish support.
- MERaLiON's model card separates API/open-model results and describes a regional code-switch benchmark. Check access to each constituent dataset before claiming the complete benchmark can be reproduced publicly.

## Implemented cloud dictation, 29 October 2026

An approved increment added short editable dictation ahead of the sequence below, using a cloud recognizer instead of a local one. The Chat page's **Record** button records one request (up to one minute) and sends it to `POST /chat/transcriptions`. The backend passes it to OpenAI's `gpt-transcribe` with English and Mandarin language hints and workshop/product names as keywords, and returns only the text.

It follows this research's dictation rules: push-to-talk for one request, an editable transcript in the spoken language before **Send**, text entry as the fallback, and no automatic sending, processing or approval. The sender name remains a display label.

It departs from the local-execution recommendation. The recording leaves the host for OpenAI, contrary to "do not send recordings to an external provider by default". The route is therefore off unless the API runs with `ALLOW_PAID_PROCESSING=1`, the same switch as processing, and neither recording nor transcript is stored. Spoken names or addresses reach the provider before any text PII filter could act.

English is the supported language. A transcript containing Chinese characters is marked experimental in the interface, because the cancellation, date and quantity checks still read English only. Accuracy, latency and cost on real speech, Singapore English pronunciation, Singlish and code-switching are unmeasured. OpenAI listed $0.0045 per minute of audio when checked on 29 October 2026. A local recognizer such as Qwen3-ASR remains the recommended replacement behind the same editable flow. The [system design](docs/system-design.md#voice-input-decision-29-october-2026) records the decision and alternatives.

## Implemented local translation, 30 October 2026

The first translation candidate above, Tencent Hy-MT2-1.8B, now runs on the host through `mlx-lm`, converted to 8 bits from the official weights. When `[translation]` in `backend/config.toml` is on, **Send** translates a message containing Chinese characters into English and saves the English, so intake, processing and the English-oriented checks read English. The worker reads the Chinese in the message box before **Send**. A translation that loses, changes or adds an `ORD-` or `W` identifier is refused, and nothing is saved. No message leaves the host and there is no per-message charge.

It follows this research in running locally, keeping identifiers protected and leaving Python's scheduling authority unchanged. It departs from it in two ways. The translation replaces the original instead of appearing beside it, contrary to "do not silently replace the source conversation", so exact-source evidence and the dispatcher's view are English only. And processing always reads the translation; direct Chinese interpretation was not compared.

Measured on an M2 Pro with 16 GB, with 12 made-up messages including four of the examples above (not the proposed test suite): about 2.6 s for the first Chinese Send after start-up, then a median 0.27 s, and 2.2 GB peak memory. The 8-bit model matched the unquantized one word for word on 11 of 12 messages; a 4-bit conversion matched 4. Two observations bear on the guards above. 换别的车间 became "has been transferred to another workshop", turning an instruction into a statement. 暂停 became "Suspended", which the existing cancellation check does not recognize; it has no hold or suspend pattern in English either. Quantities, dates, negation and intent are not validated after translation. The [system design](docs/system-design.md#local-translation-decision-30-october-2026) records the decision and alternatives.

## Implementation touchpoints and sequence

These are existing integration boundaries to review, not files changed by this research:

| Existing location | Future work to design and verify |
|---|---|
| [Chat composer](frontend/components/Composer.tsx) | Language preference and a labeled translation beside the original (Send currently saves only the English). Editable dictation exists through the cloud increment; a local recognizer would replace the backend call, not this flow. Retain the save-versus-process boundary and retry behavior. |
| [Chat API](backend/fastapi_routes/chat.py) | Explicit original/derived provenance and snapshot representation; Send now calls `order_intake_from_chat/translate_message.py`. The audio boundary is `POST /chat/transcriptions` (5 MB maximum, paid-call switch, nothing stored). |
| [Extraction](backend/order_processing_into_tasks/extract_items.py) and [prompts](backend/order_processing_into_tasks/model_prompts.py) | Multilingual original evidence, derived context, correct ownership and exact quotation semantics. |
| [Task verification](backend/order_processing_into_tasks/verify_tasks.py) | Supported Chinese date/quantity expressions, cancellation/negation/exclusion checks and trusted-record reconciliation. |
| [Pipeline graph](backend/app_full_pipeline/pipeline_graph.py) | Redacted state before tracing, language/model/policy versions and reproducible derived-output reuse. |
| [Frontend guide](frontend/README.md) and [backend guide](backend/README.md) | Document the selected subset only after implementation and measurement. |

Suggested increments, after the core correctness and required evaluation priorities:

1. Freeze supported language/script scope, bilingual fixtures, source/derived schema and evaluation criteria. Compare direct interpretation and local MT with separately authorized inference.
2. Implement typed bilingual input/display, reviewed static labels and language-aware guards. Verify exact-source links and outbound privacy before enabling automatic processing of Chinese.
3. Replace the cloud transcription call with one local ASR model behind the existing editable dictation. Compare original/recognized/corrected task outcomes, fallback and latency, using the cloud results as a reference once they are measured.
4. Compare regional ASR only where local speech tests show a meaningful weakness. Keep Singlish experimental until the acceptance set and unseen speakers support a stronger claim.
5. Consider other languages, dialects or continuous speech only if user evidence justifies them. Containerization and deployment remain last.

## Current status, 31 October 2026

Multilingual expansion is deferred under the current [product priorities](docs/project-plan.md). The local translation implementation is retained but disabled by default, and its MLX runtime is an optional dependency extra. The research above does not establish bilingual review, local voice recognition or measured Singlish/code-switching support.
