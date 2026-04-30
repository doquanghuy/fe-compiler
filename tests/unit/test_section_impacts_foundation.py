"""Lock the v1 ``section_impacts.<workflow_id>.yaml`` foundation.

Coverage map (one assertion class per block):

- module exports the documented surface (constants + dataclasses);
- filename helpers round-trip and reject ill-formed shapes;
- ``parse_section_impacts`` happy path covers all three target
  modes mixed in one file;
- every documented intra-file rejection raises
  ``SectionImpactsError`` with a useful message;
- empty ``impacts`` list is accepted (formal opt-in with no current
  downstream impact);
- ``validate_against_workflow`` flags out-of-workflow step ids on
  both the owning step and downstream targets;
- ``validate_against_section_trees`` flags missing ``from_section``,
  missing downstream ``section_ids``, and the downstream-no-tree
  rule (``target='artifact'`` is the only mode allowed when the
  downstream has no section tree);
- ``load_section_impacts`` returns ``None`` when the file is absent
  and a parsed file when it is present;
- ``load_all_section_impacts`` returns a workflow-id-keyed dict and
  rejects filename/content workflow_id drift.
"""

from __future__ import annotations

from dataclasses import is_dataclass
from pathlib import Path
from typing import Any

import pytest

from fe_compiler.section_impacts import (
    SECTION_IMPACT_TARGET_MODES,
    SECTION_IMPACTS_FILENAME_PREFIX,
    SECTION_IMPACTS_FILENAME_SUFFIX,
    SECTION_IMPACTS_SCHEMA,
    SectionImpactRule,
    SectionImpactsError,
    SectionImpactsFile,
    SectionImpactTo,
    load_all_section_impacts,
    load_section_impacts,
    parse_section_impacts,
    parse_workflow_id_from_filename,
    section_impacts_filename,
    validate_against_section_trees,
    validate_against_workflow,
)
from fe_compiler.section_tree import (
    SECTION_TREE_SCHEMA,
    SectionTree,
    parse_section_tree,
)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _screen_outline_impacts_payload() -> dict[str, Any]:
    """Canonical mixed-mode fixture: section + subtree + artifact."""
    return {
        "schema": SECTION_IMPACTS_SCHEMA,
        "workflow_id": "fe-pipeline",
        "step_id": "screen_outline",
        "impacts": [
            {
                "from_section": "SCREEN_OUTLINE.LAYOUT",
                "to": [
                    {
                        "step_id": "component_design",
                        "target": "section",
                        "section_ids": ["COMPONENT.LIST"],
                    },
                    {
                        "step_id": "state_design",
                        "target": "subtree",
                        "section_ids": ["STATE.MODELS"],
                    },
                    {
                        "step_id": "integration_summary",
                        "target": "artifact",
                    },
                ],
            },
        ],
    }


def _screen_outline_tree() -> SectionTree:
    return parse_section_tree(
        {
            "schema": SECTION_TREE_SCHEMA,
            "step_id": "screen_outline",
            "sections": [
                {
                    "id": "SCREEN_OUTLINE",
                    "title": "Screen outline",
                    "children": [
                        {"id": "SCREEN_OUTLINE.LAYOUT", "title": "Layout"},
                        {"id": "SCREEN_OUTLINE.STATES", "title": "States"},
                    ],
                },
            ],
        }
    )


def _component_design_tree() -> SectionTree:
    return parse_section_tree(
        {
            "schema": SECTION_TREE_SCHEMA,
            "step_id": "component_design",
            "sections": [
                {
                    "id": "COMPONENT",
                    "title": "Component",
                    "children": [
                        {"id": "COMPONENT.LIST", "title": "List"},
                        {"id": "COMPONENT.PROPS", "title": "Props"},
                    ],
                },
            ],
        }
    )


def _state_design_tree() -> SectionTree:
    return parse_section_tree(
        {
            "schema": SECTION_TREE_SCHEMA,
            "step_id": "state_design",
            "sections": [
                {
                    "id": "STATE",
                    "title": "State",
                    "children": [
                        {
                            "id": "STATE.MODELS",
                            "title": "Models",
                            "children": [
                                {"id": "STATE.MODELS.SESSION", "title": "Session"},
                            ],
                        },
                    ],
                },
            ],
        }
    )


# --------------------------------------------------------------------------- #
# Module surface lock
# --------------------------------------------------------------------------- #


