# legacy-lines

Created by Bruna C. de Melo, 2025.

Set of Python and Jupyter Notebook codes I developed to read active seismic refraction lines from the DIAS repository that were inverted using the RayInvr package.
These datasets mostly do not contain metadata, so I was able to infer the different measurements from trial and error...

Contains:
/src:
Contains the codes necessary to read the velocity 2D models and extract the information to csv and netcdf datasets, and visualization tools.

/example:
set of original files from COOLE1.
can be read and interpolated using main.ipynb.
the netcdf and csv files are the output from main.ipynb and can be plotted with plot.py.

/ICSSP:
codes to digise points from the original figure from Jacob et al., 1985, Fig 8.
the digitising proccess had to be done locally as I could not open the digitasing window in the server.
interpolate.ipynb reads the digitised values and interpolates and exports to a netcdf and csv in the same format as main.ipynb produces.

line_coords
start and end coordinates from each profile. the coordinates where either obtained from a file provided or approximated from a point comoon point in google maps. --\(._.)/--

requirements.txt
list of required python packages to run the codes used here.
