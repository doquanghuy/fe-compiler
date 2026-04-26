"""Frontend workflow definitions — Spec Kit schema v1.0.

Each ``.yaml`` file in this package is a Spec Kit workflow
definition. Workflows execute inside Spec Kit; action steps in
those workflows dispatch ``axcore.*`` commands (see
``axcore-v1/docs/spec-kit-extension.md``). This subpackage only
ships the declarations — no runtime code.

The plugin manifest (``fe_compiler/plugin/plugin.yaml``)
enumerates which workflow files in this directory are registered
under which ids. Files not listed in the manifest are ignored —
they may exist as drafts or documentation-only references.

Shipped today:

- ``fe_pipeline_v1.yaml`` — workflow ``fe-pipeline-v1``. Single
  entry step (``screen_outline``) dispatched via the canonical
  ``/speckit-axcore-step-run`` slash form. No gate, no fan-out,
  no fan-in — the smallest honest end-to-end shape that proves
  the FE plugin participates in the shared final path.
"""

from __future__ import annotations

__all__: list[str] = []
