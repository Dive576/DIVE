# DIVE: Data Interface for Visual Exploration

DIVE is a Qt GUI that provides a simple way to plot and animate `pandas` DataFrames using `vispy`. It provides support for the following features:

* 2D and 3D axes that can display numeric, timestamp, and str values
* Several common types of artists including scatter plots, polygons, surface plots, and text
* Colorbars
* Artist legend
* Unit conversion for axes and colorbars (if `pint` module is installed)
* Animation controls (if DIVE is given data with a time field)
* Data filtering
* Data selection/highlighting (for arrow and scatter plots)
* Table to show values/statistics of data fields
* Screenshot capture
* Video recording (if `opencv-python` module is installed)
* API that allows the GUI to be controlled programmatically for use in a larger Qt application

## Prerequisites

DIVE is compatible with Python &ge; 3.7
`pandas` and `vispy` are required; `opencv-python` (for video recording), `pint` (for unit conversions), `qdarkstyle` (for GUI themes) are optional.

## Usage

The following example shows the basic process for using DIVE:

```python
from DIVE import DIVEWidget # Assuming that the DIVE source directory is in your current python directory
from PyQt5.QtWidgets import QApplication

app = QApplication([])
widget = DIVEWidget()

# Add data using widget.add_data(...)
# Add axes using widget.add_axis(...)
# Add artists using widget.add_scatter_artist(...)

widget.show()
app.exec()
```

You can also look at `dive_example.py` to see a basic example of how to use DIVE. The full list of functions and inputs supported by DIVE can be found in `DIVE/_widgets.py`.

## Example

![dive_example](https://user-images.githubusercontent.com/62649460/132419446-ae942864-bc34-4ee9-89f4-a0864a2e7ffb.png)
