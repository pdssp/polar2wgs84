# Polar to WGS84 Converter - polar2wgs84 is a Python tool to seamlessly convert geographic footprints between polar stereographic projections (EPSG:3031/EPSG:3575) and WGS84 (EPSG:4326), handling pole-crossing geometries, densification, and validation for accurate GIS workflows.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""
Module to handle splitting of polygons crossing the equator or the antimeridian (±180° longitude).
It provides utilities to generate valid GeoJSON-ready polygons or multipolygons by
handling polar inclusion, antimeridian splitting, and longitude normalization.

Classes
-------
EquatorSplitter
    Splits polygons along the equator and delegates pole/antimeridian handling.
AntimeridianLineSplitter
    Splits a LineString along the antimeridian.
AntimeridianSplitter
    Detects and splits geometries crossing the antimeridian.
"""
from typing import Union

from loguru import logger
from shapely.geometry import LineString
from shapely.geometry import MultiPoint
from shapely.geometry import MultiPolygon
from shapely.geometry import Point
from shapely.geometry import Polygon
from shapely.ops import orient
from shapely.ops import split
from shapely.ops import unary_union

from .angle_operation import normalize_lon_to_180
from .angle_operation import normalize_lon_to_360
from .pole import Pole
from .pole import PoleFactory


class EquatorSplitter:
    """
    Split polygons along the equator (latitude=0) and handle resulting
    geometries by delegating to Pole or Antimeridian handling.
    """

    LONGITUDE_WEST = -180
    LONGITUDE_EST = 180
    EQUATOR_LATITUDE = 0

    EQUATOR_LINE = LineString(
        [
            (LONGITUDE_WEST, EQUATOR_LATITUDE),
            (LONGITUDE_EST, EQUATOR_LATITUDE),
        ]
    )

    def __init__(self, geometry: Polygon):
        """
        Initialize with a polygon potentially crossing the equator.

        Parameters
        ----------
        geometry : Polygon
            Input polygon in WGS84 coordinates.
        """
        self.geometry = geometry

    def make_valid_geojson_geometry(self) -> Polygon | MultiPolygon:
        """
        Split the polygon along the equator and handle each resulting piece.
        Polygons containing a pole are delegated to the Pole class.
        Other polygons are handled by AntimeridianSplitter if needed.

        Returns
        -------
        Polygon or MultiPolygon
            Valid GeoJSON-ready geometry.
        """
        geometry_collection = split(self.geometry, EquatorSplitter.EQUATOR_LINE)
        geom_validated = []

        for geom in geometry_collection.geoms:
            pole: Pole = PoleFactory.create(geom)
            if pole.is_pole_included:
                geom_validated.append(pole.make_valid_geojson_geometry())
            else:
                antimeridian = AntimeridianSplitter(geom)
                valid_geom = antimeridian.make_valid_geojson_geometry()
                geom_validated.append(valid_geom)

        # Flatten and unify all geometries
        all_polygons = []
        for geom in geom_validated:
            if geom.geom_type == "Polygon":
                all_polygons.append(geom)
            elif geom.geom_type == "MultiPolygon":
                all_polygons.extend(list(geom.geoms))

        final_multipolygon = MultiPolygon(all_polygons)
        return unary_union(final_multipolygon)


class AntimeridianLineSplitter:
    """
    Split a LineString along the antimeridian (longitude=±180°).
    Returns the intersection point as a Shapely Point.
    """

    def __init__(self, line: LineString):
        """
        Parameters
        ----------
        line : LineString
            Line to split along the antimeridian.
        """
        self.line = line

    def split(self) -> Point:
        """
        Compute the intersection of the line with the antimeridian.

        Returns
        -------
        Point
            Intersection point with the antimeridian.

        Notes
        -----
        If multiple points exist (MultiPoint), the second point is returned
        as convention.
        """
        result: Point | MultiPoint = self.line.intersection(
            AntimeridianSplitter.ANTI_MERIDIAN_LINE
        )
        if isinstance(result, Point):
            return result
        else:
            # Return the second point if multiple intersections exist
            return result.geoms[1]


class AntimeridianSplitter:
    """
    Detect and split polygons crossing the antimeridian (±180° longitude).
    Provides utilities to normalize longitudes and produce valid GeoJSON polygons.
    """

    ANTI_MERIDIAN_LONGITUDE = 180
    POLE_NORTH_LATITUDE = 90
    POLE_SOUTH_LATITUDE = -90

    ANTI_MERIDIAN_LINE = LineString(
        [
            (ANTI_MERIDIAN_LONGITUDE, POLE_SOUTH_LATITUDE),
            (ANTI_MERIDIAN_LONGITUDE, POLE_NORTH_LATITUDE),
        ]
    )

    def __init__(self, geometry: Polygon):
        """
        Parameters
        ----------
        geometry : Polygon
            Input polygon potentially crossing the antimeridian.
        """
        self.geometry = geometry

    # -------------------------------------------------------------------------
    # Detection utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def crosses_antimeridian(geometry: Polygon) -> bool:
        """
        Detect if a polygon crosses the antimeridian.

        Returns True if any consecutive vertices differ by more than 180° longitude.

        Parameters
        ----------
        geometry : Polygon
            Input polygon.

        Returns
        -------
        bool
        """
        exterior = geometry.exterior.coords
        for (lon1, _), (lon2, _) in zip(exterior, exterior[1:]):
            if abs(lon2 - lon1) > 180:
                logger.debug("Detected antimeridian crossing: {} -> {}", lon1, lon2)
                return True
        return False

    @staticmethod
    def contains_lon_gt_180(polygon: Polygon) -> bool:
        """
        Check whether any longitude in the polygon is greater than 180°.

        Parameters
        ----------
        polygon : Polygon

        Returns
        -------
        bool
        """
        return any(x > 180 for x, _ in polygon.exterior.coords)

    # -------------------------------------------------------------------------
    # Main splitter logic
    # -------------------------------------------------------------------------

    def make_valid_geojson_geometry(self) -> Polygon | MultiPolygon:
        """
        Split the polygon along the antimeridian and normalize longitudes.

        Returns
        -------
        Polygon or MultiPolygon
        """
        if not self.crosses_antimeridian(self.geometry):
            logger.info("Geometry does not cross the antimeridian. No split needed.")
            return self.geometry

        logger.info("Geometry crosses the antimeridian. Splitting...")

        # Normalize to 0–360° longitude for easier splitting
        geom_360 = normalize_lon_to_360(self.geometry)
        geometry_collection = split(geom_360, AntimeridianSplitter.ANTI_MERIDIAN_LINE)
        split_geometries = geometry_collection.geoms

        logger.debug("Geometry split into {} parts.", len(split_geometries))

        corrected_parts = []
        for part in split_geometries:
            if self.contains_lon_gt_180(part):
                corrected = normalize_lon_to_180(part, is_360_space=True)
            else:
                corrected = normalize_lon_to_180(part, is_360_space=False)

            corrected_parts.append(orient(corrected))

        if len(corrected_parts) == 1:
            return corrected_parts[0]

        return MultiPolygon(corrected_parts)
