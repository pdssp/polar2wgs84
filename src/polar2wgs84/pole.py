# Polar to WGS84 Converter - polar2wgs84 is a Python tool to seamlessly convert geographic footprints between polar stereographic projections (EPSG:3031/EPSG:3575) and WGS84 (EPSG:4326), handling pole-crossing geometries, densification, and validation for accurate GIS workflows.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""
Module to handle polygons containing the North or South Pole.
It provides classes to determine if a pole is inside a polygon,
adjust geometries crossing the antimeridian, and produce valid GeoJSON-ready polygons.

Classes
-------
Pole
    Base class representing a pole and handling geometry adjustments.
NorthPole
    Represents a polygon containing the North Pole.
SouthPole
    Represents a polygon containing the South Pole.
PoleFactory
    Factory class to instantiate the correct pole class based on polygon location.
"""
import numpy as np
from loguru import logger
from shapely.geometry import LineString
from shapely.geometry import Point
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from .angle_operation import normalize_lon_to_360
from .angle_operation import reorganize_longitudes
from .projection import Projection


class Pole:
    """
    Base class to represent a pole and handle polygons that include it.

    Attributes
    ----------
    geometry : Polygon
        Original polygon in WGS84 coordinates.
    pole_latitude : float
        Latitude of the pole (90 for North, -90 for South).
    is_north : bool
        True if this is the North Pole, False for South Pole.
    is_pole_included : bool
        True if the pole is contained within the polygon.
    """

    POLE_NORTH_LATITUDE = 90
    POLE_SOUTH_LATITUDE = -90

    def __init__(self, geometry: Polygon, pole_latitude: float):
        """
        Initialize a Pole object with its polygon and pole latitude.

        Parameters
        ----------
        geometry : Polygon
            Polygon potentially containing the pole.
        pole_latitude : float
            Latitude of the pole.
        """
        self.geometry = geometry
        self.pole_latitude = pole_latitude
        self.is_north = pole_latitude == Pole.POLE_NORTH_LATITUDE

        # Project polygon to polar coordinates
        projection = Projection()
        geometry_polar = projection.project_to_polar(self.geometry, self.is_north)

        # Check if the pole is included
        self.is_pole_included = self._is_pole_included(geometry_polar)
        logger.info("Pole is contained in the geometry: {}", self.is_pole_included)

    def _is_pole_included(self, geom: Polygon, tol: float = 1e-6) -> bool:
        """
        Determine if the pole is included in a polar-projected polygon.

        Parameters
        ----------
        geom : Polygon
            Polygon projected to polar coordinates.
        tol : float
            Small buffer to avoid numerical precision issues.

        Returns
        -------
        bool
            True if the pole is contained in the polygon.
        """
        return geom.buffer(-tol).contains(Point(0, 0))

    def _insert_all_sign_changes(self, line: LineString, point: Point) -> LineString:
        """
        Insert a point at every longitude sign change in a LineString.

        This is used to handle antimeridian crossings when a pole is included.

        Parameters
        ----------
        line : LineString
            LineString representing polygon exterior.
        point : Point
            Point to insert at each sign change.

        Returns
        -------
        LineString
            Updated LineString with points inserted at all sign changes.
        """
        coords = list(line.coords)
        i = 0
        while i < len(coords) - 1:
            x1, _ = coords[i]
            x2, _ = coords[i + 1]
            if x1 * x2 < 0:
                coords.insert(i + 1, (point.x, point.y))
                i += 1
            i += 1
        return LineString(coords)

    def make_valid_geojson_geometry(self) -> Polygon:
        """
        Produce a GeoJSON-ready polygon, adjusting for antimeridian and pole inclusion.

        Returns
        -------
        Polygon
            Polygon valid for GeoJSON with coordinates adjusted as necessary.
        """
        if self.is_pole_included:
            from polar2wgs84.splitter import AntimeridianLineSplitter

            # Normalize polygon longitudes to [0, 360]
            geometry_360 = normalize_lon_to_360(self.geometry)
            line = LineString(geometry_360.exterior.coords)

            # Split along the antimeridian if needed
            antimeridian = AntimeridianLineSplitter(line)
            point: Point = antimeridian.split()

            # Insert points at all sign changes for original polygon
            line_180 = LineString(self.geometry.exterior.coords)
            line: LineString = self._insert_all_sign_changes(
                line_180, Point(-180, point.y)
            )

            # Create a polar cap along the pole
            cap_ring = [
                (lon, self.pole_latitude)
                for lon in np.linspace(
                    PoleFactory.LONGITUDE_EST, PoleFactory.LONGITUDE_WEST, 2
                )
            ]

            # Reorganize coordinates and append polar cap
            coords_reorder = reorganize_longitudes(line)
            coords_reorder.extend(cap_ring)

            # Ensure polygon closure
            if coords_reorder[0] != coords_reorder[-1]:
                coords_reorder.append(coords_reorder[0])

            polygon_wgs84 = orient(Polygon(coords_reorder))
        else:
            polygon_wgs84 = self.geometry

        return polygon_wgs84


class NorthPole(Pole):
    """
    Polygon representing the North Pole.
    """

    def __init__(self, geometry: Polygon):
        super().__init__(geometry, Pole.POLE_NORTH_LATITUDE)


class SouthPole(Pole):
    """
    Polygon representing the South Pole.
    """

    def __init__(self, geometry: Polygon):
        super().__init__(geometry, Pole.POLE_SOUTH_LATITUDE)


class PoleFactory:
    """
    Factory to create the correct Pole object (North or South) based on
    polygon latitude.

    Attributes
    ----------
    LONGITUDE_WEST : float
        Western boundary longitude (-180).
    LONGITUDE_EST : float
        Eastern boundary longitude (180).
    EQUATOR_LATITUDE : float
        Latitude of the equator (0).
    EQUATOR_LINE : LineString
        Representation of the equator as a LineString.
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

    @staticmethod
    def create(geometry: Polygon) -> Pole:
        """
        Create the appropriate Pole instance based on polygon latitude.

        Parameters
        ----------
        geometry : Polygon
            Input polygon.

        Returns
        -------
        Pole
            NorthPole or SouthPole instance.
        """
        latitude = geometry.exterior.coords[0][1]
        return NorthPole(geometry) if latitude >= 0 else SouthPole(geometry)
