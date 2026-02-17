from __future__ import annotations

from dataclasses import dataclass

from accessibility import AccessibleEntity


@dataclass
class Vehicle(AccessibleEntity):
    vehicle_type: str = ""
