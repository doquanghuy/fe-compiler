"""axcore plugin entry class for fe-compiler.

``axcore`` discovers consumer plugins through the
``axcore.plugins`` entry-point group (see ``pyproject.toml``).
The entry points resolve to :class:`~axcore.api.Plugin`
subclasses. This module defines the one this package exposes.

Identity summary:

- ``plugin_id``           ``fe``
- Importable package       ``fe_compiler``
- Distribution             ``fe-compiler``
- Entry-point group        ``axcore.plugins``
- Entry-point name         ``fe``

The class is thin. All domain declarations (workflows, steps,
bundle roots) live in :file:`plugin.yaml`. ``axcore``'s
registry reads ``manifest_path`` to load the manifest at
discovery time.

Section-stale position
----------------------

FE explicitly does **not** support runtime section-stale at v1.

The package ships the section-stale *foundation* — a parsed
``section_tree.yaml`` for the ``screen_outline`` step, plus the
:mod:`fe_compiler.section_tree` and
:mod:`fe_compiler.section_impacts` parsers / validators — but the
runtime hooks ``load_section_impact_graph`` and
``extract_section_hashes`` are deliberate ``return None``
overrides. This position is locked because:

- the canonical FE workflow (``fe-pipeline-v1``) has a single
  entry step (``screen_outline``) with no downstream consumers;
- FE ships zero ``section_impacts.<workflow>.yaml`` files (locked
  by ``tests/unit/test_real_fe_section_configs.py``);
- with no downstream consumer of section-level change information,
  emitting per-section hashes or building an impact graph would
  be carry-only bookkeeping that nothing would ever read.

When FE grows a downstream step that genuinely consumes section
precision, override the two hooks below — the
``section_tree.yaml`` foundation is already in place to make
that override straightforward.

Operators / test suites that need a machine-checkable signal
should read ``FeCompilerPlugin.SECTION_STALE_SUPPORTED`` (a
class attribute that is ``False`` at v1).
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from axcore.api import Plugin, PluginMetadata, SectionImpactGraph

from fe_compiler import __version__ as _package_version


def _manifest_path() -> Path:
    """Return the on-disk path to the plugin manifest YAML.

    The manifest is packaged as data (see
    ``[tool.setuptools.package-data]`` in ``pyproject.toml``) so
    it is reachable both from a source checkout and from an
    installed wheel.
    """
    manifest = resources.files("fe_compiler.plugin").joinpath("plugin.yaml")
    return Path(str(manifest))


class FeCompilerPlugin(Plugin):
    """Frontend-compiler plugin registered with ``axcore``.

    ``metadata.name`` MUST match the ``plugin_id`` in
    ``plugin.yaml`` (``"fe"``) — ``axcore``'s registry uses
    that field as the dedup key and cross-checks it against the
    manifest at load time.

    Section-stale support is explicitly OFF at v1 — see the module
    docstring for the architectural rationale and the
    :attr:`SECTION_STALE_SUPPORTED` machine-checkable marker.
    """

    metadata: PluginMetadata = PluginMetadata(
        name="fe",
        version=_package_version,
        summary="Frontend-domain compiler plugin built on axcore.",
    )

    #: On-disk path to the plugin manifest YAML. ``axcore``'s
    #: registry reads this at discovery time to load the manifest.
    manifest_path: Path = _manifest_path()

    #: Explicit, machine-checkable marker that FE does NOT support runtime
    #: section-stale at v1. Test suites and integration tests can read this
    #: attribute instead of probing whether the hooks return ``None``. See
    #: module docstring for the architectural rationale.
    SECTION_STALE_SUPPORTED: bool = False

    def load_section_impact_graph(self, workflow_id: str) -> SectionImpactGraph | None:
        """Explicit non-support: FE has no section-impact graph at v1.

        This override exists to make FE's "no section-stale" position
        structurally explicit instead of inheriting a silent base-class
        default. FE ships zero
        ``section_impacts.<workflow_id>.yaml`` files (the test
        suite ``test_real_fe_section_configs.py`` locks the empty
        impacts ledger); there is therefore nothing to build a
        graph from. Returning ``None`` is the documented "section
        precision is not available for this plugin/workflow"
        signal that ``axcore.api.compute_section_stale_report``
        and the ``axcore.stale-show`` SKILL section-mode treat as
        a clean opt-out.

        When FE adds a downstream step that genuinely consumes
        section precision, this override is the single place the
        opt-in lands (build the graph from the section-impacts
        files via :mod:`fe_compiler.section_impacts`).
        """
        del workflow_id  # explicit non-use
        return None

    def extract_section_hashes(
        self, step_id: str, content: bytes
    ) -> dict[str, str] | None:
        """Explicit non-support: FE does not stamp per-section hashes.

        Same rationale as :meth:`load_section_impact_graph`. FE has the
        ``section_tree.yaml`` for ``screen_outline`` parsed and
        validated, but no downstream step consumes per-section
        change information at v1. Emitting per-section hashes
        here would write a payload no caller reads.

        The kernel always carries the artifact's regular
        ``input_signature`` (step-level hash); this method
        controls only the *section-level* opt-in. Returning
        ``None`` keeps ``Artifact.section_input_signature`` empty,
        which is the backward-compatible default for every legacy
        bundle.

        When FE adds a downstream consumer of section precision,
        this override switches to a real per-section hash
        emitter (parsing the content via the validated
        ``section_tree.yaml`` for the named ``step_id``).
        """
        del step_id, content  # explicit non-use
        return None