def test_module_exports_documented_surface() -> None:
    assert SECTION_IMPACTS_FILENAME_PREFIX == "section_impacts."
    assert SECTION_IMPACTS_FILENAME_SUFFIX == ".yaml"
    assert SECTION_IMPACTS_SCHEMA == "axcore.section-impacts/v1"
    assert frozenset({"section", "subtree", "artifact"}) == SECTION_IMPACT_TARGET_MODES
    # Dataclasses are frozen.
    assert is_dataclass(SectionImpactTo)
    assert is_dataclass(SectionImpactRule)
    assert is_dataclass(SectionImpactsFile)
    entry = SectionImpactTo(step_id="x", target="artifact")
    with pytest.raises(Exception):
        entry.target = "section"  # type: ignore[misc]
    # Error type is a ValueError subtype.
    assert issubclass(SectionImpactsError, ValueError)


# --------------------------------------------------------------------------- #
# Filename helpers
# --------------------------------------------------------------------------- #


def test_filename_round_trip() -> None:
    name = section_impacts_filename("fe-pipeline")
    assert name == "section_impacts.fe-pipeline.yaml"
    assert parse_workflow_id_from_filename(name) == "fe-pipeline"


def test_filename_round_trip_for_alt_workflow() -> None:
    name = section_impacts_filename("fe-design-refresh-v1")
    assert name == "section_impacts.fe-design-refresh-v1.yaml"
    assert parse_workflow_id_from_filename(name) == "fe-design-refresh-v1"


def test_section_impacts_filename_rejects_empty_workflow_id() -> None:
    with pytest.raises(SectionImpactsError):
        section_impacts_filename("")


def test_parse_workflow_id_returns_none_for_non_matches() -> None:
    for bad in (
        "section_tree.yaml",
        "section_impacts.yaml",
        "section_impacts..yaml",
        "section_impacts.UPPER.yaml",
        "section_impacts.has space.yaml",
        "section_impacts.has/slash.yaml",
        "section_impacts.has.dot.yaml",
        "section_impacts.fe-pipeline.yml",
        "bundle.yaml",
        "",
    ):
        assert parse_workflow_id_from_filename(bad) is None, bad


# --------------------------------------------------------------------------- #
# parse_section_impacts — happy path
# --------------------------------------------------------------------------- #


def test_parse_section_impacts_happy_path_mixed_modes() -> None:
    parsed = parse_section_impacts(
        _screen_outline_impacts_payload(),
        expected_workflow_id="fe-pipeline",
        expected_step_id="screen_outline",
    )
    assert isinstance(parsed, SectionImpactsFile)
    assert parsed.workflow_id == "fe-pipeline"
    assert parsed.step_id == "screen_outline"
    assert len(parsed.impacts) == 1
    rule = parsed.impacts[0]
    assert rule.from_section == "SCREEN_OUTLINE.LAYOUT"
    targets = {entry.step_id: entry for entry in rule.to}
    assert targets["component_design"].target == "section"
    assert targets["component_design"].section_ids == ("COMPONENT.LIST",)
    assert targets["state_design"].target == "subtree"
    assert targets["state_design"].section_ids == ("STATE.MODELS",)
    assert targets["integration_summary"].target == "artifact"
    assert targets["integration_summary"].section_ids == ()


def test_parse_section_impacts_accepts_empty_impacts_list() -> None:
    payload = _screen_outline_impacts_payload()
    payload["impacts"] = []
    parsed = parse_section_impacts(payload)
    assert parsed.impacts == ()


# --------------------------------------------------------------------------- #
# parse_section_impacts — rejection paths
# --------------------------------------------------------------------------- #


def test_parse_section_impacts_rejects_schema_mismatch() -> None:
    payload = _screen_outline_impacts_payload()
    payload["schema"] = "axcore.section-impacts/v0"
    with pytest.raises(SectionImpactsError, match="schema mismatch"):
        parse_section_impacts(payload)


def test_parse_section_impacts_rejects_workflow_id_mismatch() -> None:
    with pytest.raises(SectionImpactsError, match="workflow_id mismatch"):
        parse_section_impacts(
            _screen_outline_impacts_payload(),
            expected_workflow_id="fe-design-refresh-v1",
        )


def test_parse_section_impacts_rejects_step_id_mismatch() -> None:
    with pytest.raises(SectionImpactsError, match="step_id mismatch"):
        parse_section_impacts(
            _screen_outline_impacts_payload(),
            expected_step_id="overview",
        )


