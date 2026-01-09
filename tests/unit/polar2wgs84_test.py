import argparse
import sys
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest


# ============================================================================
# Mocks "métiers" simples mais réalistes
# ============================================================================


class MockDensifyGeometryGeodesic:
    R_EARTH_KM = 6371.0


class MockFootprint:
    def __init__(self, geometry):
        self.geometry = geometry

    def make_valid_geojson_geometry(self):
        return self.geometry

    def to_wgs84_plate_carre(self, geometry, **kwargs):
        return geometry


class MockGeometryVisualizer:
    @staticmethod
    def draw_geometry(*args, **kwargs):
        pass


# ============================================================================
# Import du module testé
# ============================================================================

from polar2wgs84 import __main__ as polar2wgs84_main


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def cli_args():
    """Arguments CLI simulés."""
    return argparse.Namespace(
        geometry="[(0, 0), (1, 0), (1, 1), (0, 0)]",
        densify_polygon=10,
        radius_planet=6371,
        simplify_points=30,
        simplify_tolerance_start=2000,
        simplify_tolerance_max=60000,
        level="INFO",
    )


@pytest.fixture
def valid_polygon():
    """Mock minimal d'un Polygon shapely valide."""
    polygon = MagicMock(name="Polygon")
    polygon.wkt = "POLYGON ((0 0, 1 0, 1 1, 0 0))"
    return polygon


@pytest.fixture
def mock_dependencies(cli_args, valid_polygon):
    """
    Mocke toutes les dépendances externes de run()
    AU BON ENDROIT (__main__).
    """
    with (
        patch("polar2wgs84.__main__.parse_cli", return_value=cli_args),
        patch("polar2wgs84.__main__.configure_logging"),
        patch("polar2wgs84.__main__.SigintHandler"),
        patch(
            "polar2wgs84.__main__.ast.literal_eval",
            return_value=[(0, 0), (1, 0), (1, 1), (0, 0)],
        ),
        patch("polar2wgs84.__main__.Polygon", return_value=valid_polygon),
        patch(
            "polar2wgs84.__main__.Footprint", return_value=MockFootprint(valid_polygon)
        ),
        patch("polar2wgs84.__main__.GeometryVisualizer", MockGeometryVisualizer),
        patch("polar2wgs84.__main__.compute_centroid", return_value=(0.0, 0.0)),
        patch("polar2wgs84.__main__.compute_nbpoints", return_value=4),
        patch("polar2wgs84.__main__.plt"),
    ):
        yield


# ============================================================================
# Tests unitaires
# ============================================================================


def test_str2bool():
    """Test de la conversion string -> bool."""
    true_values = ["yes", "true", "True", "t", "1"]
    false_values = ["no", "false", "False", "f", "0"]

    for v in true_values:
        assert polar2wgs84_main.str2bool(v) is True

    for v in false_values:
        assert polar2wgs84_main.str2bool(v) is False


def test_parse_cli_minimal():
    """Test du parsing CLI sans mock."""
    test_args = [
        "polar2wgs84",
        "--geometry",
        "[(0, 0), (1, 0), (1, 1), (0, 0)]",
    ]

    with patch.object(sys, "argv", test_args):
        args = polar2wgs84_main.parse_cli()
        assert args.geometry == "[(0, 0), (1, 0), (1, 1), (0, 0)]"


def test_run_nominal(mock_dependencies):
    """
    Test du chemin nominal :
    - aucune exception
    - sys.exit(0) appelé
    """
    with patch.object(sys, "exit") as mock_exit:
        polar2wgs84_main.run()
        mock_exit.assert_called_once_with(0)
