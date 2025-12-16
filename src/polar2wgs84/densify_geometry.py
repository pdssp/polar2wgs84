# Polar to WGS84 Converter - polar2wgs84 is a Python tool to seamlessly convert geographic footprints between polar stereographic projections (EPSG:3031/EPSG:3575) and WGS84 (EPSG:4326), handling pole-crossing geometries, densification, and validation for accurate GIS workflows.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""
Module to densify and simplify Shapely geometries along geodesic paths.
This is particularly useful for polygons near the poles or crossing large
distances, where planar projection can distort geometry.

Classes
-------
DensifyGeometryGeodesic
    Provides methods to densify polygons along geodesic paths and simplify them
    while controlling the number of vertices.
"""
from typing import List
from typing import Tuple

import numpy as np
from loguru import logger
from shapely.geometry import Polygon


class DensifyGeometryGeodesic:
    """
    Class to densify geometries (polygons) along geodesic paths.
    Useful for preserving shape when projecting, especially near poles
    or for large-area polygons.

    Attributes
    ----------
    geometry : shapely.geometry.Polygon
        Polygon to densify.
    R_EARTH_KM : float
        Approximate radius of the Earth in kilometers.
    """

    R_EARTH_KM = 6371.0  # Earth's radius in km

    def __init__(self, geometry: Polygon):
        """
        Initialize the densifier with a Shapely Polygon.

        Parameters
        ----------
        geometry : shapely.geometry.Polygon
            The polygon to densify.
        """
        if not isinstance(geometry, Polygon):
            raise TypeError("geometry must be a shapely Polygon")
        self.geometry = geometry
        logger.debug("Initialized DensifyGeometryGeodesic with polygon: {}", geometry)

    def _lonlat_to_unit(self, lon: float, lat: float) -> np.ndarray:
        """
        Convert longitude and latitude to a 3D unit vector.

        Parameters
        ----------
        lon : float
            Longitude in degrees.
        lat : float
            Latitude in degrees.

        Returns
        -------
        numpy.ndarray
            3D unit vector corresponding to the point on the sphere.
        """
        lon_rad = np.deg2rad(lon)
        lat_rad = np.deg2rad(lat)
        return np.array(
            [
                np.cos(lat_rad) * np.cos(lon_rad),
                np.cos(lat_rad) * np.sin(lon_rad),
                np.sin(lat_rad),
            ]
        )

    def _unit_to_lonlat(self, u: np.ndarray) -> tuple[float, float]:
        """
        Convert a 3D unit vector back to longitude and latitude.

        Parameters
        ----------
        u : numpy.ndarray
            3D unit vector.

        Returns
        -------
        tuple
            (longitude, latitude) in degrees.
        """
        lon = np.arctan2(u[1], u[0])
        lat = np.arcsin(u[2])
        return np.rad2deg(lon), np.rad2deg(lat)

    def _densify_segment_km(
        self,
        lon0: float,
        lat0: float,
        lon1: float,
        lat1: float,
        max_step_km: float,
        radius_planet: float,
    ) -> list[tuple[float, float]]:
        """
        Densify a geodesic segment between two points.

        Parameters
        ----------
        lon0, lat0 : float
            Start coordinates.
        lon1, lat1 : float
            End coordinates.
        max_step_km : float
            Maximum distance between interpolated points.
        radius_planet : float
            Radius of the planet (e.g., Earth) in km.

        Returns
        -------
        list of (lon, lat)
            List of points along the geodesic segment.
        """
        u0 = self._lonlat_to_unit(lon0, lat0)
        u1 = self._lonlat_to_unit(lon1, lat1)

        # Angle between vectors
        dot = np.clip(np.dot(u0, u1), -1.0, 1.0)
        theta = np.arccos(dot)

        if theta == 0:
            return [(lon0, lat0)]

        # Number of steps along the geodesic
        step_angle = max_step_km / radius_planet
        n = int(np.ceil(theta / step_angle))

        pts = []
        for i in range(n + 1):
            t = i / n
            # Spherical linear interpolation (slerp)
            u = (np.sin((1 - t) * theta) * u0 + np.sin(t * theta) * u1) / np.sin(theta)
            u /= np.linalg.norm(u)
            pts.append(self._unit_to_lonlat(u))

        return pts

    def _densify_ring_km(
        self,
        coords: list[tuple[float, float]],
        max_step_km: float,
        radius_planet: float,
    ) -> list[tuple[float, float]]:
        """
        Densify a closed linear ring (polygon exterior or interior).

        Parameters
        ----------
        coords : list of (lon, lat)
            Ring coordinates.
        max_step_km : float
            Maximum distance between interpolated points.
        radius_planet : float
            Planet radius in km.

        Returns
        -------
        list of (lon, lat)
            Densified ring coordinates.
        """
        coords = list(coords)
        if coords[0] != coords[-1]:
            coords.append(coords[0])  # Ensure closure

        new_coords = []
        for (lon0, lat0), (lon1, lat1) in zip(coords[:-1], coords[1:]):
            segment = self._densify_segment_km(
                lon0, lat0, lon1, lat1, max_step_km, radius_planet
            )
            new_coords.extend(segment[:-1])  # Avoid duplicate points

        new_coords.append(new_coords[0])  # Close ring
        return new_coords

    def densify_polygon_km(
        self, max_step_km: float = 5.0, radius_planet: float = R_EARTH_KM, **kwargs
    ) -> Polygon:
        """
        Densify the polygon along geodesic paths.

        Parameters
        ----------
        max_step_km : float
            Maximum distance between points in km.
        radius_planet : float
            Planet radius in km.

        Returns
        -------
        shapely.geometry.Polygon
            Densified polygon.
        """
        logger.info(
            f"""
                Running _densify_segment_km with the following parameter:
                    - max_step_km = {max_step_km}
                    - radius_planet = {radius_planet}"""
        )
        polygon = self.geometry

        # Densify exterior ring
        exterior_coords = self._densify_ring_km(
            polygon.exterior.coords, max_step_km, radius_planet
        )

        # Densify interior rings (holes)
        interiors = []
        for ring in polygon.interiors:
            interiors.append(
                self._densify_ring_km(ring.coords, max_step_km, radius_planet)
            )

        densified_poly = Polygon(exterior_coords, interiors)
        logger.info(
            "Densified polygon: {} points exterior, {} holes",
            len(exterior_coords),
            len(interiors),
        )
        return densified_poly

    @staticmethod
    def limit_polygon_vertices(
        polygon: Polygon,
        max_points: int = 20,
        tolerance_start: float = 1000,
        tolerance_factor: float = 1.5,
        tolerance_max: float = 50000,
        **kwargs,
    ) -> Polygon:
        """
        Simplify a polygon until it contains at most `max_points` vertices.

        Parameters
        ----------
        polygon : shapely.geometry.Polygon
            Polygon to simplify.
        max_points : int
            Maximum number of vertices.
        tolerance_start : float
            Initial simplification tolerance.
        tolerance_factor : float
            Factor to increase tolerance at each iteration.
        tolerance_max : float
            Maximum allowed tolerance.

        Returns
        -------
        shapely.geometry.Polygon
            Simplified polygon with at most `max_points` vertices.
        """
        logger.info(
            f"""
        Running limit_polygon_vertices with the following parameter:
                    - max_points = {max_points}
                    - tolerance_start = {tolerance_start}
                    - tolerance_max = {tolerance_max}"""
        )
        tolerance = tolerance_start
        simplified = polygon

        def num_points(poly: Polygon) -> int:
            return len(poly.exterior.coords)

        while num_points(simplified) > max_points:
            if tolerance > tolerance_max:
                logger.warning(
                    "Reached maximum tolerance ({}) before achieving target vertices ({})",
                    tolerance,
                    max_points,
                )
                break

            simplified = polygon.simplify(tolerance=tolerance, preserve_topology=True)
            logger.debug(
                "Simplified with tolerance {:.3f}, points: {}",
                tolerance,
                num_points(simplified),
            )
            tolerance *= tolerance_factor

        logger.info(
            "Final simplification: tolerance {:.3f}, points {}",
            tolerance,
            num_points(simplified),
        )
        return simplified
