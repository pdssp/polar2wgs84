import numpy as np
import pytest
from polar2wgs84.exception import UnsupportedGeometryTypeError
from polar2wgs84.projection import compute_centroid
from polar2wgs84.projection import compute_nbpoints
from polar2wgs84.projection import Projection
from polar2wgs84.projection import Stats
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def simple_polygon():
    """
    Simple square polygon in WGS84.
    """
    return Polygon(
        [
            (-10, 10),
            (10, 10),
            (10, 20),
            (-10, 20),
            (-10, 10),
        ]
    )


@pytest.fixture
def antimeridian_polygon():
    """
    Polygon crossing the antimeridian.
    """
    return Polygon(
        [
            (170, 10),
            (-170, 10),
            (-170, 20),
            (170, 20),
            (170, 10),
        ]
    )


@pytest.fixture
def multipolygon(simple_polygon):
    """
    Simple MultiPolygon composed of two shifted polygons.
    """
    poly2 = Polygon(
        [
            (20, 10),
            (30, 10),
            (30, 20),
            (20, 20),
            (20, 10),
        ]
    )
    return MultiPolygon([simple_polygon, poly2])


@pytest.fixture
def projection():
    return Projection()


# -----------------------------------------------------------------------------
# Projection class
# -----------------------------------------------------------------------------


def test_project_to_plate_carree_roundtrip(simple_polygon, projection):
    projected = projection.project_to_plate_carree(simple_polygon)
    restored = projection.project_to_plate_carree(projected, reverse=True)

    assert isinstance(restored, Polygon)
    assert restored.is_valid
    assert pytest.approx(restored.area, rel=1e-6) == simple_polygon.area


def test_project_to_polar_north_roundtrip(simple_polygon, projection):
    projected = projection.project_to_polar(simple_polygon, is_north=True)
    restored = projection.project_to_polar(projected, is_north=True, reverse=True)

    assert isinstance(restored, Polygon)
    assert restored.is_valid
    assert pytest.approx(restored.area, rel=1e-6) == simple_polygon.area


def test_project_to_polar_south_roundtrip(simple_polygon, projection):
    projected = projection.project_to_polar(simple_polygon, is_north=False)
    restored = projection.project_to_polar(projected, is_north=False, reverse=True)

    assert isinstance(restored, Polygon)
    assert restored.is_valid
    assert pytest.approx(restored.area, rel=1e-6) == simple_polygon.area


def test_projection_with_multipolygon(multipolygon, projection):
    projected = projection.project_to_plate_carree(multipolygon)
    restored = projection.project_to_plate_carree(projected, reverse=True)

    assert isinstance(restored, MultiPolygon)
    assert len(restored.geoms) == 2


# -----------------------------------------------------------------------------
# Stats dataclass
# -----------------------------------------------------------------------------


def test_stats_dataclass():
    stats = Stats(
        only_positive_lat=True,
        only_negative_lat=False,
        high_latitude_pos=3,
        high_latitude_neg=0,
    )

    assert stats.only_positive_lat is True
    assert stats.only_negative_lat is False
    assert stats.high_latitude_pos == 3
    assert stats.high_latitude_neg == 0


# -----------------------------------------------------------------------------
# compute_nbpoints
# -----------------------------------------------------------------------------


def test_compute_nbpoints_polygon(simple_polygon):
    nb = compute_nbpoints(simple_polygon)
    assert nb == len(simple_polygon.exterior.coords)


def test_compute_nbpoints_multipolygon(multipolygon):
    nb = compute_nbpoints(multipolygon)
    expected = sum(len(p.exterior.coords) for p in multipolygon.geoms)
    assert nb == expected


# -----------------------------------------------------------------------------
# compute_centroid
# -----------------------------------------------------------------------------


def test_compute_centroid_simple_polygon(simple_polygon):
    lon, lat = compute_centroid(simple_polygon)

    assert -180 <= lon <= 180
    assert -90 <= lat <= 90

    # Expected centroid approximately (0, 15)
    assert pytest.approx(lon, abs=1e-6) == 0
    assert pytest.approx(lat, abs=1e-6) == 15


def test_compute_centroid_antimeridian_polygon(antimeridian_polygon):
    lon, lat = compute_centroid(antimeridian_polygon)

    assert -180 <= lon <= 180
    assert -90 <= lat <= 90

    # Centroid longitude should be near ±180, not ~0
    assert abs(abs(lon) - 0) < 1e-6
    assert pytest.approx(lat, abs=1e-6) == 15


def test_compute_centroid_multipolygon(multipolygon):
    lon, lat = compute_centroid(multipolygon)

    assert -180 <= lon <= 180
    assert -90 <= lat <= 90


def test_compute_centroid_invalid_type():
    with pytest.raises(UnsupportedGeometryTypeError):
        compute_centroid("not a geometry")  # type: ignore
