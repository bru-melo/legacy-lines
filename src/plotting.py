
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt

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