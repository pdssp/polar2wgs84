# Polar to WGS84 Converter - Global geometry processing utilities for GeoJSON-safe WGS84 polygons.
# Copyright (C) 2025 - Centre National d'Etudes Spatiales
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""
Rings whose edges cross the antimeridian without being split.

Some footprints, especially near the poles, are described with edges that
cross ±180° along the shortest path, for example the MRO CTX footprint
``J06_046958_0890_XN_89S158W``: in the lon/lat plane, the edge from -148.74°
to 100.63° goes eastward through 0° (249°) instead of westward through 180°
(111°), so the polygon covers the wrong side of the globe. This module
recognizes these rings and rebuilds them in the plane, split at ±180°.

A polygon wider than 180° described in the plane (e.g., a box from -100° to
100°) is therefore reinterpreted as its narrower complement crossing ±180°:
a warning is logged for each rebuilt polygon.

This module is ported from geom180to360 2.0.0 (antimeridian module), where
the input footprints are expected to be already correct: the reconstruction
belongs to the GeoJSON-safety pipeline, i.e. here. It is applied first in
:meth:`polar2wgs84.footprint.Footprint.make_valid_geojson_geometry`.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import shapely
from shapely.geometry import box
from shapely.geometry import GeometryCollection
from shapely.geometry import LinearRing
from shapely.geometry import MultiPolygon
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .logging_config import get_logger

logger = get_logger(__name__)

__all__ = ["crosses_antimeridian", "resolve_antimeridian_rings"]

#: Tolerance for coordinate comparisons (degrees).
EPS = 1e-12

#: Maximum step (degrees of arc and of longitude) when densifying an edge
#: along its great circle.
_STEP = 1.0

_WORLD_180 = box(-180, -90, 180, 90)


def _wrap_dlon(dlon: np.ndarray) -> np.ndarray:
    """Bring longitude differences within ]-180, 180]."""
    return dlon - 360.0 * np.ceil((dlon - 180.0) / 360.0)


def _unwrap_ring(coords) -> np.ndarray:
    """Longitudes laid end-to-end: each difference is taken along the shortest path.

    :param coords: ring coordinates (n, 2).
    :return: array (n, 2) whose longitudes may be outside [-180, 180].
    """
    coords = np.asarray(coords, dtype=float)[:, :2]
    lons = coords[0, 0] + np.concatenate(
        [[0.0], np.cumsum(_wrap_dlon(np.diff(coords[:, 0])))]
    )
    return np.column_stack([lons, coords[:, 1]])


def _polar_winding(coords) -> float:
    """Sum of longitude differences along a ring (0 or ±360)."""
    unwrapped = _unwrap_ring(coords)
    return float(unwrapped[-1, 0] - unwrapped[0, 0])


def _translate(geom: BaseGeometry, dx: float) -> BaseGeometry:
    """Shift all longitudes by ``dx`` degrees."""

    def _transform(coords):
        coords = coords.copy()
        coords[:, 0] += dx
        return coords

    return shapely.transform(geom, _transform, include_z=geom.has_z)


def _get_dimension(geom: BaseGeometry, dim: int) -> list[BaseGeometry]:
    """Extract simple components of dimension ``dim`` from a geometry."""
    if geom.is_empty:
        return []
    if hasattr(geom, "geoms"):
        parts: list[BaseGeometry] = []
        for g in geom.geoms:
            parts.extend(_get_dimension(g, dim))
        return parts
    return [geom] if shapely.get_dimensions(geom) == dim else []


def _drop_collinear(geom: BaseGeometry) -> BaseGeometry:
    """Remove collinear vertices left by the cuts at ±180°."""
    return shapely.simplify(geom, 0)


def _assemble(parts: list[BaseGeometry], multi: bool) -> BaseGeometry:
    """Reconstruct a homogeneous polygonal geometry from simple components."""
    merged = _drop_collinear(unary_union(parts)) if parts else Polygon()
    polys = _get_dimension(merged, 2)
    if len(polys) == 1 and not multi:
        return polys[0]
    return MultiPolygon(polys)


def _fold_180(geom: BaseGeometry) -> BaseGeometry:
    """Fold back into [-180, 180] a geometry whose longitudes exceed it."""
    pieces = [
        _translate(geom, 360.0 * k).intersection(_WORLD_180) for k in range(-2, 3)
    ]
    return unary_union([p for piece in pieces for p in _get_dimension(piece, 2)])


def _crossing_ring(ring: LinearRing) -> bool:
    """``True`` if an edge of the ring crosses ±180° along the shortest path.

    The ring must not go around a pole (sum of longitude differences = 0), nor
    have a vertex at the pole, nor an edge spanning the full width
    (-180° → 180°): these are already described in the lon/lat plane.
    """
    coords = np.asarray(ring.coords)[:, :2]
    if np.any(np.abs(coords[:, 1]) >= 90.0 - EPS):
        return False
    dlon = np.abs(np.diff(coords[:, 0]))
    if not np.any(dlon > 180.0 + EPS) or np.any(dlon >= 360.0 - EPS):
        return False
    return abs(_polar_winding(coords)) <= 1e-6


