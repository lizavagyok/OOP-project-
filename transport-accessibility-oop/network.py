from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from line import Line
from passenger import Passenger
from station import Station


@dataclass
class RouteStep:
    station_name: str
    line_name: str
    is_transfer: bool = False

    def __repr__(self) -> str:
        tag = " [TRANSFER]" if self.is_transfer else ""
        return f"{self.station_name} via {self.line_name}{tag}"


@dataclass
class TransportNetwork:
    stations: dict[str, Station] = field(default_factory=dict)
    lines: list[Line] = field(default_factory=list)

    def can_travel(self, passenger: Passenger) -> tuple[bool, list[str], list[RouteStep], str]:
        required = passenger.accessibility_needs
        start = passenger.start_station
        end = passenger.end_station

        if start not in self.stations:
            return False, [], [], f"Unknown start station: {start}"
        if end not in self.stations:
            return False, [], [], f"Unknown end station: {end}"
        if not self.stations[start].supports_all(required):
            return False, [], [], f"Start station '{start}' does not meet passenger needs"
        if not self.stations[end].supports_all(required):
            return False, [], [], f"End station '{end}' does not meet passenger needs"

        if start == end:
            return True, [start], [], "Start and destination are the same station"

        accessible_line_indices = [
            index for index, line in enumerate(self.lines) if line.is_accessible_for(required)
        ]

        station_to_line_indices: dict[str, list[int]] = {}
        for line_index in accessible_line_indices:
            line = self.lines[line_index]
            for station in line.stations:
                station_to_line_indices.setdefault(station.name, []).append(line_index)

        if start not in station_to_line_indices:
            return False, [], [], "No accessible vehicle can be boarded at the start station"

        queue = deque()
        previous: dict[tuple[str, int], tuple[str, int] | None] = {}

        for line_index in station_to_line_indices[start]:
            start_state = (start, line_index)
            previous[start_state] = None
            queue.append(start_state)

        while queue:
            current_station, current_line_index = queue.popleft()
            current_state = (current_station, current_line_index)

            if current_station == end:
                state_path = self._reconstruct_state_path(previous, current_state)
                station_path = self._states_to_station_path(state_path)
                detailed_path = self._states_to_detailed_path(state_path)
                return True, station_path, detailed_path, "Accessible route found"

            current_line = self.lines[current_line_index]

            for neighbor in current_line.adjacent_station_names(current_station):
                neighbor_state = (neighbor, current_line_index)
                if neighbor_state in previous:
                    continue
                previous[neighbor_state] = current_state
                queue.append(neighbor_state)

            if not self.stations[current_station].supports_all(required):
                continue

            for other_line_index in station_to_line_indices.get(current_station, []):
                if other_line_index == current_line_index:
                    continue
                transfer_state = (current_station, other_line_index)
                if transfer_state in previous:
                    continue
                previous[transfer_state] = current_state
                queue.append(transfer_state)

        return False, [], [], "No route satisfies all accessibility requirements"

    def _states_to_detailed_path(self, state_path: list[tuple[str, int]]) -> list[RouteStep]:
        detailed: list[RouteStep] = []

        for i, (station_name, line_index) in enumerate(state_path):
            line_name = self.lines[line_index].name

            is_transfer = (
                i > 0
                and state_path[i - 1][0] == station_name
                and state_path[i - 1][1] != line_index
            )

            if detailed and detailed[-1].station_name == station_name and not is_transfer:
                continue

            detailed.append(RouteStep(
                station_name=station_name,
                line_name=line_name,
                is_transfer=is_transfer,
            ))

        return detailed

    @staticmethod
    def _reconstruct_state_path(
        previous: dict[tuple[str, int], tuple[str, int] | None],
        end_state: tuple[str, int],
    ) -> list[tuple[str, int]]:
        path: list[tuple[str, int]] = []
        current: tuple[str, int] | None = end_state

        while current is not None:
            path.append(current)
            current = previous[current]

        return list(reversed(path))

    @staticmethod
    def _states_to_station_path(state_path: list[tuple[str, int]]) -> list[str]:
        station_path: list[str] = []

        for station_name, _ in state_path:
            if station_path and station_path[-1] == station_name:
                continue
            station_path.append(station_name)

        return station_path
