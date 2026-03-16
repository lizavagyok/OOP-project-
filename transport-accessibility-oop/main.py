from accessibility import AccessibilityNeed
from line import Line
from network import TransportNetwork
from passenger import Passenger
from station import Station
from vehicle import Vehicle


def build_demo_network() -> TransportNetwork:
    central = Station(
        name="Central",
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.ELEVATOR,
            AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
            AccessibilityNeed.VISUAL_SIGNAGE,
        },
    )
    park = Station(
        name="Park",
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.ELEVATOR,
            AccessibilityNeed.VISUAL_SIGNAGE,
        },
    )
    museum = Station(
        name="Museum",
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.VISUAL_SIGNAGE,
        },
    )
    harbor = Station(
        name="Harbor",
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.ELEVATOR,
            AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
            AccessibilityNeed.VISUAL_SIGNAGE,
        },
    )

    tram = Vehicle(
        vehicle_type="Tram",
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.LOW_FLOOR_BOARDING,
            AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
            AccessibilityNeed.VISUAL_SIGNAGE,
        },
    )
    older_tram = Vehicle(
        vehicle_type="Older Tram",
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.VISUAL_SIGNAGE,
        },
    )
    metro = Vehicle(
        vehicle_type="Metro",
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
            AccessibilityNeed.VISUAL_SIGNAGE,
            AccessibilityNeed.ELEVATOR,
        },
    )

    green_line = Line(
        name="Green Line",
        vehicle=tram,
        vehicles=[older_tram],
        stations=[central, park, museum],
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.VISUAL_SIGNAGE,
        },
    )
    blue_line = Line(
        name="Blue Line",
        vehicle=metro,
        stations=[central, harbor],
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.ELEVATOR,
            AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
            AccessibilityNeed.VISUAL_SIGNAGE,
        },
    )

    return TransportNetwork(
        stations={station.name: station for station in [central, park, museum, harbor]},
        lines=[green_line, blue_line],
    )


def print_trip_result(network: TransportNetwork, passenger: Passenger) -> None:
    can_go, path, detailed_path, reason = network.can_travel(passenger)

    print(f"Passenger: {passenger.start_station} -> {passenger.end_station}")
    print(f"Needs: {[need.name for need in passenger.accessibility_needs]}")

    if can_go:
        print("Result: Trip is possible")
        print(f"Path: {' -> '.join(path)}")
        if detailed_path:
            print("Detailed steps:")
            for step in detailed_path:
                print(f"  {step}")
    else:
        print("Result: Trip is not possible")

    print(f"Reason: {reason}")
    print("-" * 60)


def build_transfer_failure_network() -> TransportNetwork:
    alpha = Station(
        name="Alpha",
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
        },
    )
    transfer_hub = Station(
        name="TransferHub",
        accessibility_traits=set(),
    )
    omega = Station(
        name="Omega",
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
        },
    )

    feeder_bus = Vehicle(
        vehicle_type="Feeder Bus",
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
        },
    )
    connector_bus = Vehicle(
        vehicle_type="Connector Bus",
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
        },
    )

    line_1 = Line(
        name="Line 1",
        vehicle=feeder_bus,
        stations=[alpha, transfer_hub],
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
        },
    )
    line_2 = Line(
        name="Line 2",
        vehicle=connector_bus,
        stations=[transfer_hub, omega],
        accessibility_traits={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
        },
    )

    return TransportNetwork(
        stations={station.name: station for station in [alpha, transfer_hub, omega]},
        lines=[line_1, line_2],
    )


def main() -> None:
    network = build_demo_network()
    transfer_failure_network = build_transfer_failure_network()

    passenger_1 = Passenger(
        accessibility_needs={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.ELEVATOR,
            AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
        },
        start_station="Central",
        end_station="Harbor",
    )

    passenger_2 = Passenger(
        accessibility_needs={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
            AccessibilityNeed.ELEVATOR,
            AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
        },
        start_station="Central",
        end_station="Museum",
    )
    passenger_3 = Passenger(
        accessibility_needs={
            AccessibilityNeed.WHEELCHAIR_ACCESS,
        },
        start_station="Alpha",
        end_station="Omega",
    )

    print_trip_result(network, passenger_1)
    print_trip_result(network, passenger_2)
    print_trip_result(transfer_failure_network, passenger_3)


if __name__ == "__main__":
    main()