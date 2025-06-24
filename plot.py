import argparse
from src.plotting import plot_section

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot a Vp model from the NetCDF file and layer boundary CSV generated with legacy-lines."
    )
    parser.add_argument("--ncfile", required=True, help="Path to NetCDF file (e.g. ICSSP_vp.nc)")
    parser.add_argument("--bounds", required=True, help="Path to CSV file (e.g. ICSSP_layers.csv)")
    parser.add_argument("--title", default="Vp cross section", help="Title to use for the plot")
    parser.add_argument("--cmap", default="gnuplot2_r", help="Matplotlib colormap (default: gnuplot2_r)")
    parser.add_argument("--vmin", type=float, default=4.5, help="Min value for colour scale (default: 4.5)")
    parser.add_argument("--vmax", type=float, default=8.5, help="Max value for colour scale (default: 8.5)")
    parser.add_argument("--output", default="vp_plot.png", help="Output figure filename (default: ICSSP_vp.png)")

    args = parser.parse_args()

    plot_section(
        ncfile=args.ncfile,
        layers_file=args.bounds,
        title=args.title,
        cmap=args.cmap,
        vmin=args.vmin,
        vmax=args.vmax,
        output=args.output
    )
