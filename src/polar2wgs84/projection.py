# Polar to WGS84 Converter - polar2wgs84 is a Python tool to seamlessly convert geographic footprints between polar stereographic projections (EPSG:3031/EPSG:3575) and WGS84 (EPSG:4326), handling pole-crossing geometries, densification, and validation for accurate GIS workflows.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
import math

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString
from shapely.geometry import MultiPolygon
from shapely.geometry import Point
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.ops import transform
from shapely.validation import explain_validity


# ----------------------------------------------------------
# Class for processing geometries, especially for polar projections
# ----------------------------------------------------------
class GeometryProcessor:
    """
    A class to handle geometry processing, including reprojection, densification, and simplification.
    Supports polar projections (EPSG:3031 for South Pole, EPSG:3575 for North Pole) and WGS84 (EPSG:4326).
    """

    def __init__(self, src_crs: str, dst_crs: str, geom: Polygon):
        """
        Initialize the GeometryProcessor.

        If the user provided WGS84 (EPSG:4326), automatically determine
        whether the geometry is located close enough to a pole to justify
        switching to the corresponding polar stereographic projection.
        This step makes EPSG:4326 act like an "auto" mode for polar work.

        Args:
            src_crs (str): Source Coordinate Reference System (e.g., "EPSG:4326", "EPSG:3031").
            dst_crs (str): Destination Coordinate Reference System.
            geom: Shapely geometry object Polygon
        """
        self.src_crs = src_crs
        self.dst_crs = dst_crs
        if geom.exterior.is_ccw:
            self.geom = geom
        else:
            self.geom = orient(geom)
        # Default pole is set to (0, 0) for transformation purposes
        self.pole = Point(0, 0)
        # Set the physical pole based on the source CRS
        if src_crs == "EPSG:3031":
            self.physical_pole = -90  # South Pole
        elif src_crs == "EPSG:3575":
            self.physical_pole = 90  # North Pole
        elif src_crs == "EPSG:4326":
            # Determine if the geometry is suitable for a polar projection
            pole = GeometryProcessor.is_polar_projection_suitable(geom)
            if pole == "north":
                self.src_crs = "EPSG:3575"
                self.physical_pole = 90
            elif pole == "south":
                self.src_crs = "EPSG:3031"
                self.physical_pole = -90
            else:
                raise Exception("The geometry is not polar.")
            # Reproject the geometry to the appropriate polar CRS
            transformer = Transformer.from_crs(
                "EPSG:4326", self.src_crs, always_xy=True
            )
            coords = [
                transformer.transform(lon, lat) for lon, lat in geom.exterior.coords
            ]
            self.geom = Polygon(coords)
        else:
            raise Exception(f"CRS {src_crs} not supported.")

    @staticmethod
    def is_polar_projection_suitable(polygon, pole_threshold=0):
        """
        Determine if a Polygon geometry is more suitable for a North or South polar projection.

        Args:
            polygon: Shapely Polygon object.
            pole_threshold (float): Latitude threshold (in degrees) to consider a polar projection.

        Returns:
            str: "north", "south", or None if neither is suitable.
        """
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
    def shift_coords_to_minus_180(coords):
        """
        Reorder coordinates to start at -180 longitude and follow a logical sequence.

        Args:
            coords: List of (longitude, latitude) tuples in CCW order.

        Returns:
            tuple: Reordered coordinates.
        """
        coords_list = list(
            coords[:-1]
        )  # Exclude the last point (duplicate of the first)
        # Normalize longitudes to the range [-180, 180]
        normalized_coords = []
        for lon, lat in coords_list:
            while lon > 180:
                lon -= 360
            while lon < -180:
                lon += 360
            normalized_coords.append((lon, lat))
        # Find the index of the point closest to -180 longitude
        min_index = min(
            range(len(normalized_coords)),
            key=lambda i: abs(normalized_coords[i][0] + 180),
        )
        # Reorder points to start at the point closest to -180
        reordered_coords = normalized_coords[min_index:] + normalized_coords[:min_index]
        # Sort coordinates by longitude to ensure a logical sequence
        sorted_coords = sorted(reordered_coords, key=lambda coord: coord[0])
        return tuple(sorted_coords)

    def densify_geometry(self, max_distance: float):
        """
        Densify the geometry by adding intermediate points if the distance between points exceeds max_distance.

        Args:
            max_distance (float): Maximum allowed distance between points.

        Returns:
            Shapely geometry: Densified geometry.
        """
        return GeometryProcessor._densify_geometry(self.geom, max_distance)

    @staticmethod
    def _densify_geometry(geom, max_distance: float):
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
                [GeometryProcessor._densify_geometry(p, max_distance) for p in geom]
            )
        return geom

    def reproject_geometry(self, geom, reverse=False):
        """
        Reproject a geometry from the source CRS to the destination CRS, or vice versa.

        Args:
            geom: Shapely geometry object.
            reverse (bool): If True, reproject from destination CRS to source CRS.

        Returns:
            Shapely geometry: Reprojected geometry.
        """
        if reverse:
            transformer = Transformer.from_crs(
                self.dst_crs, self.src_crs, always_xy=True
            )
        else:
            transformer = Transformer.from_crs(
                self.src_crs, self.dst_crs, always_xy=True
            )

        def transform_coords(coords):
            """
            Transform coordinates using the transformer, handling pole points separately.

            Args:
                coords: List of (x, y) tuples.

            Returns:
                list: Transformed coordinates.
            """
            new_coords = []
            pole_indices = []
            non_pole_lons = []
            for i, (x, y) in enumerate(coords):
                if x == 0 and y == 0:
                    pole_indices.append(i)
                else:
                    lon, lat = transformer.transform(x, y)
                    non_pole_lons.append(lon)
            mean_lon = np.mean(non_pole_lons) if non_pole_lons else 0
            for i, (x, y) in enumerate(coords):
                if i in pole_indices:
                    new_coords.append((mean_lon, self.physical_pole))
                else:
                    lon, lat = transformer.transform(x, y)
                    new_coords.append((lon, lat))
            return new_coords

        if isinstance(geom, LineString):
            return LineString(transform_coords(geom.coords))
        elif isinstance(geom, Polygon):
            if not reverse and geom.contains(self.pole):
                # Handle polar polygons by adding a cap at the pole
                cap_ring = [
                    (lon, self.physical_pole) for lon in np.linspace(180, -180, 100)
                ]
                exterior_coords = transform_coords(geom.exterior.coords)
                coords_reorder = list(
                    self.shift_coords_to_minus_180(tuple(exterior_coords))
                )
                coords_reorder.extend(cap_ring)
                if coords_reorder[0] != coords_reorder[-1]:
                    coords_reorder.append(coords_reorder[0])
                return orient(Polygon(coords_reorder))
            else:
                exterior = transform_coords(geom.exterior.coords)
                return orient(Polygon(exterior))
        elif isinstance(geom, MultiPolygon):
            return MultiPolygon(
                [self.reproject_geometry(p, reverse=reverse) for p in geom]
            )
        return transform(transformer.transform, geom)

    @staticmethod
    def simplify_geometry(geom, tolerance: float = 1.0):
        """
        Simplify a geometry using the Douglas-Peucker algorithm.

        Args:
            geom: Shapely geometry object.
            tolerance (float): Simplification tolerance.

        Returns:
            Shapely geometry: Simplified geometry.
        """
        return geom.simplify(tolerance, preserve_topology=True)


