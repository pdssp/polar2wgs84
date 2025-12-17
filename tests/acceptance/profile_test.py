import json
import os
from pathlib import Path

import pytest
from polar2wgs84.footprint import check_polygon
from polar2wgs84.footprint import Footprint
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon
from shapely.geometry import shape


def load_polygon(geometry):
    polygon = geometry
    if isinstance(polygon, str):
        my_directory = Path(__file__).resolve().parent
        file_path = my_directory / polygon
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        polygon = shape(data["features"][0]["geometry"])
    return polygon


# Liste des géométries à tester, avec leurs paramètres associés
test_geometries = [
    {
        "name": "Footprint1",
        "poly": "footprint1.json",
    },
    {
        "name": "Footprint3",
        "poly": "footprint3.json",
    },
    {
        "name": "Footprint4",
        "poly": "footprint4.json",
    },
    {
        "name": "Footprint5",
        "poly": "footprint5.json",
    },
    {
        "name": "Footprint6",
        "poly": "footprint6.json",
    },
    {
        "name": "Footprint7",
        "poly": "footprint7.json",
    },
    {
        "name": "Footprint8",
        "poly": "footprint8.json",
    },
    {
        "name": "Footprint9",
        "poly": "footprint9.json",
    },
    {
        "name": "Footprint11",
        "poly": "footprint11.json",
    },
    {
        "name": "Footprint12",
        "poly": "footprint12.json",
    },
    {
        "name": "Footprint17",
        "poly": "footprint17.json",
    },
    {
        "name": "Footprint18",
        "poly": "footprint18.json",
    },
    {
        "name": "On Antimeridian",
        "poly": Polygon(
            [
                (180, 60),
                (180, 70),
                (175, 70),
                (175, 60),
                (180, 60),
            ]
        ),
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
    },
    {
        "name": "Small Arctic Polygon",
        "poly": Polygon([(0, 80), (30, 80), (60, 80), (-30, 85), (0, 80)]),
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
    },
    {
        "name": "S",
        "poly": Polygon(
            [
                (150, 50),
                (-170, 50),
                (-170, 40),
                (170, 40),
                (170, 30),
                (-170, 30),
                (-170, 0),
                (150, 0),
                (150, 10),
                (160, 10),
                (160, 20),
                (150, 20),
                (150, 50),
            ]
        ),
    },
]


def compute_nbpoints(geometry: Polygon | MultiPolygon):
    if isinstance(geometry, MultiPolygon):
        nb_points = 0
        for poly in geometry.geoms:
            nb_points += len(poly.exterior.coords)
    else:
        nb_points = len(geometry.exterior.coords)
    return nb_points


@pytest.mark.parametrize("geometry", test_geometries)
def test_manual_geometry_processing(geometry):
    """Test manuel pour chaque géométrie définie."""
    print(f"\n=== Testing: {geometry['name']} ===")

    polygon: Polygon = load_polygon(geometry["poly"])
    footprint = Footprint(polygon)
    geom_wgs84 = footprint.make_valid_geojson_geometry()
    geom_wgs84_simplified = footprint.to_wgs84_plate_carre(geom_wgs84)

    check_polygon(geom_wgs84)
    check_polygon(geom_wgs84_simplified)
    assert geom_wgs84.is_valid is True
    assert geom_wgs84_simplified.is_valid is True
