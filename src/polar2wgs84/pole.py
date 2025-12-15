import numpy as np
from loguru import logger
from polar2wgs84.angle_operation import shift_coords_to_minus_180
from polar2wgs84.projection import limit_polygon_vertices
from polar2wgs84.projection import Projection
from polar2wgs84.projection import Stats
from shapely import Point
from shapely import Polygon
from shapely import simplify
from shapely.geometry.polygon import orient


class Pole:

    POLE_NORTH_LATITUDE = 90
    POLE_SOUTH_LATITUDE = -90

    def __init__(
        self, geometry: Polygon, stats: Stats, tolerance=0.01, max_distance=5000
    ):
        self.geometry = geometry
        self.stats = stats
        self.tolerance = tolerance
        self.max_distance = max_distance
        self.projection = Projection()
        self.is_north = (
            True
            if Projection.is_polar_projection_suitable(self.geometry) == "north"
            else False
        )
        self.physical_pole = (
            Pole.POLE_NORTH_LATITUDE
            if Projection.is_polar_projection_suitable(self.geometry) == "north"
            else Pole.POLE_SOUTH_LATITUDE
        )
        self.geometry_polar = self.projection.reproject_geometry(
            self.geometry, self.is_north
        )
        self.is_contained = self._contains_strict(self.geometry_polar, Point(0, 0))
        logger.info(
            f"Pole is contained in the geometry: {self._contains_strict(self.geometry_polar, Point(0, 0))}"
        )

    def _contains_strict(self, geom, point, tol=1e-6):
        return geom.buffer(-tol).contains(point)

    def toWgs84(self) -> Polygon:
        if self.is_contained:
            geometry_polar_densified = Projection.densify_geometry(
                self.geometry_polar, max_distance=self.max_distance
            )
            geometry_wgs84 = self.projection.reproject_geometry(
                geometry_polar_densified, self.is_north, reverse=True
            )
            cap_ring = [
                (lon, self.physical_pole) for lon in np.linspace(180, -180, 100)
            ]
            coords_reorder = list(
                shift_coords_to_minus_180(tuple(geometry_wgs84.exterior.coords))
            )
            coords_reorder.extend(cap_ring)
            if coords_reorder[0] != coords_reorder[-1]:
                coords_reorder.append(coords_reorder[0])

            polygon_wgs84 = orient(
                limit_polygon_vertices(
                    Polygon(coords_reorder),
                    max_points=60,
                    tolerance_start=self.tolerance,
                )
            )
        else:
            polygon_wgs84 = limit_polygon_vertices(
                self.geometry, max_points=60, tolerance_start=self.tolerance
            )
        return polygon_wgs84
