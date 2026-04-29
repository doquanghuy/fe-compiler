"""Lock ``fe-compiler`` plugin discovery + manifest shape.

These tests prove the minimum identity contract:

- the package is installed and reachable via the ``axcore.plugins``
  entry point with name ``"fe"``;
- the entry-point class constructs + carries ``metadata.name == "fe"``;
- the manifest YAML loads with the locked identity fields;
- the plugin declares exactly one workflow id (``fe-pipeline-v1``);
- the plugin declares exactly one step (``screen_outline``); and
- the step bundle resolves and carries the expected resource
  keys (template / rules / validation_spec).

The tests are structural, not runtime-dependent: they do not
exercise the axcore kernel end-to-end. Kernel-side integration
(bundle loading, cross-step consumption, wire projection) is
covered by ``tests/test_screen_outline_step.py``.
"""

from __future__ import annotations

import importlib.metadata as importlib_metadata
from pathlib import Path

from axcore.api import PluginRegistry
import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PLUGIN_MANIFEST = _REPO_ROOT / "src" / "fe_compiler" / "plugin" / "plugin.yaml"


# --------------------------------------------------------------------------- #
# Entry-point discovery
# --------------------------------------------------------------------------- #


def test_fe_plugin_entry_point_is_registered_under_axcore_plugins() -> None:
    """``axcore.plugins`` entry-point group must expose a ``fe`` entry."""
    eps = importlib_metadata.entry_points(group="axcore.plugins")
    names = [ep.name for ep in eps]
    assert "fe" in names, (
        f"axcore.plugins entry-point group is missing `fe`; saw {names!r}. "
        "Is fe-compiler pip-installed in the active environment?"
    )


def test_fe_plugin_entry_point_resolves_to_the_plugin_class() -> None:
    from fe_compiler.plugin.entry import FeCompilerPlugin

    eps = importlib_metadata.entry_points(group="axcore.plugins", name="fe")
    ep_iter = list(eps)
    assert len(ep_iter) == 1, (
        f"expected exactly one `fe` entry point; saw {len(ep_iter)}"
    )
    loaded = ep_iter[0].load()
    assert loaded is FeCompilerPlugin


def test_fe_plugin_metadata_identity() -> None:
    from fe_compiler.plugin.entry import FeCompilerPlugin

    md = FeCompilerPlugin.metadata
    assert md.name == "fe"
    assert isinstance(md.version, str) and md.version
    assert "frontend" in md.summary.lower()


# --------------------------------------------------------------------------- #
# Manifest YAML shape
# --------------------------------------------------------------------------- #


def _manifest() -> dict:
    return yaml.safe_load(_PLUGIN_MANIFEST.read_text(encoding="utf-8"))


def test_manifest_identity_fields() -> None:
    data = _manifest()
    assert data["plugin_id"] == "fe"
    assert isinstance(data["version"], str) and data["version"]
    assert data["bundle_roots"] == ["bundles/flows/"]


def test_manifest_declares_pipeline_workflow() -> None:
    data = _manifest()
    workflows = data.get("workflows") or []
    assert len(workflows) == 1, (
        "fe-compiler ships one workflow today; splitting into "
        "multiple workflows is a deliberate architectural decision."
    )
    assert workflows[0]["id"] == "fe-pipeline-v1"
    assert workflows[0]["file"] == "workflows/fe_pipeline_v1.yaml"


def test_manifest_declares_one_real_step() -> None:
    data = _manifest()
    assert data["steps"] == ["screen_outline"], (
        f"fe-compiler's shipped step set drifted; got {data['steps']!r}"
    )


def test_manifest_capabilities_mark_the_package_as_frontend_domain() -> None:
    data = _manifest()
    assert "frontend-domain" in (data.get("capabilities") or [])


# --------------------------------------------------------------------------- #
# Kernel-side discovery — the registry sees fe cleanly alongside anything else
# --------------------------------------------------------------------------- #


@pytest.fixture
def registry() -> PluginRegistry:
    return PluginRegistry.discover()


def test_registry_discovers_fe_plugin(registry: PluginRegistry) -> None:
    assert "fe" in registry.names(), (
        f"axcore PluginRegistry did not discover `fe`; names={registry.names()!r}"
    )


def test_registry_workflow_ids_for_fe(registry: PluginRegistry) -> None:
    assert registry.workflow_ids("fe") == ["fe-pipeline-v1"]


def test_registry_can_load_the_screen_outline_bundle(
    registry: PluginRegistry,
) -> None:
    bundle = registry.get_bundle_manifest("fe", "screen_outline")
    assert bundle["step_id"] == "screen_outline"
    # Every FE bundle must declare the same resource trio as the BE
    # bundles — the kernel's deterministic check runner keys off
    # the `validation_spec` type, not any FE-specific shape.
    resources = bundle["resources"]
    assert set(resources) >= {"template", "rules", "validate"}
    assert resources["template"]["type"] == "template"
    assert resources["rules"]["type"] == "rules"
    assert resources["validate"]["type"] == "validation_spec"
