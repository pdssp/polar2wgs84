# Polar to WGS84 Converter - polar2wgs84 is a Python tool to seamlessly convert geographic footprints between polar stereographic projections (EPSG:3031/EPSG:3575) and WGS84 (EPSG:4326), handling pole-crossing geometries, densification, and validation for accurate GIS workflows.
# Copyright (C) 2025 - CNES (Jean-Christophe Malapert for PDSSP)
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""Main program."""
import argparse
import ast
import signal
import sys

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from loguru import logger
from polar2wgs84 import __author__
from polar2wgs84 import __copyright__
from polar2wgs84 import __description__
from polar2wgs84 import __version__
from polar2wgs84.densify_geometry import DensifyGeometryGeodesic
from polar2wgs84.footprint import Footprint
from polar2wgs84.projection import compute_centroid
from polar2wgs84.projection import compute_nbpoints
from polar2wgs84.visu import GeometryVisualizer
from shapely.geometry import Polygon

logger.remove()


class SmartFormatter(argparse.HelpFormatter):
    """Smart formatter for argparse - The lines are split for long text"""

    def _split_lines(self, text, width):
        if text.startswith("R|"):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(  # pylint: disable=protected-access
            self, text, width
        )


class SigintHandler:  # pylint: disable=too-few-public-methods
    """Handles the signal"""

    def __init__(self):
        self.SIGINT = False  # pylint: disable=invalid-name

    def signal_handler(self, sig: int, frame):
        """Trap the signal

        Args:
            sig (int): the signal number
            frame: the current stack frame
        """
        # pylint: disable=unused-argument
        logger.error("You pressed Ctrl+C")
        self.SIGINT = True
        sys.exit(2)


def str2bool(string_to_test: str) -> bool:
    """Checks if a given string is a boolean

    Args:
        string_to_test (str): string to test

    Returns:
        bool: True when the string is a boolean otherwise False
    """
    return string_to_test.lower() in ("yes", "true", "True", "t", "1")


def parse_cli() -> argparse.Namespace:
    """Parse command line inputs.

    Returns
    -------
    argparse.Namespace
        Command line options
    """
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=SmartFormatter,
        epilog=__author__ + " - " + __copyright__,
    )

    parser.add_argument(
        "--geometry",
        type=str,
        required=True,
        help="Geometry (ex: [(lon1,lat1), (lon2,lat2),(lon3,lat3),(lon1,lat1)])",
    )

    parser.add_argument(
        "--densify_polygon",
        type=float,
        required=False,
        default=5,
        help="Maximum distance between points in Km (default: %(default)s)",
    )

    parser.add_argument(
        "--radius_planet",
        type=float,
        required=False,
        default=DensifyGeometryGeodesic.R_EARTH_KM,
        help="Radius of the planet in Km (default: %(default)s)",
    )

    parser.add_argument(
        "--simplify_points",
        type=int,
        required=False,
        default=20,
        help="Maximum number of vertices (default: %(default)s)",
    )

    parser.add_argument(
        "--simplify_tolerance_start",
        type=float,
        required=False,
        default=1000,
        help="Initial simplification tolerance in meters (default: %(default)s)",
    )

    parser.add_argument(
        "--simplify_tolerance_max",
        type=float,
        required=False,
        default=50000,
        help="Maximum allowed tolerance in meters (default: %(default)s)",
    )

    parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s " + __version__
    )

    parser.add_argument(
        "--level",
        choices=[
            "INFO",
            "DEBUG",
            "WARNING",
            "ERROR",
            "CRITICAL",
            "TRACE",
        ],
        default="INFO",
        help="set Level log (default: %(default)s)",
    )

    return parser.parse_args()


def run():
    """Main function that instanciates the library."""
    handler = SigintHandler()
    signal.signal(signal.SIGINT, handler.signal_handler)
    try:
        options_cli = parse_cli()
        logger.add(sys.stderr, level=options_cli.level)

        arguments = {}
        if options_cli.densify_polygon:
            arguments["max_step_km"] = options_cli.densify_polygon
        if options_cli.radius_planet:
            arguments["radius_planet"] = options_cli.radius_planet
        if options_cli.simplify_points:
            arguments["max_step_km"] = options_cli.simplify_points
        if options_cli.simplify_tolerance_start:
            arguments["tolerance_start"] = options_cli.simplify_tolerance_start
        if options_cli.simplify_tolerance_max:
            arguments["tolerance_max"] = options_cli.simplify_tolerance_max

        logger.info(f"Running with theses parameters: {arguments}")

        poly = ast.literal_eval(options_cli.geometry)
        geometry = Polygon(poly)

        footprint = Footprint(geometry)
        geometry_valid = footprint.make_valid_geojson_geometry()
        geometry_valid_simplified = footprint.to_wgs84_plate_carre(
            geometry_valid, **arguments
        )
        print(geometry_valid_simplified)
        nb_points = compute_nbpoints(geometry_valid)
        nb_points_geom_simplified = compute_nbpoints(geometry_valid_simplified)

        lon_mean, lat_mean = compute_centroid(geometry_valid)

        proj = ccrs.Orthographic(central_longitude=lon_mean, central_latitude=lat_mean)

        fig = plt.figure(figsize=(21, 7))

        fig.suptitle("", fontsize=16, fontweight="bold")
        ax1 = fig.add_subplot(1, 4, 1, projection=proj)
        GeometryVisualizer.draw_geometry(
            ax1,
            "original",
            geometry,
            ccrs.PlateCarree(),
            mode="points",
            edgecolor="blue",
        )
        ax2 = fig.add_subplot(1, 4, 2, projection=ccrs.PlateCarree())
        GeometryVisualizer.draw_geometry(
            ax2,
            f"Projected ({nb_points}) points",
            geometry_valid,
            ccrs.PlateCarree(),
            mode="lines",
            edgecolor="blue",
        )

        # Original
        ax3 = fig.add_subplot(1, 4, 3, projection=ccrs.PlateCarree())
        GeometryVisualizer.draw_geometry(
            ax3,
            f"Densify & projected ({nb_points_geom_simplified} points)",
            geometry_valid_simplified,
            ccrs.PlateCarree(),
            mode="lines",
            edgecolor="blue",
        )

        ax4 = fig.add_subplot(1, 4, 4, projection=proj)
        GeometryVisualizer.draw_geometry(
            ax4,
            f"Densify & projected ({nb_points_geom_simplified} points)",
            geometry_valid_simplified,
            ccrs.PlateCarree(),
            mode="points",
            edgecolor="blue",
        )

        plt.tight_layout()
        plt.show()
        sys.exit(0)
    except Exception as error:  # pylint: disable=broad-except
        logger.exception(error)
        sys.exit(1)


if __name__ == "__main__":
    # execute only if run as a script
    run()
