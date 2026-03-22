from __future__ import annotations

from dataclasses import dataclass

from accessibility import AccessibilityNeed


@dataclass(frozen=True)
class Passenger:
    accessibility_needs: set[AccessibilityNeed]
    start_station: str
    end_station: str
