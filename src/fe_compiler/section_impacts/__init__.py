"""Compiler-owned ``section_impacts.<workflow_id>.yaml`` foundation.

A *section impacts* file is the compiler-owned, **workflow-specific**
declaration of which downstream steps (and which sections within
them) are invalidated when a given upstream section changes. It
lives inside the step bundle directory alongside ``bundle.yaml``
and ``section_tree.yaml``::

    bundles/flows/<step_id>/
        bundle.yaml
        section_tree.yaml
        section_impacts.<workflow_id>.yaml   <-- here
        <step_id>.md
        <step_id>_rules.md
        <step_id>_validate.json

A step may participate in multiple workflows; one impacts file per
workflow is allowed (and each is optional). The filename embeds the
workflow id so file ⇄ workflow alignment is detectable at load
time without parsing the body. Mismatch is a hard error.

Why this lives in the compiler (not in ``axcore``)
-----------------------------------------------------

Section impacts are domain knowledge tied to a *specific* workflow.
The ``axcore`` kernel is intentionally domain-agnostic — it does
not infer or author impact relationships. The compiler owns the
file, declares the cross-step dependency edges deterministically,
and ships the file inside the step bundle.

Locked schema
-------------

The on-disk file shape is locked at::

    schema: axcore.section-impacts/v1
    workflow_id: fe-pipeline-v1
    step_id: screen_outline

    impacts:
      - from_section: SCREEN_OUTLINE.LAYOUT
        to:
          - step_id: component_design
            target: section
            section_ids:
              - COMPONENT.LIST
          - step_id: integration_summary
            target: artifact

Top-level keys are restricted to ``schema``, ``workflow_id``,
``step_id``, ``impacts``. Each ``impacts`` entry has exactly two
keys: ``from_section`` (a section id from the owning step's tree)
and ``to`` (a non-empty list of downstream effects). Each ``to``
entry has ``step_id``, ``target``, and — for ``section`` /
``subtree`` modes — ``section_ids``.

Three target modes are accepted, no others:

- ``section``  — the listed downstream section ids only.
- ``subtree``  — the listed downstream section ids plus every
  descendant in the downstream's section tree.
- ``artifact`` — the entire downstream artifact / step. MUST NOT
  declare ``section_ids``.

The module is small on purpose: the v1 contract is *just* a
filename helper, a parser/validator, and two cross-file checks
(workflow scope + section-tree alignment). Runtime invalidation
is layered on top elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

from fe_compiler.section_tree import SECTION_ID_PATTERN, SectionTree

__all__ = [
    "SECTION_IMPACTS_FILENAME_PREFIX",
    "SECTION_IMPACTS_FILENAME_SUFFIX",
    "SECTION_IMPACTS_SCHEMA",
    "SECTION_IMPACT_TARGET_MODES",
    "SectionImpactTo",
    "SectionImpactRule",
    "SectionImpactsFile",
    "SectionImpactsError",
    "section_impacts_filename",
    "parse_workflow_id_from_filename",
    "load_section_impacts",
    "load_all_section_impacts",
    "parse_section_impacts",
    "validate_against_workflow",
    "validate_against_section_trees",
]


# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

SECTION_IMPACTS_FILENAME_PREFIX: str = "section_impacts."
"""Locked filename prefix. Sits in front of the workflow id."""

SECTION_IMPACTS_FILENAME_SUFFIX: str = ".yaml"
"""Locked filename suffix."""

SECTION_IMPACTS_SCHEMA: str = "axcore.section-impacts/v1"
"""Locked schema id. Wire incompatibilities bump this."""

SECTION_IMPACT_TARGET_MODES: frozenset[str] = frozenset(
    {"section", "subtree", "artifact"}
)
"""The complete, closed set of target modes accepted in v1.

