"""fe-compiler — frontend-domain compiler package built on axcore.

Sibling of ``be-compiler``. Contributes a plugin manifest, one
Spec Kit workflow definition (``fe-pipeline``), and one real
step bundle (``screen_outline``) against the
mode-specific step-run SKILL handlers that ``axcore`` ships.

End users run the pipeline through Spec Kit
(``specify workflow run fe-pipeline``); this package never
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
__version__: str = "0.1.1"
