# Polar to WGS84 Converter - Global geometry processing utilities for GeoJSON-safe WGS84 polygons.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""
Utility class to visualize Shapely Polygon and MultiPolygon geometries
using Matplotlib and Cartopy. Supports line and point plotting modes.
"""
from typing import Union

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon


class GeometryVisualizer:
    """
    Utility class for plotting Shapely geometries on Matplotlib axes
    using Cartopy coordinate reference systems.
    """

    @staticmethod
    def draw_geometry(
        ax: plt.Axes,
        title: str,
        geom: Polygon | MultiPolygon,
        crs,
        mode: str = "lines",
        edgecolor: str = "black",
        point_size: int = 15,
        linewidth: float = 2,
    ):
        """
        Draw a Polygon or MultiPolygon on a Matplotlib axis with Cartopy.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The Matplotlib axis to draw on.
        title : str
            Title for the plot.
        geom : Polygon or MultiPolygon
            Geometry to visualize.
        crs : cartopy.crs.CRS
            Coordinate reference system for plotting the geometry.
        mode : str, optional
            Plotting mode: "lines" to draw edges, anything else to draw vertices (default: "lines").
        edgecolor : str, optional
            Color for polygon edges or points (default: "black").
        point_size : int, optional
            Size of points when mode is not "lines" (default: 15).
        linewidth : float, optional
            Width of polygon edges when mode is "lines" (default: 2).

        Raises
        ------
        TypeError
            If `geom` is not a Polygon or MultiPolygon.
        """
        ax.set_title(title)
        ax.set_global()
        ax.coastlines(linewidth=0.5, color="gray")

        # Draw gridlines
        gl1 = ax.gridlines(
            crs=ccrs.PlateCarree(),
            draw_labels=True,
            linewidth=0.5,
            color="gray",
            alpha=0.5,
            linestyle="--",
        )
        gl1.top_labels = False
        gl1.right_labels = False

        if mode == "lines":
            # Draw geometry edges
            ax.add_geometries(
                [geom],
                crs=crs,
                edgecolor=edgecolor,
                facecolor="none",
                linewidth=linewidth,
            )
            return

        # Collect all coordinates for scatter plot mode
        coords = []
        if isinstance(geom, Polygon):
            coords = list(geom.exterior.coords)
            for interior in geom.interiors:
                coords += list(interior.coords)
        elif isinstance(geom, MultiPolygon):
            for p in geom.geoms:
                coords += list(p.exterior.coords)
                for interior in p.interiors:
                    coords += list(interior.coords)
        else:
            raise TypeError(f"Geometry {type(geom)} is not supported")

        # Plot vertices as points
        if coords:
            xs = [x for x, y in coords]
            ys = [y for x, y in coords]
            ax.scatter(xs, ys, s=point_size, color=edgecolor, transform=crs)
