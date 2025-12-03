#!/usr/bin/env python3

import numpy as np
from PyQt5 import QtWidgets
import pyqtgraph as pg

from artiq.applets.simple import TitleApplet


class ETraceProjectionWidget(QtWidgets.QWidget):
    def __init__(self, args):
        super().__init__()
        self.args = args

        # --- Layout: three plots in one horizontal row ----------------------
        main_layout = QtWidgets.QVBoxLayout(self)
        plots_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(plots_layout)

        self.plot_xy = pg.PlotWidget()
        self.plot_xz = pg.PlotWidget()
        self.plot_yz = pg.PlotWidget()

        self.plot_xy.setLabel("bottom", "Ex")
        self.plot_xy.setLabel("left", "Ey")
        self.plot_xy.setTitle("Ex vs Ey")

        self.plot_xz.setLabel("bottom", "Ex")
        self.plot_xz.setLabel("left", "Ez")
        self.plot_xz.setTitle("Ex vs Ez")

        self.plot_yz.setLabel("bottom", "Ey")
        self.plot_yz.setLabel("left", "Ez")
        self.plot_yz.setTitle("Ey vs Ez")

        plots_layout.addWidget(self.plot_xy)
        plots_layout.addWidget(self.plot_xz)
        plots_layout.addWidget(self.plot_yz)

        # Color mode selector: ratio_signal vs old-new (index)
        self.color_mode_box = QtWidgets.QComboBox()
        self.color_mode_box.addItems(["ratio_signal", "old-new"])
        main_layout.addWidget(self.color_mode_box)

    # ----------------------------------------------------------------------
    # ARTIQ applet API
    # ----------------------------------------------------------------------
    def data_changed(self, data, mods, title):
        # 1) Extract datasets
        try:
            e_trace = np.array(data["e_trace"][1])
            ratio = np.array(data["ratio_signal"][1])
        except KeyError:
            return

        if e_trace.ndim != 2 or e_trace.shape[1] != 3:
            return

        n = e_trace.shape[0]
        if ratio.shape[0] != n:
            n_min = min(n, ratio.shape[0])
            e_trace = e_trace[:n_min]
            ratio = ratio[:n_min]
            n = n_min

        Ex = e_trace[:, 0]
        Ey = e_trace[:, 1]
        Ez = e_trace[:, 2]

        # 2) Choose coloring
        mode = self.color_mode_box.currentText()
        if mode == "ratio_signal":
            vals = ratio
        else:
            # old-new: color by index (0 -> oldest, 1 -> newest)
            vals = np.linspace(0.0, 1.0, n)

        # Normalize to [0, 1]
        vmin = np.nanmin(vals)
        vmax = np.nanmax(vals)
        if vmax > vmin:
            norm = (vals - vmin) / (vmax - vmin)
        else:
            norm = np.zeros_like(vals)

        # 3) Build colors (blue → red gradient)
        colors = []
        for v in norm:
            c = pg.QtGui.QColor()
            # HSV: h from ~240° (blue) to 0° (red)
            c.setHsvF(0.66 * (1.0 - v), 1.0, 1.0)
            colors.append(c)

        # 4) Scatter items
        spots_xy = [
            {"pos": (Ex[i], Ey[i]), "brush": colors[i], "pen": None, "size": 10}
            for i in range(n)
        ]
        spots_xz = [
            {"pos": (Ex[i], Ez[i]), "brush": colors[i], "pen": None, "size": 10}
            for i in range(n)
        ]
        spots_yz = [
            {"pos": (Ey[i], Ez[i]), "brush": colors[i], "pen": None, "size": 10}
            for i in range(n)
        ]

        s_xy = pg.ScatterPlotItem(spots=spots_xy)
        s_xz = pg.ScatterPlotItem(spots=spots_xz)
        s_yz = pg.ScatterPlotItem(spots=spots_yz)

        # 5) Update plots
        self.plot_xy.clear()
        self.plot_xz.clear()
        self.plot_yz.clear()

        self.plot_xy.addItem(s_xy)
        self.plot_xz.addItem(s_xz)
        self.plot_yz.addItem(s_yz)

        self.plot_xy.setTitle(f"Ex vs Ey — {title}")
        self.plot_xz.setTitle(f"Ex vs Ez — {title}")
        self.plot_yz.setTitle(f"Ey vs Ez — {title}")


def main():
    applet = TitleApplet(ETraceProjectionWidget)
    applet.add_dataset("e_trace", "2D array, shape (N,3): columns Ex, Ey, Ez")
    applet.add_dataset("ratio_signal", "1D array, length N: objective values")
    applet.run()


if __name__ == "__main__":
    main()

