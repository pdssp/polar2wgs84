# Polar to WGS84 Converter - Global geometry processing utilities for GeoJSON-safe WGS84 polygons.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""
Module to handle polygons representing satellite footprints or geographic regions.
Provides utilities to ensure valid GeoJSON polygons, densify geometries along geodesic paths,
handle polar regions, equator and antimeridian crossings, and project polygons to Plate Carrée.
"""
from typing import Union

from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon
from shapely.ops import orient
from shapely.validation import explain_validity

from .angle_operation import normalize_lon_to_180
from .densify_geometry import DensifyGeometryGeodesic
from .pole import Pole
from .pole import PoleFactory
from .projection import Projection
from .projection import Stats
from .splitter import AntimeridianSplitter
from .splitter import EquatorSplitter


class Footprint:
    """
    Represents a geographic footprint polygon with utilities to validate, densify,
    and project it. Handles special cases such as polar inclusion and antimeridian crossing.
    """

    def __init__(self, geometry: Polygon):
        """
        Initialize a Footprint object.

        Parameters
        ----------
        geometry : Polygon
            Shapely Polygon representing the footprint in WGS84 coordinates.
        """
        # Ensure polygon is oriented CCW and longitudes are normalized to [-180, 180]
        self.geometry = orient(normalize_lon_to_180(geometry))
        self.stats = self._compute_stats_location()
        self.densify_geometry = DensifyGeometryGeodesic(self.geometry)
        self.projection = Projection()

    def _compute_stats_location(self) -> Stats:
        """
        Compute statistics about the polygon's location:
        - Whether all vertices are in northern or southern hemisphere
        - How many points lie above/below 60° latitude

        Returns
        -------
        Stats
            Statistics object summarizing polygon latitude distribution.
        """
        coords = list(self.geometry.exterior.coords)
        latitudes = [y for _, y in coords]

        positive_lat = sum(1 for lat in latitudes if lat >= 0)
        negative_lat = sum(1 for lat in latitudes if lat < 0)
        only_positive_lat = positive_lat == len(latitudes)
        only_negative_lat = negative_lat == len(latitudes)

        high_latitude_pos = sum(1 for lat in latitudes if lat > 60)
        high_latitude_neg = sum(1 for lat in latitudes if lat < -60)

        return Stats(
            only_positive_lat=only_positive_lat,
            only_negative_lat=only_negative_lat,
            high_latitude_pos=high_latitude_pos,
            high_latitude_neg=high_latitude_neg,
        )

    def make_valid_geojson_geometry(self) -> Polygon | MultiPolygon:
        """
        Generate a GeoJSON-valid geometry by resolving global-geography edge cases.

        Algorithm overview
        ------------------
        GeoJSON imposes strict rules on polygon validity, especially for geometries
        expressed in longitude/latitude (WGS84). This method enforces those rules by
        detecting and resolving three major sources of invalidity:

        1. **Polar inclusion**
        Polygons that fully enclose the North or South Pole cannot be represented
        as a single linear ring in GeoJSON without special handling.

        2. **Antimeridian crossing (±180° longitude)**
        Polygons crossing the dateline must be split into multiple parts to
        avoid longitude discontinuities.

        3. **Equator crossing**
        Polygons spanning both hemispheres may require splitting to ensure
        correct orientation and winding rules.

        The algorithm selects the appropriate correction strategy based on the
        latitude distribution of the geometry.
        """
        if self.stats.only_positive_lat or self.stats.only_negative_lat:
            # Polygon is entirely north or south → may contain pole
            pole: Pole = PoleFactory.create(self.geometry)
            if pole.is_pole_included:
                valid_geometry = pole.make_valid_geojson_geometry()
            else:
                antimeridian = AntimeridianSplitter(self.geometry)
                valid_geometry = antimeridian.make_valid_geojson_geometry()
            return valid_geometry
        else:
            # Polygon crosses equator → use equator splitter
            equator_splitter = EquatorSplitter(self.geometry)
            return equator_splitter.make_valid_geojson_geometry()

    def to_wgs84_plate_carre(
        self, geometry: Polygon | MultiPolygon, **kwargs
    ) -> Polygon | MultiPolygon:
        """
        Densify, project, and optionally simplify a geometry using a
        Plate Carrée (equirectangular) intermediate projection.

        Algorithm overview
        ------------------
        This method follows a 4-step pipeline designed to preserve geometric
        fidelity for large or high-latitude polygons while keeping vertex
        count under control:

        1. **Geodesic densification (on the sphere)**
        Polygon edges are densified along great-circle paths in WGS84
        (lon/lat). This prevents distortions that would appear if long
        edges were projected directly in a planar coordinate system.

        2. **Projection to Plate Carrée**
        The densified polygon is projected to a simple planar coordinate
        system (lon, lat → x, y). This projection is the projection for
        STAC's geometry

        3. **Planar simplification**
        The polygon is simplified in projected space to reduce the number
        of vertices while preserving topology. Simplifying in planar space
        is faster and more predictable than simplifying directly on the
        sphere.

        4. **Back-projection to WGS84**
        The simplified geometry is re-projected back to WGS84 coordinates.

        This approach ensures:
        - Correct handling of long edges and polar regions
        - Controlled vertex count
        - Minimal topological distortion

        Parameters
        ----------
        geometry : Polygon or MultiPolygon
            Input geometry in WGS84 coordinates (lon, lat).
        kwargs : dict
            Optional parameters forwarded to:
            - geodesic densification
            - polygon vertex limiting (simplification)

        Returns
        -------
        Polygon or MultiPolygon
            Geometry simplified in a geodesically consistent manner
            and returned in WGS84 coordinates.
        """
        expected_params_densify = {"max_step_km", "radius_planet"}
        filtered_kwargs_densify = {
            k: v for k, v in kwargs.items() if k in expected_params_densify
        }

        expected_params_limit_poly = {
            "max_points",
            "tolerance_start",
            "tolerance_factor",
            "tolerance_max",
        }
        filtered_kwargs_limit_poly = {
            k: v for k, v in kwargs.items() if k in expected_params_limit_poly
        }

        if isinstance(geometry, Polygon):
            self.densify_geometry.geometry = geometry
            geometry_density: Polygon = self.densify_geometry.densify_polygon_km(
                **filtered_kwargs_densify
            )
            poly_car = self.projection.project_to_plate_carree(geometry_density)
            poly_car_simplified = DensifyGeometryGeodesic.limit_polygon_vertices(
                poly_car, **filtered_kwargs_limit_poly
            )
            wgs84_simplified = self.projection.project_to_plate_carree(
                poly_car_simplified, reverse=True
            )
        else:
            geoms = []
            for geom in geometry.geoms:
                self.densify_geometry.geometry = geom
                geometry_density = self.densify_geometry.densify_polygon_km(
                    **filtered_kwargs_densify
                )
                poly_car = self.projection.project_to_plate_carree(geometry_density)
                poly_car_simplified = DensifyGeometryGeodesic.limit_polygon_vertices(
                    poly_car, **filtered_kwargs_limit_poly
                )
                geom_simplified = self.projection.project_to_plate_carree(
                    poly_car_simplified, reverse=True
                )
                geoms.append(geom_simplified)
            wgs84_simplified = MultiPolygon(geoms)

        return wgs84_simplified


def check_polygon(poly: Polygon | MultiPolygon, verbose: bool = True) -> dict:
    """
    Check the validity and properties of a Shapely Polygon or MultiPolygon.

    Parameters
    ----------
    poly : Polygon or MultiPolygon
        Geometry to check.
    verbose : bool
        If True, print detailed information.

    Returns
    -------
    dict
        Dictionary containing:
        - is_valid: True if geometry is valid
        - validity_reason: explanation if invalid
        - area: polygon area
        - has_area: whether area > 0
        - exterior_ccw: whether exterior ring is counter-clockwise
        - nb_points: number of points in exterior (or list per polygon)
    """
    results = {}
    results["is_valid"] = poly.is_valid
    results["validity_reason"] = None if poly.is_valid else explain_validity(poly)
    results["area"] = poly.area
    results["has_area"] = poly.area > 0
    results["exterior_ccw"] = (
        poly.exterior.is_ccw
        if isinstance(poly, Polygon)
        else [p.exterior.is_ccw for p in poly.geoms]
    )
    results["nb_points"] = (
        len(poly.exterior.coords)
        if isinstance(poly, Polygon)
        else [len(p.exterior.coords) for p in poly.geoms]
    )

    if verbose:
        print("✅ Valid:", results["is_valid"])
        if not results["is_valid"]:
            print("   Reason:", results["validity_reason"])
        print("🌐 Area:", results["area"])
        print("🔹 Non-zero area:", results["has_area"])
        print("🌀 Exterior CCW:", results["exterior_ccw"])
        print("Nb points:", results["nb_points"])

    return results
