"""fe-compiler-v1 — frontend-domain compiler package built on axcore-v1.

Sibling of ``be-compiler-v1``. Contributes a plugin manifest, one
Spec Kit workflow definition (``fe-pipeline-v1``), and one real
step bundle (``screen_outline``) against the
``speckit.axcore.step-run`` SKILL that ``axcore-v1`` ships.

End users run the pipeline through Spec Kit
(``specify workflow run fe-pipeline-v1``); this package never
implements orchestration.

Subpackages:

- ``fe_compiler.plugin``    — plugin entry class + manifest YAML.
- ``fe_compiler.workflows`` — Spec Kit workflow definitions.
- ``fe_compiler.bundles``   — step bundles (one per step, under
                              ``flows/<step-id>/``).
- ``fe_compiler.validators``— domain-specific validators (scaffold).
- ``fe_compiler.cli``       — optional developer CLI (scaffold).
"""

from __future__ import annotations

__all__: list[str] = ["__version__"]
__version__: str = "0.1.0"
