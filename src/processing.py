import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from geopy.distance import geodesic
from geopy import Point
from matplotlib.path import Path
from scipy.interpolate import interp1d, griddata
from scipy.ndimage import gaussian_filter
from scipy.ndimage import generic_filter
from scipy.spatial import cKDTree
import numpy.ma as ma

# Extract start and end coordinates from the coords_file
def get_profile_coords(tag, tag2, coords_file):
    """
    Extract start and end coordinates for a profile from a CSV coordinates file.
    The CSV should have columns: line, start_lon, start_lat, end_lon, end_lat
    """
    df_coords = pd.read_csv(coords_file)
    line_name = f"{tag}{tag2}"
    row = df_coords[df_coords['tag'] == line_name]
    if row.empty:
        raise ValueError(f"Could not find coordinates for {line_name} in {coords_file}")
    start_lon = float(row.iloc[0]['start_lon'])
    start_lat = float(row.iloc[0]['start_lat'])
    end_lon = float(row.iloc[0]['end_lon'])
    end_lat = float(row.iloc[0]['end_lat'])
    return start_lat, start_lon, end_lat, end_lon

def parse_velocity_model(filepath):
    """
    Parser for RayInvr v.in velocity model files.
    This function reads a v.in_{tag} file and extracts the velocity model and layer boundaries.
    The file is structured in repeating blocks for each layer:
        1. Line 1: layer ID (integer) followed by x values (floats).
        2. Line 2: flag (0 or 1) followed by z or velocity values (floats).
          - If flag==1, the values continue on the next line (accumulate until flag==0).
        3. Line 3: dummy line (ignored).
        4. The next block may contain x and vp_top, or x and vp_bottom, depending on the stage.
        5. The process repeats for each layer, cycling through (x, z), (x_vel, vp_top), (x_vel, vp_bottom).
    The function returns a list of dictionaries, one per layer, with keys:
    'n', 'x', 'z', 'x_vel_top', 'x_vel_bottom', 'vp_top', 'vp_bottom'
    """
    layers = []
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    i = 0
    current_layer = None
    block_stage = 0  # 0: (x, z), 1: (x_vel, vp_top), 2: (x_vel, vp_bottom)
    layer_data = {}
    buffer_x = []
    buffer_y = []

    while i < len(lines) - 2:
        # Line 1: layer ID + x values
        line1 = lines[i].split()
        layer_id = int(line1[0])
        x_vals = list(map(float, line1[1:]))

        # Line 2: flag + y values (z or velocity)
        line2 = lines[i + 1].split()
        flag = int(line2[0])
        y_vals = list(map(float, line2[1:]))

        # Skip dummy line
        i += 3

        # If new layer, save previous and start new dictionary
        if current_layer != layer_id:
            if layer_data:
                layers.append(layer_data)
            current_layer = layer_id
            layer_data = {
                "n": current_layer - 1,
                "x": [],
                "z": [],
                "x_vel_top": [],
                "x_vel_bottom": [],
                "vp_top": [],
                "vp_bottom": []
            }
            block_stage = 0
            buffer_x = []
            buffer_y = []

        # If flag==1, accumulate values for continuation lines
        if flag == 1:
            buffer_x.extend(x_vals)
            buffer_y.extend(y_vals)
            continue

        # If previous lines were accumulated, combine them
        if buffer_x and buffer_y:
            x_vals = buffer_x + x_vals
            y_vals = buffer_y + y_vals
            buffer_x = []
            buffer_y = []

        # Assign values to the correct fields based on block_stage
        if block_stage == 0:  # (x, z)
            layer_data["x"] = x_vals
            layer_data["z"] = y_vals
        elif block_stage == 1:  # (x_vel, vp_top)
            layer_data["x_vel_top"] = x_vals
            layer_data["vp_top"] = y_vals
        elif block_stage == 2:  # (x_vel, vp_bottom)
            layer_data["x_vel_bottom"] = x_vals
            layer_data["vp_bottom"] = y_vals

        # Move to next block stage
        block_stage = (block_stage + 1) % 3

    # Save the last layer
    if layer_data:
        layers.append(layer_data)

    return layers

