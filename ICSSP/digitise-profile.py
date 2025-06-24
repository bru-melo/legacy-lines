# Had to run these localy as the server does not allow for pop-up windows
# This script allows you to digitise points on a profile image by clicking on it.
# You can change the layer by pressing 'L' and quit by pressing 'Q'.

import matplotlib.pyplot as plt
import csv

import matplotlib
matplotlib.use('MacOSX')  # or 'Qt5Agg' if you have PyQt/PySide installed

from matplotlib.widgets import Cursor
# Load image
img = plt.imread("ICSSP-rotate.jpeg")
points = []
current_layer = None

def onclick(event):
    if event.inaxes is not None and current_layer is not None:
        x, y = event.xdata, event.ydata
        points.append({'x': x, 'y': y, 'layer': current_layer})
        print(f"Added point: x={x:.2f}, y={y:.2f}, layer={current_layer}")
        ax.plot(x, y, 'ro')
        fig.canvas.draw()

def onkey(event):
    global current_layer
    if event.key.lower() == 'l':
        plt.pause(0.01)
        new_layer = input("Enter new layer name: ")
        if new_layer.strip():
            current_layer = new_layer
            print(f"Switched to layer: {current_layer}")
    elif event.key.lower() == 'q':
        print("Finished digitising. Closing window.")
        plt.close()

fig, ax = plt.subplots()
cursor = Cursor(ax, useblit=True, color='black', linewidth=1)
ax.imshow(img, extent=[0, 400, 45, 0])
ax.set_xlabel("Distance (km)")
ax.set_ylabel("Depth (km)")
ax.set_title("Click to digitise | 'L' = change layer | 'Q' = quit")

plt.pause(0.01)
current_layer = input("Enter initial layer name: ")

fig.canvas.mpl_connect('button_press_event', onclick)
fig.canvas.mpl_connect('key_press_event', onkey)

plt.show()

# Save points grouped by layer
points_sorted = sorted(points, key=lambda p: p['layer'])
with open('digitised_points_no_velocity.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['x', 'y', 'layer'])
    writer.writeheader()
    last_layer = None
    for p in points_sorted:
        if last_layer is not None and p['layer'] != last_layer:
            writer.writerow({'x': '', 'y': '', 'layer': ''})  # blank line between layers
        writer.writerow(p)
        last_layer = p['layer']

print("Saved to 'digitised_points_no_velocity.csv'")