# Polar to WGS84 Converter - polar2wgs84 is a Python tool to seamlessly convert geographic footprints between polar stereographic projections (EPSG:3031/EPSG:3575) and WGS84 (EPSG:4326), handling pole-crossing geometries, densification, and validation for accurate GIS workflows.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
import math
from dataclasses import dataclass

from loguru import logger
from pyproj import CRS
from pyproj import Transformer
from shapely.geometry import LineString
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon
from shapely.ops import transform


class Projection:

    def __init__(self):
        pass

    def polar_crs(self, is_north, lon0=180):
        return CRS.from_proj4(
            f"""
            +proj=stere
            +lat_0={'90' if is_north else '-90'}
            +lon_0={lon0}
            +datum=WGS84
            +units=m
            +no_defs
            """
        )

    def reproject_geometry(self, geom, is_north=True, reverse=False):
        polar = self.polar_crs(is_north, lon0=180)
        wgs84 = CRS.from_epsg(4326)
        if reverse:
            transformer = Transformer.from_crs(polar, wgs84, always_xy=True)
        else:
            transformer = Transformer.from_crs(wgs84, polar, always_xy=True)
        if isinstance(geom, Polygon):
            return transform(transformer.transform, geom)
        else:
            return MultiPolygon(
                transform(transformer.transform, poly) for poly in list(geom.geoms)
            )

    @staticmethod
    def is_polar_projection_suitable(polygon, pole_threshold=0):
        coords = list(polygon.exterior.coords)
        # Extract latitudes from coordinates
        latitudes = [y for x, y in coords]
        # Count latitudes above and below the threshold
        positive_lat = sum(1 for lat in latitudes if lat > pole_threshold)
        negative_lat = sum(1 for lat in latitudes if lat < -pole_threshold)
        if positive_lat > negative_lat:
            return "north"
        elif negative_lat > positive_lat:
            return "south"
        else:
            return None

    @staticmethod
    def densify_geometry(geom, max_distance: float):
        """
        Static method to densify a geometry.

        Args:
            geom: Shapely geometry object.
            max_distance (float): Maximum allowed distance between points.

        Returns:
            Shapely geometry: Densified geometry.
        """
        if geom.is_empty:
            return geom

        def densify_line(line: LineString):
            """
            Densify a LineString by adding intermediate points if the distance between points exceeds max_distance.

            Args:
                line (LineString): Shapely LineString object.

            Returns:
                LineString: Densified LineString.
            """
            coords = list(line.coords)
            new_coords = [coords[0]]
            for p1, p2 in zip(coords[:-1], coords[1:]):
                dist = math.dist(p1, p2)
                if dist > max_distance:
                    n = int(dist // max_distance)
                    for i in range(1, n + 1):
                        t = i / (n + 1)
                        new_coords.append(
                            (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
                        )
                new_coords.append(p2)
            return LineString(new_coords)

        if isinstance(geom, LineString):
            return densify_line(geom)
        elif isinstance(geom, Polygon):
            exterior = densify_line(geom.exterior)
            interiors = [densify_line(interior) for interior in geom.interiors]
            return Polygon(list(exterior.coords), [list(i.coords) for i in interiors])
        elif isinstance(geom, MultiPolygon):
            return MultiPolygon(
                [Projection.densify_geometry(p, max_distance) for p in geom]
            )
        return geom


def limit_polygon_vertices(
    polygon: Polygon,
    max_points: int,
    tolerance_start: float = 1e-6,
    tolerance_factor: float = 1.5,
    tolerance_max: float = 1.0,
) -> Polygon:
    """
    Simplify a polygon until it contains at most `max_points` vertices.
    """

    tolerance = tolerance_start
    simplified = polygon

    def num_points(poly: Polygon) -> int:
        return len(poly.exterior.coords)

    while num_points(simplified) > max_points:
        if tolerance > tolerance_max:
            logger.warning(
                "Maximum tolerance reached before achieving target vertex count"
            )
            break

        simplified = polygon.simplify(tolerance=tolerance, preserve_topology=True)
        tolerance *= tolerance_factor

    logger.debug(
        f"Final tolerance={tolerance:.6f}, " f"points={num_points(simplified)}"
    )

    return simplified


@dataclass
class Stats:
    positive_lat: int
    negative_lat: int
    high_latitude_pos: int
    high_latitude_neg: int
