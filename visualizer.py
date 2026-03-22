import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from matplotlib.widgets import CheckButtons
from matplotlib.lines import Line2D

from network import Network


class NetworkVisualizer:

    # official u-bahn colors
    UBAHN_COLORS = {
        "U1": "#E2001A",
        "U2": "#A762A3",
        "U3": "#F68712",
        "U4": "#009540",
        "U6": "#8D5E2A",
    }

    TRAM_COLOR = "#E40716"
    BUS_COLOR = "#1A5DA6"
    DEFAULT_COLOR = "#333333"

    # wait factor colormap: green (1.0) to red (2.0)
    WAIT_CMAP = cm.RdYlGn_r
    WAIT_NORM = mcolors.Normalize(vmin=1.0, vmax=2.0)

    def __init__(self, network: Network):
        self.network = network

    def _classify_mode(self, line) -> str:
        # classify using the transport mode from csv data
        if line.transport_mode == "ptMetro":
            return "ubahn"
        if line.transport_mode == "ptTram":
            return "tram"
        return "bus"

    def _classic_color(self, line) -> str:
        if line.name in self.UBAHN_COLORS:
            return self.UBAHN_COLORS[line.name]
        mode = self._classify_mode(line)
        if mode == "tram":
            return self.TRAM_COLOR
        if mode == "bus":
            return self.BUS_COLOR
        return self.DEFAULT_COLOR

    def _wait_factor_color(self, line) -> str:
        rgba = self.WAIT_CMAP(self.WAIT_NORM(line.expected_wait_factor))
        return mcolors.to_hex(rgba)

    def _station_primary_mode(self, station_name: str) -> str:
        # hierarchy: ubahn > tram > bus
        modes = set()
        for line in self.network.lines:
            if line.serves_station(station_name):
                modes.add(self._classify_mode(line))
        if "ubahn" in modes:
            return "ubahn"
        if "tram" in modes:
            return "tram"
        return "bus"

    def _compute_stats(self) -> dict:
        modes = {"ubahn": 0, "tram": 0, "bus": 0}
        mixed_fleet = 0
        total_lines = len(self.network.lines)
        wait_factors = []

        for line in self.network.lines:
            mode = self._classify_mode(line)
            modes[mode] += 1
            if not line.guaranteed_accessible_vehicle:
                mixed_fleet += 1
            wait_factors.append(line.expected_wait_factor)

        avg_wait = sum(wait_factors) / len(wait_factors) if wait_factors else 1.0
        return {
            "total_stations": len(self.network.stations),
            "total_lines": total_lines,
            "ubahn_lines": modes["ubahn"],
            "tram_lines": modes["tram"],
            "bus_lines": modes["bus"],
            "mixed_fleet": mixed_fleet,
            "avg_wait_factor": avg_wait,
        }

    def render_interactive_map(self) -> None:
        fig, (ax_classic, ax_access) = plt.subplots(1, 2, figsize=(22, 11))
        fig.patch.set_facecolor("#fafafa")
        ax_classic.set_facecolor("#f0f0f0")
        ax_access.set_facecolor("#f0f0f0")

        # group artists by mode for toggle
        artists = {
            "ubahn": {"classic": [], "access": []},
            "tram": {"classic": [], "access": []},
            "bus": {"classic": [], "access": []},
        }

        marker_size = {"ubahn": 6, "tram": 3, "bus": 0}
        line_width = {"ubahn": 3.5, "tram": 1.8, "bus": 1.2}
        zorder_map = {"ubahn": 3, "tram": 2, "bus": 1}

        for line in self.network.lines:
            if not line.stations:
                continue

            lats = [s.latitude for s in line.stations if s.latitude != 0]
            lons = [s.longitude for s in line.stations if s.longitude != 0]
            if not lats or not lons:
                continue

            mode = self._classify_mode(line)
            lw = line_width[mode]
            ms = marker_size[mode]
            zo = zorder_map[mode]

            # thinner markers for non-ubahn, softer alpha for bus
            alpha = 0.5 if mode == "bus" else 0.9
            mew = 1 if mode == "ubahn" else 0.5

            # classic panel
            color_c = self._classic_color(line)
            art_c, = ax_classic.plot(
                lons, lats,
                marker="o" if ms > 0 else "", markerfacecolor="white",
                markeredgewidth=mew,
                color=color_c, linewidth=lw, markersize=ms,
                label=line.name, zorder=zo, alpha=alpha,
            )
            artists[mode]["classic"].append(art_c)

            # accessibility panel
            color_a = self._wait_factor_color(line)
            art_a, = ax_access.plot(
                lons, lats,
                marker="o" if ms > 0 else "", markerfacecolor="white",
                markeredgewidth=mew,
                color=color_a, linewidth=lw, markersize=ms,
                label=line.name, zorder=zo, alpha=alpha,
            )
            artists[mode]["access"].append(art_a)

            # annotate mixed-fleet lines on accessibility panel
            if not line.guaranteed_accessible_vehicle and len(lats) > 1:
                mid = len(lats) // 2
                ax_access.annotate(
                    f"{line.name}\n{line.expected_wait_factor:.2f}x",
                    (lons[mid], lats[mid]),
                    fontsize=6, fontweight="bold", ha="center",
                    color="#333", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#999", alpha=0.8),
                )

        # label u-bahn terminal stations on both panels
        for line in self.network.lines:
            if self._classify_mode(line) != "ubahn" or not line.stations:
                continue
            valid = [(s.name, s.latitude, s.longitude)
                     for s in line.stations if s.latitude != 0]
            if not valid:
                continue
            for name, lat, lon in (valid[0], valid[-1]):
                for ax in (ax_classic, ax_access):
                    ax.text(
                        lon, lat + 0.001, name,
                        fontsize=6, fontweight="bold", ha="center",
                        zorder=5, color="#222",
                    )

        # titles and labels
        ax_classic.set_title("Classic View (by transport mode)", fontsize=13, fontweight="bold")
        ax_access.set_title("Accessibility View (by wait factor)", fontsize=13, fontweight="bold")

        for ax in (ax_classic, ax_access):
            ax.set_xlabel("Longitude", fontsize=10)
            ax.set_ylabel("Latitude", fontsize=10)
            ax.grid(True, linestyle="--", alpha=0.3, zorder=0)

        # classic panel legend
        classic_handles = [
            Line2D([0], [0], color=self.UBAHN_COLORS.get("U1"), lw=3, label="U-Bahn"),
            Line2D([0], [0], color=self.TRAM_COLOR, lw=2, label="Tram"),
            Line2D([0], [0], color=self.BUS_COLOR, lw=1.5, label="Bus"),
        ]
        ax_classic.legend(handles=classic_handles, loc="upper left", fontsize=8)

        # colorbar for accessibility panel
        sm = cm.ScalarMappable(cmap=self.WAIT_CMAP, norm=self.WAIT_NORM)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax_access, shrink=0.6, pad=0.02)
        cbar.set_label("Wait Factor (1.0 = guaranteed, 2.0 = worst)", fontsize=9)

        # mode legend on accessibility panel
        access_handles = [
            Line2D([0], [0], color="#666", lw=3.5, marker="o", markersize=5,
                   markerfacecolor="white", label="U-Bahn"),
            Line2D([0], [0], color="#666", lw=1.8, marker="o", markersize=3,
                   markerfacecolor="white", label="Tram"),
            Line2D([0], [0], color="#666", lw=1.2, label="Bus"),
        ]
        ax_access.legend(handles=access_handles, loc="upper left", fontsize=8)

        # stats box
        stats = self._compute_stats()
        stats_text = (
            f"stations: {stats['total_stations']}\n"
            f"lines: {stats['total_lines']} "
            f"({stats['ubahn_lines']} U / {stats['tram_lines']} T / {stats['bus_lines']} B)\n"
            f"mixed-fleet lines: {stats['mixed_fleet']}\n"
            f"avg wait factor: {stats['avg_wait_factor']:.2f}x"
        )
        fig.text(
            0.5, 0.02, stats_text,
            ha="center", fontsize=9, fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.4", fc="#eee", ec="#ccc", alpha=0.9),
        )

        # checkbox toggles
        plt.subplots_adjust(left=0.08, right=0.88, bottom=0.1, top=0.93, wspace=0.15)
        check_ax = fig.add_axes([0.90, 0.4, 0.09, 0.15])
        labels = ["U-Bahn", "Tram", "Bus"]
        modes_keys = ["ubahn", "tram", "bus"]
        visibility = [True, True, True]
        check = CheckButtons(check_ax, labels, visibility)

        def toggle(label):
            idx = labels.index(label)
            mode_key = modes_keys[idx]
            for panel in ("classic", "access"):
                for art in artists[mode_key][panel]:
                    art.set_visible(not art.get_visible())
            fig.canvas.draw_idle()

        check.on_clicked(toggle)

        # keep reference so checkbox doesn't get garbage collected
        fig._check_buttons = check

        plt.show()

    # keep the old static method available
    def render_map(self, output_filename: str = "vienna_map.png") -> None:
        fig, ax = plt.subplots(figsize=(14, 14))
        ax.set_facecolor("#f4f4f4")

        for line in self.network.lines:
            if not line.stations:
                continue

            lats = [s.latitude for s in line.stations if s.latitude != 0]
            lons = [s.longitude for s in line.stations if s.longitude != 0]

            if not lats or not lons:
                continue

            color = self._classic_color(line)
            linewidth = 4 if "U-Bahn" in line.vehicle_type else 2

            ax.plot(
                lons, lats,
                marker="o", markerfacecolor="white", markeredgewidth=1.5,
                color=color, linewidth=linewidth,
                markersize=6 if "U-Bahn" in line.vehicle_type else 3,
                label=line.name, zorder=3 if "U-Bahn" in line.vehicle_type else 2,
                alpha=0.9,
            )

            names = [s.name for s in line.stations if s.latitude != 0]
            if names and lats:
                ax.text(
                    lons[0], lats[0] + 0.001, names[0],
                    fontsize=7, fontweight="bold", ha="center", zorder=4,
                )
                ax.text(
                    lons[-1], lats[-1] + 0.001, names[-1],
                    fontsize=7, fontweight="bold", ha="center", zorder=4,
                )

        ax.set_title(
            "Vienna Transport Network\n(Object-Oriented Accessibility Map)",
            fontsize=16, fontweight="bold",
        )
        ax.set_xlabel("Longitude", fontsize=11)
        ax.set_ylabel("Latitude", fontsize=11)
        ax.grid(True, linestyle="--", alpha=0.4, zorder=1)

        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(
            by_label.values(), by_label.keys(),
            title="Lines", fontsize=8, title_fontsize=10,
            loc="upper left", ncol=2,
        )

        plt.tight_layout()
        fig.savefig(output_filename, dpi=300, bbox_inches="tight")
        print(f"Map saved to {output_filename}")
