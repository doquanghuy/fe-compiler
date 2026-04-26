"""End-to-end lock of the `fe/screen_outline` step through the kernel.

Walks `Kernel.run_step("fe", "screen_outline", ...)` against the
real bundle and verifies:

- the bundle loads cleanly;
- the canonical phase plan runs (no required_inputs → empty upstream);
- the produced artifact is persisted with the expected ref and
  content type;
- the wire JSON projection matches the canonical v5 shape;
- improve / rebuild runs thread lineage correctly.

Tagged ``integration`` because it requires both ``axcore-v1``
and ``fe-compiler-v1`` installed in the active env (entry-point
discovery + on-disk artifact store).
"""

from __future__ import annotations

from pathlib import Path

from axcore.api import Kernel, PluginRegistry, step_result_summary
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    proot = tmp_path / "project"
    (proot / ".specify").mkdir(parents=True)
    return proot


@pytest.fixture
def kernel(project_root: Path) -> Kernel:
    return Kernel(PluginRegistry.discover(), project_root=project_root)


# --------------------------------------------------------------------------- #
# Bundle load + run
# --------------------------------------------------------------------------- #


def test_kernel_can_load_the_screen_outline_bundle(kernel: Kernel) -> None:
    bundle = kernel.load_step_bundle("fe", "screen_outline")
    assert bundle.plugin_id == "fe"
    assert bundle.step_id == "screen_outline"
    # Entry step: no upstream consumption.
    assert (bundle.raw.get("required_inputs") or []) == []


def test_screen_outline_runs_and_persists(kernel: Kernel) -> None:
    r = kernel.run_step("fe", "screen_outline", intent="auto")
    assert r.status == "ok"
    assert r.artifact.ref == "fe.screen_outline.placeholder"
    # No upstream → empty generation context + empty signature.
    assert r.generation_context.upstream_artifacts == ()
    assert r.artifact.input_signature == ()


def test_screen_outline_improve_records_lineage(kernel: Kernel) -> None:
    kernel.run_step("fe", "screen_outline", intent="auto")
    r = kernel.run_step("fe", "screen_outline", intent="improve", human_notes="more")
    assert r.status == "improved"
    assert r.artifact.ref == "fe.screen_outline.improved"
    assert r.artifact.parent_ref == "fe.screen_outline.placeholder"


# --------------------------------------------------------------------------- #
# Wire JSON — canonical v5 projection
# --------------------------------------------------------------------------- #


def test_screen_outline_wire_projection_is_canonical(kernel: Kernel) -> None:
    r = kernel.run_step("fe", "screen_outline", intent="auto")
    s = step_result_summary(r)
    assert s["schema"] == "axcore.step-result/v5"
    assert s["plugin_id"] == "fe"
    assert s["step_id"] == "screen_outline"
    assert s["status"] == "ok"
    assert s["artifact"]["ref"] == "fe.screen_outline.placeholder"
    # Single-output bundle → empty supplementary list.
    assert s["supplementary_artifacts"] == []
    # No upstream → empty input_signature on the wire.
    assert s["artifact"]["input_signature"] == []


# --------------------------------------------------------------------------- #
# Cross-process persistence — a fresh Kernel sees the same artifact
# --------------------------------------------------------------------------- #


def test_persistence_survives_fresh_kernel(project_root: Path) -> None:
    k1 = Kernel(PluginRegistry.discover(), project_root=project_root)
    k1.run_step("fe", "screen_outline", intent="auto")
    k2 = Kernel(PluginRegistry.discover(), project_root=project_root)
    a = k2.read_artifact("fe.screen_outline.placeholder")
    assert a.content_type == "text/markdown"
    assert len(a.hash) == 64  # sha256 hex
