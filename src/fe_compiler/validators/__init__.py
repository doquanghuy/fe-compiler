"""Domain-specific validators for ``fe-compiler`` (scaffold).

Today the frontend steps rely entirely on ``axcore``'s
deterministic-check runner (section-presence, placeholder
resolution, marker integrity). Future frontend-specific semantic
validators (e.g. navigation graph reachability) would land here
and would register via the plugin manifest's ``validator_hooks``
list.
"""

from __future__ import annotations

__all__: list[str] = []
