"""Notebooks 05 and 06 as the reference for the module tests. The notebook files are only read, never written.

load_notebook_05 runs notebook 05's definitions cells in a temporary folder and blocks every API call.
load_notebook_06_part_8 runs notebook 06's dispatcher calculation and decision helpers for one run folder.
"""
import ast
import contextlib
import io
import json
import os
import shutil
import sys
import types
from datetime import date
from pathlib import Path

from order_processing_into_tasks.verify_tasks import possibly_affected_tasks

# Notebook 05 loads backend/.env with override=False, so these empty values win: the tests never
# see the API key, and nothing is sent to LangSmith.
os.environ["OPENAI_API_KEY"] = ""
os.environ["LANGSMITH_TRACING"] = "false"

BACKEND_DIR = Path(__file__).resolve().parents[1]
NOTEBOOK_05 = BACKEND_DIR / "experimentation_notebooks/05-order-pipeline-mvp.ipynb"
NOTEBOOK_06 = BACKEND_DIR / "experimentation_notebooks/06-dispatcher-workflow.ipynb"
# The 23 saved model answers of notebook 05. The tests copy them; they never write here.
SAVED_ANSWERS = BACKEND_DIR / "experimentation_notebooks/output/order-pipeline-mvp/response-cache"
CHAT_FILE = BACKEND_DIR / "data/dispatch_requests.txt"


class CacheMiss(RuntimeError):
    """A model request had no saved answer, so a real run would have paid for an API call."""


def refuse_api_call(model_name, sampling=None):
    """Stand-in for make_chat_model: stop instead of creating an API client.

    Notebook 05 passes only the model; the modules also pass the request's temperature or effort.
    """
    raise CacheMiss(f"cache miss: no API call was made (model {model_name})")


def definitions_source():
    """Return the source of notebook 05's "definitions" cells, joined in notebook order."""
    cells = json.loads(NOTEBOOK_05.read_text(encoding="utf-8"))["cells"]
    return "\n\n".join("".join(cell["source"]) for cell in cells
                       if cell["cell_type"] == "code"
                       and "definitions" in cell["metadata"].get("tags", []))


def notebook_prompt(name):
    """Return one of notebook 05's prompts, built by running only the statements that assign it."""
    namespace = {}
    for node in ast.parse(definitions_source()).body:
        target = node.targets[0] if isinstance(node, ast.Assign) else getattr(node, "target", None)
        if isinstance(target, ast.Name) and target.id == name:
            exec(compile(ast.Module([node], []), str(NOTEBOOK_05), "exec"), namespace)
    return namespace[name]


def top_level_definitions(source):
    """Return {name: AST node} for every top-level function, class and NAME = value in source."""
    definitions = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            definitions[node.name] = node
        elif (isinstance(node, ast.Assign) and len(node.targets) == 1
              and isinstance(node.targets[0], ast.Name)):
            definitions[node.targets[0].id] = node
    return definitions


def load_notebook_05(work_dir):
    """Run notebook 05's definitions cells in memory and return their namespace.

    The notebook's run folders and a copy of the saved answers are pointed at work_dir, and its
    model client is replaced by refuse_api_call, so nothing outside work_dir is written and nothing
    is paid for. Printed output is discarded.
    """
    source = definitions_source()
    shutil.copytree(SAVED_ANSWERS, work_dir / "response-cache")
    # A registered module, so dataclasses and pydantic can find the classes' module.
    module = types.ModuleType("notebook_05")
    sys.modules[module.__name__] = module
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(source, str(NOTEBOOK_05), "exec"), module.__dict__)
    module.RUNS_DIR = work_dir / "runs"
    module.CACHE_DIR = work_dir / "response-cache"
    module.make_chat_model = refuse_api_call
    return module.__dict__


def notebook_06_cell(prefix):
    """Return the source of notebook 06's one code cell that starts with prefix, such as "# Part 8a"."""
    cells = json.loads(NOTEBOOK_06.read_text(encoding="utf-8"))["cells"]
    (source,) = ["".join(cell["source"]) for cell in cells
                 if cell["cell_type"] == "code" and "".join(cell["source"]).startswith(prefix)]
    return source


def load_notebook_06_part_8(run_folder):
    """Run notebook 06's Parts 8a and 8b for one run folder and return their namespace.

    The two cells use names that the notebook's earlier cells define; they are set here as Parts 1 and
    2 set them. Part 8b loads the folder's dispatcher-decisions.json, if any. Nothing is written, and
    printed output is discarded.
    """
    namespace = {"contextlib": contextlib, "date": date, "io": io, "json": json,
                 "possibly_affected_tasks": possibly_affected_tasks, "RUN_NAME": run_folder.name,
                 "run_folder": run_folder,
                 "state": json.loads((run_folder / "state.json").read_text(encoding="utf-8"))}
    with contextlib.redirect_stdout(io.StringIO()):
        for prefix in ("# Part 8a", "# Part 8b"):
            exec(compile(notebook_06_cell(prefix), f"{NOTEBOOK_06.name} {prefix[2:]}", "exec"), namespace)
    return namespace