def test_parse_section_impacts_rejects_target_section_without_section_ids() -> None:
    payload = _screen_outline_impacts_payload()
    del payload["impacts"][0]["to"][0]["section_ids"]
    with pytest.raises(SectionImpactsError, match="requires non-empty 'section_ids'"):
        parse_section_impacts(payload)


def test_parse_section_impacts_rejects_target_subtree_without_section_ids() -> None:
    payload = _screen_outline_impacts_payload()
    del payload["impacts"][0]["to"][1]["section_ids"]
    with pytest.raises(SectionImpactsError, match="requires non-empty 'section_ids'"):
        parse_section_impacts(payload)


def test_parse_section_impacts_rejects_target_artifact_with_section_ids() -> None:
    payload = _screen_outline_impacts_payload()
    payload["impacts"][0]["to"][2]["section_ids"] = ["X.Y"]
    with pytest.raises(
        SectionImpactsError, match="target='artifact' MUST NOT declare 'section_ids'"
    ):
        parse_section_impacts(payload)


def test_parse_section_impacts_rejects_unknown_target_mode() -> None:
    payload = _screen_outline_impacts_payload()
    payload["impacts"][0]["to"][0]["target"] = "wildcard"
    with pytest.raises(SectionImpactsError, match="target must be one of"):
        parse_section_impacts(payload)


def test_parse_section_impacts_rejects_bad_section_id_format() -> None:
    payload = _screen_outline_impacts_payload()
    payload["impacts"][0]["from_section"] = "screen_outline.layout"  # lowercase
    with pytest.raises(SectionImpactsError, match="does not match"):
        parse_section_impacts(payload)


def test_parse_section_impacts_rejects_bad_downstream_section_id_format() -> None:
    payload = _screen_outline_impacts_payload()
    payload["impacts"][0]["to"][0]["section_ids"] = ["component.list"]
    with pytest.raises(SectionImpactsError, match="does not match"):
        parse_section_impacts(payload)


def test_parse_section_impacts_rejects_unknown_top_level_key() -> None:
    payload = _screen_outline_impacts_payload()
    payload["extra"] = "nope"
    with pytest.raises(SectionImpactsError, match="unknown top-level key"):
        parse_section_impacts(payload)


def test_parse_section_impacts_rejects_unknown_impact_level_key() -> None:
    payload = _screen_outline_impacts_payload()
    payload["impacts"][0]["note"] = "should not be here"
    with pytest.raises(SectionImpactsError, match="unknown impact key"):
        parse_section_impacts(payload)


def test_parse_section_impacts_rejects_unknown_to_entry_key() -> None:
    payload = _screen_outline_impacts_payload()
    payload["impacts"][0]["to"][0]["weight"] = 0.5
    with pytest.raises(SectionImpactsError, match="unknown 'to' key"):
        parse_section_impacts(payload)


def test_parse_section_impacts_rejects_empty_to_list() -> None:
    payload = _screen_outline_impacts_payload()
    payload["impacts"][0]["to"] = []
    with pytest.raises(SectionImpactsError, match="'to' must be a non-empty list"):
        parse_section_impacts(payload)


# --------------------------------------------------------------------------- #
# validate_against_workflow
# --------------------------------------------------------------------------- #


def _full_workflow_step_ids() -> frozenset[str]:
    return frozenset(
        {
            "screen_outline",
            "component_design",
            "state_design",
            "integration_summary",
        }
    )


def test_validate_against_workflow_passes_for_in_scope_file() -> None:
    parsed = parse_section_impacts(_screen_outline_impacts_payload())
    assert (
        validate_against_workflow(parsed, workflow_step_ids=_full_workflow_step_ids())
        == []
    )


def test_validate_against_workflow_flags_out_of_workflow_to_step_id() -> None:
    payload = _screen_outline_impacts_payload()
    payload["impacts"][0]["to"][0]["step_id"] = "ghost_step"
    parsed = parse_section_impacts(payload)
    errors = validate_against_workflow(
        parsed, workflow_step_ids=_full_workflow_step_ids()
    )
    assert any("ghost_step" in e for e in errors)


def test_validate_against_workflow_flags_owning_step_not_in_workflow() -> None:
    parsed = parse_section_impacts(_screen_outline_impacts_payload())
    truncated = frozenset({"component_design"})
    errors = validate_against_workflow(parsed, workflow_step_ids=truncated)
    assert any(
        "owning step_id 'screen_outline' is not in workflow" in e for e in errors
    )


