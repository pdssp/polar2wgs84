import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import pytest
from polar2wgs84.footprint import check_polygon
from polar2wgs84.footprint import Footprint
from polar2wgs84.projection import Projection
from polar2wgs84.visu import GeometryVisualizer
from shapely.geometry import Polygon

# Liste des géométries à tester, avec leurs paramètres associés
test_geometries = [
    {
        "name": "On Antimeridian",
        "poly": Polygon(
            [
                (180, 60),  # Point de départ
                (180, 70),  # Traverse l'antiméridien
                (175, 70),  # Après l'antiméridien
                (175, 60),
                (180, 60),
            ]
        ),
        "src_crs": "EPSG:4326",
        "dst_crs": "EPSG:4326",
        "max_distance": 50000,
        "tolerance": 0.5,
        "display_mode": "lines",
        "extent_polar": [-3000000, 3000000, -3000000, 3000000],
        "extent_wgs84": [-180, 180, -90, 90],
    },
    {
        "name": "Simple Antimeridian",
        "poly": Polygon(
            [
                (170, 60),  # Point de départ
                (179, 60),  # Traverse l'antiméridien
                (-170, 60),  # Après l'antiméridien
                (-160, 70),
                (150, 80),
                (170, 60),
            ]
        ),
        "src_crs": "EPSG:4326",
        "dst_crs": "EPSG:4326",
        "max_distance": 50000,
        "tolerance": 0.5,
        "display_mode": "lines",
        "extent_polar": [-3000000, 3000000, -3000000, 3000000],
        "extent_wgs84": [-180, 180, -90, 90],
    },
    {
        "name": "Antimeridian North Pole",
        "poly": Polygon(
            [
                (170, 60),  # Point de départ
                (180, 60),  # Traverse l'antiméridien
                (-170, 60),  # Après l'antiméridien
                (-160, 70),
                (-150, 80),
                (-140, 85),
                (180, 89),  # Pôle Nord
                (140, 85),
                (150, 80),
                (160, 70),
                (170, 60),  # Retour au point de départ pour fermer le polygone
            ]
        ),
        "src_crs": "EPSG:4326",
        "dst_crs": "EPSG:4326",
        "max_distance": 50000,
        "tolerance": 0.5,
        "display_mode": "lines",
        "extent_polar": [-3000000, 3000000, -3000000, 3000000],
        "extent_wgs84": [-180, 180, -90, 90],
    },
    {
        "name": "Small Arctic Polygon",
        "poly": Polygon([(0, 80), (30, 80), (60, 80), (-30, 85), (0, 80)]),
        "src_crs": "EPSG:4326",  # WGS84, mais sera détecté comme polaire
        "dst_crs": "EPSG:4326",
        "max_distance": 50000,
        "tolerance": 0.5,
        "display_mode": "lines",
        "extent_polar": [-30000000, 30000000, -3000000, 3000000],
        "extent_wgs84": [-180, 180, -90, 90],
    },
    {
        "name": "Complex Antarctic Polygon",
        "poly": Polygon(
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
        ),
        "src_crs": "EPSG:4326",
        "dst_crs": "EPSG:4326",
        "max_distance": 50000,
        "tolerance": 0.5,
        "display_mode": "lines",
        "extent_polar": [-3000000, 3000000, -3000000, 3000000],
        "extent_wgs84": [-180, 180, -90, 90],
    },
]


@pytest.mark.parametrize("geometry", test_geometries)
@pytest.mark.manual
def test_manual_geometry_processing(geometry):
    """Test manuel pour chaque géométrie définie."""
    print(f"\n=== Testing: {geometry['name']} ===")

    # Initialisation
    footprint = Footprint(
        geometry["poly"],
        tolerance=geometry["tolerance"],
        max_distance=geometry["max_distance"],
    )
    geom_wgs84 = footprint.toWgs84()

    projection = Projection()
    geometry_projected = projection.reproject_geometry(
        geometry["poly"], footprint.is_north
    )

    geometry_back = projection.reproject_geometry(geom_wgs84, footprint.is_north)

    # Vérification des polygones
    print("\n--- Checking Polar polygon ---")
    check_polygon(geometry_projected)
    print("\n--- Checking WGS84 polygon ---")
    check_polygon(geom_wgs84)
    print("\n--- Checking back-projected polar polygon ---")
    check_polygon(geometry_back)

    # Visualisation
    source_crs_cartopy = (
        ccrs.NorthPolarStereo(central_longitude=180)
        if footprint.is_north
        else ccrs.SouthPolarStereo(central_longitude=180)
    )
    target_crs_cartopy = ccrs.PlateCarree()
    fig = plt.figure(figsize=(21, 7))
    fig.suptitle(f"{geometry['name']}", fontsize=16, fontweight="bold")

    # Original
    ax1 = fig.add_subplot(1, 3, 1, projection=source_crs_cartopy)
    ax1.set_title("Original")
    ax1.set_extent(geometry["extent_polar"], crs=source_crs_cartopy)
    gl1 = ax1.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        linewidth=0.5,
        color="gray",
        alpha=0.5,
        linestyle="--",
    )
    gl1.top_labels = False
    gl1.right_labels = False
    GeometryVisualizer.draw_geometry(
        ax1,
        geometry_projected,
        source_crs_cartopy,
        mode=geometry["display_mode"],
        edgecolor="blue",
    )

    # Reprojected
    ax2 = fig.add_subplot(1, 3, 2, projection=target_crs_cartopy)
    ax2.set_title("Reprojected (EPSG:4326)")
    ax2.set_extent(geometry["extent_wgs84"], crs=target_crs_cartopy)
    gl2 = ax2.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        linewidth=0.5,
        color="gray",
        alpha=0.5,
        linestyle="--",
    )
    gl2.top_labels = True
    gl2.right_labels = True
    GeometryVisualizer.draw_geometry(
        ax2,
        geom_wgs84,
        target_crs_cartopy,
        mode=geometry["display_mode"],
        edgecolor="red",
    )

    # Back to polar
    ax3 = fig.add_subplot(1, 3, 3, projection=source_crs_cartopy)
    ax3.set_title("Back to polar")
    ax3.set_extent(geometry["extent_polar"], crs=source_crs_cartopy)
    gl3 = ax3.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        linewidth=0.5,
        color="gray",
        alpha=0.5,
        linestyle="--",
    )
    gl3.top_labels = False
    gl3.right_labels = False
    GeometryVisualizer.draw_geometry(
        ax3,
        geometry_back,
        source_crs_cartopy,
        mode=geometry["display_mode"],
        edgecolor="green",
    )

    plt.tight_layout()
    plt.show(block=False)

    user_input = input("Is it valid ? (y/n) : ").strip().lower()
    assert user_input == "y", "Graphic rejected by user."

    plt.close()
