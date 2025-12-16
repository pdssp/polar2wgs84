# Polar to WGS84 Converter - polar2wgs84 is a Python tool to seamlessly convert geographic footprints between polar stereographic projections (EPSG:3031/EPSG:3575) and WGS84 (EPSG:4326), handling pole-crossing geometries, densification, and validation for accurate GIS workflows.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""
Module for projecting geometries between geographic (WGS84), Plate Carrée,
and polar stereographic coordinate systems. Also provides utilities for
computing simple statistics on polygon location.

Classes
-------
Projection
    Provides methods to project polygons to/from polar or Plate Carrée CRS.
Stats
    Data class summarizing polygon latitude statistics.
"""
from dataclasses import dataclass
from typing import Tuple
from typing import Union

import numpy as np
from loguru import logger
from pyproj import CRS
from pyproj import Transformer
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon
from shapely.ops import transform

from .angle_operation import normalize_lon_to_360


class Projection:
    """
    Handles projections of geometries between WGS84, Plate Carrée,
    and polar stereographic coordinate systems (north/south).
    """

    # Coordinate Reference Systems (CRS)
    WGS_84 = CRS.from_epsg(4326)
    PLATE_CARREE = CRS("EPSG:32662")

    POLAR_NORTH = CRS.from_proj4(
        """
        +proj=stere
        +lat_0=90
        +lon_0=180
        +datum=WGS84
        +units=m
        +no_defs
        """
    )

    POLAR_SOUTH = CRS.from_proj4(
        """
        +proj=stere
        +lat_0=-90
        +lon_0=180
        +datum=WGS84
        +units=m
        +no_defs
        """
    )

    # Predefined Transformers
    WGS84_TO_PLATE_CARREE = Transformer.from_crs(
        WGS_84, PLATE_CARREE, always_xy=True
    ).transform
    PLATE_CARREE_TO_WGS84 = Transformer.from_crs(
        PLATE_CARREE, WGS_84, always_xy=True
    ).transform

    WGS84_TO_POLAR_NORTH = Transformer.from_crs(
        WGS_84, POLAR_NORTH, always_xy=True
    ).transform
    POLAR_NORTH_TO_WGS84 = Transformer.from_crs(
        POLAR_NORTH, WGS_84, always_xy=True
    ).transform

    WGS84_TO_POLAR_SOUTH = Transformer.from_crs(
        WGS_84, POLAR_SOUTH, always_xy=True
    ).transform
    POLAR_SOUTH_TO_WGS84 = Transformer.from_crs(
        POLAR_SOUTH, WGS_84, always_xy=True
    ).transform

    def __init__(self):
        """Empty constructor; all transformations are class-level."""
        pass

    def project_to_polar(
        self,
        geom: Polygon | MultiPolygon,
        is_north: bool = True,
        reverse: bool = False,
    ) -> Polygon | MultiPolygon:
        """
        Project a geometry to a polar stereographic projection or back to WGS84.

        Parameters
        ----------
        geom : Polygon or MultiPolygon
            Geometry to project.
        is_north : bool, optional
            If True, use north polar projection; otherwise, south polar.
        reverse : bool, optional
            If True, project from polar to WGS84; otherwise, WGS84 to polar.

        Returns
        -------
        Polygon or MultiPolygon
            Projected geometry.
        """
        if reverse:
            transformer = (
                Projection.POLAR_NORTH_TO_WGS84
                if is_north
                else Projection.POLAR_SOUTH_TO_WGS84
            )
        else:
            transformer = (
                Projection.WGS84_TO_POLAR_NORTH
                if is_north
                else Projection.WGS84_TO_POLAR_SOUTH
            )

        if isinstance(geom, Polygon):
            projected_geom = transform(transformer, geom)
        else:
            projected_geom = MultiPolygon(
                transform(transformer, poly) for poly in geom.geoms
            )

        logger.debug(
            "Projected geometry using {} polar projection (reverse={})",
            "north" if is_north else "south",
            reverse,
        )
        return projected_geom

    def project_to_plate_carree(
        self, geom: Polygon | MultiPolygon, reverse: bool = False
    ) -> Polygon | MultiPolygon:
        """
        Project a geometry to Plate Carrée projection or back to WGS84.

        Parameters
        ----------
        geom : Polygon or MultiPolygon
            Geometry to project.
        reverse : bool, optional
            If True, project from Plate Carrée to WGS84; otherwise, WGS84 to Plate Carrée.

        Returns
        -------
        Polygon or MultiPolygon
            Projected geometry.
        """
        transformer = (
            Projection.PLATE_CARREE_TO_WGS84
            if reverse
            else Projection.WGS84_TO_PLATE_CARREE
        )

        if isinstance(geom, Polygon):
            projected_geom = transform(transformer, geom)
        else:
            projected_geom = MultiPolygon(
                transform(transformer, poly) for poly in geom.geoms
            )

        logger.debug("Projected geometry to Plate Carrée (reverse={})", reverse)
        return projected_geom


@dataclass
class Stats:
    """
    Data class representing basic statistics about a polygon's latitude distribution.

    Attributes
    ----------
    only_positive_lat : bool
        True if all polygon vertices are in the northern hemisphere.
    only_negative_lat : bool
        True if all polygon vertices are in the southern hemisphere.
    high_latitude_pos : int
        Number of vertices above 60° latitude north.
    high_latitude_neg : int
        Number of vertices below -60° latitude south.
    """

    only_positive_lat: bool
    only_negative_lat: bool
    high_latitude_pos: int
    high_latitude_neg: int


def compute_nbpoints(geometry: Polygon | MultiPolygon):
    if isinstance(geometry, MultiPolygon):
        nb_points = 0
        for poly in geometry.geoms:
            nb_points += len(poly.exterior.coords)
    else:
        nb_points = len(geometry.exterior.coords)
    return nb_points


def compute_centroid(geometry: Polygon | MultiPolygon) -> tuple[float, float]:
    """
    Compute the centroid of a Polygon or MultiPolygon, taking into account
    geometries that cross the antimeridian. Longitudes are normalized to
    [0, 360] before computing the mean and converted back to [-180, 180].

    Parameters
    ----------
    geometry : Polygon or MultiPolygon
        The input geometry for which the centroid will be computed.

    Returns
    -------
    Tuple[float, float]
        The (longitude, latitude) of the centroid.
    """
    lons = []
    lats = []

    if isinstance(geometry, Polygon):
        # Normalize longitudes to [0, 360] to handle antimeridian crossing
        geom = normalize_lon_to_360(geometry)
        lons_poly, lats_poly = geom.exterior.xy
        lons.extend(lons_poly)
        lats.extend(lats_poly)
    elif isinstance(geometry, MultiPolygon):
        # Iterate over each polygon in the multipolygon
        for poly in geometry.geoms:
            geom = normalize_lon_to_360(poly)
            lons_poly, lats_poly = geom.exterior.xy
            lons.extend(lons_poly)
            lats.extend(lats_poly)
    else:
        raise TypeError("Input must be a Polygon or MultiPolygon")

    # Compute mean longitude and latitude
    lon_mean = np.mean(lons[:-1])
    if lon_mean >= 180:
        # Convert back to [-180, 180] if needed
        lon_mean = 180 - lon_mean
    lat_mean = np.mean(lats[:-1])

    return lon_mean, lat_mean
