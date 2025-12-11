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
from polar2wgs84.projection import check_polygon
from polar2wgs84.projection import GeometryProcessor
from polar2wgs84.projection import GeometryVisualizer
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
        "--crs",
        choices=["PLATE_CARREE", "NORTH_STEREO", "SOUTH_STEREO"],
        default="PLATE_CARREE",
        help="set Level log (default: %(default)s)",
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
        display_mode = "lines"
        options_cli = parse_cli()
        logger.add(sys.stderr, level=options_cli.level)
        src_crs = "EPSG:4326"
        if options_cli.crs == "SOUTH_STEREO":
            src_crs = "EPSG:3031"
        elif options_cli.crs == "NORTH_STEREO":
            src_crs = "EPSG:3575"
        else:
            src_crs = "EPSG:4326"
        poly = ast.literal_eval(options_cli.geometry)
        geometry = Polygon(poly)
        processor = GeometryProcessor(src_crs, "EPSG:4326", geometry)

        # Processing pipeline
        poly_dense = processor.densify_geometry(max_distance=50000)
        poly_reproj = processor.reproject_geometry(poly_dense)
        poly_final = GeometryProcessor.simplify_geometry(poly_reproj, tolerance=1)
        poly_back = processor.reproject_geometry(poly_final, reverse=True)

        # Check all polygons
        print("\n--- Checking initial polygon ---")
        check_polygon(geometry)
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
        sys.exit(0)
    except Exception as error:  # pylint: disable=broad-except
        logger.exception(error)
        sys.exit(1)


if __name__ == "__main__":
    # execute only if run as a script
    run()