Wildcards, regexes, and pattern modes are out of scope by design;
v1 is deterministic enumeration only.
"""


# Top-level keys accepted in section_impacts.<workflow_id>.yaml.
_ALLOWED_TOP_KEYS: frozenset[str] = frozenset(
    {"schema", "workflow_id", "step_id", "impacts"}
)

# Per-impact dict keys.
_ALLOWED_IMPACT_KEYS: frozenset[str] = frozenset({"from_section", "to"})

# Per-`to`-entry dict keys.
_ALLOWED_TO_KEYS: frozenset[str] = frozenset({"step_id", "target", "section_ids"})

# Filename-id grammar: lowercase alphanumeric + hyphens (matches the
# Spec Kit workflow-id grammar — see workflows/fe_pipeline_v1.yaml).
_FILENAME_WORKFLOW_ID_PATTERN: re.Pattern[str] = re.compile(r"^[a-z0-9][a-z0-9-]*$")


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #


class SectionImpactsError(ValueError):
    """Raised on any invalid ``section_impacts.<workflow_id>.yaml``.

    Subclasses ``ValueError`` so callers that already catch
    ``ValueError`` for parse paths keep working; the dedicated type
    is preferred for new code.
    """


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SectionImpactTo:
    """One downstream effect of a single upstream section change.

    ``section_ids`` is empty for ``target='artifact'`` (whole-step
    invalidation), and a non-empty tuple for ``target='section'`` /
    ``target='subtree'``.
    """

    step_id: str
    target: str
    section_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SectionImpactRule:
    """One impact rule rooted at a single upstream section id.

    A rule pairs the upstream ``from_section`` with one or more
    downstream effects. Ordering of ``to`` entries is preserved as
    declared so re-serialisation is stable.
    """

    from_section: str
    to: tuple[SectionImpactTo, ...]


@dataclass(frozen=True)
class SectionImpactsFile:
    """The fully parsed + validated impacts file for one workflow.

    Frozen + hashable. ``impacts`` may be empty: a step that opts
    in to the contract for a workflow but has no current downstream
    impact in that workflow is valid (an explicit "no impacts
    today" declaration is preferable to silence).
    """

    workflow_id: str
    step_id: str
    impacts: tuple[SectionImpactRule, ...]


# --------------------------------------------------------------------------- #
# Filename helpers
# --------------------------------------------------------------------------- #


def section_impacts_filename(workflow_id: str) -> str:
    """Return the on-disk filename for a workflow's impacts file.

    ``section_impacts.<workflow_id>.yaml``. The workflow id is
    inserted verbatim — the caller is responsible for passing a
    valid id.
    """
    if not isinstance(workflow_id, str) or not workflow_id:
        raise SectionImpactsError(
            f"workflow_id must be a non-empty string, got {workflow_id!r}"
        )
    return (
        f"{SECTION_IMPACTS_FILENAME_PREFIX}{workflow_id}"
        f"{SECTION_IMPACTS_FILENAME_SUFFIX}"
    )


def parse_workflow_id_from_filename(filename: str) -> str | None:
    """Inverse of :func:`section_impacts_filename`.

    Returns the embedded workflow id if ``filename`` matches the
    locked ``section_impacts.<workflow_id>.yaml`` shape, or
    ``None`` otherwise. The id segment must match the Spec Kit
    workflow-id grammar (lowercase alphanumeric + hyphens) — this
    rules out path traversal (``..``), nested directories (``/``),
    and uppercase drift.
    """
    if not isinstance(filename, str):
        return None
    if not filename.startswith(SECTION_IMPACTS_FILENAME_PREFIX):
        return None
    if not filename.endswith(SECTION_IMPACTS_FILENAME_SUFFIX):
        return None
    middle = filename[
        len(SECTION_IMPACTS_FILENAME_PREFIX) : -len(SECTION_IMPACTS_FILENAME_SUFFIX)
    ]
    if not middle:
        return None
    if not _FILENAME_WORKFLOW_ID_PATTERN.match(middle):
        return None
    return middle


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #


def load_section_impacts(
    bundle_dir: Path,
    workflow_id: str,
) -> SectionImpactsFile | None:
    """Load ``<bundle_dir>/section_impacts.<workflow_id>.yaml`` if present.

    Returns ``None`` when the file is absent — impacts files are
    *optional*; a step with no downstream impact for a workflow may
    simply omit the file. A file that is present but malformed
    raises :class:`SectionImpactsError`.

    The bundle's directory name is used as the expected step id;
    parsers cross-check that the file's ``step_id`` matches.
    """
    bundle_dir = Path(bundle_dir)
    path = bundle_dir / section_impacts_filename(workflow_id)
    if not path.is_file():
        return None
    raw = _read_yaml_mapping(path)
    return parse_section_impacts(
        raw,
        expected_workflow_id=workflow_id,
        expected_step_id=bundle_dir.name,
    )


def load_all_section_impacts(bundle_dir: Path) -> dict[str, SectionImpactsFile]:
    """Discover and parse every impacts file in a bundle directory.

    Returns a mapping ``{workflow_id: SectionImpactsFile}``. The
    embedded workflow id (from the filename) is used as the
    dictionary key and is cross-checked against the file's
    ``workflow_id`` field — disagreement is a hard error.

    Files matching the prefix/suffix but with an ill-formed embedded
    workflow id are also rejected; we do not silently skip drift.
    """
    bundle_dir = Path(bundle_dir)
    out: dict[str, SectionImpactsFile] = {}
    if not bundle_dir.is_dir():
        return out

    for entry in sorted(bundle_dir.iterdir()):
        name = entry.name
        if not name.startswith(SECTION_IMPACTS_FILENAME_PREFIX):
            continue
        if not name.endswith(SECTION_IMPACTS_FILENAME_SUFFIX):
            continue
        if not entry.is_file():
            continue
        wf_id = parse_workflow_id_from_filename(name)
        if wf_id is None:
            raise SectionImpactsError(
                f"{entry}: filename does not match "
                f"'{SECTION_IMPACTS_FILENAME_PREFIX}<workflow_id>"
                f"{SECTION_IMPACTS_FILENAME_SUFFIX}' shape"
            )
        raw = _read_yaml_mapping(entry)
        parsed = parse_section_impacts(
            raw,
            expected_workflow_id=wf_id,
            expected_step_id=bundle_dir.name,
        )
        out[wf_id] = parsed
    return out


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #


def parse_section_impacts(
    raw: dict[str, Any],
    *,
    expected_workflow_id: str | None = None,
    expected_step_id: str | None = None,
) -> SectionImpactsFile:
    """Validate and convert a raw mapping into a :class:`SectionImpactsFile`.

    Intra-file validation only — workflow scope and section-tree
    alignment are handled by :func:`validate_against_workflow` and
    :func:`validate_against_section_trees` respectively. Raises
    :class:`SectionImpactsError` on any contract violation.
    """
    if not isinstance(raw, dict):
        raise SectionImpactsError(
            f"section_impacts must be a mapping, got {type(raw).__name__}"
        )

    unknown = set(raw) - _ALLOWED_TOP_KEYS
    if unknown:
        raise SectionImpactsError(
            f"unknown top-level key(s): {sorted(unknown)!r}; "
            f"allowed: {sorted(_ALLOWED_TOP_KEYS)!r}"
        )

    schema = raw.get("schema")
    if schema != SECTION_IMPACTS_SCHEMA:
        raise SectionImpactsError(
            f"schema mismatch: expected {SECTION_IMPACTS_SCHEMA!r}, got {schema!r}"
        )

    workflow_id = raw.get("workflow_id")
    if not isinstance(workflow_id, str) or not workflow_id:
        raise SectionImpactsError(
            f"workflow_id must be a non-empty string, got {workflow_id!r}"
        )
    if expected_workflow_id is not None and workflow_id != expected_workflow_id:
        raise SectionImpactsError(
            f"workflow_id mismatch: expected {expected_workflow_id!r}, "
            f"got {workflow_id!r}"
        )

    step_id = raw.get("step_id")
    if not isinstance(step_id, str) or not step_id:
        raise SectionImpactsError(
            f"step_id must be a non-empty string, got {step_id!r}"
        )
    if expected_step_id is not None and step_id != expected_step_id:
        raise SectionImpactsError(
            f"step_id mismatch: expected {expected_step_id!r}, got {step_id!r}"
        )

    impacts_raw = raw.get("impacts")
    if not isinstance(impacts_raw, list):
        raise SectionImpactsError(
            f"impacts must be a list, got {type(impacts_raw).__name__}"
        )

    impacts = tuple(_parse_impact(node) for node in impacts_raw)
    return SectionImpactsFile(
        workflow_id=workflow_id,
        step_id=step_id,
        impacts=impacts,
    )


# --------------------------------------------------------------------------- #
# Cross-file validators
# --------------------------------------------------------------------------- #


def validate_against_workflow(
    impacts_file: SectionImpactsFile,
    *,
    workflow_step_ids: frozenset[str],
) -> list[str]:
    """Check every step id referenced is inside the named workflow.

    Returns an error list (empty ⇒ valid). Both the owning
    ``step_id`` and every ``to.step_id`` must be members of
    ``workflow_step_ids``. Errors are returned (not raised) so
    callers can surface them in bulk during a single validation
    pass.
    """
    errors: list[str] = []
    if impacts_file.step_id not in workflow_step_ids:
        errors.append(
            f"owning step_id {impacts_file.step_id!r} is not in workflow "
            f"{impacts_file.workflow_id!r} step ids: "
            f"{sorted(workflow_step_ids)!r}"
        )
    for rule in impacts_file.impacts:
        for entry in rule.to:
            if entry.step_id not in workflow_step_ids:
                errors.append(
                    f"impact from {rule.from_section!r}: downstream step_id "
                    f"{entry.step_id!r} is not in workflow "
                    f"{impacts_file.workflow_id!r}"
                )
    return errors


def validate_against_section_trees(
    impacts_file: SectionImpactsFile,
    *,
    owning_step_tree: SectionTree,
    downstream_trees: dict[str, SectionTree | None],
) -> list[str]:
    """Check every section id referenced exists in the relevant tree.

    Returns an error list (empty ⇒ valid).

    Rules:

    1. Every ``from_section`` must be in ``owning_step_tree.flat_ids``.
    2. For every ``to`` entry:

       - If ``target='artifact'``: no section-id check (the whole
         downstream artifact is in scope).
       - If ``target in {'section','subtree'}``:

         a. ``downstream_trees[step_id]`` must be a parsed
            :class:`SectionTree` (downstream-no-tree forbids
            section-level targeting).
         b. Every id in ``section_ids`` must be in that tree's
            ``flat_ids``.

    Errors are accumulated, not raised.
    """
    errors: list[str] = []
    owning_ids = set(owning_step_tree.flat_ids)
    for rule in impacts_file.impacts:
        if rule.from_section not in owning_ids:
            errors.append(
                f"from_section {rule.from_section!r} is not in owning step "
                f"{impacts_file.step_id!r} section tree"
            )
        for entry in rule.to:
            if entry.target == "artifact":
                continue
            downstream_tree = downstream_trees.get(entry.step_id)
            if downstream_tree is None:
                errors.append(
                    f"impact from {rule.from_section!r} to {entry.step_id!r}: "
                    f"downstream has no section_tree.yaml; only "
                    f"target='artifact' is allowed for tree-less downstreams"
                )
                continue
            downstream_ids = set(downstream_tree.flat_ids)
            for sid in entry.section_ids:
                if sid not in downstream_ids:
                    errors.append(
                        f"impact from {rule.from_section!r} to "
                        f"{entry.step_id!r}: section_id {sid!r} is not in "
                        f"downstream section tree"
                    )
    return errors


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    raw_text = path.read_text(encoding="utf-8")
    try:
        raw = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:  # pragma: no cover - delegated to PyYAML
        raise SectionImpactsError(f"{path}: not valid YAML ({exc})") from exc
    if not isinstance(raw, dict):
        raise SectionImpactsError(
            f"{path}: top-level YAML must be a mapping, got {type(raw).__name__}"
        )
    return raw


def _parse_impact(raw: Any) -> SectionImpactRule:
    if not isinstance(raw, dict):
        raise SectionImpactsError(
            f"impact entry must be a mapping, got {type(raw).__name__}"
        )

    unknown = set(raw) - _ALLOWED_IMPACT_KEYS
    if unknown:
        raise SectionImpactsError(
            f"unknown impact key(s): {sorted(unknown)!r}; "
            f"allowed: {sorted(_ALLOWED_IMPACT_KEYS)!r}"
        )

    from_section = raw.get("from_section")
    if not isinstance(from_section, str) or not from_section:
        raise SectionImpactsError(
            f"impact from_section must be a non-empty string, got {from_section!r}"
        )
    if not SECTION_ID_PATTERN.match(from_section):
        raise SectionImpactsError(
            f"impact from_section {from_section!r} does not match "
            f"{SECTION_ID_PATTERN.pattern}"
        )

    to_raw = raw.get("to")
    if not isinstance(to_raw, list) or not to_raw:
        raise SectionImpactsError(
            f"impact from {from_section!r}: 'to' must be a non-empty list"
        )

    to_entries = tuple(_parse_to_entry(node, from_section) for node in to_raw)
    return SectionImpactRule(from_section=from_section, to=to_entries)


def _parse_to_entry(raw: Any, from_section: str) -> SectionImpactTo:
    if not isinstance(raw, dict):
        raise SectionImpactsError(
            f"impact from {from_section!r}: 'to' entry must be a mapping, "
            f"got {type(raw).__name__}"
        )

    unknown = set(raw) - _ALLOWED_TO_KEYS
    if unknown:
        raise SectionImpactsError(
            f"impact from {from_section!r}: unknown 'to' key(s): "
            f"{sorted(unknown)!r}; allowed: {sorted(_ALLOWED_TO_KEYS)!r}"
        )

    step_id = raw.get("step_id")
    if not isinstance(step_id, str) or not step_id:
        raise SectionImpactsError(
            f"impact from {from_section!r}: 'to' step_id must be a non-empty "
            f"string, got {step_id!r}"
        )

    target = raw.get("target")
    if target not in SECTION_IMPACT_TARGET_MODES:
        raise SectionImpactsError(
            f"impact from {from_section!r} to {step_id!r}: target must be one "
            f"of {sorted(SECTION_IMPACT_TARGET_MODES)!r}, got {target!r}"
        )

    has_section_ids_key = "section_ids" in raw
    if target == "artifact":
        if has_section_ids_key:
            raise SectionImpactsError(
                f"impact from {from_section!r} to {step_id!r}: "
                f"target='artifact' MUST NOT declare 'section_ids'"
            )
        return SectionImpactTo(step_id=step_id, target=target, section_ids=())

    # target in {'section', 'subtree'}
    if not has_section_ids_key:
        raise SectionImpactsError(
            f"impact from {from_section!r} to {step_id!r}: target={target!r} "
            f"requires non-empty 'section_ids'"
        )
    section_ids_raw = raw.get("section_ids")
    if not isinstance(section_ids_raw, list) or not section_ids_raw:
        raise SectionImpactsError(
            f"impact from {from_section!r} to {step_id!r}: target={target!r} "
            f"requires 'section_ids' to be a non-empty list"
        )
    section_ids: list[str] = []
    for sid in section_ids_raw:
        if not isinstance(sid, str) or not sid:
            raise SectionImpactsError(
                f"impact from {from_section!r} to {step_id!r}: each "
                f"section_id must be a non-empty string, got {sid!r}"
            )
        if not SECTION_ID_PATTERN.match(sid):
            raise SectionImpactsError(
                f"impact from {from_section!r} to {step_id!r}: section_id "
                f"{sid!r} does not match {SECTION_ID_PATTERN.pattern}"
            )
        section_ids.append(sid)
    return SectionImpactTo(
        step_id=step_id,
        target=target,
        section_ids=tuple(section_ids),
    )
