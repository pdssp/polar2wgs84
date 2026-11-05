# Polar to WGS84 Converter - Global geometry processing utilities for GeoJSON-safe WGS84 polygons.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""Tests of the repair of self-intersecting rings (bow-tie polygons)."""
import pytest
from polar2wgs84.footprint import Footprint
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon

# (0, 0) - (2, 2) crosses (2, 0) - (0, 2): a self-intersecting bow-tie
# made of two triangles of area 1 each.
BOWTIE = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])


def test_bowtie_is_repaired_by_make_valid_geojson_geometry():
    assert not BOWTIE.is_valid

    footprint = Footprint(BOWTIE)
    geom = footprint.make_valid_geojson_geometry()

    assert geom.is_valid
    assert geom.geom_type == "MultiPolygon"
    assert len(geom.geoms) == 2
    assert geom.area == pytest.approx(2.0)


def test_bowtie_stays_valid_after_plate_carree_pipeline():
    footprint = Footprint(BOWTIE)
    geom = footprint.make_valid_geojson_geometry()
    simplified = footprint.to_wgs84_plate_carre(geom)

    assert simplified.is_valid
    assert isinstance(simplified, (Polygon, MultiPolygon))
    assert simplified.area == pytest.approx(2.0, rel=1e-2)


def test_valid_geometry_passes_through_unchanged():
    square = Polygon([(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)])
    footprint = Footprint(square)
    geom = footprint.make_valid_geojson_geometry()

    assert geom.is_valid
    assert geom.geom_type == "Polygon"
    assert geom.equals(square)


# A footprint crossing the antimeridian gets split by
# make_valid_geojson_geometry into a MultiPolygon -- the case that
# motivated to_geojson(): Shapely's mapping() used to leak tuples there.
CROSSING = Polygon(
    [
        (181.476, 85.6931),
        (181.476, 85.7946),
        (179.868, 85.7946),
        (179.868, 85.6931),
        (181.476, 85.6931),
    ]
)


def test_to_geojson_returns_json_native_lists():
    footprint = Footprint(CROSSING)
    geom_json = footprint.to_geojson(footprint.make_valid_geojson_geometry())

    assert isinstance(geom_json, dict)
    assert geom_json["type"] == "MultiPolygon"

    def any_tuple(node) -> bool:
        return isinstance(node, tuple) or (
            isinstance(node, list) and any(any_tuple(n) for n in node)
        )

    assert not any_tuple(geom_json["coordinates"])


def test_to_geojson_round_trips_through_shapely_shape():
    from shapely.geometry import shape

    footprint = Footprint(CROSSING)
    geom = footprint.make_valid_geojson_geometry()
    assert shape(footprint.to_geojson(geom)).equals(geom)


def test_to_geojson_defaults_to_the_footprints_own_geometry():
    footprint = Footprint(Polygon([(10, 1), (10, 5), (20, 5), (20, 1), (10, 1)]))
    geom_json = footprint.to_geojson()
    assert geom_json["type"] == "Polygon"
    assert geom_json["coordinates"] == [[[10, 1], [20, 1], [20, 5], [10, 5], [10, 1]]]
