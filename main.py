import os

from accessibility import AccessibilityNeed
from dataloader import load_network
from network import Network, RouteStep
from passenger import Passenger

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATHS = {
    "linien": os.path.join(_BASE_DIR, "wienerlinien-ogd-linien.csv"),
    "haltestellen": os.path.join(_BASE_DIR, "wienerlinien-ogd-haltestellen.csv"),
    "steige": os.path.join(_BASE_DIR, "wienerlinien-ogd-steige.csv"),
    "accessibility_json": os.path.join(_BASE_DIR, "wiener_linien_accessibility_model_v2.json"),
}

ACCESSIBILITY_OPTIONS = list(AccessibilityNeed)
DEFAULT_HEADWAY_MINUTES = 5.0


def _print_wait_info(network: Network, detailed_path: list[RouteStep]) -> None:
    """Print per-line wait factor detail and total extra wait summary."""
    line_infos, total_extra = network.estimate_wait_info(
        detailed_path, base_headway_minutes=DEFAULT_HEADWAY_MINUTES
    )

    has_mixed = any(not guaranteed for _, _, guaranteed in line_infos)
    if not has_mixed:
        print("Wait info: All lines on this route have fully accessible fleets.")
        return

    print("Wait factor info:")
    for line_name, factor, guaranteed in line_infos:
        if guaranteed:
            print(f"  Line {line_name}: fully accessible fleet (wait factor 1.0x)")
        else:
            print(f"  Line {line_name}: mixed fleet (wait factor {factor:.2f}x)")

    if total_extra > 0:
        print(
            f"Estimated extra wait due to mixed fleets: ~{total_extra:.1f} min "
            f"(assuming {DEFAULT_HEADWAY_MINUTES:.0f} min headway)"
        )


def print_trip_result(network: Network, passenger: Passenger) -> None:
    can_go, path, detailed_path, reason = network.can_travel(passenger)

    print(f"Passenger: {passenger.start_station} -> {passenger.end_station}")
    print(f"Needs: {[need.name for need in passenger.accessibility_needs]}")

    if can_go:
        print("Result: Trip is accessible")
        print(f"Path: {' -> '.join(path)}")
        if detailed_path:
            print("Detailed steps:")
            for step in detailed_path:
                print(f"  {step}")
            _print_wait_info(network, detailed_path)
    else:
        print(f"Result: Trip is NOT accessible - {reason}")
        # propose alternative without accessibility constraints
        found, alt_path, alt_detailed, _ = network.find_any_route(
            passenger.start_station, passenger.end_station
        )
        if found:
            print("Alternative route (without accessibility guarantees):")
            print(f"  Path: {' -> '.join(alt_path)}")
            if alt_detailed:
                for step in alt_detailed:
                    print(f"    {step}")
                _print_wait_info(network, alt_detailed)
            barriers = network.report_barriers(alt_detailed, passenger.accessibility_needs)
            if barriers:
                print("  Barriers on this route:")
                for barrier in barriers:
                    print(f"    - {barrier}")
        else:
            print("  No physical route exists between these stations.")

    print("-" * 60)


