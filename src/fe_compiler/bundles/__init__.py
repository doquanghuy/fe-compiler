"""Step bundles shipped by ``fe-compiler``.

Bundles live under :mod:`fe_compiler.bundles.flows` (one
subdirectory per step). The plugin manifest's ``bundle_roots``
points at ``bundles/flows/``; the axcore registry walks it
recursively to discover every step bundle this package ships.
"""

from __future__ import annotations

__all__: list[str] = []
