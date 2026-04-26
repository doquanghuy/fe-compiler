"""Compiler-owned ``section_tree.yaml`` foundation.

A *section tree* is the compiler-owned source of truth for the
section structure of a single step's primary artifact. It lives
inside the step bundle directory alongside ``bundle.yaml``,
template, rules, and validation spec::

    bundles/flows/<step_id>/
        bundle.yaml
        section_tree.yaml      <-- here
        <step_id>.md
        <step_id>_rules.md
        <step_id>_validate.json

Why this lives in the compiler (not in ``axcore-v1``)
-----------------------------------------------------

Section semantics are domain knowledge: which sections a frontend
``screen_outline`` artifact carries, what the canonical id for the
"layout" section is, how children nest under a parent. The
``axcore`` kernel is intentionally domain-agnostic — it never
parses compiler template prose. The compiler owns the tree, and
templates *align* to it via deterministic markers (see
:func:`validate_template_alignment`).

Locked schema
-------------

The on-disk file shape is locked at::

    schema: axcore.section-tree/v1
    step_id: <step_id>

    sections:
      - id: SCREEN_OUTLINE
        title: Screen outline
        children:
          - id: SCREEN_OUTLINE.LAYOUT
            title: Layout
          - id: SCREEN_OUTLINE.STATES
            title: States

Top-level keys are restricted to ``schema``, ``step_id``,
``sections``. Section-id format is locked to
:data:`SECTION_ID_PATTERN` and a child id MUST be prefixed by its
parent id plus a literal ``.`` separator. Ids are stable contracts
— renaming an id is a breaking change.

The module is small on purpose: the v1 contract is *just* a
parser, a flat-id projection, and a deterministic alignment
validator. Workflow-scope ("which sections of step X invalidate
step Y?") is the ``section_impacts`` layer and lives elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import yaml

__all__ = [
    "SECTION_TREE_FILENAME",
    "SECTION_TREE_SCHEMA",
    "SECTION_ID_PATTERN",
    "SECTION_MARKER_PATTERN",
    "SectionNode",
    "SectionTree",
    "SectionTreeError",
    "load_section_tree",
    "parse_section_tree",
    "flatten_section_ids",
    "validate_template_alignment",
]


# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

SECTION_TREE_FILENAME: str = "section_tree.yaml"
"""On-disk filename inside a step bundle directory."""

SECTION_TREE_SCHEMA: str = "axcore.section-tree/v1"
"""Locked schema id. Wire incompatibilities bump this."""

SECTION_ID_PATTERN: re.Pattern[str] = re.compile(
    r"^[A-Z][A-Z0-9_]*(\.[A-Z][A-Z0-9_]*)*$"
)
"""Locked id grammar.

Uppercase, dot-separated dotted identifiers: each segment starts
with ``A-Z`` and may contain ``A-Z``, ``0-9``, ``_``. Examples:
``SCREEN_OUTLINE``, ``SCREEN_OUTLINE.LAYOUT``,
``SCREEN_OUTLINE.STATES``. Counter-examples: ``layout``,
``Layout``, ``.SCREEN``, ``SCREEN.``, ``SCREEN..LAYOUT``,
``2D.GRID``.
"""

SECTION_MARKER_PATTERN: re.Pattern[str] = re.compile(
    r"<!--\s*section:\s*([A-Z][A-Z0-9_]*(?:\.[A-Z][A-Z0-9_]*)*)\s*-->"
)
"""Template-side marker grammar.

