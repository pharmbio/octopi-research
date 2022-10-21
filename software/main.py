# set QT_API environment variable
import os 
import argparse
os.environ["QT_API"] = "pyqt5"
import qtpy

# qt libraries
from qtpy.QtCore import *
from qtpy.QtWidgets import *
from qtpy.QtGui import *

# app specific libraries
import control.gui as gui
#import control.gui_2cameras_async as gui
#import control.gui_tiscamera as gui

parser = argparse.ArgumentParser()
args = parser.parse_args()

if __name__ == "__main__":

    app = QApplication([])
    app.setStyle('Fusion')
    win = gui.OctopiGUI()
    win.show()
    app.exec_() #sys.exit(app.exec_())
