"""Package-data helpers for fe-compiler.

All helpers use :func:`importlib.resources.files` so they work from both
an editable source checkout and a wheel installation.  No path is
constructed relative to ``__file__``.

Usage::

    from fe_compiler.assets import (
        get_plugin_manifest_path,
        iter_workflow_files,
        iter_bundle_flow_dirs,
    )

    manifest_text = get_plugin_manifest_path().read_text(encoding="utf-8")

    for wf in iter_workflow_files():
        print(wf.name)

    for flow_dir in iter_bundle_flow_dirs():
        bundle_yaml = flow_dir / "bundle.yaml"
        print(bundle_yaml.read_text(encoding="utf-8")[:80])
"""

from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable


def get_plugin_manifest_path() -> Traversable:
    """Return the packaged ``plugin.yaml`` as a :class:`Traversable`."""
    return files("fe_compiler.plugin") / "plugin.yaml"


def iter_workflow_files() -> list[Traversable]:
    """Return all packaged workflow ``.yaml`` files, sorted by name."""
    wf_dir = files("fe_compiler.workflows")
    return sorted(
        (
            f
            for f in wf_dir.iterdir()
            if f.name.endswith(".yaml") or f.name.endswith(".yml")
        ),
        key=lambda f: f.name,
    )


def iter_bundle_flow_dirs() -> list[Traversable]:
    """Return each flow bundle directory under ``fe_compiler/bundles/flows/``.

    Each entry is a :class:`Traversable` pointing to a flow subdirectory
    that contains at least a ``bundle.yaml``.
    """
    flows_dir = files("fe_compiler.bundles.flows")
    return sorted(
        (d for d in flows_dir.iterdir() if not d.name.startswith("_")),
        key=lambda d: d.name,
    )
