from loguru import logger
from polar2wgs84.angle_operation import normalize_lon_to_180
from polar2wgs84.angle_operation import normalize_lon_to_360
from polar2wgs84.projection import limit_polygon_vertices
from polar2wgs84.projection import Projection
from polar2wgs84.projection import Stats
from shapely import GeometryCollection
from shapely import LineString
from shapely import MultiPolygon
from shapely import Polygon
from shapely import simplify
from shapely.ops import split


class AntimeridianSplitter:
    """
    Utility class to detect and split geometries crossing the antimeridian (±180° longitude).
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

    def __init__(
        self, geometry: Polygon, stats: Stats, tolerance=0.01, max_distance=5000
    ):
        self.geometry = geometry
        self.stats = stats
        self.tolerance = tolerance
        self.max_distance = max_distance
        # Vertical line at 180° used for splitting normalized geometries
        self.projection = Projection()
        self.is_north = (
            True
            if Projection.is_polar_projection_suitable(self.geometry) == "north"
            else False
        )
        self.physical_pole = (
            AntimeridianSplitter.POLE_NORTH_LATITUDE
            if Projection.is_polar_projection_suitable(self.geometry) == "north"
            else AntimeridianSplitter.POLE_SOUTH_LATITUDE
        )
        if self.stats.high_latitude_neg or self.stats.high_latitude_pos:
            self.geometry = self.projection.reproject_geometry(
                self.geometry, self.is_north
            )
            self.geometry = Projection.densify_geometry(
                self.geometry, max_distance=self.max_distance
            )
            self.geometry = self.projection.reproject_geometry(
                self.geometry, self.is_north, reverse=True
            )

    # -------------------------------------------------------------------------
    # Detection utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def crosses_antimeridian(geometry: Polygon) -> bool:
        """
        Return True if the polygon crosses the antimeridian.
        Detection based on a longitude jump > 180° between consecutive vertices.
        """
        exterior = geometry.exterior.coords
        for (lon1, _), (lon2, _) in zip(exterior, exterior[1:]):
            if abs(lon2 - lon1) > 180:
                logger.debug(f"Detected antimeridian crossing: {lon1} -> {lon2}")
                return True
        return False

    @staticmethod
    def contains_lon_gt_180(polygon: Polygon) -> bool:
        """
        Check whether a polygon has any coordinate with longitude > 180°.
        (i.e., in normalized 0–360° space)
        """
        return any(x > 180 for x, _ in polygon.exterior.coords)

    # -------------------------------------------------------------------------
    # Main splitter logic
    # -------------------------------------------------------------------------

    def toWgs84(self) -> Polygon | MultiPolygon:
        """
        Split the geometry along the antimeridian.
        Returns a Polygon or MultiPolygon depending on the result.
        """

        # No crossing → return original geometry unchanged
        if not self.crosses_antimeridian(self.geometry):
            logger.info("Geometry does not cross the antimeridian. No split needed.")
            return limit_polygon_vertices(
                self.geometry, max_points=60, tolerance_start=self.tolerance
            )

        logger.info("Geometry crosses the antimeridian. Splitting...")

        # Normalize to 0–360° longitude for easier splitting
        geom_360 = normalize_lon_to_360(self.geometry)

        # Split in normalized space
        geometry_collection = split(geom_360, AntimeridianSplitter.ANTI_MERIDIAN_LINE)
        split_geometries = list(geometry_collection.geoms)

        logger.debug(f"Geometry split into {len(split_geometries)} parts.")

        corrected_parts = []
        for part in split_geometries:
            # If the part lies in the >180° half, shift back appropriately
            if self.contains_lon_gt_180(part):
                corrected = normalize_lon_to_180(part, is_360_space=True)
            else:
                corrected = normalize_lon_to_180(part, is_360_space=False)

            corrected_parts.append(
                limit_polygon_vertices(
                    corrected, max_points=60, tolerance_start=self.tolerance
                )
            )

        # Build final output
        if len(corrected_parts) == 1:
            return corrected_parts[0]

        return MultiPolygon(corrected_parts)


if __name__ == "__main__":
    geometry: Polygon = Polygon(
        [(170, 60), (-170, 80), (-190, 80), (-190, 60), (170, 60)]
    )
    lantimeridian = AntimeridianSplitter(geometry)
    polygons = lantimeridian.toWgs84()
    print(polygons)
