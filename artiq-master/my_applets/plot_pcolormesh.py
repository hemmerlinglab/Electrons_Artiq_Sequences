#!/usr/bin/env python3

import numpy as np
from PyQt5 import QtWidgets
import pyqtgraph

from artiq.applets.simple import TitleApplet

class PcolormeshPlot(pyqtgraph.PlotWidget):
    def __init__(self, args):
        pyqtgraph.PlotWidget.__init__(self)
        self.args = args

    def data_changed(self, data, mods, title):

        # Extract new data for the new plot
        try:
            z = data[self.args.z][1]
            if self.args.x is None:
                x = None
            else:
                x = data[self.args.x][1]
            if self.args.y is None:
                y = None
            else:
                y = data[self.args.y][1]
        except KeyError:
            return
        if x is None:
            x = np.array(range(len(z)+1))
        if y is None:
            y = np.array(range(len(z[0])+1))

        ys, xs = np.meshgrid(y, x)

        # Create the new plot
        self.clear()
        pcolmsh = pyqtgraph.PColorMeshItem(xs, ys, z)
        self.addItem(pcolmsh)
        self.setTitle(title)

def main():
    applet = TitleApplet(PcolormeshPlot)
    applet.add_dataset('z', '2D dataset of values of z=f(x,y) on every grid points')
    applet.add_dataset('x', '1D dataset of x values of the grid', required=False)
    applet.add_dataset('y', '1D dataset of y values of the grid', required=False)
    applet.run()

if __name__ == '__main__':
    main()
