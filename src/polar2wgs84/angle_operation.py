# Polar to WGS84 Converter - Global geometry processing utilities for GeoJSON-safe WGS84 polygons.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""
This module provides utility functions for handling geographic geometries
using Shapely. The focus is on operations involving polygons, multipolygons,
and lines, particularly with respect to handling longitudes across
the -180/180 meridian.

Functions included:
- compute_centroid: Compute the centroid of a Polygon or MultiPolygon, handling longitude normalization.
- reorganize_longitudes: Sort LineString coordinates by longitude.
- normalize_lon_to_360: Shift geometry longitudes from [-180, 180] to [0, 360].
- normalize_lon_to_180: Convert geometry longitudes from [0, 360] back to [-180, 180].
"""
from typing import Tuple
from typing import Union

from shapely.geometry import LineString
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon
from shapely.ops import transform


def reorganize_longitudes(line: LineString) -> list[tuple[float, float]]:
    """
    Sort the coordinates of a LineString by increasing longitude.
    The resulting list does not close the LineString by default; if needed,
    the first coordinate should be appended at the end to close the loop.

    Parameters
    ----------
    line : LineString
        The input line whose coordinates will be sorted.

    Returns
    -------
    List[Tuple[float, float]]
        Sorted coordinates of the line by longitude.
    """
    # Remove the closing point if it exists
    coords = list(line.coords[:-1]) if line.is_ring else list(line.coords)

    # Sort coordinates by longitude
    sorted_coords = sorted(coords, key=lambda pt: pt[0])

    # Optionally, append the first point to close the LineString
    # For now, this adds 180 as a placeholder, you may want to handle closure differently
    sorted_coords.append((180, sorted_coords[0][1]))

    return sorted_coords


def normalize_lon_to_360(
    geom: Polygon | LineString | MultiPolygon,
) -> Polygon | LineString | MultiPolygon:
    """
    Convert geometry longitudes from [-180, 180] to [0, 360].
    Useful for handling geometries that cross the antimeridian.

    Parameters
    ----------
    geom : Polygon, LineString, or MultiPolygon
        Geometry to normalize.

    Returns
    -------
    Polygon, LineString, or MultiPolygon
        Geometry with longitudes shifted to [0, 360].
    """

    def _shift(x: float, y: float) -> tuple[float, float]:
        x_new = x + 360 if x < 0 else x
        return x_new, y

    return transform(_shift, geom)


def normalize_lon_to_180(
    geom: Polygon | LineString | MultiPolygon, is_360_space: bool = False
) -> Polygon | LineString | MultiPolygon:
    """
    Convert geometry longitudes from [0, 360] back to [-180, 180].

    Parameters
    ----------
    geom : Polygon, LineString, or MultiPolygon
        Geometry to normalize.
    is_360_space : bool, default False
        If True, treats longitudes >= 180 as needing a shift to [-180, 180].
        Otherwise, shifts only values strictly greater than 180.

    Returns
    -------
    Polygon, LineString, or MultiPolygon
        Geometry with longitudes shifted to [-180, 180].
    """

    def _unshift(x: float, y: float) -> tuple[float, float]:
        if not is_360_space:
            x_new = x - 360 if x > 180 else x
        else:
            x_new = x - 360 if x >= 180 else x
        return x_new, y

    return transform(_unshift, geom)
