# Polar to WGS84 Converter - Global geometry processing utilities for GeoJSON-safe WGS84 polygons.
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
from shapely.geometry import LineString
from shapely.geometry import MultiLineString
from shapely.geometry import MultiPoint
from shapely.geometry import MultiPolygon
from shapely.geometry import Point
from shapely.geometry import Polygon
from shapely.ops import orient
from shapely.ops import split
from shapely.ops import unary_union

from .angle_operation import normalize_lon_to_180
from .angle_operation import normalize_lon_to_360
from .exception import InvalidGeoJSONGeometryError
from .logging_config import get_logger
from .monitoring import UtilsMonitoring
from .pole import Pole
from .pole import PoleFactory

logger = get_logger(__name__)


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

    @UtilsMonitoring.time_spend(level="DEBUG")
    def make_valid_geojson_geometry(self) -> Polygon | MultiPolygon:
        """
        Split the polygon along the equator and handle each resulting piece.
        Polygons containing a pole are delegated to the Pole class.
        Other polygons are handled by AntimeridianSplitter if needed.

        If no piece contains a pole, each piece is handled by AntimeridianSplitter
        and the results are combined. A unary_union is attempted to merge the pieces
        into a single polygon if possible.

        Returns
        -------
        Polygon or MultiPolygon
            Valid GeoJSON-ready geometry.
        """
        logger.debug("Splitting polygon along equator...")
        geometry_collection = split(self.geometry, EquatorSplitter.EQUATOR_LINE)
        logger.debug("Equator split produced {} parts.", len(geometry_collection.geoms))

        # Check if at least one piece contains a pole
        any_pole_included = False
        for geom in geometry_collection.geoms:
            pole: Pole = PoleFactory.create(geom)
            if pole.is_pole_included:
                any_pole_included = True
                break

        if not any_pole_included:
            logger.debug(
                "No pole included in any part after equator split. "
                "Processing each part with AntimeridianSplitter."
            )
            all_polygons = []
            for geom in geometry_collection.geoms:
                antimeridian = AntimeridianSplitter(geom)
                valid_geom = antimeridian.make_valid_geojson_geometry()
                if valid_geom.geom_type == "Polygon":
                    all_polygons.append(valid_geom)
                elif valid_geom.geom_type == "MultiPolygon":
                    all_polygons.extend(list(valid_geom.geoms))

            if len(all_polygons) == 1:
                return all_polygons[0]

            result = unary_union(MultiPolygon(all_polygons))
            if isinstance(result, Polygon) and result.is_valid and not result.is_empty:
                logger.debug("unary_union merged pole parts into a single Polygon.")
                return result
            if (
                isinstance(result, MultiPolygon)
                and result.is_valid
                and not result.is_empty
            ):
                logger.debug(
                    "unary_union produced a valid MultiPolygon from pole parts."
                )
                return result
            raise InvalidGeoJSONGeometryError(
                result.geom_type, f"valid={result.is_valid}, empty={result.is_empty}"
            )

        # At least one piece contains a pole → process each piece
        geom_validated = []
        for geom in geometry_collection.geoms:
            pole: Pole = PoleFactory.create(geom)
            if pole.is_pole_included:
                geom_validated.append(pole.make_valid_geojson_geometry())
            else:
                antimeridian = AntimeridianSplitter(geom)
                valid_geom = antimeridian.make_valid_geojson_geometry()
                geom_validated.append(valid_geom)

        # Flatten
        all_polygons = []
        for geom in geom_validated:
            if geom.geom_type == "Polygon":
                all_polygons.append(geom)
            elif geom.geom_type == "MultiPolygon":
                all_polygons.extend(list(geom.geoms))

        if len(all_polygons) == 1:
            return all_polygons[0]

        result = unary_union(MultiPolygon(all_polygons))
        if isinstance(result, Polygon) and result.is_valid and not result.is_empty:
            logger.debug("unary_union produced a valid Polygon.")
            return result
        if isinstance(result, MultiPolygon) and result.is_valid and not result.is_empty:
            logger.debug("unary_union produced a valid MultiPolygon.")
            return result

        raise InvalidGeoJSONGeometryError(
            result.geom_type, f"valid={result.is_valid}, empty={result.is_empty}"
        )


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
        result: Point | MultiPoint | LineString | MultiLineString = (
            self.line.intersection(AntimeridianSplitter.ANTI_MERIDIAN_LINE)
        )
        if isinstance(result, Point):
            return result
        elif isinstance(result, MultiPoint):
            return result.geoms[1]
        elif isinstance(result, MultiLineString):
            first_line = result.geoms[0]
            first_point_coords = first_line.coords[1]
            first_point = Point(first_point_coords)
            return first_point
        else:  # LineString
            first_point_coords = result.coords[1]
            first_point = Point(first_point_coords)
            return first_point


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

        Returns True if any consecutive vertices differ by more than 180°
        longitude but less than 360° (a difference of exactly 360° means
        both points are on the antimeridian itself, not a true crossing).

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
            diff = abs(lon2 - lon1)
            # True crossing: diff > 180 but not 360
            # diff = 360 means both points are at ±180 (same meridian, not a crossing)
            if 180 < diff < 360:
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

    @UtilsMonitoring.time_spend(level="DEBUG")
    def make_valid_geojson_geometry(self) -> Polygon | MultiPolygon:
        """
        Split the polygon along the antimeridian and normalize longitudes.

        Returns
        -------
        Polygon or MultiPolygon
        """
        if not self.crosses_antimeridian(self.geometry):
            logger.debug("Geometry does not cross the antimeridian. No split needed.")
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
