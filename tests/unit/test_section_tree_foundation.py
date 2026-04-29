"""Lock the v1 ``section_tree.yaml`` foundation in fe-compiler.

Coverage map (one assertion class per block):

- module exports the documented surface (constants + dataclasses);
- ``parse_section_tree`` happy path round-trips the locked v1
  shape;
- every documented rejection path raises ``SectionTreeError`` with
  a useful message;
- ``flatten_section_ids`` is deterministic pre-order;
- ``load_section_tree`` returns ``None`` when the file is absent
  and a parsed tree when it is present;
- ``validate_template_alignment`` reports the three deterministic
  failure classes (missing marker, extra marker, wrong order) and
  is silent when the template aligns.

These tests are the foundation locking surface. Workflow impact tests,
template alignment tests, and end-to-end stale wiring all build on top
of them.
"""

from __future__ import annotations

from dataclasses import is_dataclass
from pathlib import Path
import re

import pytest

from fe_compiler.section_tree import (
    SECTION_ID_PATTERN,
    SECTION_MARKER_PATTERN,
    SECTION_TREE_FILENAME,
    SECTION_TREE_SCHEMA,
    SectionNode,
    SectionTree,
    SectionTreeError,
    flatten_section_ids,
    load_section_tree,
    parse_section_tree,
    validate_template_alignment,
)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _screen_outline_payload() -> dict[str, object]:
    """The canonical v1 fixture, FE-flavoured."""
    return {
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


# --------------------------------------------------------------------------- #
# Module surface lock
# --------------------------------------------------------------------------- #


def test_module_exports_documented_surface() -> None:
    assert SECTION_TREE_FILENAME == "section_tree.yaml"
    assert SECTION_TREE_SCHEMA == "axcore.section-tree/v1"
    assert isinstance(SECTION_ID_PATTERN, re.Pattern)
    assert isinstance(SECTION_MARKER_PATTERN, re.Pattern)
    assert is_dataclass(SectionNode)
    assert is_dataclass(SectionTree)
    n = SectionNode(id="A", title="A")
    with pytest.raises(Exception):
        n.id = "B"  # type: ignore[misc]
    assert issubclass(SectionTreeError, ValueError)


def test_section_id_pattern_accepts_valid_ids_and_rejects_invalid() -> None:
    for good in (
        "SCREEN_OUTLINE",
        "SCREEN_OUTLINE.LAYOUT",
        "SCREEN_OUTLINE.STATE_V2",
        "X1.Y2.Z3",
    ):
        assert SECTION_ID_PATTERN.match(good), good
    for bad in (
        "screen_outline",
        "Screen_Outline",
        ".SCREEN",
        "SCREEN.",
        "SCREEN..LAYOUT",
        "2D.GRID",
        "",
    ):
        assert not SECTION_ID_PATTERN.match(bad), bad


# --------------------------------------------------------------------------- #
# parse_section_tree — happy path
# --------------------------------------------------------------------------- #


def test_parse_section_tree_happy_path() -> None:
    tree = parse_section_tree(
        _screen_outline_payload(), expected_step_id="screen_outline"
    )
    assert isinstance(tree, SectionTree)
    assert tree.step_id == "screen_outline"
    assert tree.flat_ids == (
        "SCREEN_OUTLINE",
        "SCREEN_OUTLINE.LAYOUT",
        "SCREEN_OUTLINE.STATES",
    )
    root = tree.sections[0]
    assert root.id == "SCREEN_OUTLINE"
    assert root.title == "Screen outline"
    assert tuple(c.id for c in root.children) == (
        "SCREEN_OUTLINE.LAYOUT",
        "SCREEN_OUTLINE.STATES",
    )


# --------------------------------------------------------------------------- #
# parse_section_tree — rejection paths
# --------------------------------------------------------------------------- #


def test_parse_section_tree_rejects_schema_mismatch() -> None:
    payload = _screen_outline_payload()
    payload["schema"] = "axcore.section-tree/v0"
    with pytest.raises(SectionTreeError, match="schema mismatch"):
        parse_section_tree(payload)


def test_parse_section_tree_rejects_step_id_mismatch() -> None:
    with pytest.raises(SectionTreeError, match="step_id mismatch"):
        parse_section_tree(_screen_outline_payload(), expected_step_id="other_step")


def test_parse_section_tree_rejects_bad_section_id_format() -> None:
    payload = _screen_outline_payload()
    payload["sections"][0]["children"][0]["id"] = "screen_outline.layout"  # type: ignore[index]
    with pytest.raises(SectionTreeError, match="does not match"):
        parse_section_tree(payload)


def test_parse_section_tree_rejects_duplicate_id() -> None:
    payload = _screen_outline_payload()
    payload["sections"][0]["children"][1]["id"] = "SCREEN_OUTLINE.LAYOUT"  # type: ignore[index]
    with pytest.raises(SectionTreeError, match="duplicate section id"):
        parse_section_tree(payload)


def test_parse_section_tree_rejects_child_without_parent_prefix() -> None:
    payload = _screen_outline_payload()
    payload["sections"][0]["children"][0]["id"] = "LAYOUT"  # type: ignore[index]
    with pytest.raises(SectionTreeError, match="must be prefixed by parent id"):
        parse_section_tree(payload)


def test_parse_section_tree_rejects_empty_sections() -> None:
    payload = _screen_outline_payload()
    payload["sections"] = []
    with pytest.raises(SectionTreeError, match="non-empty list"):
        parse_section_tree(payload)


def test_parse_section_tree_rejects_unknown_top_level_key() -> None:
    payload = _screen_outline_payload()
    payload["extra"] = "nope"
    with pytest.raises(SectionTreeError, match="unknown top-level key"):
        parse_section_tree(payload)


def test_parse_section_tree_rejects_empty_children_key() -> None:
    payload = _screen_outline_payload()
    payload["sections"][0]["children"][0]["children"] = []  # type: ignore[index]
    with pytest.raises(SectionTreeError, match="empty children"):
        parse_section_tree(payload)


def test_parse_section_tree_rejects_unknown_section_key() -> None:
    payload = _screen_outline_payload()
    payload["sections"][0]["description"] = "should not be here"  # type: ignore[index]
    with pytest.raises(SectionTreeError, match="unknown section key"):
        parse_section_tree(payload)


# --------------------------------------------------------------------------- #
# flatten_section_ids
# --------------------------------------------------------------------------- #


def test_flatten_section_ids_is_pre_order() -> None:
    tree = parse_section_tree(
        {
            "schema": SECTION_TREE_SCHEMA,
            "step_id": "demo",
            "sections": [
                {
                    "id": "A",
                    "title": "a",
                    "children": [
                        {
                            "id": "A.B",
                            "title": "b",
                            "children": [{"id": "A.B.C", "title": "c"}],
                        },
                        {"id": "A.D", "title": "d"},
                    ],
                },
                {"id": "E", "title": "e"},
            ],
        }
    )
    assert tree.flat_ids == ("A", "A.B", "A.B.C", "A.D", "E")
    assert flatten_section_ids(tree.sections) == tree.flat_ids


# --------------------------------------------------------------------------- #
# load_section_tree
# --------------------------------------------------------------------------- #


def test_load_section_tree_returns_none_when_absent(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "screen_outline"
    bundle_dir.mkdir()
    assert load_section_tree(bundle_dir) is None


def test_load_section_tree_parses_present_file(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "screen_outline"
    bundle_dir.mkdir()
    (bundle_dir / SECTION_TREE_FILENAME).write_text(
        "schema: axcore.section-tree/v1\n"
        "step_id: screen_outline\n"
        "sections:\n"
        "  - id: SCREEN_OUTLINE\n"
        "    title: Screen outline\n"
        "    children:\n"
        "      - id: SCREEN_OUTLINE.LAYOUT\n"
        "        title: Layout\n"
        "      - id: SCREEN_OUTLINE.STATES\n"
        "        title: States\n",
        encoding="utf-8",
    )
    tree = load_section_tree(bundle_dir)
    assert tree is not None
    assert tree.step_id == "screen_outline"
    assert tree.flat_ids == (
        "SCREEN_OUTLINE",
        "SCREEN_OUTLINE.LAYOUT",
        "SCREEN_OUTLINE.STATES",
    )


def test_load_section_tree_uses_dir_name_as_expected_step_id(
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "wrong_dir"
    bundle_dir.mkdir()
    (bundle_dir / SECTION_TREE_FILENAME).write_text(
        "schema: axcore.section-tree/v1\n"
        "step_id: screen_outline\n"
        "sections:\n"
        "  - id: SCREEN_OUTLINE\n"
        "    title: Screen outline\n",
        encoding="utf-8",
    )
    with pytest.raises(SectionTreeError, match="step_id mismatch"):
        load_section_tree(bundle_dir)


# --------------------------------------------------------------------------- #
# validate_template_alignment
# --------------------------------------------------------------------------- #


def _aligned_template() -> str:
    return (
        "# Screen outline\n\n"
        "<!-- section: SCREEN_OUTLINE -->\n\n"
        "## Layout\n"
        "<!-- section: SCREEN_OUTLINE.LAYOUT -->\n"
        "Body text.\n\n"
        "## States\n"
        "<!-- section: SCREEN_OUTLINE.STATES -->\n"
        "More body.\n"
    )


def test_validate_template_alignment_happy_path() -> None:
    tree = parse_section_tree(_screen_outline_payload())
    assert validate_template_alignment(tree, _aligned_template()) == []


def test_validate_template_alignment_flags_missing_marker() -> None:
    tree = parse_section_tree(_screen_outline_payload())
    template = _aligned_template().replace(
        "<!-- section: SCREEN_OUTLINE.STATES -->\n", ""
    )
    errors = validate_template_alignment(tree, template)
    assert any("SCREEN_OUTLINE.STATES" in e and "no marker" in e for e in errors)


def test_validate_template_alignment_flags_extra_marker_not_in_tree() -> None:
    tree = parse_section_tree(_screen_outline_payload())
    template = _aligned_template() + "<!-- section: SCREEN_OUTLINE.GHOST -->\n"
    errors = validate_template_alignment(tree, template)
    assert any(
        "SCREEN_OUTLINE.GHOST" in e and "not in section_tree" in e for e in errors
    )


def test_validate_template_alignment_flags_wrong_marker_order() -> None:
    tree = parse_section_tree(_screen_outline_payload())
    template = (
        "<!-- section: SCREEN_OUTLINE -->\n"
        "<!-- section: SCREEN_OUTLINE.STATES -->\n"
        "<!-- section: SCREEN_OUTLINE.LAYOUT -->\n"
    )
    errors = validate_template_alignment(tree, template)
    assert any("order does not match" in e for e in errors)


def test_validate_template_alignment_tolerates_inline_markers() -> None:
    tree = parse_section_tree(_screen_outline_payload())
    template = (
        "Intro <!--   section: SCREEN_OUTLINE   -->\n"
        "Then <!-- section: SCREEN_OUTLINE.LAYOUT --> body, "
        "ending with <!--section: SCREEN_OUTLINE.STATES-->.\n"
    )
    assert validate_template_alignment(tree, template) == []
