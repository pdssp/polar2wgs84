# Polar to WGS84 Converter - polar2wgs84 is a Python tool to seamlessly convert geographic footprints between polar stereographic projections (EPSG:3031/EPSG:3575) and WGS84 (EPSG:4326), handling pole-crossing geometries, densification, and validation for accurate GIS workflows.
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
        self.densifyGeometry = DensifyGeometryGeodesic(self.geometry)
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
        Generate a valid GeoJSON-ready polygon or multipolygon,
        handling poles, antimeridian crossing, and equator splitting as needed.

        Returns
        -------
        Polygon or MultiPolygon
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
        Densify, project, and optionally simplify the polygon to Plate Carrée projection.

        Parameters
        ----------
        geometry : Polygon or MultiPolygon
            Polygon(s) to process.
        kwargs : dict
            Additional parameters for densification and simplification.

        Returns
        -------
        Polygon or MultiPolygon
            Processed polygon(s) in WGS84 coordinates.
        """
        if isinstance(geometry, Polygon):
            self.densifyGeometry.geometry = geometry
            geometry_density: Polygon = self.densifyGeometry.densify_polygon_km(
                **kwargs
            )
            poly_car = self.projection.project_to_plate_carree(geometry_density)
            poly_car_simplified = DensifyGeometryGeodesic.limit_polygon_vertices(
                poly_car, **kwargs
            )
            wgs84_simplified = self.projection.project_to_plate_carree(
                poly_car_simplified, reverse=True
            )
        else:
            geoms = []
            for geom in geometry.geoms:
                self.densifyGeometry.geometry = geom
                geometry_density = self.densifyGeometry.densify_polygon_km(**kwargs)
                poly_car = self.projection.project_to_plate_carree(geometry_density)
                poly_car_simplified = DensifyGeometryGeodesic.limit_polygon_vertices(
                    poly_car, **kwargs
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
