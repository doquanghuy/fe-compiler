"""Plugin discovery provider contract for fe-compiler (P3 + P4).

Verifies that the FE plugin appears correctly in the installed-plugin
discovery result from axcore's provider contract.

Locked invariants:

1. ``fe`` plugin appears in ``discover_installed_plugins()`` result.
2. FE plugin declares the canonical workflow id ``fe-pipeline-v1``.
3. FE workflow file exists on disk and is readable YAML.
4. ``list_workflow_resources`` includes the FE workflow.
5. FE plugin's ``package_root`` resolves to the fe_compiler package directory.
6. No compatibility errors for FE against axcore 0.1.0.
7. FE plugin has correct P4 compat fields: ``requires_axcore``, ``compatible``, ``compatibility_error``.
"""

from __future__ import annotations

import yaml

from axcore.plugins.provider import (
    DiscoveredPlugin,
    PluginDiscoveryResult,
    collect_workflow_roots,
    discover_installed_plugins,
    list_workflow_resources,
)

_FE_WORKFLOW_IDS = frozenset({"fe-pipeline-v1"})


def _result() -> PluginDiscoveryResult:
    return discover_installed_plugins(axcore_version="0.1.0")


def _fe_plugin() -> DiscoveredPlugin:
    result = _result()
    for p in result.plugins:
        if p.plugin_id == "fe":
            return p
    raise AssertionError("'fe' plugin not found in discovery result")


# ---------------------------------------------------------------------------
# 1 — fe appears in discovered plugins
# ---------------------------------------------------------------------------


def test_fe_appears_in_discovered_plugins() -> None:
    ids = {p.plugin_id for p in _result().plugins}
    assert "fe" in ids, f"expected 'fe' in discovered plugins; got {ids!r}"


def test_fe_discovery_result_has_no_errors() -> None:
    result = _result()
    assert not result.errors, f"unexpected discovery errors: {result.errors!r}"


# ---------------------------------------------------------------------------
# 2 — canonical workflow id
# ---------------------------------------------------------------------------


def test_fe_pipeline_v1_in_workflow_ids() -> None:
    assert "fe-pipeline-v1" in _fe_plugin().workflow_ids


def test_fe_has_exactly_one_workflow_id() -> None:
    dp = _fe_plugin()
    assert set(dp.workflow_ids) == _FE_WORKFLOW_IDS, (
        f"expected {sorted(_FE_WORKFLOW_IDS)!r}; got {sorted(dp.workflow_ids)!r}"
    )


# ---------------------------------------------------------------------------
# 3 — workflow file exists and is valid YAML
# ---------------------------------------------------------------------------


def test_fe_workflow_files_exist() -> None:
    dp = _fe_plugin()
    for f in dp.workflow_files:
        assert f.is_file(), f"FE workflow file not on disk: {f}"


def test_fe_workflow_file_is_valid_yaml() -> None:
    dp = _fe_plugin()
    for f in dp.workflow_files:
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"FE workflow {f.name!r} did not parse to dict"


def test_fe_workflow_ids_and_files_parallel() -> None:
    dp = _fe_plugin()
    assert len(dp.workflow_ids) == len(dp.workflow_files), (
        "workflow_ids and workflow_files must be parallel sequences"
    )


# ---------------------------------------------------------------------------
# 4 — list_workflow_resources includes FE workflow
# ---------------------------------------------------------------------------


def test_list_workflow_resources_includes_fe_pipeline_v1() -> None:
    result = _result()
    ids = {wr.workflow_id for wr in list_workflow_resources(result) if wr.plugin_id == "fe"}
    assert "fe-pipeline-v1" in ids


def test_list_workflow_resources_fe_path_exists() -> None:
    result = _result()
    for wr in list_workflow_resources(result):
        if wr.plugin_id == "fe":
            assert wr.path.is_file(), f"FE workflow resource path not on disk: {wr.path}"


# ---------------------------------------------------------------------------
# 5 — package_root resolves to fe_compiler package directory
# ---------------------------------------------------------------------------


def test_fe_package_root_is_directory() -> None:
    dp = _fe_plugin()
    assert dp.package_root.is_dir(), f"fe package_root not a directory: {dp.package_root}"


def test_fe_package_root_contains_fe_compiler_package() -> None:
    dp = _fe_plugin()
    assert dp.package_root.name == "fe_compiler" or (
        (dp.package_root / "__init__.py").is_file()
    ), f"fe package_root does not look like fe_compiler package: {dp.package_root}"


# ---------------------------------------------------------------------------
# 6 — no compatibility errors against axcore 0.1.0
# ---------------------------------------------------------------------------


def test_fe_no_compatibility_errors() -> None:
    result = _result()
    compat_errors = [e for e in result.errors if "fe" in e and "requires.axcore" in e]
    assert not compat_errors, (
        f"unexpected compatibility errors for FE plugin: {compat_errors!r}"
    )


# ---------------------------------------------------------------------------
# 7 — P4 compat fields for FE plugin
# ---------------------------------------------------------------------------


def test_fe_compatible_is_true() -> None:
    dp = _fe_plugin()
    assert dp.compatible, (
        f"FE plugin should be compatible against axcore 0.1.0; "
        f"compatibility_error={dp.compatibility_error!r}"
    )


def test_fe_requires_axcore_populated() -> None:
    dp = _fe_plugin()
    assert dp.requires_axcore, "FE plugin has empty requires_axcore field"


def test_fe_requires_axcore_value() -> None:
    dp = _fe_plugin()
    assert dp.requires_axcore == ">=0.1.0,<0.2.0", (
        f"unexpected requires_axcore: {dp.requires_axcore!r}"
    )


def test_fe_compatibility_error_empty() -> None:
    dp = _fe_plugin()
    assert dp.compatibility_error == "", (
        f"FE plugin should have no compatibility_error; got {dp.compatibility_error!r}"
    )


# ---------------------------------------------------------------------------
# collect_workflow_roots includes FE workflow directory
# ---------------------------------------------------------------------------


def test_collect_workflow_roots_includes_fe_dir() -> None:
    result = _result()
    roots = collect_workflow_roots(result)
    dp = _fe_plugin()
    fe_dirs = set(dp.workflow_dirs)
    overlap = fe_dirs & set(roots)
    assert overlap, (
        f"collect_workflow_roots does not include any FE workflow dir; "
        f"fe_dirs={[str(d) for d in fe_dirs]!r}, roots={[str(r) for r in roots]!r}"
    )
