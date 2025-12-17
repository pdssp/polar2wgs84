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

## Installing Poetry

To manage the dependencies of Polar to WGS84 Converter, we use
\[Poetry\](<https://python-poetry.org/>). If you don\'t have Poetry
installed, follow these steps:

1.  **Install Poetry**:

    > ``` shell
    > $ curl -LsSf https://astral.sh/uv/install.sh | sh
    > ```

2.  **Verify the installation**:

    > ``` console
    > $ poetry --version
    > ```

Please note that this project has been tested with Poetry version 2.0.1.

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

``` shell
import polar2wgs84
```

If the Docker image has been created, use the Docker image with the
following command line.

``` console
$ docker run -u $(id -u):$(id -g) -v $(pwd):/app --rm --name polar2wgs84 pdssp/polar2wgs84
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
