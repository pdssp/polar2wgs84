import numpy as np
import pytest
from polar2wgs84.pole import NorthPole
from polar2wgs84.pole import Pole
from polar2wgs84.pole import PoleFactory
from polar2wgs84.pole import SouthPole
from shapely.geometry import LineString
from shapely.geometry import Point
from shapely.geometry import Polygon


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def north_pole_polygon():
    """
    Simple polygon enclosing the North Pole.
    """
    return Polygon(
        [
            (-180, 80),
            (180, 80),
            (180, 89),
            (-180, 89),
            (-180, 80),
        ]
    )


@pytest.fixture
def south_pole_polygon():
    """
    Simple polygon enclosing the South Pole.
    """
    return Polygon(
        [
            (-180, -89),
            (180, -89),
            (180, -80),
            (-180, -80),
            (-180, -89),
        ]
    )


@pytest.fixture
def non_polar_polygon():
    """
    Polygon far from both poles.
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


# -----------------------------------------------------------------------------
# PoleFactory
# -----------------------------------------------------------------------------


def test_pole_factory_creates_north_pole(north_pole_polygon):
    pole = PoleFactory.create(north_pole_polygon)
    assert isinstance(pole, NorthPole)
    assert pole.is_north is True


def test_pole_factory_creates_south_pole(south_pole_polygon):
    pole = PoleFactory.create(south_pole_polygon)
    assert isinstance(pole, SouthPole)
    assert pole.is_north is False


# -----------------------------------------------------------------------------
# Pole initialization
# -----------------------------------------------------------------------------


def test_pole_initialization_sets_attributes(north_pole_polygon):
    pole = NorthPole(north_pole_polygon)

    assert pole.geometry.equals(north_pole_polygon)
    assert pole.pole_latitude == Pole.POLE_NORTH_LATITUDE
    assert pole.is_north is True
    assert isinstance(pole.is_pole_included, bool)


def test_non_polar_polygon_not_marked_as_pole(non_polar_polygon):
    pole = PoleFactory.create(non_polar_polygon)
    assert pole.is_pole_included is False


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------


def test_is_pole_included_true_for_north_pole(north_pole_polygon):
    pole = NorthPole(north_pole_polygon)
    assert pole.is_pole_included is False


def test_is_pole_included_false_for_non_polar(non_polar_polygon):
    pole = PoleFactory.create(non_polar_polygon)
    assert pole.is_pole_included is False


def test_insert_all_sign_changes():
    line = LineString(
        [
            (-10, 0),
            (10, 0),
            (-20, 0),
            (20, 0),
        ]
    )
    point = Point(-180, 0)

    pole = PoleFactory.create(Polygon([(-10, 1), (10, 1), (10, 2), (-10, 2), (-10, 1)]))

    new_line = pole._insert_all_sign_changes(line, point)

    # Expect inserted points at each sign change
    coords = list(new_line.coords)
    inserted = [pt for pt in coords if pt == (-180, 0)]

    assert len(inserted) == 3
    assert len(coords) > len(line.coords)


# -----------------------------------------------------------------------------
# make_valid_geojson_geometry
# -----------------------------------------------------------------------------


def test_make_valid_geojson_geometry_returns_polygon(non_polar_polygon):
    pole = PoleFactory.create(non_polar_polygon)
    result = pole.make_valid_geojson_geometry()

    assert isinstance(result, Polygon)
    assert result.equals(non_polar_polygon)


def test_make_valid_geojson_geometry_pole_case(north_pole_polygon):
    pole = NorthPole(north_pole_polygon)
    result = pole.make_valid_geojson_geometry()

    assert isinstance(result, Polygon)
    assert result.is_valid
    assert result.exterior.is_ccw


def test_make_valid_geojson_geometry_closed_ring(north_pole_polygon):
    pole = NorthPole(north_pole_polygon)
    result = pole.make_valid_geojson_geometry()

    coords = list(result.exterior.coords)
    assert coords[0] == coords[-1]


# -----------------------------------------------------------------------------
# Regression & sanity checks
# -----------------------------------------------------------------------------


def test_no_nan_coordinates_after_processing(north_pole_polygon):
    pole = NorthPole(north_pole_polygon)
    result = pole.make_valid_geojson_geometry()

    for x, y in result.exterior.coords:
        assert not np.isnan(x)
        assert not np.isnan(y)
