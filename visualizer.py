import matplotlib.pyplot as plt

from network import Network


class NetworkVisualizer:

    COLOR_MAP = {
        "U1": "#E2001A",
        "U2": "#A762A3",
        "U3": "#F68712",
        "U4": "#009540",
        "U6": "#8D5E2A",
    }

    TRAM_COLOR = "#E40716"
    BUS_COLOR = "#1A5DA6"
    DEFAULT_COLOR = "#333333"

    def __init__(self, network: Network):
        self.network = network

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

            color = self._color_for_line(line.name, line.vehicle_type)
            linewidth = 4 if "U-Bahn" in line.vehicle_type else 2

            ax.plot(
                lons,
                lats,
                marker="o",
                markerfacecolor="white",
                markeredgewidth=1.5,
                color=color,
                linewidth=linewidth,
                markersize=6 if "U-Bahn" in line.vehicle_type else 3,
                label=line.name,
                zorder=3 if "U-Bahn" in line.vehicle_type else 2,
                alpha=0.9,
            )

            # label first and last station
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
            fontsize=16,
            fontweight="bold",
        )
        ax.set_xlabel("Longitude", fontsize=11)
        ax.set_ylabel("Latitude", fontsize=11)
        ax.grid(True, linestyle="--", alpha=0.4, zorder=1)

        # deduplicate legend entries
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(
            by_label.values(),
            by_label.keys(),
            title="Lines",
            fontsize=8,
            title_fontsize=10,
            loc="upper left",
            ncol=2,
        )

        plt.tight_layout()
        fig.savefig(output_filename, dpi=300, bbox_inches="tight")
        print(f"Map saved to {output_filename}")

    def _color_for_line(self, line_name: str, vehicle_type: str) -> str:
        if line_name in self.COLOR_MAP:
            return self.COLOR_MAP[line_name]
        if "Tram" in vehicle_type:
            return self.TRAM_COLOR
        if "Bus" in vehicle_type:
            return self.BUS_COLOR
        return self.DEFAULT_COLOR