A section id is bound to its place in a template by the literal
HTML-comment marker ``<!-- section: <ID> -->``. Markers can sit
on their own line or be embedded inline; whitespace around the
``section:`` tag and the id is tolerated, but the marker itself
must be exactly an HTML comment. Anything else is invisible to
the alignment validator.
"""


# Top-level keys accepted in section_tree.yaml.
_ALLOWED_TOP_KEYS: frozenset[str] = frozenset({"schema", "step_id", "sections"})

# Per-section dict keys accepted in section_tree.yaml.
_ALLOWED_SECTION_KEYS: frozenset[str] = frozenset({"id", "title", "children"})


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #


class SectionTreeError(ValueError):
    """Raised on any invalid ``section_tree.yaml`` payload.

    Subclasses ``ValueError`` so callers that already catch
    ``ValueError`` for parse paths keep working; the dedicated type
    is preferred for new code.
    """


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SectionNode:
    """A single section in the tree.

    Frozen + hashable. ``children`` is a tuple (not list) so two
    parsed trees from the same source compare equal and so the
    structure is safe to share across cached call sites.
    """

    id: str
    title: str
    children: tuple[SectionNode, ...] = ()


@dataclass(frozen=True)
class SectionTree:
    """The fully parsed + validated section tree for one step.

    ``flat_ids`` is the pre-order traversal of the tree, computed
    once at parse time so callers (alignment validator,
    workflow-scope impacts) can rely on a deterministic order
    without re-walking the tree.
    """

    step_id: str
    sections: tuple[SectionNode, ...]
    flat_ids: tuple[str, ...] = field(default_factory=tuple)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def load_section_tree(bundle_dir: Path) -> SectionTree | None:
    """Load ``<bundle_dir>/section_tree.yaml`` if present.

    Returns ``None`` when the file is absent — section trees are
    *optional* today; the platform rolls them out per-step. A
    file that is present but malformed raises
    :class:`SectionTreeError` (we do not silently swallow drift).

    The bundle's directory name is used as the expected step id;
    parsers cross-check that the file's ``step_id`` matches.
    """
    bundle_dir = Path(bundle_dir)
    path = bundle_dir / SECTION_TREE_FILENAME
    if not path.is_file():
        return None
    raw_text = path.read_text(encoding="utf-8")
    try:
        raw = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:  # pragma: no cover - delegated to PyYAML
        raise SectionTreeError(f"{path}: not valid YAML ({exc})") from exc
    if not isinstance(raw, dict):
        raise SectionTreeError(
            f"{path}: top-level YAML must be a mapping, got {type(raw).__name__}"
        )
    return parse_section_tree(raw, expected_step_id=bundle_dir.name)


def parse_section_tree(
    raw: dict[str, Any],
    *,
    expected_step_id: str | None = None,
) -> SectionTree:
    """Validate and convert a raw mapping into a :class:`SectionTree`.

    Raises :class:`SectionTreeError` on any contract violation —
    this is the single chokepoint for v1-shape enforcement so the
    failure mode is uniform across ``load_section_tree`` callers
    and tests that hand-build payloads.
    """
    if not isinstance(raw, dict):
        raise SectionTreeError(
            f"section_tree must be a mapping, got {type(raw).__name__}"
        )

    # Top-level key allow-list. Reject unknowns so the schema does
    # not silently grow.
    unknown = set(raw) - _ALLOWED_TOP_KEYS
    if unknown:
        raise SectionTreeError(
            f"unknown top-level key(s): {sorted(unknown)!r}; "
            f"allowed: {sorted(_ALLOWED_TOP_KEYS)!r}"
        )

    schema = raw.get("schema")
    if schema != SECTION_TREE_SCHEMA:
        raise SectionTreeError(
            f"schema mismatch: expected {SECTION_TREE_SCHEMA!r}, got {schema!r}"
        )

    step_id = raw.get("step_id")
    if not isinstance(step_id, str) or not step_id:
        raise SectionTreeError(f"step_id must be a non-empty string, got {step_id!r}")
    if expected_step_id is not None and step_id != expected_step_id:
        raise SectionTreeError(
            f"step_id mismatch: expected {expected_step_id!r}, got {step_id!r}"
        )

    sections_raw = raw.get("sections")
    if not isinstance(sections_raw, list) or not sections_raw:
        raise SectionTreeError("sections must be a non-empty list")

    seen_ids: set[str] = set()
    sections = tuple(
        _parse_section(node, parent_id=None, seen=seen_ids) for node in sections_raw
    )

    flat_ids = flatten_section_ids(sections)
    return SectionTree(step_id=step_id, sections=sections, flat_ids=flat_ids)


def flatten_section_ids(sections: tuple[SectionNode, ...]) -> tuple[str, ...]:
    """Pre-order traversal of section ids.

    Order matters: ``validate_template_alignment`` requires the
    template's marker order to match this projection exactly.
    """
    out: list[str] = []
    for node in sections:
        _flatten_walk(node, out)
    return tuple(out)


def validate_template_alignment(tree: SectionTree, template_text: str) -> list[str]:
    """Return alignment errors between a parsed tree and a template.

    Empty list ⇒ aligned. The validator is fully deterministic:

    1. Every id in ``tree.flat_ids`` must appear at least once as a
       ``<!-- section: ID -->`` marker in ``template_text``.
    2. Every marker found in ``template_text`` must correspond to an
       id in ``tree.flat_ids``.
    3. The first occurrence of each id's marker, scanned in source
       order, must follow the same order as ``tree.flat_ids``
       (the pre-order traversal).

    Errors are returned (not raised) so callers can present them in
    bulk — repair flows want to see all problems at once, not one
    at a time.
    """
    errors: list[str] = []
    tree_ids = tree.flat_ids
    tree_id_set = set(tree_ids)

    # All marker occurrences, in source order.
    marker_hits: list[str] = [
        m.group(1) for m in SECTION_MARKER_PATTERN.finditer(template_text)
    ]

    # 1) Missing markers (tree id never appears).
    seen_in_template = set(marker_hits)
    for tid in tree_ids:
        if tid not in seen_in_template:
            errors.append(f"section_tree id {tid!r} has no marker in template")

    # 2) Markers not in tree.
    for marker_id in marker_hits:
        if marker_id not in tree_id_set:
            errors.append(f"template marker {marker_id!r} is not in section_tree")

    # 3) Order check — first-occurrence order must equal flat_ids.
    # Only compare ids that both sides know about, so we do not
    # double-report the missing/extra cases above as an order error.
    first_seen_order: list[str] = []
    seen: set[str] = set()
    for marker_id in marker_hits:
        if marker_id in tree_id_set and marker_id not in seen:
            first_seen_order.append(marker_id)
            seen.add(marker_id)
    expected_order = [tid for tid in tree_ids if tid in seen]
    if first_seen_order != expected_order:
        errors.append(
            "template marker order does not match section_tree pre-order: "
            f"expected {expected_order!r}, got {first_seen_order!r}"
        )

    return errors


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _parse_section(
    raw: Any,
    *,
    parent_id: str | None,
    seen: set[str],
) -> SectionNode:
    if not isinstance(raw, dict):
        raise SectionTreeError(
            f"section node must be a mapping, got {type(raw).__name__}"
        )

    unknown = set(raw) - _ALLOWED_SECTION_KEYS
    if unknown:
        raise SectionTreeError(
            f"unknown section key(s): {sorted(unknown)!r}; "
            f"allowed: {sorted(_ALLOWED_SECTION_KEYS)!r}"
        )

    sid = raw.get("id")
    if not isinstance(sid, str) or not sid:
        raise SectionTreeError(f"section id must be a non-empty string, got {sid!r}")
    if not SECTION_ID_PATTERN.match(sid):
        raise SectionTreeError(
            f"section id {sid!r} does not match {SECTION_ID_PATTERN.pattern}"
        )

    if parent_id is not None and not sid.startswith(parent_id + "."):
        raise SectionTreeError(
            f"child id {sid!r} must be prefixed by parent id {parent_id!r} plus '.'"
        )

    if sid in seen:
        raise SectionTreeError(f"duplicate section id {sid!r}")
    seen.add(sid)

    title = raw.get("title")
    if not isinstance(title, str) or not title:
        raise SectionTreeError(
            f"section {sid!r} title must be a non-empty string, got {title!r}"
        )

    children_raw = raw.get("children")
    if "children" in raw:
        if not isinstance(children_raw, list):
            raise SectionTreeError(
                f"section {sid!r} children must be a list, "
                f"got {type(children_raw).__name__}"
            )
        if not children_raw:
            raise SectionTreeError(
                f"section {sid!r} has empty children: omit the key when there "
                f"are no children"
            )
        children = tuple(
            _parse_section(child, parent_id=sid, seen=seen) for child in children_raw
        )
    else:
        children = ()

    return SectionNode(id=sid, title=title, children=children)


def _flatten_walk(node: SectionNode, out: list[str]) -> None:
    out.append(node.id)
    for child in node.children:
        _flatten_walk(child, out)
