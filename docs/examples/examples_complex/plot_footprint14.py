"""
Footprint 9
===========
"""

import json
import os

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from polar2wgs84.footprint import Footprint
from polar2wgs84.projection import compute_centroid
from polar2wgs84.projection import compute_nbpoints
from polar2wgs84.visu import GeometryVisualizer
from shapely.geometry import shape

cnes_certificate = os.getenv("CNES_CERTIFICATE", False)
if cnes_certificate:
    import ssl

    ssl._create_default_https = ssl.create_default_context
    ssl._create_default_https_context().load_verify_locations(cafile=cnes_certificate)


def load_polygon(geometry):
    polygon = geometry
    if isinstance(polygon, str):
        file_path = os.path.join("../../../tests/acceptance", geometry)
        print(file_path)
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        polygon = shape(data["features"][0]["geometry"])
    return polygon


polygon = load_polygon("footprint9.json")

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
