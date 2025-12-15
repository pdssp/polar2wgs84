from polar2wgs84.angle_operation import normalize_lon_to_180
from polar2wgs84.antimeridian import AntimeridianSplitter
from polar2wgs84.pole import Pole
from polar2wgs84.projection import Stats
from shapely import MultiPolygon
from shapely import Polygon
from shapely.ops import orient
from shapely.ops import transform
from shapely.validation import explain_validity


class Footprint:

    def __init__(self, geometry: Polygon, tolerance=0.01, max_distance=5000):
        self.geometry = orient(normalize_lon_to_180(geometry))
        self.is_north = False
        self.is_south = False
        self.tolerance = tolerance
        self.max_distance = max_distance
        self.stats = self._compute_stats_location()

    def _compute_stats_location(self) -> Stats:
        coords = list(self.geometry.exterior.coords)
        latitudes = [y for _, y in coords]

        positive_lat = sum(1 for lat in latitudes if lat >= 0)
        negative_lat = sum(1 for lat in latitudes if lat < 0)
        high_latitude_pos = sum(1 for lat in latitudes if lat > 70)
        high_latitude_neg = sum(1 for lat in latitudes if lat < -70)

        return Stats(positive_lat, negative_lat, high_latitude_pos, high_latitude_neg)

    def toWgs84(self) -> Polygon | MultiPolygon:
        pole = Pole(
            self.geometry,
            stats=self.stats,
            tolerance=self.tolerance,
            max_distance=self.max_distance,
        )
        self.is_north = pole.is_north
        self.is_south = not self.is_north
        if pole.is_contained:
            geometry_wgs84 = pole.toWgs84()
        else:
            antimeridian = AntimeridianSplitter(
                self.geometry,
                stats=self.stats,
                tolerance=self.tolerance,
                max_distance=self.max_distance,
            )
            geometry_wgs84 = antimeridian.toWgs84()
        return geometry_wgs84


def check_polygon(poly: Polygon | MultiPolygon, verbose=True):
    """
    Check the validity and properties of a Shapely Polygon.

    Args:
        poly (Polygon): Shapely Polygon object.
        verbose (bool): If True, print detailed results.

    Returns:
        dict: Dictionary containing validity, area, and orientation information.
    """
    results = {}
    results["is_valid"] = poly.is_valid
    results["validity_reason"] = None if poly.is_valid else explain_validity(poly)
    results["area"] = poly.area
    results["has_area"] = poly.area > 0
    results["exterior_ccw"] = (
        poly.exterior.is_ccw
        if isinstance(poly, Polygon)
        else [p.exterior.is_ccw for p in list(poly.geoms)]
    )
    results["nb_points"] = (
        len(poly.exterior.coords)
        if isinstance(poly, Polygon)
        else [len(p.exterior.coords) for p in list(poly.geoms)]
    )
    # results["interiors_ccw"] = [i.is_ccw for i in poly.interiors]
    if verbose:
        print("✅ Valid:", results["is_valid"])
        if not results["is_valid"]:
            print("   Reason:", results["validity_reason"])
        print("🌐 Area:", results["area"])
        print("🔹 Non-zero area:", results["has_area"])
        print("🌀 Exterior CCW:", results["exterior_ccw"])
        # print("🌀 Holes CCW:", results["interiors_ccw"])
        print("Nb points:", results["nb_points"])
    return results


if __name__ == "__main__":
    geometry: Polygon = Polygon(
        [
            (170, 60),  # Point de départ
            (179, 60),  # Traverse l'antiméridien
            (-170, 60),  # Après l'antiméridien
            (-160, 70),
            (150, 80),
            (170, 60),
        ]
    )
    footprint = Footprint(geometry)
    polygons = footprint.toWgs84()
    print(polygons)
