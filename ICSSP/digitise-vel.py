# This script allows the user to click on an image to assign velocity values.
# The user can input the velocity after clicking, and the points will be saved to a CSV file.
import matplotlib.pyplot as plt
import csv

import matplotlib
matplotlib.use('MacOSX')  # or 'Qt5Agg' if you have PyQt/PySide installed

from matplotlib.widgets import Cursor

velocity_points = []

def onclick(event):
    if event.inaxes is not None:
        x, y = event.xdata, event.ydata
        print(f"Clicked at x={x:.2f}, y={y:.2f}")
        while True:
            try:
                velocity = float(input("Enter velocity (km/s): "))
                break
            except ValueError:
                print("Invalid input. Please enter a number.")
        velocity_points.append({'x': x, 'y': y, 'velocity': velocity})
        ax.plot(x, y, 'ro')
        fig.canvas.draw()

def onkey(event):
    if event.key.lower() == 'q':
        print("Finished. Closing plot and saving...")
        plt.close()

# Load the image
img = plt.imread("ICSSP-noaxis.png")

fig, ax = plt.subplots()
cursor = Cursor(ax, useblit=True, color='black', linewidth=1)
ax.imshow(img, extent=[0, 400, 45, 0])  # Make sure this matches your image axes
ax.set_xlabel("Distance (km)")
ax.set_ylabel("Depth (km)")
ax.set_title("Click to assign velocity | 'Q' = quit")

fig.canvas.mpl_connect('button_press_event', onclick)
fig.canvas.mpl_connect('key_press_event', onkey)

plt.show()

# Save the data
output_file = "velocity_picks_with_values.csv"
with open(output_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['x', 'y', 'velocity'])
    writer.writeheader()
    for p in velocity_points:
        writer.writerow(p)

print(f"Saved velocity picks to: {output_file}")
