import numpy as np
import pytest
from polar2wgs84.densify_geometry import _densify_segment_km
from polar2wgs84.densify_geometry import _lonlat_to_unit
from polar2wgs84.densify_geometry import _unit_to_lonlat
from polar2wgs84.densify_geometry import DensifyGeometryGeodesic
from polar2wgs84.exception import InvalidGeometryError
from shapely.geometry import Polygon


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def simple_square_polygon():
    """
    A small square near the equator to keep geodesic distortion minimal.
    """
    return Polygon(
        [
            (0.0, 0.0),
            (1.0, 0.0),
            (1.0, 1.0),
            (0.0, 1.0),
            (0.0, 0.0),
        ]
    )


@pytest.fixture
def polygon_with_hole():
    """
    Polygon with a square hole.
    """
    exterior = [
        (0, 0),
        (10, 0),
        (10, 10),
        (0, 10),
        (0, 0),
    ]
    hole = [
        (3, 3),
        (7, 3),
        (7, 7),
        (3, 7),
        (3, 3),
    ]
    return Polygon(exterior, [hole])


# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------


def test_init_accepts_polygon(simple_square_polygon):
    densifier = DensifyGeometryGeodesic(simple_square_polygon)
    assert densifier.geometry.equals(simple_square_polygon)


def test_init_rejects_non_polygon():
    with pytest.raises(InvalidGeometryError):
        DensifyGeometryGeodesic("not a polygon")


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------


def test_lonlat_to_unit_and_back_roundtrip(simple_square_polygon):
    lon, lat = 12.3, -45.6
    u = _lonlat_to_unit(lon, lat)
    ll = _unit_to_lonlat(u)
    lon2 = ll[0]
    lat2 = ll[1]

    assert np.isclose(lon, lon2, atol=1e-6)
    assert np.isclose(lat, lat2, atol=1e-6)


def test_densify_segment_zero_length(simple_square_polygon):
    densifier = DensifyGeometryGeodesic(simple_square_polygon)

    pts = _densify_segment_km(
        lon0=0,
        lat0=0,
        lon1=0,
        lat1=0,
        max_step_km=10,
        radius_planet=densifier.R_EARTH_KM,
    )

    assert np.allclose(pts, np.array([[0.0, 0.0]]))


def test_densify_segment_increases_points(simple_square_polygon):
    densifier = DensifyGeometryGeodesic(simple_square_polygon)

    pts = _densify_segment_km(
        lon0=0,
        lat0=0,
        lon1=10,
        lat1=0,
        max_step_km=100,
        radius_planet=densifier.R_EARTH_KM,
    )

    assert len(pts) > 2
    assert pts[0] == pytest.approx((0, 0))
    assert pts[-1] == pytest.approx((10, 0))


# -----------------------------------------------------------------------------
# Ring densification
# -----------------------------------------------------------------------------


def test_densify_ring_preserves_closure(simple_square_polygon):
    densifier = DensifyGeometryGeodesic(simple_square_polygon)

    coords = list(simple_square_polygon.exterior.coords)
    densified = densifier._densify_ring_km(
        coords, max_step_km=50, radius_planet=densifier.R_EARTH_KM
    )

    assert np.array_equal(densified[0], densified[-1])
    assert len(densified) > len(coords)


# -----------------------------------------------------------------------------
# Polygon densification
# -----------------------------------------------------------------------------


def test_densify_polygon_increases_vertex_count(simple_square_polygon):
    densifier = DensifyGeometryGeodesic(simple_square_polygon)

    densified = densifier.densify_polygon_km(max_step_km=50)

    assert isinstance(densified, Polygon)
    assert len(densified.exterior.coords) > len(simple_square_polygon.exterior.coords)
    assert densified.is_valid


def test_densify_polygon_with_hole(polygon_with_hole):
    densifier = DensifyGeometryGeodesic(polygon_with_hole)

    densified = densifier.densify_polygon_km(max_step_km=100)

    assert len(densified.interiors) == 1
    assert densified.is_valid
    assert len(densified.exterior.coords) > len(polygon_with_hole.exterior.coords)
    assert len(densified.interiors[0].coords) > len(
        polygon_with_hole.interiors[0].coords
    )


# -----------------------------------------------------------------------------
# Vertex limiting
# -----------------------------------------------------------------------------


def test_limit_polygon_vertices_reduces_points(simple_square_polygon):
    densifier = DensifyGeometryGeodesic(simple_square_polygon)

    # Artificially densify
    dense = densifier.densify_polygon_km(max_step_km=10)

    simplified = DensifyGeometryGeodesic.limit_polygon_vertices(dense, max_points=10)

    assert isinstance(simplified, Polygon)
    assert len(simplified.exterior.coords) <= 10
    assert simplified.is_valid


def test_limit_polygon_vertices_no_change_if_already_small(simple_square_polygon):
    simplified = DensifyGeometryGeodesic.limit_polygon_vertices(
        simple_square_polygon, max_points=10
    )

    assert simplified.equals(simple_square_polygon)