# ----------------------------------------------------------
# Class for visualizing geometries
# ----------------------------------------------------------
class GeometryVisualizer:
    """An utility class to help for plotting a geometry with matplotlib"""

    @staticmethod
    def draw_geometry(
        ax, geom, crs, mode="lines", edgecolor="black", point_size=15, linewidth=2
    ):
        """
        Draw a Shapely geometry on a matplotlib axis.

        Args:
            ax: Matplotlib axis.
            geom: Shapely geometry object.
            crs: Cartopy CRS for the axis.
            mode (str): Drawing mode ("lines" or "points").
            edgecolor (str): Color for edges/points.
            point_size (int): Size of points.
            linewidth (int): Width of lines.
        """
        if mode == "lines":
            ax.add_geometries(
                [geom],
                crs=crs,
                edgecolor=edgecolor,
                facecolor="none",
                linewidth=linewidth,
            )
            return
        coords = []
        if isinstance(geom, LineString):
            coords = list(geom.coords)
        elif isinstance(geom, Polygon):
            coords = list(geom.exterior.coords)
            for interior in geom.interiors:
                coords += list(interior.coords)
        elif isinstance(geom, MultiPolygon):
            for p in geom:
                coords += list(p.exterior.coords)
                for interior in p.interiors:
                    coords += list(interior.coords)
        if coords:
            xs = [x for x, y in coords]
            ys = [y for x, y in coords]
            ax.scatter(xs, ys, s=point_size, color=edgecolor, transform=crs)


