# Polar to WGS84 Converter - Global geometry processing utilities for GeoJSON-safe WGS84 polygons.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""
Module to densify and simplify Shapely geometries along geodesic paths.

This module provides utilities to:

- Interpolate polygon edges along great-circle (geodesic) paths on a sphere instead of straight lines in a planar projection.
- Reduce geometric distortion for polygons spanning large distances or located at high latitudes (near the poles).
- Optionally simplify geometries to control vertex count after densification.

The implementation is designed to be:

- Numerically stable for spherical geometry
- Efficient, using Numba for critical numeric routines
- Compatible with Shapely polygons (exterior rings)

Notes:

- Coordinates are assumed to be (longitude, latitude) in degrees.
- Distances are expressed in kilometers.
- The planet is approximated as a perfect sphere.


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

from .exception import InvalidGeometryError
from .monitoring import UtilsMonitoring


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
    Convert a 3D unit vector back to geographic coordinates.
    This is the inverse operation of ``_lonlat_to_unit``.

    Parameters
    ----------
    u : numpy.ndarray
    3D unit vector [x, y, z].

    Returns
    -------
    numpy.ndarray
    Array ``[lon, lat]`` in degrees.
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
    """
    Densify a geodesic segment between two geographic points.

    Intermediate points are inserted along the great-circle arc so that
    the distance between consecutive points does not exceed ``max_step_km``.

    Parameters
    ----------
    lon0, lat0 : float
    Longitude and latitude of the segment start point (degrees).
    lon1, lat1 : float
    Longitude and latitude of the segment end point (degrees).
    max_step_km : float
    Maximum allowed distance between two consecutive points (km).
    radius_planet : float
    Radius of the planet (km).

    Returns
    -------
    numpy.ndarray
    Array of shape (N, 2) containing interpolated (lon, lat) points.
    The first point corresponds to the start of the segment.

    """
    # Convert endpoints to unit vectors
    u0 = _lonlat_to_unit(lon0, lat0)
    u1 = _lonlat_to_unit(lon1, lat1)

    # Dot product gives cos(theta) where theta is the central angle
    dot = u0[0] * u1[0] + u0[1] * u1[1] + u0[2] * u1[2]

    # Numerical safety: clamp to valid acos range
    if dot > 1.0:
        dot = 1.0
    elif dot < -1.0:
        dot = -1.0

    theta = np.arccos(dot)

    # Degenerate case: points are almost identical
    if theta < 1e-12:
        out = np.empty((1, 2), dtype=np.float64)
        out[0, 0] = lon0
        out[0, 1] = lat0
        return out

    # Convert maximum linear step to angular step
    step_angle = max_step_km / radius_planet
    n = int(np.ceil(theta / step_angle))
    if n < 1:
        n = 1

    out = np.empty((n + 1, 2), dtype=np.float64)
    sin_theta = np.sin(theta)

    # Spherical linear interpolation (SLERP)
    for i in range(n + 1):
        t = i / n

        s0 = np.sin((1.0 - t) * theta)
        s1 = np.sin(t * theta)

        u = (s0 * u0 + s1 * u1) / sin_theta

        # Explicit renormalization for numerical stability
        norm = np.sqrt(u[0] * u[0] + u[1] * u[1] + u[2] * u[2])
        u /= norm

        out[i, 0] = np.rad2deg(np.arctan2(u[1], u[0]))
        out[i, 1] = np.rad2deg(np.arcsin(u[2]))

    return out


class DensifyGeometryGeodesic:
    """
    Utility class to densify polygon geometries along geodesic paths.

    This class operates on Shapely ``Polygon`` objects and replaces each
    straight edge with a sequence of points following the great-circle arc
    on a spherical planet.

    Attributes
    ----------
    geometry : shapely.geometry.Polygon
    Input polygon to densify.
    R_EARTH_KM : float
    Mean radius of the Earth in kilometers.
    """

    R_EARTH_KM = 6371.0  # Earth's radius in km

    def __init__(self, geometry: Polygon):
        """
        Initialize the densifier with a Shapely Polygon.

        Parameters
        ----------
        geometry : shapely.geometry.Polygon
            The polygon to densify.

        Raises
        ------
        InvalidGeometryError
            If `geometry` is not a Polygon.
        """
        logger.debug("Initializing DensifyGeometryGeodesic with input geometry...")

        if not isinstance(geometry, Polygon):
            logger.error(
                f"Invalid geometry type: {type(geometry).__name__}. "
                f"Expected a Shapely Polygon."
            )
            raise InvalidGeometryError(geometry)

        self.geometry = geometry
        logger.debug(
            f"Successfully initialized DensifyGeometryGeodesic with polygon: {geometry.wkt}"
        )

    def _densify_ring_km(
        self,
        coords: list[tuple[float, float]],
        max_step_km: float,
        radius_planet: float,
    ) -> list[tuple[float, float]]:
        """
        Densify a closed linear ring (exterior or interior of a polygon).

        Each consecutive coordinate pair is densified independently and
        concatenated to form a new closed ring.

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

        # Ensure ring closure
        if coords[0] != coords[-1]:
            logger.debug("Closing ring by duplicating first coordinate.")
            coords.append(coords[0])

        new_coords = []
        for (lon0, lat0), (lon1, lat1) in zip(coords[:-1], coords[1:]):
            segment = _densify_segment_km(
                lon0, lat0, lon1, lat1, max_step_km, radius_planet
            )

            # Drop last point to avoid duplicates between segments
            new_coords.extend(segment[:-1])

        if new_coords:  # Check the new_coords is not empty
            new_coords.append(new_coords[0])
            logger.debug(f"Closed densified ring with {len(new_coords)} coordinates.")
        else:
            logger.warning(
                "Densified ring is empty. Check input coordinates and parameters."
            )

        return new_coords

    @UtilsMonitoring.time_spend(level="DEBUG")
    def densify_polygon_km(
        self, max_step_km: float = 5.0, radius_planet: float = R_EARTH_KM
    ) -> Polygon:
        """
        Densify the polygon along geodesic paths.

        Both the exterior boundary and all interior holes are processed.

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
        logger.debug(
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
        logger.debug(
            "Densified polygon: {} points exterior, {} holes",
            len(exterior_coords),
            len(interiors),
        )
        return densified_poly

    @staticmethod
    @UtilsMonitoring.time_spend(level="DEBUG")
    def limit_polygon_vertices(
        polygon: Polygon,
        max_points: int = 20,
        tolerance_start: float = 1000,
        tolerance_factor: float = 1.5,
        tolerance_max: float = 50000,
    ) -> Polygon:
        """
        Iteratively simplify a polygon until a vertex limit is reached.

        The simplification tolerance is progressively increased until the
        number of exterior vertices is less than or equal to ``max_points``.

        Parameters
        ----------
        polygon : shapely.geometry.Polygon
        Polygon to simplify.
        max_points : int, optional
        Target maximum number of exterior vertices.
        tolerance_start : float, optional
        Initial tolerance for ``shapely.simplify``.
        tolerance_factor : float, optional
        Multiplicative factor applied to the tolerance at each iteration.
        tolerance_max : float, optional
        Maximum allowed tolerance.

        Returns
        -------
        shapely.geometry.Polygon
        Simplified polygon (topology preserved).
        """
        logger.debug(
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

        logger.debug(
            "Final simplification: tolerance {:.3f}, points {}",
            tolerance,
            num_points(simplified),
        )
        return simplified
