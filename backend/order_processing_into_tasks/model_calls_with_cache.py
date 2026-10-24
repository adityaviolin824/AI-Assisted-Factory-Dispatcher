# model_calls_with_cache.py: every request to the model goes through RecordedModel.
#
# Processing flow: extract_items, create_and_link_tasks and verify_tasks each call the model through a
#                  RecordedModel, as ask(stage, prompt, payload, response_format).
# Came from:       notebook 05, Section 4 (copied unchanged).
# Reads:           saved answers in CACHE_DIR; OPENAI_API_KEY, only when a request has no saved answer.
# Writes:          <run folder>/calls/<stage>-<key>.json for every request, and CACHE_DIR/<key>.json
#                  for every new answer that matches its response format.
#
# A request's key (fingerprint) covers the stage, the stage's model, the temperature (or, for a
# reasoning model, its reasoning effort), the prompt, the payload and the response format. The same
# key means the same request, so its saved answer is reused with no API call. An answer is only a
# proposal: the calling step still checks it.


import json
import os
import time

from pydantic import BaseModel, ConfigDict, ValidationError

from order_processing_into_tasks.model_prompts import INTAKE_PROMPT, LINK_PROMPT, VERIFY_PROMPT
from order_processing_into_tasks.settings_and_data import (
    CACHE_DIR, MAX_PAYLOAD_CHARS, REASONING_EFFORTS, STAGE_MODELS, TEMPERATURE, digest, write_json)


# Raised for an input or a model answer that cannot be trusted. The step that catches it saves a
# review record and continues. Any other error (API, file, programming) stops the run.
class ReviewRequired(ValueError):
    """The input or model answer needs review before it can be used."""


# The base of every response format the model must follow (extract_items, create_and_link_tasks,
# verify_tasks). extra="forbid" rejects any field we did not define, so the model cannot add fields.
# No docstring here or in any response format: a docstring is part of the JSON schema, and so of
# every request's key, so adding one would stop every saved answer from matching.
class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def make_chat_model(model_name, sampling):
    """Create the OpenAI chat client for model_name; called only for a request with no saved answer.

    sampling is the request's {"temperature": ...}, or {"reasoning_effort": ...} for a reasoning
    model: GPT-5 reasoning models accept no temperature but their default, so none is sent.
    A fully cached run never creates a client, so it needs no API key and costs nothing. One attempt
    per request (max_retries=0) and a 60-second timeout, so failures show directly. cache=False turns
    off LangChain's own cache, because RecordedModel handles reuse. The key is never printed.
    """
    from langchain_openai import ChatOpenAI

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured; no credential value was displayed.")
    return ChatOpenAI(model=model_name, **sampling, max_retries=0,
                      timeout=60, base_url="https://api.openai.com/v1",
                      use_responses_api=False, cache=False)


