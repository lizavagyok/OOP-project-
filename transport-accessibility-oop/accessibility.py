from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class AccessibilityNeed(Enum):
    WHEELCHAIR_ACCESS = auto()
    ELEVATOR = auto()
    AUDIO_ANNOUNCEMENTS = auto()
    VISUAL_SIGNAGE = auto()
    LOW_FLOOR_BOARDING = auto()
    TACTILE_GUIDANCE = auto()
    AUTOMATIC_DOORS = auto()
    ACCESSIBLE_SEATING = auto()
    


@dataclass
class AccessibleEntity:
    """Base class (heritage) for entities with accessibility traits."""

    accessibility_traits: set[AccessibilityNeed] = field(default_factory=set)

    def supports_all(self, needs: set[AccessibilityNeed]) -> bool:
        return needs.issubset(self.accessibility_traits)
