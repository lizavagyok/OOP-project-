from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from accessibility import AccessibilityNeed, station_relevant, vehicle_relevant
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
class Network:
    stations: dict[str, Station] = field(default_factory=dict)
    lines: list[Line] = field(default_factory=list)

    def can_travel(self, passenger: Passenger) -> tuple[bool, list[str], list[RouteStep], str]:
        return self._find_route(
            passenger.start_station,
            passenger.end_station,
            passenger.accessibility_needs,
        )

    def find_any_route(self, start: str, end: str) -> tuple[bool, list[str], list[RouteStep], str]:
        return self._find_route(start, end, required=set())

    def find_station(self, query: str) -> tuple[str | None, list[str]]:
        query_lower = query.lower()
        for name in self.stations:
            if name.lower() == query_lower:
                return name, []
        matches = [name for name in self.stations if query_lower in name.lower()]
        if len(matches) == 1:
            return matches[0], []
        return None, matches[:10]

    def estimate_wait_info(
        self, detailed_path: list[RouteStep], base_headway_minutes: float = 5.0
    ) -> tuple[list[tuple[str, float, bool]], float]:
        """Return per-line wait info and total extra wait in minutes.

        Returns:
            (line_infos, total_extra_minutes) where line_infos is a list of
            (line_name, wait_factor, guaranteed) tuples.
        """
        line_infos: list[tuple[str, float, bool]] = []
        seen_lines: set[str] = set()
        total_extra = 0.0

        for step in detailed_path:
            if step.line_name in seen_lines:
                continue
            seen_lines.add(step.line_name)
            line = next((l for l in self.lines if l.name == step.line_name), None)
            if line:
                line_infos.append(
                    (line.name, line.expected_wait_factor, line.guaranteed_accessible_vehicle)
                )
                total_extra += (line.expected_wait_factor - 1.0) * base_headway_minutes

        return line_infos, round(total_extra, 1)

    def report_barriers(
        self, detailed_path: list[RouteStep], needs: set[AccessibilityNeed]
    ) -> list[str]:
        if not needs:
            return []
        stn_needs = station_relevant(needs)
        veh_needs = vehicle_relevant(needs)
        barriers: list[str] = []
        seen_stations: set[str] = set()
        seen_lines: set[str] = set()
        for step in detailed_path:
            if step.station_name not in seen_stations:
                seen_stations.add(step.station_name)
                station = self.stations.get(step.station_name)
                if station and stn_needs:
                    missing = stn_needs - station.accessibility_traits
                    if missing:
                        barriers.append(
                            f"Station '{step.station_name}' lacks: "
                            + ", ".join(n.name for n in missing)
                        )
            if step.line_name not in seen_lines:
                seen_lines.add(step.line_name)
                line = next((l for l in self.lines if l.name == step.line_name), None)
                if line and veh_needs:
                    missing_line = veh_needs - line.accessibility_traits
                    if missing_line:
                        barriers.append(
                            f"Line '{step.line_name}' may lack: "
                            + ", ".join(n.name for n in missing_line)
                        )
        return barriers

    def _find_route(
        self, start: str, end: str, required: set[AccessibilityNeed]
    ) -> tuple[bool, list[str], list[RouteStep], str]:
        if start not in self.stations:
            return False, [], [], f"Unknown start station: {start}"
        if end not in self.stations:
            return False, [], [], f"Unknown end station: {end}"
        stn_needs = station_relevant(required)
        if stn_needs and not self.stations[start].supports_all(stn_needs):
            return False, [], [], f"Start station '{start}' does not meet passenger needs"
        if stn_needs and not self.stations[end].supports_all(stn_needs):
            return False, [], [], f"End station '{end}' does not meet passenger needs"

        if start == end:
            return True, [start], [], "Start and destination are the same station"

        if required:
            accessible_line_indices = [
                i for i, line in enumerate(self.lines) if line.is_accessible_for(required)
            ]
        else:
            accessible_line_indices = list(range(len(self.lines)))

        station_to_line_indices: dict[str, list[int]] = {}
        for line_index in accessible_line_indices:
            line = self.lines[line_index]
            for station in line.stations:
                station_to_line_indices.setdefault(station.name, []).append(line_index)

        if start not in station_to_line_indices:
            return False, [], [], "No accessible vehicle can be boarded at the start station"

        queue: deque[tuple[str, int]] = deque()
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

            if stn_needs and not self.stations[current_station].supports_all(stn_needs):
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
