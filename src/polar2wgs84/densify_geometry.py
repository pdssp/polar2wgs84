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
import numba
import numpy as np
from loguru import logger
from shapely.geometry import Polygon


@numba.jit(cache=True)
def _lonlat_to_unit(lon: float, lat: float) -> np.ndarray:
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


@numba.jit(cache=True)
def _unit_to_lonlat(u: np.ndarray):
    """
    Convert a 3D unit vector back to longitude and latitude.

    Parameters
    ----------
    u : numpy.ndarray
        3D unit vector.

    Returns
    -------
        (longitude, latitude) in degrees.
    """
    out = np.empty(2, dtype=np.float64)

    lon = np.arctan2(u[1], u[0])
    lat = np.arcsin(u[2])

    out[0] = np.rad2deg(lon)
    out[1] = np.rad2deg(lat)

    return out


@numba.jit(cache=True)
def _densify_segment_km(
    lon0,
    lat0,
    lon1,
    lat1,
    max_step_km,
    radius_planet,
):
    u0 = _lonlat_to_unit(lon0, lat0)
    u1 = _lonlat_to_unit(lon1, lat1)

    dot = u0[0] * u1[0] + u0[1] * u1[1] + u0[2] * u1[2]
    if dot > 1.0:
        dot = 1.0
    elif dot < -1.0:
        dot = -1.0

    theta = np.arccos(dot)

    # cas dégénéré
    if theta < 1e-12:
        out = np.empty((1, 2), dtype=np.float64)
        out[0, 0] = lon0
        out[0, 1] = lat0
        return out

    step_angle = max_step_km / radius_planet
    n = int(np.ceil(theta / step_angle))
    if n < 1:
        n = 1

    out = np.empty((n + 1, 2), dtype=np.float64)
    sin_theta = np.sin(theta)

    for i in range(n + 1):
        t = i / n

        s0 = np.sin((1.0 - t) * theta)
        s1 = np.sin(t * theta)

        u = (s0 * u0 + s1 * u1) / sin_theta

        # normalisation manuelle
        norm = np.sqrt(u[0] * u[0] + u[1] * u[1] + u[2] * u[2])
        u /= norm

        out[i, 0] = np.rad2deg(np.arctan2(u[1], u[0]))
        out[i, 1] = np.rad2deg(np.arcsin(u[2]))

    return out


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
            segment = _densify_segment_km(
                lon0, lat0, lon1, lat1, max_step_km, radius_planet
            )
            new_coords.extend(segment[:-1])  # Avoid duplicate points

        new_coords.append(new_coords[0])  # Close ring
        return new_coords

    def densify_polygon_km(
        self, max_step_km: float = 5.0, radius_planet: float = R_EARTH_KM
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