class RecordedModel:
    """Send model requests, save each one in the run folder and reuse saved answers.

    Each processing run creates one and passes it to every step as ask(stage, prompt, payload, schema).
    The same request always gets the same answer, so a rerun costs nothing, and every answer can be
    inspected after the run.
    """

    # Store this run's folder and prompts. The API clients are created later, and only if needed.
    def __init__(self, run_dir):
        self.run_dir = run_dir
        self.prompts = {"intake": INTAKE_PROMPT, "link": LINK_PROMPT, "verify": VERIFY_PROMPT}
        self.clients = {}  # stage -> API client, created at the stage's first request with no saved answer
        self.last_trace_file = None
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "calls").mkdir(exist_ok=True)

    # Send one request for a stage ("intake", "link" or "verify") and return the parsed answer.
    # schema is the response format (a StrictModel class, such as IntakeBatch). The answer is only
    # a proposal: the calling stage still runs its own checks on it.
    def __call__(self, stage, prompt, payload, schema):
        # 1. Safety checks: the prompt must be the one stored for this run, and the payload
        #    must fit within MAX_PAYLOAD_CHARS.
        self.last_trace_file = None
        if prompt != self.prompts[stage]:
            raise ValueError("A prompt changed during the run; start a new recorded run.")
        if len(json.dumps(payload)) > MAX_PAYLOAD_CHARS:
            raise ReviewRequired("Payload exceeds the bounded context limit; review the complete input.")
        # 2. Fingerprint the full request (stage, the stage's model, temperature or reasoning effort,
        #    prompt, payload, schema). The same fingerprint means the same request, so a saved answer
        #    can be reused. A stage given another model or effort gets new fingerprints, so it never
        #    reuses an answer of the old setting. A stage with no reasoning effort sends the
        #    temperature as before, so its requests and saved answers are unchanged.
        model_name = STAGE_MODELS[stage]
        effort = REASONING_EFFORTS.get(stage)
        sampling = {"reasoning_effort": effort} if effort else {"temperature": TEMPERATURE}
        request = {"stage": stage, "model": model_name, **sampling,
                   "prompt": prompt, "payload": payload, "schema": schema.model_json_schema()}
        key = digest(request)
        cached = self.cache_dir / f"{key}.json"
        trace_file = self.run_dir / "calls" / f"{stage}-{key[:16]}.json"
        self.last_trace_file = str(trace_file)
        # A saved answer exists: record the reuse in this run and return it. No API call.
        if cached.exists():
            record = json.loads(cached.read_text(encoding="utf-8"))
            write_json(trace_file, {**record, "reused_response": True})
            print(f"[Model: {stage}] reused a saved answer; no API call ({trace_file.name})")
            try:
                return schema.model_validate(record["parsed"])
            except ValidationError:
                raise ReviewRequired("The saved model answer does not match the required response format.") from None
        # 3. No saved answer: create this stage's client if needed. Save the request before
        #    sending it, so even a failed call leaves a record.
        if stage not in self.clients:
            self.clients[stage] = make_chat_model(model_name, sampling)
        record = {"request": request, "request_hash": key}
        write_json(trace_file, record)
        print(f"[Model: {stage}] API request sent: {len(json.dumps(payload))} payload characters to {model_name}")
        started = time.monotonic()
        # 4. One call that must return JSON matching the schema (strict structured output).
        #    On failure, save only the error type and status code, then stop the run.
        #    "from None" keeps the raw error details out of the printed output.
        try:
            response = self.clients[stage].with_structured_output(
                schema, method="json_schema", strict=True, include_raw=True
            ).invoke([("system", prompt), ("human", json.dumps(payload, ensure_ascii=False))])
        except Exception as error:
            record.update(error_type=type(error).__name__, status_code=getattr(error, "status_code", None))
            write_json(trace_file, record)
            print(f"[Model: {stage}] stopped with {type(error).__name__}; see {trace_file}")
            raise RuntimeError(f"API request failed ({type(error).__name__}); inspect its saved trace.") from None
        # 5. Save the raw answer, response ID, metadata, token usage and time taken.
        raw = response["raw"]
        record.update(raw_content=raw.content, response_id=raw.id,
                      metadata=raw.response_metadata, usage=raw.usage_metadata,
                      elapsed_seconds=round(time.monotonic() - started, 3),
                      parsed=response["parsed"].model_dump() if response["parsed"] is not None else None)
        write_json(trace_file, record)
        print(f"[Model: {stage}] returned in {record['elapsed_seconds']} s; tokens: {record['usage']}")
        # An unreadable answer: the calling stage sends it to review.
        if response["parsing_error"] is not None or response["parsed"] is None:
            raise ReviewRequired("The model did not return a valid structured result; inspect its saved response.")
        # 6. Add the answer to the shared cache. It matches the response format; the stage's checks
        #    run next. An answer that later fails a check stays cached, so a rerun reaches the same
        #    review without paying again.
        write_json(cached, record)
        return response["parsed"]
