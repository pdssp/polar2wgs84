from shapely.geometry import LineString
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon


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
            for p in list(geom.geoms):
                coords += list(p.exterior.coords)
                for interior in p.interiors:
                    coords += list(interior.coords)
        if coords:
            xs = [x for x, y in coords]
            ys = [y for x, y in coords]
            ax.scatter(xs, ys, s=point_size, color=edgecolor, transform=crs)
