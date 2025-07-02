
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import pygmt
from geopy.distance import geodesic

def plot_section(ncfile, layers_file, output='vp_plot', title='Vp cross section', cmap='gnuplot2_r', vmin=4.5, vmax=8.5):
    # Load data
    bounds = pd.read_csv(layers_file)
    ds = xr.open_dataset(ncfile)

    # Extract coordinates and Vp
    x = ds["x"]
    z = ds["z"]
    vp = ds["vp"]

    # Plot
    fig, ax = plt.subplots(figsize=(12, 5))
    c = ax.pcolormesh(x, z, vp, shading='auto', cmap=cmap, vmin=vmin, vmax=vmax)

    for id, group in bounds.groupby("layer"):
        ax.plot(group["x"], group["z"], color='k', linewidth=1.2)

    ax.invert_yaxis()
    ax.set_xlabel("Distance (km)")
    ax.set_ylabel("Depth (km)")
    cbar = fig.colorbar(c, ax=ax, label="Vp (km/s)")
    cbar.ax.invert_yaxis()
    ax.set_title(title)
    plt.tight_layout()

    # Save and show
    fig.savefig(output, dpi=300)
    plt.show()
    
# Functions used in interpolate-3D.ipynb

def plot_scatter(fig, files, lines, depth, tolerance, spacing):
    """
    Sample original Vp profile points at a given depth ± tolerance, with minimum spacing.

    Parameters:
        depth (float): Target depth (km).
        tolerance (float): Depth window (km).
        spacing (float): Minimum spacing between points (km).

    Returns:
        pd.DataFrame: DataFrame with columns ['lon', 'lat', 'vp'] for sampled points.
    """
    # Collect original Vp sample points at target depth ± tol
    scatter_points = []

    for path in files:
        ds_2d = xr.open_dataset(path)
        lat = ds_2d["lat"].values
        lon = ds_2d["lon"].values
        z   = ds_2d["z"].values
        vp  = ds_2d["vp"].values  # shape (z, x)

        # Find indices of depth levels close to target depth
        close_depths = np.where(np.abs(z - depth) <= tolerance)[0]

        for zi in close_depths:
            last_sample_point = None
            for j in range(len(lon)):
                point = (lat[j], lon[j])
                # Only sample if far enough from last point
                if last_sample_point is None or geodesic(point, last_sample_point).km >= spacing:
                    scatter_points.append([lon[j], lat[j], vp[zi, j]])
                    last_sample_point = point

    # Convert to DataFrame
    df_scatter = pd.DataFrame(scatter_points, columns=["lon", "lat", "vp"]) 
            
    # Plot each line
    for _, row in lines.iterrows():
        fig.plot(x=[row["start_lon"], row["end_lon"]],
                    y=[row["start_lat"], row["end_lat"]],
                    pen="2p,red")
                    #label=row["tag"]) 

    # Overlay Vp sample points at target depth
    fig.plot(
        x=df_scatter["lon"],
        y=df_scatter["lat"],
        style="c0.2c",
        fill=df_scatter["vp"],
        cmap=True,
        pen="black",
    )

# # Optionally annotate line names at midpoints
# for _, row in lines.iterrows():
#     mid_lon = (row["start_lon"] + row["end_lon"]) / 2
#     mid_lat = (row["start_lat"] + row["end_lat"]) / 2
#     fig.text(x=row["start_lon"],
#              y=row["start_lat"], 
#              text=row["tag"], 
#              font="10p,Helvetica-Bold,black", 
#              justify="LT")
    return

def plot_velocity_map(fig, ds, region, depth, cmap="plasma", series=[5, 8, 0.1]):
    
    lat = ds["lat"].values
    lon = ds["lon"].values
    z   = ds["z"].values
    vp = ds["vp"].transpose("z", "lat", "lon").values
    depth_idx = (np.abs(z - depth)).argmin()
    vp_slice = vp[depth_idx, :, :]  # (lat, lon)
    ds_slice = xr.Dataset(
        {"vp": (("lat", "lon"), vp_slice)},
        coords={"lat": lat, "lon": lon}
    )
    
    fig.basemap(
        region=region,
        #projection="L-8/53.5/49.5/53.5/14c",
        projection="M?",
        #frame=["a", f"+tVp at {z[depth_idx]:.1f} km"]
    )
    pygmt.makecpt(cmap=cmap, series=series, background=True, reverse=False)#, continuous=True)
    fig.grdimage(grid=ds_slice["vp"], shading=False, nan_transparent=True)
    fig.coast(shorelines=True, borders="1/0.5p,black", resolution="i")#, water="white")
    fig.text(position='TL', text=str(depth) + "km", clearance="0.1c", fill="white")
    #fig.colorbar(frame='af+lVp (km/s)')