# Polar to WGS84 Converter - Global geometry processing utilities for GeoJSON-safe WGS84 polygons.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""
This module provides custom exceptions for handling geometry-related errors in applications using
Shapely geometries. These exceptions are designed to improve error handling clarity and provide
helpful tips for debugging.
"""


class InvalidGeometryError(ValueError):
    """Exception raised when the input geometry is not a valid Shapely Polygon."""

    def __init__(self, geometry):
        geometry_type = type(geometry).__name__
        message = (
            f"Expected a Shapely Polygon, but got '{geometry_type}'.\n"
            f"Tip: Make sure to pass a Shapely Polygon object. "
            f"You can create one using `Polygon([(lon1, lat1), (lon2, lat2), ...])`."
        )
        super().__init__(message)


class UnsupportedGeometryTypeError(TypeError):
    """Exception raised when the input geometry is not a Polygon or MultiPolygon."""

    def __init__(self, geometry_type: type):
        geometry_name = geometry_type.__name__ if geometry_type else "None"
        message = (
            f"Unsupported geometry type: '{geometry_name}'. "
            f"Expected a Shapely Polygon or MultiPolygon. "
            f"Use `Polygon([(lon1, lat1), ...])` or `MultiPolygon([polygon1, polygon2, ...])`."
        )
        super().__init__(message)
