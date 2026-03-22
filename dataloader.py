import json

import pandas as pd

from accessibility import AccessibilityNeed
from line import Line
from network import Network
from station import Station
from vehicle import Vehicle

# vehicle field to accessibility need mapping

_VEHICLE_FIELD_MAP: list[tuple[str, AccessibilityNeed]] = [
    ("wheelchair_accessible", AccessibilityNeed.WHEELCHAIR_ACCESS),
    ("step_free_boarding", AccessibilityNeed.LOW_FLOOR_BOARDING),
    ("audio_announcements", AccessibilityNeed.AUDIO_ANNOUNCEMENTS),
    ("visual_next_stop_display", AccessibilityNeed.VISUAL_SIGNAGE),
    ("priority_seating", AccessibilityNeed.ACCESSIBLE_SEATING),
]

# station field to accessibility need mapping

_STATION_FIELD_MAP: list[tuple[str, AccessibilityNeed]] = [
    ("step_free_access_to_platform", AccessibilityNeed.WHEELCHAIR_ACCESS),
    ("ramp_access", AccessibilityNeed.WHEELCHAIR_ACCESS),
    ("elevator", AccessibilityNeed.ELEVATOR),
    ("audio_announcements_platform", AccessibilityNeed.AUDIO_ANNOUNCEMENTS),
    ("visual_signage", AccessibilityNeed.VISUAL_SIGNAGE),
    ("tactile_guidance_strips", AccessibilityNeed.TACTILE_GUIDANCE),
]

# csv transport mode to json category

_MODE_TO_JSON_CATEGORY = {
    "ptMetro": "ubahn",
    "ptTram": "tram",
    "ptBusCity": "bus",
    "ptBusNight": "bus",
}

_MODE_TO_STOP_TYPE = {
    "ptMetro": "ubahn_station",
    "ptTram": "tram_stop",
    "ptBusCity": "bus_stop",
    "ptBusNight": "bus_stop",
}


def _traits_from_json(data: dict, field_map: list[tuple[str, AccessibilityNeed]]) -> set[AccessibilityNeed]:
    traits: set[AccessibilityNeed] = set()
    for json_field, need in field_map:
        value = data.get(json_field, False)
        if value is True:
            traits.add(need)
    return traits


def _build_vehicles_from_json(json_data: dict) -> dict[str, Vehicle]:
    vehicle_types_data = json_data.get("vehicle_type_traits", {})
    vehicles: dict[str, Vehicle] = {}
    for type_id, vdata in vehicle_types_data.items():
        if type_id.startswith("_"):
            continue
        traits = _traits_from_json(vdata, _VEHICLE_FIELD_MAP)
        vehicles[type_id] = Vehicle(
            vehicle_type=vdata.get("display_name", type_id),
            accessibility_traits=traits,
        )
    return vehicles


def _build_stop_type_traits(json_data: dict) -> dict[str, set[AccessibilityNeed]]:
    station_traits_data = json_data.get("station_traits", {}).get("stop_type_defaults", {})
    stop_type_traits: dict[str, set[AccessibilityNeed]] = {}
    for stop_type, sdata in station_traits_data.items():
        stop_type_traits[stop_type] = _traits_from_json(sdata, _STATION_FIELD_MAP)
    return stop_type_traits


def _get_line_assignment(
    json_data: dict, line_name: str, json_category: str
) -> dict | None:
    assignments = json_data.get("line_vehicle_assignments", {})
    category_data = assignments.get(json_category, {})

    # direct lookup
    if line_name in category_data and isinstance(category_data[line_name], dict):
        return category_data[line_name]

    # bus default
    if json_category == "bus" and "default" in category_data:
        return category_data["default"]

    return None


