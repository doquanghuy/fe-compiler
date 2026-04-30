"""Lock the real shipped FE section trees + workflow-specific impacts.

This suite asserts that the on-disk section configuration *as
shipped* in ``src/fe_compiler/bundles/flows/<step>/`` parses,
aligns with its template, and is consistent with the workflow
files in ``src/fe_compiler/workflows/`` it claims to be scoped to.

Why this is its own suite (not folded into the foundation suite)
----------------------------------------------------------------
The foundation suite (``test_section_tree_foundation.py``,
``test_section_impacts_foundation.py``) locks the *parser /
validator* contract using hand-built fixtures. This suite locks
the *real product configuration* against drift so that:

- adding a section to a tree without adding the marker fails,
- renaming a section id without updating impacts files fails,
- introducing a downstream step + workflow edge without backfilling
  an impacts file fails because the impacts ledger pin will not
  match,
- referencing a step id outside the workflow fails the per-bundle
  workflow-scope assertion.

FE rollout is intentionally *partial* at v1: a single entry step
(``screen_outline``) with no downstream consumers. The impacts
ledger is therefore an explicitly-empty pin — adding the first
real downstream step + impacts file is a deliberate, test-paired
change that flips this ledger.

Tests use ``pytest.parametrize`` so per-bundle / per-workflow
failures are legible in CI output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from fe_compiler.section_impacts import (
    SECTION_IMPACTS_FILENAME_PREFIX,
    SECTION_IMPACTS_FILENAME_SUFFIX,
    load_all_section_impacts,
    parse_section_impacts,
    parse_workflow_id_from_filename,
    validate_against_section_trees,
    validate_against_workflow,
)
from fe_compiler.section_tree import (
    SectionTree,
    load_section_tree,
    parse_section_tree,
    validate_template_alignment,
)

# --------------------------------------------------------------------------- #
# Repo geometry
# --------------------------------------------------------------------------- #


PKG_ROOT: Path = Path(__file__).resolve().parents[2] / "src" / "fe_compiler"
BUNDLES_ROOT: Path = PKG_ROOT / "bundles" / "flows"
WORKFLOWS_ROOT: Path = PKG_ROOT / "workflows"


def _bundle_dirs() -> list[Path]:
    """Every shipped FE step bundle directory, sorted by name."""
    return sorted(
        p for p in BUNDLES_ROOT.iterdir() if p.is_dir() and not p.name.startswith("__")
    )


def _bundle_ids() -> list[str]:
    return [p.name for p in _bundle_dirs()]


def _bundles_with_tree() -> list[Path]:
    return [p for p in _bundle_dirs() if (p / "section_tree.yaml").is_file()]


def _impacts_files() -> list[tuple[str, str, Path]]:
    """Every shipped impacts file as (step_id, workflow_id, path).

    May be empty: FE ships zero impacts files at v1 (single-step DAG
    has no downstream edges to model)."""
    out: list[tuple[str, str, Path]] = []
    for bundle_dir in _bundle_dirs():
        for entry in sorted(bundle_dir.iterdir()):
            name = entry.name
            if not name.startswith(SECTION_IMPACTS_FILENAME_PREFIX):
                continue
            if not name.endswith(SECTION_IMPACTS_FILENAME_SUFFIX):
                continue
            wf_id = parse_workflow_id_from_filename(name)
            assert wf_id is not None, f"unparseable impacts filename: {entry}"
            out.append((bundle_dir.name, wf_id, entry))
    return out


def _collect_step_ids(steps: list[dict[str, Any]] | None) -> set[str]:
    """Recursively collect every step id reachable from a workflow's
    ``steps`` list. Walks switch-cases so nested branches count as
    in-scope (FE has none today; future-proofs the helper)."""
    out: set[str] = set()
    for step in steps or []:
        sid = step.get("id")
        if isinstance(sid, str) and sid:
            out.add(sid)
        if step.get("type") == "switch":
            for case_steps in (step.get("cases") or {}).values():
                out |= _collect_step_ids(case_steps)
    return out


def _load_workflow(workflow_id: str) -> dict[str, Any]:
    """Find a workflow by id (filenames don't always equal ids)."""
    for wf_path in sorted(WORKFLOWS_ROOT.glob("*.yaml")):
        raw = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
        if (raw.get("workflow") or {}).get("id") == workflow_id:
            return raw
    raise AssertionError(
        f"workflow id {workflow_id!r} not found under {WORKFLOWS_ROOT}"
    )


def _workflow_step_ids(workflow_id: str) -> frozenset[str]:
    return frozenset(_collect_step_ids(_load_workflow(workflow_id).get("steps") or []))


def _all_trees() -> dict[str, SectionTree | None]:
    """Map every bundle dir name → parsed tree (or None when absent)."""
    return {p.name: load_section_tree(p) for p in _bundle_dirs()}


# --------------------------------------------------------------------------- #
# Inventory ledgers — the load-bearing pins
# --------------------------------------------------------------------------- #


# The exact set of bundles shipping section_tree.yaml today. Adding a
# new bundle without a tree (or removing an existing tree) must update
# this ledger explicitly.
EXPECTED_BUNDLES_WITH_TREE: frozenset[str] = frozenset(
    {
        "screen_outline",
    }
)


# The exact (step, workflow) pairs that ship an impacts file. EMPTY at
# v1 — FE is a single-step DAG with no downstream edges to model.
# Adding the first impacts file is a deliberate, test-paired change
# that flips this ledger.
EXPECTED_IMPACTS_LEDGER: frozenset[tuple[str, str]] = frozenset()


def test_bundle_ledger_pins_real_step_set() -> None:
    """Every shipped flow bundle is named — adding/removing one fails fast.

    FE is intentionally minimal at v1: one entry step. Any new step
    must extend this set explicitly.
    """
    expected = {"screen_outline"}
    assert set(_bundle_ids()) == expected


def test_section_tree_ledger_matches_expected() -> None:
    """The set of bundles shipping section_tree.yaml is pinned."""
    on_disk = {p.name for p in _bundles_with_tree()}
    assert on_disk == EXPECTED_BUNDLES_WITH_TREE


def test_impacts_ledger_matches_expected() -> None:
    """The (step, workflow) impacts pairs that ship today are pinned.

    FE ships ZERO impacts files at v1 — the single-step DAG has no
    downstream edges. The empty pin is the architecture-clean honest
    answer; flipping it requires adding at least one downstream step
    AND its impacts file in the same change.
    """
    on_disk = {(step, wf) for (step, wf, _path) in _impacts_files()}
    assert on_disk == EXPECTED_IMPACTS_LEDGER


def test_screen_outline_is_terminal_today_with_no_impacts_file() -> None:
    """`screen_outline` is the sole step of `fe-pipeline` today;
    with no downstream consumer in any workflow, it ships no impacts
    file. Pins the partial-rollout shape against accidental drift
    (a stray empty impacts file would still fail this test)."""
    so_dir = BUNDLES_ROOT / "screen_outline"
    impacts = list(
        so_dir.glob(
            f"{SECTION_IMPACTS_FILENAME_PREFIX}*{SECTION_IMPACTS_FILENAME_SUFFIX}"
        )
    )
    assert impacts == [], (
        f"screen_outline has no downstream consumers; impacts files found: {impacts!r}"
    )


# --------------------------------------------------------------------------- #
# Per-bundle: section_tree.yaml parses + aligns with template
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bundle_dir", _bundles_with_tree(), ids=lambda p: p.name)
def test_section_tree_parses_with_expected_step_id(bundle_dir: Path) -> None:
    """`parse_section_tree` accepts the file and the embedded step_id
    matches the bundle directory name."""
    raw_text = (bundle_dir / "section_tree.yaml").read_text(encoding="utf-8")
    raw = yaml.safe_load(raw_text)
    tree = parse_section_tree(raw, expected_step_id=bundle_dir.name)
    assert tree.step_id == bundle_dir.name
    # Every tree we ship today has a non-trivial id set (the top-level
    # parent + at least one child).
    assert len(tree.flat_ids) >= 2


@pytest.mark.parametrize("bundle_dir", _bundles_with_tree(), ids=lambda p: p.name)
def test_template_aligns_with_section_tree(bundle_dir: Path) -> None:
    """Template carries one `<!-- section: ID -->` marker per tree id,
    in pre-order. `validate_template_alignment` returns ``[]``."""
    tree = load_section_tree(bundle_dir)
    assert tree is not None
    template_path = bundle_dir / f"{bundle_dir.name}.md"
    assert template_path.is_file(), f"missing template: {template_path}"
    template_text = template_path.read_text(encoding="utf-8")
    errors = validate_template_alignment(tree, template_text)
    assert errors == [], f"alignment errors for {bundle_dir.name}: {errors}"


# --------------------------------------------------------------------------- #
# Per-impacts-file: parse + cross-file validation
#
# FE ships zero impacts files today. The parametrised tests below
# collect to zero cases and are silently no-ops; the ledger pin
# (`test_impacts_ledger_matches_expected`) is the load-bearing
# emptiness check. The parametrised shape is deliberately retained
# so that the FIRST impacts file added flips four pins simultaneously
# (parse + filename match + workflow scope + tree alignment) without
# new test scaffolding.
# --------------------------------------------------------------------------- #


def _impacts_param_id(triple: tuple[str, str, Path]) -> str:
    step, wf, _path = triple
    return f"{step}@{wf}"


@pytest.mark.parametrize("triple", _impacts_files(), ids=_impacts_param_id)
def test_impacts_filename_workflow_id_matches_body(
    triple: tuple[str, str, Path],
) -> None:
    """The workflow id encoded in the filename matches the body's
    ``workflow_id``. The loader enforces this; the test pins it for
    every shipped file (none today)."""
    step_id, workflow_id, path = triple
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert raw["workflow_id"] == workflow_id
    assert raw["step_id"] == step_id


@pytest.mark.parametrize("triple", _impacts_files(), ids=_impacts_param_id)
def test_impacts_file_parses(triple: tuple[str, str, Path]) -> None:
    """`parse_section_impacts` accepts the on-disk file with the
    expected step + workflow ids."""
    step_id, workflow_id, path = triple
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    impacts = parse_section_impacts(
        raw,
        expected_workflow_id=workflow_id,
        expected_step_id=step_id,
    )
    assert impacts.workflow_id == workflow_id
    assert impacts.step_id == step_id
    assert len(impacts.impacts) >= 1


@pytest.mark.parametrize("triple", _impacts_files(), ids=_impacts_param_id)
def test_impacts_file_step_ids_are_in_workflow(triple: tuple[str, str, Path]) -> None:
    """Every step id referenced by an impacts file lives inside that
    workflow."""
    step_id, workflow_id, path = triple
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    impacts = parse_section_impacts(
        raw,
        expected_workflow_id=workflow_id,
        expected_step_id=step_id,
    )
    workflow_step_ids = _workflow_step_ids(workflow_id)
    errors = validate_against_workflow(
        impacts,
        workflow_step_ids=workflow_step_ids,
    )
    assert errors == [], f"workflow-scope errors for {step_id}@{workflow_id}: {errors}"


@pytest.mark.parametrize("triple", _impacts_files(), ids=_impacts_param_id)
def test_impacts_file_section_ids_are_in_trees(triple: tuple[str, str, Path]) -> None:
    """Every section id referenced (`from_section`, downstream
    `section_ids`) exists in the relevant section tree."""
    step_id, workflow_id, path = triple
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    impacts = parse_section_impacts(
        raw,
        expected_workflow_id=workflow_id,
        expected_step_id=step_id,
    )
    trees = _all_trees()
    owning_tree = trees[step_id]
    assert owning_tree is not None, (
        f"impacts file ships for {step_id} but step has no section_tree.yaml"
    )
    errors = validate_against_section_trees(
        impacts,
        owning_step_tree=owning_tree,
        downstream_trees=trees,
    )
    assert errors == [], f"section-tree errors for {step_id}@{workflow_id}: {errors}"


# --------------------------------------------------------------------------- #
# load_all_section_impacts round-trip — discovery is consistent with
# the per-file ledger above (no silently-skipped files).
# --------------------------------------------------------------------------- #


def test_load_all_section_impacts_matches_ledger() -> None:
    """``load_all_section_impacts`` per bundle is consistent with the
    full impacts ledger. Pins discovery against silent skips. With
    today's empty ledger this proves no impacts files have been
    added without updating ``EXPECTED_IMPACTS_LEDGER`` in the same
    change."""
    discovered: set[tuple[str, str]] = set()
    for bundle_dir in _bundle_dirs():
        files = load_all_section_impacts(bundle_dir)
        for wf_id, parsed in files.items():
            assert parsed.step_id == bundle_dir.name
            assert parsed.workflow_id == wf_id
            discovered.add((bundle_dir.name, wf_id))
    assert discovered == EXPECTED_IMPACTS_LEDGER


# --------------------------------------------------------------------------- #
# Workflow scope — workflow file ↔ ledger consistency
# --------------------------------------------------------------------------- #


def test_workflow_step_ids_cover_owning_steps_in_ledger() -> None:
    """Every (step, workflow) pair in ``EXPECTED_IMPACTS_LEDGER`` names
    a step that genuinely exists inside the named workflow. With an
    empty ledger this is a vacuous true today; the test is retained
    so the FIRST entry flips it without needing new scaffolding."""
    for step_id, workflow_id in EXPECTED_IMPACTS_LEDGER:
        wf_steps = _workflow_step_ids(workflow_id)
        assert step_id in wf_steps, (
            f"ledger pair ({step_id!r}, {workflow_id!r}) names a step "
            f"that is not in workflow steps {sorted(wf_steps)!r}"
        )
