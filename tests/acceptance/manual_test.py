import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import pytest
from polar2wgs84.projection import check_polygon
from polar2wgs84.projection import GeometryProcessor
from polar2wgs84.projection import GeometryVisualizer
from shapely.geometry import Polygon

# Liste des géométries à tester, avec leurs paramètres associés
test_geometries = [
    {
        "name": "Antarctic Polygon with Pole",
        "poly": Polygon(
            [
                (-3000000, 0),
                (-2000000, 500000),
                (-1000000, 500000),
                (0, 0),  # Pole on the line
                (-3000000, 0),
            ]
        ),
        "src_crs": "EPSG:3031",
        "dst_crs": "EPSG:4326",
        "max_distance": 50000,
        "tolerance": 0.05,
        "display_mode": "lines",
        "extent_polar": [-3000000, 3000000, -3000000, 3000000],
        "extent_wgs84": [-180, 180, -90, 90],
    },
    {
        "name": "Full Circle around North Pole",
        "poly": Polygon(
            [
                (3000000, 0),  # 0°
                (2121320, 2121320),  # 30°
                (0, 3000000),  # 90°
                (-2121320, 2121320),  # 150°
                (-3000000, 0),  # 180°
                (-2121320, -2121320),  # 210°
                (0, -3000000),  # 270°
                (2121320, -2121320),  # 330°
                (3000000, 0),
            ]
        ),
        "src_crs": "EPSG:3575",
        "dst_crs": "EPSG:4326",
        "max_distance": 50000,
        "tolerance": 0.05,
        "display_mode": "lines",
        "extent_polar": [-3000000, 3000000, -3000000, 3000000],
        "extent_wgs84": [-180, 180, 0, 90],  # Hémisphère Nord uniquement
    },
    {
        "name": "Small Arctic Polygon",
        "poly": Polygon([(0, 80), (30, 80), (60, 80), (-30, 85), (0, 80)]),
        "src_crs": "EPSG:4326",  # WGS84, mais sera détecté comme polaire
        "dst_crs": "EPSG:4326",
        "max_distance": 50000,
        "tolerance": 0.05,
        "display_mode": "lines",
        "extent_polar": [-3000000, 3000000, -3000000, 3000000],
        "extent_wgs84": [-180, 180, 0, 90],
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
        "tolerance": 0.05,
        "display_mode": "lines",
        "extent_polar": [-3000000, 3000000, -3000000, 3000000],
        "extent_wgs84": [-180, 180, -90, 0],  # Hémisphère Sud uniquement
    },
]


@pytest.mark.parametrize("geometry", test_geometries)
@pytest.mark.manual
def test_manual_geometry_processing(geometry):
    """Test manuel pour chaque géométrie définie."""
    print(f"\n=== Testing: {geometry['name']} ===")

    # Initialisation
    processor = GeometryProcessor(
        geometry["src_crs"], geometry["dst_crs"], geometry["poly"]
    )

    # Pipeline de traitement
    poly_dense = processor.densify_geometry(max_distance=geometry["max_distance"])
    poly_reproj = processor.reproject_geometry(poly_dense)
    poly_final = GeometryProcessor.simplify_geometry(
        poly_reproj, tolerance=geometry["tolerance"]
    )
    poly_back = processor.reproject_geometry(poly_final, reverse=True)

    # Vérification des polygones
    print("\n--- Checking initial polygon ---")
    check_polygon(geometry["poly"])
    print("\n--- Checking reprojected polygon ---")
    check_polygon(poly_final)
    print("\n--- Checking back-projected polar polygon ---")
    check_polygon(poly_back)

    # Visualisation
    source_crs_cartopy = (
        ccrs.SouthPolarStereo()
        if geometry["src_crs"] == "EPSG:3031"
        else ccrs.NorthPolarStereo()
    )
    target_crs_cartopy = ccrs.PlateCarree()
    fig = plt.figure(figsize=(21, 7))

    # Original
    ax1 = fig.add_subplot(1, 3, 1, projection=source_crs_cartopy)
    ax1.set_title(f"Original ({processor.src_crs})")
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
        processor.geom,
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
        poly_final,
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
        poly_back,
        source_crs_cartopy,
        mode=geometry["display_mode"],
        edgecolor="green",
    )

    plt.tight_layout()
    plt.show(block=False)

    user_input = input("Is it valid ? (y/n) : ").strip().lower()
    assert user_input == "y", "Graphic rejected by user."

    plt.close()