# --------------------------------------------------------------------------- #
# validate_against_section_trees
# --------------------------------------------------------------------------- #


def test_validate_against_section_trees_passes_when_aligned() -> None:
    parsed = parse_section_impacts(_screen_outline_impacts_payload())
    errors = validate_against_section_trees(
        parsed,
        owning_step_tree=_screen_outline_tree(),
        downstream_trees={
            "component_design": _component_design_tree(),
            "state_design": _state_design_tree(),
            "integration_summary": None,
        },
    )
    assert errors == []


def test_validate_against_section_trees_flags_missing_from_section() -> None:
    payload = _screen_outline_impacts_payload()
    payload["impacts"][0]["from_section"] = "SCREEN_OUTLINE.GHOST"
    parsed = parse_section_impacts(payload)
    errors = validate_against_section_trees(
        parsed,
        owning_step_tree=_screen_outline_tree(),
        downstream_trees={
            "component_design": _component_design_tree(),
            "state_design": _state_design_tree(),
            "integration_summary": None,
        },
    )
    assert any(
        "from_section 'SCREEN_OUTLINE.GHOST' is not in owning step" in e for e in errors
    )


def test_validate_against_section_trees_flags_missing_downstream_section_ids() -> None:
    payload = _screen_outline_impacts_payload()
    payload["impacts"][0]["to"][0]["section_ids"] = ["COMPONENT.GHOST"]
    parsed = parse_section_impacts(payload)
    errors = validate_against_section_trees(
        parsed,
        owning_step_tree=_screen_outline_tree(),
        downstream_trees={
            "component_design": _component_design_tree(),
            "state_design": _state_design_tree(),
            "integration_summary": None,
        },
    )
    assert any(
        "section_id 'COMPONENT.GHOST' is not in downstream section tree" in e
        for e in errors
    )


def test_validate_against_section_trees_allows_artifact_for_downstream_without_tree() -> (
    None
):
    payload = {
        "schema": SECTION_IMPACTS_SCHEMA,
        "workflow_id": "fe-pipeline",
        "step_id": "screen_outline",
        "impacts": [
            {
                "from_section": "SCREEN_OUTLINE.LAYOUT",
                "to": [
                    {"step_id": "integration_summary", "target": "artifact"},
                ],
            },
        ],
    }
    parsed = parse_section_impacts(payload)
    errors = validate_against_section_trees(
        parsed,
        owning_step_tree=_screen_outline_tree(),
        downstream_trees={"integration_summary": None},
    )
    assert errors == []


def test_validate_against_section_trees_rejects_section_target_for_tree_less_downstream() -> (
    None
):
    payload = {
        "schema": SECTION_IMPACTS_SCHEMA,
        "workflow_id": "fe-pipeline",
        "step_id": "screen_outline",
        "impacts": [
            {
                "from_section": "SCREEN_OUTLINE.LAYOUT",
                "to": [
                    {
                        "step_id": "integration_summary",
                        "target": "section",
                        "section_ids": ["X.Y"],
                    },
                ],
            },
        ],
    }
    parsed = parse_section_impacts(payload)
    errors = validate_against_section_trees(
        parsed,
        owning_step_tree=_screen_outline_tree(),
        downstream_trees={"integration_summary": None},
    )
    assert any(
        "downstream has no section_tree.yaml" in e
        and "only target='artifact' is allowed" in e
        for e in errors
    )


def test_validate_against_section_trees_rejects_subtree_target_for_tree_less_downstream() -> (
    None
):
    payload = {
        "schema": SECTION_IMPACTS_SCHEMA,
        "workflow_id": "fe-pipeline",
        "step_id": "screen_outline",
        "impacts": [
            {
                "from_section": "SCREEN_OUTLINE.LAYOUT",
                "to": [
                    {
                        "step_id": "integration_summary",
                        "target": "subtree",
                        "section_ids": ["X.Y"],
                    },
                ],
            },
        ],
    }
    parsed = parse_section_impacts(payload)
    errors = validate_against_section_trees(
        parsed,
        owning_step_tree=_screen_outline_tree(),
        downstream_trees={"integration_summary": None},
    )
    assert any("downstream has no section_tree.yaml" in e for e in errors)


# --------------------------------------------------------------------------- #
# load_section_impacts
# --------------------------------------------------------------------------- #


