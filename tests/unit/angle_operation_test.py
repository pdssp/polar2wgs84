import pytest
from polar2wgs84.angle_operation import normalize_lon_to_180
from polar2wgs84.angle_operation import normalize_lon_to_360
from polar2wgs84.angle_operation import reorganize_longitudes
from shapely.geometry import LineString
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon


# -----------------------------------------------------------------------------
# reorganize_longitudes
# -----------------------------------------------------------------------------


def test_reorganize_longitudes_simple_line():
    line = LineString(
        [
            (10, 0),
            (-170, 0),
            (50, 0),
        ]
    )

    coords = reorganize_longitudes(line)

    # Sorted by longitude
    assert coords[:-1] == [(-170, 0), (10, 0), (50, 0)]
    # Closing placeholder added
    assert coords[-1][0] == 180
    assert coords[-1][1] == coords[0][1]


# -----------------------------------------------------------------------------
# normalize_lon_to_360
# -----------------------------------------------------------------------------


def test_normalize_lon_to_360_linestring():
    line = LineString(
        [
            (-170, 0),
            (170, 0),
        ]
    )

    norm = normalize_lon_to_360(line)
    coords = list(norm.coords)

    assert coords == [(190, 0), (170, 0)]


def test_normalize_lon_to_360_polygon():
    poly = Polygon(
        [
            (-170, 0),
            (-160, 10),
            (170, 10),
            (170, 0),
            (-170, 0),
        ]
    )

    norm = normalize_lon_to_360(poly)
    xs = [x for x, _ in norm.exterior.coords]

    assert all(0 <= x <= 360 for x in xs)


def test_normalize_lon_to_360_multipolygon():
    poly1 = Polygon([(-10, 0), (-10, 1), (10, 1), (10, 0)])
    poly2 = Polygon([(-170, 0), (-170, 1), (-160, 1), (-160, 0)])
    mp = MultiPolygon([poly1, poly2])

    norm = normalize_lon_to_360(mp)

    for poly in norm.geoms:
        for x, _ in poly.exterior.coords:
            assert x >= 0


# -----------------------------------------------------------------------------
# normalize_lon_to_180
# -----------------------------------------------------------------------------


def test_normalize_lon_to_180_default_behavior():
    line = LineString(
        [
            (190, 0),
            (180, 0),
            (170, 0),
        ]
    )

    norm = normalize_lon_to_180(line, is_360_space=False)
    coords = list(norm.coords)

    assert coords == [(-170, 0), (180, 0), (170, 0)]


def test_normalize_lon_to_180_360_space():
    line = LineString(
        [
            (180, 0),
            (190, 0),
            (350, 0),
        ]
    )

    norm = normalize_lon_to_180(line, is_360_space=True)
    coords = list(norm.coords)

    assert coords == [(-180, 0), (-170, 0), (-10, 0)]


def test_normalize_lon_to_180_polygon():
    poly = Polygon(
        [
            (190, 0),
            (200, 10),
            (210, 0),
            (190, 0),
        ]
    )

    norm = normalize_lon_to_180(poly, is_360_space=True)
    xs = [x for x, _ in norm.exterior.coords]

    assert all(-180 <= x <= 180 for x in xs)


# -----------------------------------------------------------------------------
# Round-trip consistency
# -----------------------------------------------------------------------------


def test_round_trip_normalization_polygon():
    poly = Polygon(
        [
            (-170, 0),
            (-160, 10),
            (170, 10),
            (170, 0),
            (-170, 0),
        ]
    )

    norm_360 = normalize_lon_to_360(poly)
    norm_180 = normalize_lon_to_180(norm_360, is_360_space=True)

    orig_coords = list(poly.exterior.coords)
    final_coords = list(norm_180.exterior.coords)

    assert pytest.approx(orig_coords) == final_coords
