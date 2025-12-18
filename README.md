# Polar to WGS84 Converter

[![image](https://img.shields.io/badge/Maintained%3F-yes-green.svg)]()

[![Quality gate](https://sonarqube.cnes.fr/api/project_badges/quality_gate?project=CNES.UL%3Apdssp%3Apolar2wgs84&token=sqb_daa1ae20d805694245113eccad26aa053aba0877)](https://sonarqube.cnes.fr/dashboard?id=CNES.UL%3Apdssp%3Apolar2wgs84)

[![Coverage](https://sonarqube.cnes.fr/api/project_badges/measure?project=CNES.UL%3Apdssp%3Apolar2wgs84&metric=coverage&token=sqb_daa1ae20d805694245113eccad26aa053aba0877)](https://sonarqube.cnes.fr/dashboard?id=CNES.UL%3Apdssp%3Apolar2wgs84)

[![Lines of Code](https://sonarqube.cnes.fr/api/project_badges/measure?project=CNES.UL%3Apdssp%3Apolar2wgs84&metric=ncloc&token=sqb_daa1ae20d805694245113eccad26aa053aba0877)](https://sonarqube.cnes.fr/dashboard?id=CNES.UL%3Apdssp%3Apolar2wgs84)

Global geometry processing utilities for GeoJSON-safe WGS84 polygons.

## Stable release

To install Polar to WGS84 Converter, run this command in your
terminal:

``` console
$ pip install git+https://gitlab.cnes.fr/pdssp/common/polar2wgs84.git
```

This is the preferred method to install Polar to WGS84 Converter,
as it will always install the most recent stable release.

If you don\'t have [pip](https://pip.pypa.io) installed, this [Python
installation
guide](http://docs.python-guide.org/en/latest/starting/installation/)
can guide you through the process.

## Installing UV

To manage the dependencies of Polar to WGS84 Converter, we use
\[UV\](<https://docs.astral.sh/uv/>). If you don\'t have UV
installed, follow these steps:

1.  **Install UV**:

    > ``` shell
    > $ curl -LsSf https://astral.sh/uv/install.sh | sh
    > ```

2.  **Verify the installation**:

    > ``` console
    > $ uv --version
    > ```

Please note that this project has been tested with UV version 0.9.15.

## From sources

The sources for Polar to WGS84 Converter can be downloaded from
the [Gitlab repo]().

You can either clone the public repository:

``` console
$ git clone https://gitlab.cnes.fr/pdssp/common/polar2wgs84.git
```

Or download the
[tarball]():

``` console
$ curl -OJL https://gitlab.cnes.fr/pdssp/common/polar2wgs84/tarball/main
```

Once you have a copy of the source, you can install it with:

``` console
$ make  # install
```

## Development

``` console
$ git clone polar2wgs84.git
$ cd polar2wgs84
$ make prepare-dev
$ source .venv/bin/activate
$ make install-dev
```

To get more information about the preconfigured tasks:

``` console
$ make help
```

## Usage

To use Polar to WGS84 Converter in a project:

``` python
from polar2wgs84 import Footprint
from shapely import Polygon

# Define the vertices of your spherical polygon as a list of (longitude, latitude) tuples.
# Example: A polygon with 4 vertices (e.g., a rectangle near the North Pole).
polygon_vertices = [
    (longitude_1, latitude_1),  # First vertex
    (longitude_2, latitude_2),  # Second vertex
    (longitude_3, latitude_3),  # Third vertex
    (longitude_4, latitude_4),  # Fourth vertex
    (longitude_1, latitude_1),  # Close the polygon by repeating the first vertex
]

# Create a Shapely Polygon from the vertices
polygon = Polygon(polygon_vertices)

# Instantiate the Footprint class with the polygon
footprint = Footprint(polygon)

# Convert the polygon to a valid GeoJSON-compatible geometry.
# This ensures the geometry is either a Polygon or MultiPolygon,
# which are the only types supported by the GeoJSON standard.
valid_geom = footprint.make_valid_geojson_geometry()

# Interpolate the geometry to the Plate Carrée (CAR) projection (EPSG:4326)
# and simplify it to reduce complexity while preserving its shape.
# This is useful for visualization and further processing.
simplified_valid_geom = footprint.to_wgs84_plate_carre(valid_geom)
# Additional arguments can be provided to control polygon densification and geometry simplification.
```

With command line:

``` shell

$ polar2wgs84 -h

```

## Run tests

To run automatic tests

``` console
$make tests
```

To run manual tests

``` console
pytest -m "manual" -s
```

## Documentation

The documentation is automatically deployed on
<https://pdssp.io.cnes.fr/>polar2wgs84 based on main branch

## Container

A container is automatically created on https://gitlab.cnes.fr/pdssp/common/polar2wgs84/container_registry

## Author

👤 **Jean-Christophe Malapert**

## 🤝 Contributing

Contributions, issues and feature requests are welcome!\<br /\>Feel free
to check \[issues page\](https://gitlab.cnes.fr/pdssp/common/polar2wgs84/issues). You can
also take a look at the \[contributing guide\](https://gitlab.cnes.fr/pdssp/common/polar2wgs84/blob/main/CONTRIBUTING.rst)

## 📝 License

This project is \[Apache V2.0\](https://gitlab.cnes.fr/pdssp/common/polar2wgs84/blob/main/LICENSE) licensed.
