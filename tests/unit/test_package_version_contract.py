"""Lock the fe-compiler package versioning and compatibility contract.

Locked invariants:

1. Distribution name is `fe-compiler`.
2. Package version is `0.1.0`.
3. `fe_compiler.__version__` matches pyproject.toml version.
4. `plugin.yaml` version matches package version.
5. `plugin.yaml` declares axcore compatibility `>=0.1.0,<0.2.0`.
6. Production workflow version is `0.1.0`.
7. Production workflow status is `production`.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOWS_DIR = _REPO_ROOT / "src" / "fe_compiler" / "workflows"
_PLUGIN_MANIFEST = _REPO_ROOT / "src" / "fe_compiler" / "plugin" / "plugin.yaml"

_EXPECTED_VERSION = "0.1.0"
_EXPECTED_DIST_NAME = "fe-compiler"
_PRODUCTION_WORKFLOW = "fe_pipeline.yaml"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# 1-3 — Package name and version
# --------------------------------------------------------------------------- #


def test_dist_name_is_canonical() -> None:
    pyproject = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'name = "{_EXPECTED_DIST_NAME}"' in pyproject, (
        f"pyproject.toml must have name = {_EXPECTED_DIST_NAME!r}"
    )


def test_pyproject_version_is_0_1_0() -> None:
    pyproject = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{_EXPECTED_VERSION}"' in pyproject


def test_package_version_matches_pyproject() -> None:
    import fe_compiler

    pyproject = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert fe_compiler.__version__ == _EXPECTED_VERSION
    assert f'version = "{fe_compiler.__version__}"' in pyproject


# --------------------------------------------------------------------------- #
# 4-5 — Plugin manifest version and compatibility
# --------------------------------------------------------------------------- #


def test_plugin_yaml_version_matches_package_version() -> None:
    import fe_compiler

    manifest = _load_yaml(_PLUGIN_MANIFEST)
    assert manifest.get("version") == fe_compiler.__version__, (
        f"plugin.yaml version {manifest.get('version')!r} must match "
        f"fe_compiler.__version__ {fe_compiler.__version__!r}"
    )


def test_plugin_yaml_requires_axcore_compat() -> None:
    manifest = _load_yaml(_PLUGIN_MANIFEST)
    requires = manifest.get("requires") or {}
    axcore_req = requires.get("axcore", "")
    assert ">=0.1.0" in axcore_req, (
        f"plugin.yaml requires.axcore must declare >=0.1.0 compat; got {axcore_req!r}"
    )
    assert "<0.2.0" in axcore_req, (
        f"plugin.yaml requires.axcore must declare <0.2.0 upper bound; got {axcore_req!r}"
    )


# --------------------------------------------------------------------------- #
# 6-7 — Production workflow version and status
# --------------------------------------------------------------------------- #


def test_production_workflow_has_version_0_1_0() -> None:
    data = _load_yaml(_WORKFLOWS_DIR / _PRODUCTION_WORKFLOW)
    wf_version = (data.get("workflow") or {}).get("version")
    assert wf_version == _EXPECTED_VERSION, (
        f"{_PRODUCTION_WORKFLOW} workflow.version must be {_EXPECTED_VERSION!r}; "
        f"got {wf_version!r}"
    )


def test_production_workflow_has_status_production() -> None:
    data = _load_yaml(_WORKFLOWS_DIR / _PRODUCTION_WORKFLOW)
    status = (data.get("workflow") or {}).get("workflow_status")
    assert status == "production", (
        f"{_PRODUCTION_WORKFLOW} workflow_status must be 'production'; got {status!r}"
    )