def load_network(
    linien_path: str,
    haltestellen_path: str,
    steige_path: str,
    accessibility_json_path: str | None = None,
    modes_to_include: list[str] | None = None,
) -> Network:
    if modes_to_include is None:
        modes_to_include = ["ptMetro", "ptTram", "ptBusCity"]

    # load csvs
    linien_df = pd.read_csv(linien_path, sep=";")
    haltestellen_df = pd.read_csv(haltestellen_path, sep=";")
    steige_df = pd.read_csv(steige_path, sep=";")

    # load json accessibility data
    json_data: dict = {}
    if accessibility_json_path:
        with open(accessibility_json_path, encoding="utf-8") as f:
            json_data = json.load(f)

    json_vehicles = _build_vehicles_from_json(json_data) if json_data else {}
    stop_type_traits = _build_stop_type_traits(json_data) if json_data else {}

    # fallback vehicles when json is unavailable
    fallback_vehicles: dict[str, Vehicle] = {
        "ptMetro": Vehicle(
            vehicle_type="U-Bahn (generic)",
            accessibility_traits={
                AccessibilityNeed.WHEELCHAIR_ACCESS,
                AccessibilityNeed.LOW_FLOOR_BOARDING,
                AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
                AccessibilityNeed.VISUAL_SIGNAGE,
                AccessibilityNeed.ACCESSIBLE_SEATING,
            },
        ),
        "ptTram": Vehicle(
            vehicle_type="Tram (generic)",
            accessibility_traits={
                AccessibilityNeed.WHEELCHAIR_ACCESS,
                AccessibilityNeed.LOW_FLOOR_BOARDING,
                AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
                AccessibilityNeed.VISUAL_SIGNAGE,
            },
        ),
        "ptBusCity": Vehicle(
            vehicle_type="Bus (generic)",
            accessibility_traits={
                AccessibilityNeed.WHEELCHAIR_ACCESS,
                AccessibilityNeed.LOW_FLOOR_BOARDING,
                AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
                AccessibilityNeed.VISUAL_SIGNAGE,
            },
        ),
    }

    fallback_stop_traits: dict[str, set[AccessibilityNeed]] = {
        "ptMetro": {
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.ELEVATOR,
            AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
            AccessibilityNeed.VISUAL_SIGNAGE,
            AccessibilityNeed.TACTILE_GUIDANCE,
        },
        "ptTram": {
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.VISUAL_SIGNAGE,
        },
        "ptBusCity": {
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.VISUAL_SIGNAGE,
        },
    }

    # build network
    filtered_lines = linien_df[linien_df["VERKEHRSMITTEL"].isin(modes_to_include)]

    all_stations: dict[str, Station] = {}
    station_modes: dict[str, set[str]] = {}
    network_lines: list[Line] = []

    for _, line_row in filtered_lines.iterrows():
        line_id = line_row["LINIEN_ID"]
        line_name = line_row["BEZEICHNUNG"]
        mode = line_row["VERKEHRSMITTEL"]

        # get stations for this line
        line_steige = steige_df[
            (steige_df["FK_LINIEN_ID"] == line_id) & (steige_df["RICHTUNG"] == "H")
        ].sort_values("REIHENFOLGE")

        line_stations_data = pd.merge(
            line_steige,
            haltestellen_df,
            left_on="FK_HALTESTELLEN_ID",
            right_on="HALTESTELLEN_ID",
        )

        if line_stations_data.empty:
            continue

        # build station objects
        current_line_stations: list[Station] = []
        for _, row in line_stations_data.iterrows():
            name = row["NAME"]
            if name not in all_stations:
                all_stations[name] = Station(
                    name=name,
                    latitude=row["WGS84_LAT"],
                    longitude=row["WGS84_LON"],
                    accessibility_traits=set(),
                )
                station_modes[name] = set()
            station_modes[name].add(mode)
            current_line_stations.append(all_stations[name])

        # look up json assignment for this line
        json_category = _MODE_TO_JSON_CATEGORY.get(mode, "bus")
        assignment = _get_line_assignment(json_data, line_name, json_category)

        if assignment:
            # build vehicle list from json
            vehicle_type_ids = assignment.get("vehicle_types", [])
            line_vehicles: list[Vehicle] = []
            for vid in vehicle_type_ids:
                if vid in json_vehicles:
                    line_vehicles.append(json_vehicles[vid])

            if not line_vehicles:
                line_vehicles = [fallback_vehicles.get(mode, fallback_vehicles["ptBusCity"])]

            primary_vehicle = line_vehicles[0]
            extra_vehicles = line_vehicles[1:] if len(line_vehicles) > 1 else []

            # line traits as intersection of all vehicle traits
            line_traits: set[AccessibilityNeed] = set(primary_vehicle.accessibility_traits)
            for v in extra_vehicles:
                line_traits &= v.accessibility_traits

            new_line = Line(
                name=line_name,
                stations=current_line_stations,
                vehicle=primary_vehicle,
                vehicles=extra_vehicles,
                transport_mode=mode,
                accessibility_traits=line_traits,
                line_accessible=assignment.get("line_accessible", True),
                guaranteed_accessible_vehicle=assignment.get("guaranteed_accessible_vehicle", True),
                expected_wait_factor=assignment.get("expected_wait_factor", 1.0),
            )
        else:
            # fallback when no json data for this line
            fv = fallback_vehicles.get(mode, fallback_vehicles["ptBusCity"])
            new_line = Line(
                name=line_name,
                stations=current_line_stations,
                vehicle=fv,
                transport_mode=mode,
                accessibility_traits=set(fv.accessibility_traits),
            )

        network_lines.append(new_line)

    # assign station traits based on stop type
    for name, station in all_stations.items():
        traits: set[AccessibilityNeed] = set()
        for mode in station_modes.get(name, set()):
            stop_type = _MODE_TO_STOP_TYPE.get(mode, "bus_stop")
            if stop_type_traits and stop_type in stop_type_traits:
                traits |= stop_type_traits[stop_type]
            else:
                traits |= fallback_stop_traits.get(mode, set())
        station.accessibility_traits = traits

    return Network(stations=all_stations, lines=network_lines)
