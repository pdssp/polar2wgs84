# Polar to WGS84 Converter - Global geometry processing utilities for GeoJSON-safe WGS84 polygons.
# Copyright (C) 2025 - CNES (Jean-Christophe Malapert for PDSSP)
# This file is part of Polar to WGS84 Converter <https://gitlab.cnes.fr/pdssp/common/polar2wgs84>
# SPDX-License-Identifier: Apache-2.0
"""
Global geometry processing utilities for GeoJSON-safe WGS84 polygons.

This module provides a complete, geodesically correct pipeline for
processing global-scale polygon geometries expressed in longitude/
latitude (WGS84). It is specifically designed to handle edge cases
that commonly break GeoJSON validity when geometries span large
distances or interact with global discontinuities.

Core capabilities
-----------------
1. **Geodesic densification**
   Polygon edges are densified along great-circle paths on the sphere
   prior to projection. This preserves geometric fidelity for:
   - Large-area polygons
   - High-latitude regions
   - Near-polar geometries

2. **Projection-aware simplification**
   Geometries are temporarily projected to a Plate Carrée
   (equirectangular) coordinate system to enable robust, topology-
   preserving simplification. The simplified geometry based is then
   re-projected back to WGS84.

3. **GeoJSON validity enforcement**
   The module automatically detects and resolves global geometry
   pathologies, including:
   - **Polar inclusion** (North or South Pole enclosed by a polygon)
   - **Antimeridian crossing** (±180° longitude discontinuity)
   - **Equator crossing** (multi-hemisphere geometries)

   Specialized algorithms are applied depending on the spatial
   classification of each geometry to ensure GeoJSON compliance.

Design principles
-----------------
- **Spherical correctness**: All long edges are treated as geodesics,
  not planar segments.
- **Explicit decision hierarchy**: Polar handling takes precedence
  over antimeridian logic; equator-crossing geometries follow a
  separate processing path.
- **Topology preservation**: Simplification never introduces self-
  intersections or invalid rings.
- **Performance-oriented**: Critical numeric routines are accelerated
  using Numba.
- **Standards-aware**: Output geometries conform to GeoJSON winding
  and continuity rules.
"""
from loguru import logger

from ._version import __author__
from ._version import __author_email__
from ._version import __copyright__
from ._version import __description__
from ._version import __license__
from ._version import __name_soft__
from ._version import __title__
from ._version import __url__
from ._version import __version__
from .config import configure_logging
from .footprint import Footprint

info_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
configure_logging(level="INFO", format=info_format)
logger.info(f"{__name_soft__} V{__version__} imported")

__all__ = ["Footprint"]