def plan_trip(network: Network) -> None:
    print("\n=== Vienna Accessible Transport Planner ===\n")

    # start station
    start_input = input("Enter start station: ").strip()
    start_name, suggestions = network.find_station(start_input)
    if start_name is None:
        if suggestions:
            print("Station not found. Did you mean one of these?")
            for s in suggestions:
                print(f"  - {s}")
        else:
            print(f"No station matching '{start_input}' found.")
        return
    print(f"  -> {start_name}")

    # end station
    end_input = input("Enter destination station: ").strip()
    end_name, suggestions = network.find_station(end_input)
    if end_name is None:
        if suggestions:
            print("Station not found. Did you mean one of these?")
            for s in suggestions:
                print(f"  - {s}")
        else:
            print(f"No station matching '{end_input}' found.")
        return
    print(f"  -> {end_name}")

    # accessibility needs
    print("\nAccessibility needs (enter numbers separated by commas, or press Enter for none):")
    for i, need in enumerate(ACCESSIBILITY_OPTIONS, 1):
        print(f"  {i}. {need.name}")
    choice = input("Your needs: ").strip()

    needs: set[AccessibilityNeed] = set()
    if choice:
        for num in choice.split(","):
            num = num.strip()
            if num.isdigit() and 1 <= int(num) <= len(ACCESSIBILITY_OPTIONS):
                needs.add(ACCESSIBILITY_OPTIONS[int(num) - 1])

    # find route
    passenger = Passenger(
        accessibility_needs=needs,
        start_station=start_name,
        end_station=end_name,
    )

    print(f"\n--- Trip: {start_name} -> {end_name} ---")
    if needs:
        print(f"Needs: {', '.join(n.name for n in needs)}")
    else:
        print("Needs: None")

    can_go, path, detailed, reason = network.can_travel(passenger)

    if can_go:
        print("\nAccessible route found!")
        print(f"Path: {' -> '.join(path)}")
        if detailed:
            print("Detailed steps:")
            for step in detailed:
                print(f"  {step}")
            _print_wait_info(network, detailed)
    else:
        print(f"\nAccessible route NOT possible: {reason}")

        # propose alternative
        found, alt_path, alt_detailed, _ = network.find_any_route(start_name, end_name)
        if found:
            print("\nAlternative route (without accessibility guarantees):")
            print(f"Path: {' -> '.join(alt_path)}")
            if alt_detailed:
                print("Detailed steps:")
                for step in alt_detailed:
                    print(f"  {step}")
                _print_wait_info(network, alt_detailed)
            barriers = network.report_barriers(alt_detailed, needs)
            if barriers:
                print("\nBarriers on this route:")
                for barrier in barriers:
                    print(f"  - {barrier}")
        else:
            print("No physical route exists between these stations.")

    print("-" * 60)


def run_demos(network: Network) -> None:
    print("=" * 60)
    print("DEMO SCENARIOS")
    print("=" * 60)

    # praterstern to absberggasse with wheelchair, elevator, audio
    print_trip_result(
        network,
        Passenger(
            accessibility_needs={
                AccessibilityNeed.WHEELCHAIR_ACCESS,
                AccessibilityNeed.ELEVATOR,
                AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
            },
            start_station="Praterstern",
            end_station="Absberggasse",
        ),
    )

    # multi-line journey with transfer
    print_trip_result(
        network,
        Passenger(
            accessibility_needs={
                AccessibilityNeed.WHEELCHAIR_ACCESS,
                AccessibilityNeed.ELEVATOR,
            },
            start_station="Stephansplatz",
            end_station="Karlsplatz",
        ),
    )

    # trip that may fail due to accessibility barriers
    print_trip_result(
        network,
        Passenger(
            accessibility_needs={
                AccessibilityNeed.WHEELCHAIR_ACCESS,
                AccessibilityNeed.ELEVATOR,
                AccessibilityNeed.AUDIO_ANNOUNCEMENTS,
                AccessibilityNeed.LOW_FLOOR_BOARDING,
                AccessibilityNeed.TACTILE_GUIDANCE,
            },
            start_station="Schwedenplatz",
            end_station="Schottentor",
        ),
    )


def main() -> None:
    print("Loading Vienna transport network...")
    network = load_network(
        DATA_PATHS["linien"],
        DATA_PATHS["haltestellen"],
        DATA_PATHS["steige"],
        accessibility_json_path=DATA_PATHS["accessibility_json"],
        modes_to_include=["ptMetro", "ptTram", "ptBusCity"],
    )
    print(f"Loaded {len(network.stations)} stations and {len(network.lines)} lines.\n")

    run_demos(network)

    # interactive loop
    while True:
        print("\nOptions:")
        print("  1. Plan a trip")
        print("  2. Run demos again")
        print("  3. Exit")
        choice = input("Choose: ").strip()

        if choice == "1":
            plan_trip(network)
        elif choice == "2":
            run_demos(network)
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