def _polygons(geom: BaseGeometry) -> list[Polygon]:
    if geom.geom_type == "GeometryCollection":
        return [p for g in geom.geoms for p in _polygons(g)]
    if geom.geom_type == "MultiPolygon":
        return list(geom.geoms)
    if geom.geom_type == "Polygon" and not geom.is_empty:
        return [geom]
    return []


def crosses_antimeridian(geom: BaseGeometry) -> bool:
    """
    Detect if a polygon of ``geom`` has a ring crossing ±180° unsplit.

    Unlike :meth:`polar2wgs84.splitter.AntimeridianSplitter.crosses_antimeridian`,
    which only looks at the longitude difference between consecutive
    vertices, this method also requires that the ring does not go around a
    pole, so that a ring around a pole or a cap already described in the
    plane is not rebuilt.

    Parameters
    ----------
    geom : BaseGeometry
        Geometry with longitudes in [-180, 180].

    Returns
    -------
    bool
        True if a ring has an edge crossing ±180° along the shortest path.
    """
    return any(_crossing_ring(p.exterior) for p in _polygons(geom))


def _to_xyz(lon: float, lat: float) -> np.ndarray:
    lon, lat = np.radians(lon), np.radians(lat)
    return np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


def _densify_great_circles(coords: np.ndarray) -> np.ndarray:
    """Add vertices along the great circle of each edge (step ``_STEP``)."""
    out = []
    for (lon1, lat1), (lon2, lat2) in pairwise(coords):
        a, b = _to_xyz(lon1, lat1), _to_xyz(lon2, lat2)
        arc = np.arccos(np.clip(a @ b, -1.0, 1.0))
        dlon = abs((lon2 - lon1 + 180.0) % 360.0 - 180.0)
        n = max(1, int(np.ceil(max(np.degrees(arc), dlon) / _STEP)))
        out.append((lon1, lat1))
        if arc < EPS:
            continue
        for t in np.arange(1, n) / n:
            x, y, z = (np.sin((1 - t) * arc) * a + np.sin(t * arc) * b) / np.sin(arc)
            out.append((np.degrees(np.arctan2(y, x)), np.degrees(np.arcsin(z))))
    out.append(tuple(coords[-1]))
    return np.array(out)


def _shortest_path_ring(coords) -> Polygon:
    """Ring whose edges follow the shortest path, longitudes laid end-to-end.

    Straight edges in the lon/lat plane are kept when they give a simple ring.
    Otherwise (near a pole, an edge sweeping a wide range of longitudes may
    cross another one), the edges are densified along their great circle.
    """
    coords = np.asarray(coords, dtype=float)[:, :2]
    poly = Polygon(_unwrap_ring(coords))
    if poly.is_valid:
        return poly
    return shapely.make_valid(Polygon(_unwrap_ring(_densify_great_circles(coords))))


def _rebuild(poly: Polygon) -> BaseGeometry:
    """Polygon whose edges follow the shortest path, split at ±180°."""
    result = _fold_180(_shortest_path_ring(poly.exterior.coords))
    holes = [_fold_180(_shortest_path_ring(h.coords)) for h in poly.interiors]
    return result.difference(unary_union(holes)) if holes else result


def resolve_antimeridian_rings(geom: BaseGeometry) -> BaseGeometry:
    """
    Rebuild polygons whose edges cross ±180° without being split.

    A ring is concerned when an edge spans more than 180° of longitude in the
    plane while the ring does not go around a pole: each edge is then taken
    along the shortest path (|difference| < 180°), and the polygon is split at
    ±180° and folded back into [-180, 180]. Holes are treated the same way.
    Other geometries are returned as is.

    Parameters
    ----------
    geom : BaseGeometry
        Geometry with longitudes in [-180, 180].

    Returns
    -------
    BaseGeometry
        Equivalent geometry with no edge crossing ±180°.
    """
    if geom.geom_type == "GeometryCollection":
        return GeometryCollection([resolve_antimeridian_rings(g) for g in geom.geoms])
    if geom.geom_type not in ("Polygon", "MultiPolygon") or geom.is_empty:
        return geom
    polys = _polygons(geom)
    crossing = [_crossing_ring(p.exterior) for p in polys]
    if not any(crossing):
        return geom
    for poly, is_crossing in zip(polys, crossing, strict=True):
        if is_crossing:
            logger.warning(
                "Polygon with an edge spanning more than 180° of longitude: "
                "rebuilt across the antimeridian (shortest path). Bounds: {}",
                poly.bounds,
            )
    parts = [_rebuild(p) if c else p for p, c in zip(polys, crossing, strict=True)]
    merged = [q for part in parts for q in _get_dimension(part, 2)]
    return _assemble(merged, geom.geom_type == "MultiPolygon")