def interpolate_velocity_model(layers, dx=1.0, dz=0.1, z_max=35.0):
    """
    Interpolate a velocity model from a list of layers.

    Parameters
    ----------
    layers : list of dict
        Each dict must have keys: 'x', 'z', 'x_vel_top', 'x_vel_bottom', 'vp_top', 'vp_bottom'
    dx : float
        Horizontal grid spacing (km)
    dz : float
        Vertical grid spacing (km)
    z_max : float
        Maximum depth (km)

    Returns
    -------
    x_grid : np.ndarray
        1D array of horizontal coordinates (km)
    z_grid : np.ndarray
        1D array of depth coordinates (km)
    Vp_grid : np.ndarray
        2D array of interpolated Vp (shape: [len(z_grid), len(x_grid)])
    """
    # Find full horizontal extent
    x_min = min([min(layer["x"]) for layer in layers])
    x_max = max([max(layer["x"]) for layer in layers])
    x_grid = np.arange(x_min, x_max + dx, dx)

    # Estimate maximum depth for Z grid
    z_min = min([min(layer["z"]) for layer in layers])
    z_grid = np.arange(z_min, z_max + dz, dz)

    # Prepare 2D Vp grid
    X, Z = np.meshgrid(x_grid, z_grid)
    Vp_grid = np.full_like(X, np.nan, dtype=float)

    # --- INTERPOLATION LOOP ---
    for i, layer in enumerate(layers):
        x_top = np.array(layer["x"])
        z_top = np.array(layer["z"])

        # Interpolate z_top onto the global x_grid
        f_z_top = interp1d(x_top, z_top, bounds_error=False, fill_value="extrapolate")
        z_top_interp = f_z_top(x_grid)

        # Infer z_bottom from z_top of the next layer
        if i < len(layers) - 1:
            x_next = np.array(layers[i + 1]["x"])
            z_next = np.array(layers[i + 1]["z"])
            f_z_bottom = interp1d(x_next, z_next, bounds_error=False, fill_value="extrapolate")
            z_bottom_interp = f_z_bottom(x_grid)
        else:
            # For the last layer, extend downward a bit
            z_bottom_interp = (z_max) * np.ones_like(z_top_interp)

        # Interpolate vp over x
        f_vp_min = interp1d(layer["x_vel_top"], layer["vp_top"], bounds_error=False, fill_value="extrapolate")
        vp_min_x_interp = f_vp_min(x_grid)
        f_vp_max = interp1d(layer["x_vel_bottom"], layer["vp_bottom"], bounds_error=False, fill_value="extrapolate")
        vp_max_x_interp = f_vp_max(x_grid)
        
        # Fill Vp_grid values within the layer depth interval
        for xi, x in enumerate(x_grid):
            zmin = z_top_interp[xi]
            zmax = z_bottom_interp[xi]
        
            # Avoid invalid or degenerate layers
            if zmax <= zmin:
                continue

            # Boolean mask for Z values within this vertical column
            z_column = Z[:, xi]
            z_mask = (z_column >= zmin) & (z_column < zmax)
            # Get the actual Z values within the layer at this x
            z_values = z_column[z_mask]
            # Assign interpolated Vp to all valid Z positions at column xi
            Vp_grid[z_mask, xi] = vp_min_x_interp[xi]
            
            # Interpolate Vp linearly between vp_min and vp_max
            vp_top = vp_min_x_interp[xi]
            vp_bot = vp_max_x_interp[xi]
            vp_interp = vp_top + (vp_bot - vp_top) * (z_values - zmin) / (zmax - zmin)

            # Assign to Vp grid
            Vp_grid[z_mask, xi] = vp_interp

    return x_grid, z_grid, Vp_grid

# X values are in kilometers, z values are in meters, and velocities are in km/s.
# To plot, we need to convert x values to geographic coordinates (longitude, latitude) based on the start and end points.

# --- INTERPOLATE PROFILE COORDINATES ---
def interpolate_profile_coords(x_grid, start_lat, start_lon, end_lat, end_lon):
    """
    Given a 1D array of distances (x_grid, in km) along a profile, and the start/end geographic coordinates,
    interpolate the corresponding longitude and latitude for each x value along the profile.

    Args:
        x_grid (array-like): Distances along the profile in kilometers.
        start_lat (float): Latitude of the profile start point.
        start_lon (float): Longitude of the profile start point.
        end_lat (float): Latitude of the profile end point.
        end_lon (float): Longitude of the profile end point.

    Returns:
        tuple: (lons, lats) as numpy arrays, containing the longitude and latitude for each x in x_grid.
    """
    total_distance_km = geodesic((start_lat, start_lon), (end_lat, end_lon)).km
    lats = []
    lons = []

    for x in x_grid:
        # Compute the fraction of the total profile distance
        fraction = x / total_distance_km
        if fraction > 1.0:
            fraction = 1.0
        # Compute the geographic point at distance x along the profile bearing
        point = geodesic(kilometers=x).destination(
            Point(start_lat, start_lon),
            bearing_from(start_lat, start_lon, end_lat, end_lon)
        )
        lats.append(point.latitude)
        lons.append(point.longitude)

    return np.array(lons), np.array(lats)

