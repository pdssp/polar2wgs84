# Polar to WGS84 Converter - polar2wgs84 is a Python tool to seamlessly convert geographic footprints between polar stereographic projections (EPSG:3031/EPSG:3575) and WGS84 (EPSG:4326), handling pole-crossing geometries, densification, and validation for accurate GIS workflows.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
import pytest
from polar2wgs84.projection import check_polygon
from polar2wgs84.projection import GeometryProcessor
from shapely.geometry import LineString
from shapely.geometry import MultiPolygon
from shapely.geometry import Point
from shapely.geometry import Polygon
from shapely.validation import explain_validity


@pytest.fixture
def sample_polar_polygon():
    """Un polygone simple en projection polaire sud (EPSG:3031)."""
    return Polygon(
        [(-3000000, 0), (-2000000, 500000), (-1000000, 500000), (-3000000, 0)]
    )


@pytest.fixture
def sample_wgs84_polygon():
    """Un polygone simple en WGS84 (EPSG:4326) proche du pôle Nord."""
    return Polygon([(0, 80), (30, 80), (60, 80), (30, 85), (0, 80)])


@pytest.fixture
def sample_linestring():
    """Une LineString simple en WGS84."""
    return LineString([(0, 80), (30, 80), (60, 80)])


# --- Tests pour GeometryProcessor ---
def test_init_with_polar_crs(sample_polar_polygon):
    """Teste l'initialisation avec un CRS polaire."""
    processor = GeometryProcessor("EPSG:3031", "EPSG:4326", sample_polar_polygon)
    assert processor.src_crs == "EPSG:3031"
    assert processor.dst_crs == "EPSG:4326"
    assert processor.physical_pole == -90


def test_init_with_wgs84_and_polar_geometry(sample_wgs84_polygon):
    """Teste l'initialisation avec WGS84 et une géométrie polaire (doit basculer en EPSG:3575)."""
    processor = GeometryProcessor("EPSG:4326", "EPSG:4326", sample_wgs84_polygon)
    assert processor.src_crs == "EPSG:3575"  # Doit détecter le pôle Nord et basculer
    assert processor.physical_pole == 90


def test_init_with_unsupported_crs():
    """Teste l'initialisation avec un CRS non supporté."""
    with pytest.raises(Exception, match="CRS.*not supported"):
        GeometryProcessor("EPSG:1234", "EPSG:4326", Polygon([(0, 0), (1, 1), (1, 0)]))


def test_is_polar_projection_suitable_north():
    """Teste la détection d'une géométrie adaptée à une projection polaire Nord."""
    polygon = Polygon([(0, 80), (30, 80), (60, 80), (30, 85), (0, 80)])
    assert GeometryProcessor.is_polar_projection_suitable(polygon) == "north"


def test_is_polar_projection_suitable_south():
    """Teste la détection d'une géométrie adaptée à une projection polaire Sud."""
    polygon = Polygon([(0, -80), (30, -85), (60, -80), (0, -80)])
    assert GeometryProcessor.is_polar_projection_suitable(polygon) == "south"


def test_is_polar_projection_suitable_none():
    """Teste une géométrie non polaire."""
    polygon = Polygon([(-180, 0), (0, 0), (180, 0), (-180, 0)])  # EPSG:4326
    assert GeometryProcessor.is_polar_projection_suitable(polygon) is None


def test_shift_coords_to_minus_180():
    """Teste le réordonnancement des coordonnées pour commencer à -180."""
    coords = [(-180, 80), (-90, 80), (0, 80), (90, 80), (180, 80)]
    shifted_coords = GeometryProcessor.shift_coords_to_minus_180(coords)
    assert shifted_coords[0][0] == -180  # La première coordonnée doit être -180


# --- Tests pour densify_geometry ---
def test_densify_polar_polygon():
    """Teste la densification d'un polygone en projection polaire (EPSG:3575)."""
    # Polygone en projection polaire (EPSG:3575) autour du pôle Nord
    # Coordonnées en mètres (projection stéréographique polaire)
    polygon = Polygon(
        [
            (-1000000, -1000000),  # Coin sud-ouest
            (1000000, -1000000),  # Coin sud-est
            (1000000, 1000000),  # Coin nord-est
            (-1000000, 1000000),  # Coin nord-ouest
            (-1000000, -1000000),  # Retour au coin sud-ouest
        ]
    )

    # Initialiser le GeometryProcessor avec une projection polaire
    processor = GeometryProcessor("EPSG:3575", "EPSG:3575", polygon)

    # Densifier le polygone avec une distance maximale de 200 000 mètres
    densified = processor.densify_geometry(max_distance=200000)

    # Vérifier que des points intermédiaires ont été ajoutés
    assert len(densified.exterior.coords) > 5


# --- Tests pour reproject_geometry ---
def test_reproject_polar_to_wgs84(sample_polar_polygon):
    """Teste la reprojection d'un polygone polaire vers WGS84."""
    processor = GeometryProcessor("EPSG:3031", "EPSG:4326", sample_polar_polygon)
    reprojected = processor.reproject_geometry(sample_polar_polygon)
    assert reprojected.is_valid
    assert reprojected.geom_type == "Polygon"


def test_reproject_wgs84_to_polar(sample_wgs84_polygon):
    """Teste la reprojection d'un polygone WGS84 vers polaire."""
    processor = GeometryProcessor("EPSG:4326", "EPSG:3575", sample_wgs84_polygon)
    reprojected = processor.reproject_geometry(sample_wgs84_polygon)
    assert reprojected.is_valid
    assert reprojected.geom_type == "Polygon"


# --- Tests pour simplify_geometry ---
def test_simplify_geometry():
    """Teste la simplification d'une géométrie."""
    polygon = Polygon([(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (4, 1), (0, 1), (0, 0)])
    simplified = GeometryProcessor.simplify_geometry(polygon, tolerance=1.0)
    assert simplified.is_valid
    assert len(simplified.exterior.coords) < len(polygon.exterior.coords)


# --- Tests pour check_polygon ---
def test_check_polygon_valid(sample_wgs84_polygon):
    """Teste la validation d'un polygone valide."""
    results = check_polygon(sample_wgs84_polygon, verbose=False)
    assert results["is_valid"] is True
    assert results["area"] > 0


def test_check_polygon_invalid():
    """Teste la validation d'un polygone invalide."""
    invalid_polygon = Polygon(
        [(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)]
    )  # Auto-intersection
    results = check_polygon(invalid_polygon, verbose=False)
    assert results["is_valid"] is False
    assert "Self-intersection" in results["validity_reason"]
