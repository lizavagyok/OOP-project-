from __future__ import annotations

from dataclasses import dataclass, field

from accessibility import AccessibleEntity, AccessibilityNeed, vehicle_relevant
from station import Station
from vehicle import Vehicle


@dataclass
class Line(AccessibleEntity):
    name: str = ""
    vehicle: Vehicle = field(default_factory=Vehicle)
    vehicles: list[Vehicle] = field(default_factory=list)
    stations: list[Station] = field(default_factory=list)
    transport_mode: str = ""
    line_accessible: bool = True
    guaranteed_accessible_vehicle: bool = True
    expected_wait_factor: float = 1.0

    @property
    def vehicle_type(self) -> str:
        return self.vehicle.vehicle_type

    def all_vehicles(self) -> list[Vehicle]:
        if not self.vehicles:
            return [self.vehicle]

        unique_vehicles: list[Vehicle] = [self.vehicle]
        for extra_vehicle in self.vehicles:
            if extra_vehicle is self.vehicle:
                continue
            unique_vehicles.append(extra_vehicle)

        return unique_vehicles

    def is_accessible_for(self, needs: set[AccessibilityNeed]) -> bool:
        # check if any vehicle on the line supports the needs
        # mixed-fleet lines are still accessible, just with longer wait
        vneeds = vehicle_relevant(needs)
        if not vneeds:
            return True
        return any(vehicle.supports_all(vneeds) for vehicle in self.all_vehicles())

    def serves_station(self, station_name: str) -> bool:
        return any(station.name == station_name for station in self.stations)

    def adjacent_station_names(self, station_name: str) -> list[str]:
        station_names = [station.name for station in self.stations]
        if station_name not in station_names:
            return []

        index = station_names.index(station_name)
        neighbors: list[str] = []

        if index > 0:
            neighbors.append(station_names[index - 1])
        if index < len(station_names) - 1:
            neighbors.append(station_names[index + 1])

        return neighbors
