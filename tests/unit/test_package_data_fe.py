"""Verify fe-compiler package data is complete and accessible.

Locked invariants:

1. ``plugin.yaml`` is accessible via importlib.resources.
2. Production workflow YAML is accessible via package data.
3. Bundle flow directories are accessible via package data.
4. Bundle assets (bundle.yaml, templates, validators) are accessible.
5. Package-data workflow list matches filesystem workflow list.
6. Package-data bundle flow list matches filesystem bundle list.
7. No registered production workflow is missing from package data.
8. Package-data access does not depend on sibling repo paths.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import yaml

import fe_compiler.assets as _assets

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src" / "fe_compiler"
_WORKFLOWS_DIR = _SRC_ROOT / "workflows"
_BUNDLES_FLOWS_DIR = _SRC_ROOT / "bundles" / "flows"


# --------------------------------------------------------------------------- #
# 1 — plugin.yaml accessible via importlib.resources
# --------------------------------------------------------------------------- #


def test_plugin_manifest_readable_from_package_data() -> None:
    manifest = _assets.get_plugin_manifest_path()
    content = manifest.read_text(encoding="utf-8")
    assert content.strip(), "plugin.yaml is empty"
    data = yaml.safe_load(content)
    assert data.get("plugin_id") == "fe"


def test_plugin_manifest_version_0_1_0() -> None:
    data = yaml.safe_load(
        _assets.get_plugin_manifest_path().read_text(encoding="utf-8")
    )
    assert data.get("version") == "0.1.0"


def test_plugin_manifest_requires_axcore_compat() -> None:
    data = yaml.safe_load(
        _assets.get_plugin_manifest_path().read_text(encoding="utf-8")
    )
    axcore_req = (data.get("requires") or {}).get("axcore", "")
    assert ">=0.1.0" in axcore_req
    assert "<0.2.0" in axcore_req


# --------------------------------------------------------------------------- #
# 2 — production workflow accessible
# --------------------------------------------------------------------------- #


def test_fe_pipeline_present_in_package_data() -> None:
    wf_names = {f.name for f in _assets.iter_workflow_files()}
    assert "fe_pipeline.yaml" in wf_names


def test_workflow_files_are_valid_yaml() -> None:
    for wf in _assets.iter_workflow_files():
        content = wf.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        assert isinstance(data, dict), f"workflow {wf.name!r} did not parse to dict"


# --------------------------------------------------------------------------- #
# 3 — bundle flow dirs accessible
# --------------------------------------------------------------------------- #


def test_bundle_flow_dirs_non_empty() -> None:
    dirs = _assets.iter_bundle_flow_dirs()
    assert len(dirs) > 0, "iter_bundle_flow_dirs returned no flow directories"


def test_each_bundle_flow_dir_has_bundle_yaml() -> None:
    for flow_dir in _assets.iter_bundle_flow_dirs():
        bundle_yaml = flow_dir / "bundle.yaml"
        content = bundle_yaml.read_bytes()
        assert content, f"bundle.yaml missing or empty in flow {flow_dir.name!r}"


# --------------------------------------------------------------------------- #
# 4 — bundle assets accessible
# --------------------------------------------------------------------------- #


def test_bundle_yaml_files_are_valid_yaml() -> None:
    for flow_dir in _assets.iter_bundle_flow_dirs():
        bundle_yaml = flow_dir / "bundle.yaml"
        data = yaml.safe_load(bundle_yaml.read_text(encoding="utf-8"))
        assert isinstance(data, dict), (
            f"bundle.yaml in {flow_dir.name!r} did not parse to dict"
        )


def test_bundle_markdown_templates_accessible() -> None:
    for flow_dir in _assets.iter_bundle_flow_dirs():
        md_files = [f for f in flow_dir.iterdir() if f.name.endswith(".md")]
        assert md_files, f"no .md template found in bundle flow {flow_dir.name!r}"


# --------------------------------------------------------------------------- #
# 5 — package-data workflow list matches filesystem list
# --------------------------------------------------------------------------- #


def test_workflow_list_matches_filesystem() -> None:
    fs_workflows = {
        p.name
        for p in _WORKFLOWS_DIR.iterdir()
        if p.suffix in (".yaml", ".yml") and p.is_file()
    }
    pkg_workflows = {f.name for f in _assets.iter_workflow_files()}
    assert fs_workflows == pkg_workflows, (
        f"workflow list mismatch — filesystem: {sorted(fs_workflows)}, "
        f"package: {sorted(pkg_workflows)}"
    )


# --------------------------------------------------------------------------- #
# 6 — package-data bundle list matches filesystem list
# --------------------------------------------------------------------------- #


def test_bundle_flow_list_matches_filesystem() -> None:
    fs_flows = {
        p.name
        for p in _BUNDLES_FLOWS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    }
    pkg_flows = {d.name for d in _assets.iter_bundle_flow_dirs()}
    assert fs_flows == pkg_flows, (
        f"bundle flow list mismatch — filesystem: {sorted(fs_flows)}, "
        f"package: {sorted(pkg_flows)}"
    )


# --------------------------------------------------------------------------- #
# 7 — no registered production workflow missing from package data
# --------------------------------------------------------------------------- #


def test_registered_workflows_all_present_in_package_data() -> None:
    manifest_data = yaml.safe_load(
        _assets.get_plugin_manifest_path().read_text(encoding="utf-8")
    )
    registered_ids = {
        e["id"] for e in (manifest_data.get("workflows") or []) if isinstance(e, dict)
    }
    wf_names_no_ext = {
        f.name.replace("-", "_").removesuffix(".yaml").removesuffix(".yml")
        for f in _assets.iter_workflow_files()
    }
    for wf_id in registered_ids:
        norm = wf_id.replace("-", "_")
        assert norm in wf_names_no_ext, (
            f"registered workflow {wf_id!r} has no matching YAML in package data"
        )


# --------------------------------------------------------------------------- #
# 8 — package-data access does not depend on sibling repo paths
# --------------------------------------------------------------------------- #


def test_plugin_manifest_readable_via_traversable_only() -> None:
    traversable = files("fe_compiler.plugin") / "plugin.yaml"
    assert len(traversable.read_bytes()) > 0


def test_workflow_yaml_readable_via_traversable_only() -> None:
    traversable = files("fe_compiler.workflows") / "fe_pipeline.yaml"
    assert len(traversable.read_bytes()) > 0


def test_bundle_yaml_readable_via_traversable_only() -> None:
    traversable = files("fe_compiler.bundles.flows") / "screen_outline" / "bundle.yaml"
    assert len(traversable.read_bytes()) > 0
