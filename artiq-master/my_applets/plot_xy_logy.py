#!/usr/bin/env python3

import numpy as np
from PyQt5 import QtWidgets  # same style as your other applets
import pyqtgraph

from artiq.applets.simple import TitleApplet


class PlotXYLogY(pyqtgraph.PlotWidget):
    def __init__(self, args):
        # Same pattern as your PcolormeshPlot
        pyqtgraph.PlotWidget.__init__(self)
        self.args = args

        # Basic styling
        self.showGrid(x=True, y=True)
        self.setLabel("bottom", "x")
        self.setLabel("left", "y (log scale)")
        # Let pyqtgraph handle log scaling of Y
        self.setLogMode(x=False, y=True)

    def data_changed(self, data, mods, title):
        # --- Load y ---
        try:
            y = data[self.args.y][1]
        except KeyError:
            # Dataset not available yet
            return
        if y is None:
            return

        y = np.asarray(y, dtype=float)

        # Filter out non-positive values (log scale cannot handle them)
        positive_mask = y > 0
        if not positive_mask.any():
            self.clear()
            return

        y_plot = y[positive_mask]

        # --- Load x (optional) ---
        if self.args.x is None:
            x_plot = np.arange(len(y_plot))
        else:
            try:
                x = data[self.args.x][1]
            except KeyError:
                return
            if x is None:
                return
            x = np.asarray(x, dtype=float)

            if len(x) != len(y):
                # Length mismatch: don't try to plot garbage
                return

            x_plot = x[positive_mask]

        # --- Plot ---
        self.clear()
        # Simple scatter-style plot (no pen, just symbols)
        self.plot(x_plot, y_plot, pen=None, symbol='o')

        if title is not None:
            self.setTitle(title)


def main():
    applet = TitleApplet(PlotXYLogY)
    applet.add_dataset("y", "1D dataset of y values")
    applet.add_dataset("x", "1D dataset of x values", required=False)
    applet.run()


if __name__ == "__main__":
    main()