def bearing_from(lat1, lon1, lat2, lon2):
    """
    Calculate the initial bearing (forward azimuth) from point (lat1, lon1) to (lat2, lon2).

    Args:
        lat1, lon1: Latitude and longitude of the starting point in degrees.
        lat2, lon2: Latitude and longitude of the ending point in degrees.

    Returns:
        float: Initial bearing in degrees from North.
    """
    import math
    dlon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360

def interpolate_within_layer(poly, vel_df, resolution=[700,50], smooth=10):
    
    path = Path(poly)
    in_layer = path.contains_points(vel_df[['x', 'y']].values)
    vel_in_layer = vel_df[in_layer]
    
    # Local bounding box grid for interpolation
    min_x, max_x = np.min([p[0] for p in poly]), np.max([p[0] for p in poly])
    min_y, max_y = np.min([p[1] for p in poly]), np.max([p[1] for p in poly])

    xi_local = np.linspace(min_x, max_x, resolution[0])
    yi_local = np.linspace(min_y, max_y, resolution[1])
    
    X_layer, Y_layer = np.meshgrid(xi_local, yi_local)

    V_model = griddata(
    (vel_in_layer['x'], vel_in_layer['y']),
    vel_in_layer['velocity'],
    (X_layer, Y_layer),
    method='nearest',
    )

    points = np.vstack((X_layer.ravel(), Y_layer.ravel())).T
    inside = path.contains_points(points).reshape(X_layer.shape)
    V_smooth = gaussian_filter(V_model, sigma=smooth)
    V_masked = np.ma.array(V_smooth, mask=~inside)
    
    return X_layer, Y_layer, V_masked

def interpolate_transition_layer(poly, polygon_above, polygon_below, vel_df, resolution=[700,50], x_bounds=(50, 300)):
    # Create full horizontal grid (0–400 km) and local vertical range
    min_y = np.min([p[1] for p in poly])
    max_y = np.max([p[1] for p in poly])
    min_x, max_x = x_bounds

    xi = np.linspace(min_x, max_x, resolution[0])
    yi = np.linspace(min_y, max_y, resolution[1])
    X, Y = np.meshgrid(xi, yi)

    # Create mask from polygon
    path = Path(poly)
    XY = np.vstack((X.ravel(), Y.ravel())).T
    inside_mask = path.contains_points(XY).reshape(X.shape)

    # Extract velocity points for above and below
    coords = vel_df[['x', 'y']].values
    v_above = vel_df[Path(polygon_above).contains_points(coords)]
    v_below = vel_df[Path(polygon_below).contains_points(coords)]

    if v_above.empty or v_below.empty:
        raise ValueError("Missing velocity points in layers above or below")

    tree_above = cKDTree(v_above[['x', 'y']])
    tree_below = cKDTree(v_below[['x', 'y']])

    V_interp = np.full_like(X, np.nan, dtype=float)

    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            if not inside_mask[i, j]:
                continue

            x, y = X[i, j], Y[i, j]

            # Nearest point above
            _, idx_top = tree_above.query([x, y])
            y_top = v_above.iloc[idx_top]['y']
            v_top = v_above.iloc[idx_top]['velocity']

            # Nearest point below
            _, idx_bot = tree_below.query([x, y])
            y_bot = v_below.iloc[idx_bot]['y']
            v_bot = v_below.iloc[idx_bot]['velocity']

            # Linear interpolation
            if y_top == y_bot:
                V_interp[i, j] = v_top
            else:
                V_interp[i, j] = v_top + (y - y_top) / (y_bot - y_top) * (v_bot - v_top)

    V_masked = ma.masked_invalid(V_interp)
    return X, Y, V_masked

def fill_nan_nearest(arr):
    # Apply a filter that replaces NaNs with the nearest non-NaN value in the local window
    def nan_helper(values):
        center = values[len(values) // 2]
        if np.isnan(center):
            non_nan_values = values[~np.isnan(values)]
            if len(non_nan_values) > 0:
                return non_nan_values[0]
            else:
                return np.nan
        else:
            return center

    # Apply 3x3 window filter
    return generic_filter(arr, nan_helper, size=3, mode='nearest')