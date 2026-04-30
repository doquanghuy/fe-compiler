"""Workflow-shape proof for ``fe-pipeline``.

Locks the compiler-owned workflow YAML against the mode-specific command
routing architecture. The ``screen_outline`` action step is a switch on
``{{ inputs.quality_mode }}`` with three cases dispatching to:

  fast   → speckit.axcore.step-run-fast
  review → speckit.axcore.step-run-review
  strict → speckit.axcore.step-run-strict

The deprecated monolithic ``speckit.axcore.step-run`` must not appear.
No command field may contain ``{{`` (no dynamic command interpolation).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "fe_compiler"
    / "workflows"
    / "fe_pipeline.yaml"
)

_MODE_COMMANDS = {
    "fast": "speckit.axcore.step-run-fast",
    "review": "speckit.axcore.step-run-review",
    "strict": "speckit.axcore.step-run-strict",
}


def _load_workflow() -> dict[str, Any]:
    raw = yaml.safe_load(_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), f"workflow YAML must be a mapping: {_WORKFLOW_PATH}"
    return raw


def _collect_all_commands(steps: list) -> list[dict]:
    cmds: list[dict] = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        if s.get("type") == "command":
            cmds.append(s)
        cases = s.get("cases")
        if isinstance(cases, dict):
            for nested in cases.values():
                if isinstance(nested, list):
                    cmds.extend(_collect_all_commands(nested))
        for nested_key in ("default", "steps", "then", "else"):
            nested = s.get(nested_key)
            if isinstance(nested, list):
                cmds.extend(_collect_all_commands(nested))
    return cmds


# --------------------------------------------------------------------------- #
# Basic workflow metadata
# --------------------------------------------------------------------------- #


def test_workflow_file_exists_at_committed_location() -> None:
    assert _WORKFLOW_PATH.is_file(), f"workflow YAML missing at {_WORKFLOW_PATH}"


def test_workflow_uses_spec_kit_schema_v1_0() -> None:
    data = _load_workflow()
    assert data.get("schema_version") == "1.0"


def test_workflow_identifies_as_fe_pipeline() -> None:
    data = _load_workflow()
    workflow = data.get("workflow")
    assert isinstance(workflow, dict)
    assert workflow.get("id") == "fe-pipeline"
    assert workflow.get("name")
    assert workflow.get("version")


# --------------------------------------------------------------------------- #
# Input declarations
# --------------------------------------------------------------------------- #


def test_workflow_declares_documented_inputs() -> None:
    data = _load_workflow()
    inputs = data.get("inputs", {})
    for key in (
        "workspace",
        "intent",
        "seed_path",
        "review_comments_path",
        "prior_run_id",
    ):
        assert key in inputs, f"workflow missing input {key!r}"
    assert inputs["intent"].get("enum") == ["auto", "improve", "rebuild"]


def test_workflow_declares_quality_mode_input() -> None:
    data = _load_workflow()
    inputs = data.get("inputs", {})
    assert "quality_mode" in inputs
    qm = inputs["quality_mode"]
    assert qm.get("default") == "fast"
    assert qm.get("enum") == ["fast", "review", "strict"]


def test_workflow_declares_max_quality_iterations() -> None:
    data = _load_workflow()
    inputs = data.get("inputs", {})
    assert "max_quality_iterations" in inputs
    assert inputs["max_quality_iterations"].get("default") == "2"


def test_workflow_declares_max_structural_iterations() -> None:
    data = _load_workflow()
    inputs = data.get("inputs", {})
    assert "max_structural_iterations" in inputs
    assert inputs["max_structural_iterations"].get("default") == "2"


# --------------------------------------------------------------------------- #
# screen_outline step routing
# --------------------------------------------------------------------------- #


def test_screen_outline_is_a_quality_mode_switch() -> None:
    data = _load_workflow()
    steps = [s for s in (data.get("steps") or []) if isinstance(s, dict)]
    step = next((s for s in steps if s.get("id") == "screen_outline"), None)
    assert step is not None, "screen_outline step must be declared"
    assert step.get("type") == "switch", (
        f"screen_outline must be type:switch (quality_mode router), got {step.get('type')!r}"
    )
    assert "quality_mode" in str(step.get("expression", "")), (
        "screen_outline switch expression must reference quality_mode"
    )


def test_screen_outline_switch_has_fast_review_strict_cases() -> None:
    data = _load_workflow()
    steps = [s for s in (data.get("steps") or []) if isinstance(s, dict)]
    step = next(s for s in steps if s.get("id") == "screen_outline")
    cases = step.get("cases", {})
    for mode in ("fast", "review", "strict"):
        assert mode in cases, f"screen_outline switch missing '{mode}' case"
        case_steps = cases[mode]
        assert isinstance(case_steps, list) and case_steps, (
            f"screen_outline '{mode}' case must be a non-empty list"
        )


def test_screen_outline_fast_uses_step_run_fast() -> None:
    data = _load_workflow()
    steps = [s for s in (data.get("steps") or []) if isinstance(s, dict)]
    step = next(s for s in steps if s.get("id") == "screen_outline")
    fast_cmd = step["cases"]["fast"][0]
    assert fast_cmd.get("type") == "command"
    assert fast_cmd.get("command") == "speckit.axcore.step-run-fast"
    assert fast_cmd.get("integration") == "claude"
    args = (fast_cmd.get("input") or {}).get("args", "")
    assert "plugin_id=fe" in args
    assert "step_id=screen_outline" in args
    assert "max_quality_iterations" not in args
    assert "max_structural_iterations" not in args
    assert "quality_mode" not in args


def test_screen_outline_review_uses_step_run_review() -> None:
    data = _load_workflow()
    steps = [s for s in (data.get("steps") or []) if isinstance(s, dict)]
    step = next(s for s in steps if s.get("id") == "screen_outline")
    review_cmd = step["cases"]["review"][0]
    assert review_cmd.get("command") == "speckit.axcore.step-run-review"
    args = (review_cmd.get("input") or {}).get("args", "")
    assert "plugin_id=fe" in args
    assert "step_id=screen_outline" in args
    assert "max_quality_iterations=" in args
    assert "max_structural_iterations" not in args
    assert "quality_mode" not in args


def test_screen_outline_strict_uses_step_run_strict() -> None:
    data = _load_workflow()
    steps = [s for s in (data.get("steps") or []) if isinstance(s, dict)]
    step = next(s for s in steps if s.get("id") == "screen_outline")
    strict_cmd = step["cases"]["strict"][0]
    assert strict_cmd.get("command") == "speckit.axcore.step-run-strict"
    args = (strict_cmd.get("input") or {}).get("args", "")
    assert "plugin_id=fe" in args
    assert "step_id=screen_outline" in args
    assert "max_quality_iterations=" in args
    assert "max_structural_iterations=" in args
    assert "quality_mode" not in args


# --------------------------------------------------------------------------- #
# Safety: no monolithic command, no dynamic interpolation
# --------------------------------------------------------------------------- #


def test_no_command_uses_monolithic_step_run() -> None:
    data = _load_workflow()
    all_cmds = _collect_all_commands(data.get("steps") or [])
    for cmd in all_cmds:
        assert cmd.get("command") != "speckit.axcore.step-run", (
            f"command step {cmd.get('id')!r} still uses deprecated monolithic command"
        )


def test_no_command_field_uses_template_interpolation() -> None:
    data = _load_workflow()
    all_cmds = _collect_all_commands(data.get("steps") or [])
    for cmd in all_cmds:
        assert "{{" not in str(cmd.get("command", "")), (
            f"command field in {cmd.get('id')!r} must not use template interpolation"
        )


# --------------------------------------------------------------------------- #
# Observability: workflow_id wiring
# --------------------------------------------------------------------------- #


def test_all_fe_pipeline_command_args_include_workflow_id() -> None:
    """Every step-run command invocation in fe-pipeline must pass workflow_id=fe-pipeline.

    Ensures workflow_id is threaded through all command args for observability.
    """
    data = _load_workflow()
    cmds = _collect_all_commands(data.get("steps") or [])
    assert cmds, "expected at least one command step"
    for cmd in cmds:
        args = (cmd.get("input") or {}).get("args", "")
        assert "workflow_id=fe-pipeline" in args, (
            f"command step {cmd.get('id')!r} missing workflow_id=fe-pipeline in args: {args!r}"
        )