# ----------------------------------------------------------
# Function to check polygon validity and properties
# ----------------------------------------------------------
def check_polygon(poly: Polygon, verbose=True):
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
    results["exterior_ccw"] = poly.exterior.is_ccw
    results["interiors_ccw"] = [i.is_ccw for i in poly.interiors]
    if verbose:
        print("✅ Valid:", results["is_valid"])
        if not results["is_valid"]:
            print("   Reason:", results["validity_reason"])
        print("🌐 Area:", results["area"])
        print("🔹 Non-zero area:", results["has_area"])
        print("🌀 Exterior CCW:", results["exterior_ccw"])
        print("🌀 Holes CCW:", results["interiors_ccw"])
    return results


# ----------------------------------------------------------
# Complete example
# ----------------------------------------------------------
if __name__ == "__main__":
    display_mode = "lines"
    # Example polygon (uncomment to use)
    # poly = Polygon([
    #     (-3000000, 0),
    #     (-2000000, 500000),
    #     (-1000000, 500000),
    #     (0, 0),  # Pole on the line
    #     (-3000000, 0)
    # ])

    # poly = Polygon([
    #     (3000000, 0),        # 0°
    #     (2121320, 2121320), # 30°
    #     (0, 3000000),        # 90°
    #     (-2121320, 2121320), # 150°
    #     (-3000000, 0),       # 180°
    #     (-2121320, -2121320),# 210°
    #     (0, -3000000),       # 270°
    #     (2121320, -2121320), # 330°
    #     (3000000, 0)
    # ])

    poly = Polygon([(-180, -50), (-90, -50), (0, -50), (90, -50), (-180, -50)])
    print(poly)

    # poly = Polygon([
    #     (0, 80),
    #     (30, 80),
    #     (60, 80),
    #     (30, 85),
    #     (0, 80)
    # ])

    # poly = Polygon([
    #     (0, -80),
    #     (30, -85),
    #     (60, -80),
    #     (90, -75),
    #     (110, -80),
    #     (-110, -80),
    #     (-90, -75),
    #     (-45, -80),
    #     (-20, -75),
    #     (0, -80)
    # ])

    src_crs = "EPSG:4326"  # "EPSG:3031" # "EPSG:4326"  # "EPSG:3575" or "EPSG:3031"
    dst_crs = "EPSG:4326"
    processor = GeometryProcessor(src_crs, dst_crs, poly)

    # Processing pipeline
    poly_dense = processor.densify_geometry(max_distance=50000)
    poly_reproj = processor.reproject_geometry(poly_dense)
    poly_final = GeometryProcessor.simplify_geometry(poly_reproj, tolerance=1)
    poly_back = processor.reproject_geometry(poly_final, reverse=True)

    # Check all polygons
    print("\n--- Checking initial polygon ---")
    check_polygon(poly)
    print("\n--- Checking reprojected polygon ---")
    check_polygon(poly_final)
    print("\n--- Checking back-projected polar polygon ---")
    check_polygon(poly_back)

    # Visualization
    source_crs_cartopy = ccrs.SouthPolarStereo()
    target_crs_cartopy = ccrs.PlateCarree()
    fig = plt.figure(figsize=(21, 7))

    ax1 = fig.add_subplot(1, 3, 1, projection=source_crs_cartopy)
    ax1.set_title(f"Original ({processor.src_crs})")
    ax1.set_extent([-3000000, 3000000, -3000000, 3000000], crs=source_crs_cartopy)
    gl1 = ax1.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        linewidth=0.5,
        color="gray",
        alpha=0.5,
        linestyle="--",
    )
    gl1.top_labels = False
    gl1.right_labels = False
    GeometryVisualizer.draw_geometry(
        ax1, processor.geom, source_crs_cartopy, mode=display_mode, edgecolor="blue"
    )

    ax2 = fig.add_subplot(1, 3, 2, projection=target_crs_cartopy)
    ax2.set_title("Reprojected (EPSG:4326)")
    ax2.set_extent([-180, 180, -90, 90], crs=target_crs_cartopy)
    gl2 = ax2.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        linewidth=0.5,
        color="gray",
        alpha=0.5,
        linestyle="--",
    )
    gl2.top_labels = True
    gl2.right_labels = True
    GeometryVisualizer.draw_geometry(
        ax2, poly_final, target_crs_cartopy, mode=display_mode, edgecolor="red"
    )

    ax3 = fig.add_subplot(1, 3, 3, projection=source_crs_cartopy)
    ax3.set_title("Back to polar")
    ax3.set_extent([-3000000, 3000000, -3000000, 3000000], crs=source_crs_cartopy)
    gl3 = ax3.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        linewidth=0.5,
        color="gray",
        alpha=0.5,
        linestyle="--",
    )
    gl3.top_labels = False
    gl3.right_labels = False
    GeometryVisualizer.draw_geometry(
        ax3, poly_back, source_crs_cartopy, mode=display_mode, edgecolor="green"
    )

    plt.tight_layout()
    plt.show()
