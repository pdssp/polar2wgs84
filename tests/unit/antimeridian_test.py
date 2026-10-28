# Polar to WGS84 Converter - Global geometry processing utilities for GeoJSON-safe WGS84 polygons.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""Tests of the rebuild of rings whose edges cross the antimeridian unsplit."""

import pytest
from loguru import logger
from polar2wgs84.antimeridian import crosses_antimeridian
from polar2wgs84.antimeridian import resolve_antimeridian_rings
from polar2wgs84.footprint import Footprint
from shapely import wkt as shapely_wkt
from shapely.geometry import MultiPolygon
from shapely.geometry import Point
from shapely.geometry import Polygon

# MRO CTX footprint J06_046958_0890_XN_89S158W: small quadrilateral near the
# south pole whose two long edges cross ±180°.
CTX_POLAR = (
    "POLYGON ((-134.99 -87.72330521813524, -148.74 -87.62212143546462, "
    "100.63 -89.10955011352192, 62.93 -89.43334943876465, "
    "-134.99 -87.72330521813524))"
)


def same_geometry(geom, wkt: str) -> bool:
    """Compare a geometry with a WKT, regardless of the vertex order."""
    other = shapely_wkt.loads(wkt)
    return geom.equals(other)


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("POLYGON ((170 0, -170 0, -170 10, 170 10, 170 0))", True),
        (CTX_POLAR, True),
        ("POLYGON ((-10 0, 10 0, 10 5, -10 5, -10 0))", False),
        # Already split at ±180°.
        (
            (
                "MULTIPOLYGON (((170 0, 180 0, 180 10, 170 10, 170 0)), "
                "((-180 0, -170 0, -170 10, -180 10, -180 0)))"
            ),
            False,
        ),
        # Ring around a pole.
        ("POLYGON ((0 80, 90 75, 180 80, -90 85, 0 80))", False),
        # Edge spanning the full width: band described in the plane.
        ("POLYGON ((-180 -10, 180 -10, 180 10, -180 10, -180 -10))", False),
        # Vertex at the pole.
        ("POLYGON ((-170 80, 170 80, 0 90, -170 80))", False),
        ("LINESTRING (170 0, -170 0)", False),
    ],
)
def test_crosses_antimeridian(src, expected):
    assert crosses_antimeridian(shapely_wkt.loads(src)) is expected


def test_resolve_splits_at_antimeridian():
    out = resolve_antimeridian_rings(
        shapely_wkt.loads("POLYGON ((170 0, -170 0, -170 10, 170 10, 170 0))")
    )
    assert isinstance(out, MultiPolygon)
    assert same_geometry(
        out,
        "MULTIPOLYGON (((170 0, 180 0, 180 10, 170 10, 170 0)), "
        "((-180 0, -170 0, -170 10, -180 10, -180 0)))",
    )


def test_resolve_keeps_other_geometries():
    src = shapely_wkt.loads("POLYGON ((-10 0, 10 0, 10 5, -10 5, -10 0))")
    assert resolve_antimeridian_rings(src) is src


def test_wide_box_is_reinterpreted():
    """A box wider than 180° becomes its narrower complement across ±180°."""
    out = resolve_antimeridian_rings(
        shapely_wkt.loads("POLYGON ((-100 0, 100 0, 100 10, -100 10, -100 0))")
    )
    assert isinstance(out, MultiPolygon)
    assert same_geometry(
        out,
        "MULTIPOLYGON (((100 0, 180 0, 180 10, 100 10, 100 0)), "
        "((-180 0, -100 0, -100 10, -180 10, -180 0)))",
    )


def test_rebuild_logs_warning():
    messages: list[str] = []
    handler = logger.add(lambda m: messages.append(m), level="WARNING")
    try:
        resolve_antimeridian_rings(shapely_wkt.loads(CTX_POLAR))
        resolve_antimeridian_rings(
            shapely_wkt.loads("POLYGON ((-10 0, 10 0, 10 5, -10 5, -10 0))")
        )
    finally:
        logger.remove(handler)
    assert len(messages) == 1
    assert "antimeridian" in messages[0]


def test_footprint_polar_footprint():
    """Near the pole, edges are rebuilt along their great circle."""
    footprint = Footprint(shapely_wkt.loads(CTX_POLAR))
    out = footprint.make_valid_geojson_geometry()
    assert out.is_valid
    assert isinstance(out, MultiPolygon)
    # Split at ±180°: eastern part 62.93° → 180°, western part -180° → -134.99°.
    lon_bounds = sorted(p.bounds[0::2] for p in out.geoms)
    assert lon_bounds[0] == pytest.approx((-180.0, -134.99))
    assert lon_bounds[1] == pytest.approx((62.93, 180.0))
    # The great circle from 62.93° to -134.99° passes close to the pole.
    assert out.bounds[3] == pytest.approx(-87.62212143546462)
    assert -90 < out.bounds[1] < -89.8
    # Does not wrap around through Greenwich.
    assert not out.intersects(shapely_wkt.loads("LINESTRING (0 -90, 0 -80)"))
    # The pole is not included.
    assert not out.contains(Point(0, -90))


def test_footprint_keeps_already_split_geometry():
    """A geometry already split at ±180° is not rebuilt."""
    src = shapely_wkt.loads(
        "MULTIPOLYGON (((170 0, 180 0, 180 10, 170 10, 170 0)), "
        "((-180 0, -170 0, -170 10, -180 10, -180 0)))"
    )
    assert resolve_antimeridian_rings(src) is src


def test_footprint_conventional_crossing_is_rebuilt():
    """A crossing described conventionally (175° → -175°) is rebuilt and split.

    The rebuilt geometry is the same as the conventional split at ±180°.
    """
    polygon = Polygon(
        [(170, 60), (175, 60), (-175, 65), (175, 70), (170, 70), (170, 60)]
    )
    out = resolve_antimeridian_rings(polygon)
    assert isinstance(out, MultiPolygon)
    assert out.is_valid
    assert not crosses_antimeridian(out)
