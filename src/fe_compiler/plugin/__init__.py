"""Plugin entry class + manifest YAML for ``fe-compiler``.

The Python class (:class:`~fe_compiler.plugin.entry.FeCompilerPlugin`)
is intentionally thin. All domain declarations live in
:file:`plugin.yaml`. ``axcore``'s registry reads
``manifest_path`` to locate and load the YAML at discovery time.
"""

from __future__ import annotations

__all__: list[str] = []
