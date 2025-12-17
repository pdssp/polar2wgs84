"""
Southern Polar Polygon with Circum-Antarctic Shape
==================================================
"""

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from polar2wgs84.footprint import Footprint
from polar2wgs84.projection import compute_centroid
from polar2wgs84.projection import compute_nbpoints
from polar2wgs84.visu import GeometryVisualizer
from shapely import Polygon

polygon = Polygon(
    [
        (0, -80),
        (30, -85),
        (60, -80),
        (90, -75),
        (110, -80),
        (-110, -80),
        (-90, -75),
        (-45, -80),
        (-20, -75),
        (0, -80),
    ]
)

footprint = Footprint(polygon)
valid_geom = footprint.make_valid_geojson_geometry()
simplified_valid_geom = footprint.to_wgs84_plate_carre(valid_geom)

lon_mean, lat_mean = compute_centroid(valid_geom)
proj = ccrs.Orthographic(central_longitude=lon_mean, central_latitude=lat_mean)
nb_points = compute_nbpoints(valid_geom)
nb_points_simplified = compute_nbpoints(simplified_valid_geom)


fig = plt.figure(figsize=(21, 7))

ax1 = fig.add_subplot(1, 4, 1, projection=proj)
GeometryVisualizer.draw_geometry(
    ax1,
    "original",
    polygon,
    ccrs.PlateCarree(),
    mode="points",
    edgecolor="blue",
)
ax2 = fig.add_subplot(1, 4, 2, projection=ccrs.PlateCarree())
GeometryVisualizer.draw_geometry(
    ax2,
    f"Projected ({nb_points}) points",
    valid_geom,
    ccrs.PlateCarree(),
    mode="lines",
    edgecolor="blue",
)

# Original
ax3 = fig.add_subplot(1, 4, 3, projection=ccrs.PlateCarree())
GeometryVisualizer.draw_geometry(
    ax3,
    f"Densify & projected ({nb_points_simplified} points)",
    simplified_valid_geom,
    ccrs.PlateCarree(),
    mode="lines",
    edgecolor="blue",
)

ax4 = fig.add_subplot(1, 4, 4, projection=proj)
GeometryVisualizer.draw_geometry(
    ax4,
    f"Densify & projected ({nb_points_simplified} points)",
    simplified_valid_geom,
    ccrs.PlateCarree(),
    mode="points",
    edgecolor="blue",
)

plt.tight_layout()
plt.show()

# %%
