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


# station-relevant needs
STATION_NEEDS: set[AccessibilityNeed] = {
    AccessibilityNeed.WHEELCHAIR_ACCESS,
    AccessibilityNeed.ELEVATOR,
    AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
    AccessibilityNeed.VISUAL_SIGNAGE,
    AccessibilityNeed.TACTILE_GUIDANCE,
}

# vehicle-relevant needs
VEHICLE_NEEDS: set[AccessibilityNeed] = {
    AccessibilityNeed.WHEELCHAIR_ACCESS,
    AccessibilityNeed.LOW_FLOOR_BOARDING,
    AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
    AccessibilityNeed.VISUAL_SIGNAGE,
    AccessibilityNeed.AUTOMATIC_DOORS,
    AccessibilityNeed.ACCESSIBLE_SEATING,
}


def station_relevant(needs: set[AccessibilityNeed]) -> set[AccessibilityNeed]:
    return needs & STATION_NEEDS


def vehicle_relevant(needs: set[AccessibilityNeed]) -> set[AccessibilityNeed]:
    return needs & VEHICLE_NEEDS


@dataclass
class AccessibleEntity:
    """Base class (heritage) for entities with accessibility traits."""

    accessibility_traits: set[AccessibilityNeed] = field(default_factory=set)

    def supports_all(self, needs: set[AccessibilityNeed]) -> bool:
        return needs.issubset(self.accessibility_traits)
