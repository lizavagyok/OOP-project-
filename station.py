from __future__ import annotations

from dataclasses import dataclass

from accessibility import AccessibleEntity


@dataclass
class Station(AccessibleEntity):
    name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
