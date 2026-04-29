"""``flows`` — artifact-type container for frontend step bundles.

``flows/`` is a **container directory**, not a step. Each
subdirectory (``flows/<step>/``) is one step bundle with its
own ``bundle.yaml`` and typed resources.

The plugin manifest's ``bundle_roots`` points at this directory;
the axcore registry walks it recursively to discover every
step bundle shipped by ``fe-compiler``.

Shipped today: ``screen_outline``. Future frontend steps land
here as sibling subdirectories.
"""

from __future__ import annotations

__all__: list[str] = []