def _write_screen_outline_impacts(bundle_dir: Path) -> Path:
    path = bundle_dir / "section_impacts.fe-pipeline.yaml"
    path.write_text(
        "schema: axcore.section-impacts/v1\n"
        "workflow_id: fe-pipeline\n"
        "step_id: screen_outline\n"
        "impacts:\n"
        "  - from_section: SCREEN_OUTLINE.LAYOUT\n"
        "    to:\n"
        "      - step_id: component_design\n"
        "        target: section\n"
        "        section_ids:\n"
        "          - COMPONENT.LIST\n"
        "      - step_id: integration_summary\n"
        "        target: artifact\n",
        encoding="utf-8",
    )
    return path


def test_load_section_impacts_returns_none_when_absent(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "screen_outline"
    bundle_dir.mkdir()
    assert load_section_impacts(bundle_dir, "fe-pipeline") is None


def test_load_section_impacts_parses_present_file(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "screen_outline"
    bundle_dir.mkdir()
    _write_screen_outline_impacts(bundle_dir)
    parsed = load_section_impacts(bundle_dir, "fe-pipeline")
    assert parsed is not None
    assert parsed.workflow_id == "fe-pipeline"
    assert parsed.step_id == "screen_outline"
    assert len(parsed.impacts) == 1
    assert parsed.impacts[0].from_section == "SCREEN_OUTLINE.LAYOUT"


def test_load_section_impacts_uses_dir_name_as_expected_step_id(
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "overview"
    bundle_dir.mkdir()
    # File claims step_id=screen_outline but lives in overview/ — drift.
    (bundle_dir / "section_impacts.fe-pipeline.yaml").write_text(
        "schema: axcore.section-impacts/v1\n"
        "workflow_id: fe-pipeline\n"
        "step_id: screen_outline\n"
        "impacts: []\n",
        encoding="utf-8",
    )
    with pytest.raises(SectionImpactsError, match="step_id mismatch"):
        load_section_impacts(bundle_dir, "fe-pipeline")


# --------------------------------------------------------------------------- #
# load_all_section_impacts
# --------------------------------------------------------------------------- #


def test_load_all_section_impacts_returns_dict_keyed_by_workflow_id(
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "screen_outline"
    bundle_dir.mkdir()
    _write_screen_outline_impacts(bundle_dir)
    (bundle_dir / "section_impacts.fe-design-refresh-v1.yaml").write_text(
        "schema: axcore.section-impacts/v1\n"
        "workflow_id: fe-design-refresh-v1\n"
        "step_id: screen_outline\n"
        "impacts: []\n",
        encoding="utf-8",
    )
    out = load_all_section_impacts(bundle_dir)
    assert set(out) == {"fe-pipeline", "fe-design-refresh-v1"}
    assert out["fe-pipeline"].workflow_id == "fe-pipeline"
    assert out["fe-design-refresh-v1"].impacts == ()


def test_load_all_section_impacts_flags_filename_content_workflow_id_drift(
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "screen_outline"
    bundle_dir.mkdir()
    # Filename says fe-pipeline; body says fe-design-refresh-v1.
    (bundle_dir / "section_impacts.fe-pipeline.yaml").write_text(
        "schema: axcore.section-impacts/v1\n"
        "workflow_id: fe-design-refresh-v1\n"
        "step_id: screen_outline\n"
        "impacts: []\n",
        encoding="utf-8",
    )
    with pytest.raises(SectionImpactsError, match="workflow_id mismatch"):
        load_all_section_impacts(bundle_dir)


def test_load_all_section_impacts_returns_empty_for_empty_dir(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "screen_outline"
    bundle_dir.mkdir()
    assert load_all_section_impacts(bundle_dir) == {}


def test_load_all_section_impacts_returns_empty_for_missing_dir(
    tmp_path: Path,
) -> None:
    assert load_all_section_impacts(tmp_path / "does-not-exist") == {}


def test_load_all_section_impacts_rejects_ill_formed_workflow_segment(
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "screen_outline"
    bundle_dir.mkdir()
    # Uppercase letters violate the locked filename grammar.
    (bundle_dir / "section_impacts.BAD_NAME.yaml").write_text(
        "schema: axcore.section-impacts/v1\n"
        "workflow_id: BAD_NAME\n"
        "step_id: screen_outline\n"
        "impacts: []\n",
        encoding="utf-8",
    )
    with pytest.raises(SectionImpactsError, match="filename does not match"):
        load_all_section_impacts(bundle_dir)
