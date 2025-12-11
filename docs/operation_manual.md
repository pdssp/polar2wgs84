# Operations manual for Polar2WGS84

## General overview

The Polar2WGS84 tool is designed to reproject geometries between coordinate reference systems (CRS), with a focus on polar projections (North and South Poles) and WGS84 (EPSG:4326). This tool is intended for both command-line users and developers integrating the library into their workflows.
This manual provides:

- Operational procedures for command-line usage.
- Guidelines for developers to integrate the library into their applications.
- Descriptions of error handling, recovery, and visualization.


## Set‐up and initialisation

```shell
$ make prepare-dev
$ source .venv/bin/activate
$ make
```

## Getting started

### Command-Line Usage

To project a geometry from the command line, use the following syntax:

```shell
$ polar2wgs84 --geometry "[(lon1, lat1), (lon2, lat2), ..., (lon1, lat1)]" --crs [PLATE_CARREE|NORTH_STEREO|SOUTH_STEREO] --level [INFO|DEBUG|WARNING|ERROR|CRITICAL|TRACE]
```

Arguments:

|   Argument    |      Description                         | Example                   |
|---------------|------------------------------------------|---------------------------|
| --geometry    | Geometry as a list of (longitude, latitude) tuples. Must be a closed polygon. |--geometry "[(0, 1), (10, 0), (10, 10), (0, 10), (0, 1)]" |
| --crs         | Source CRS: PLATE_CARREE (EPSG:4326), NORTH_STEREO (EPSG:3575), or SOUTH_STEREO (EPSG:3031). | --crs SOUTH_STEREO |
| --level       | Logging level. Default: INFO.            | --level DEBUG             |

### Example

```shell
$ polar2wgs84 --geometry "[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]" --crs SOUTH_STEREO --level DEBUG
```

## Developer Usage

To use the library programmatically, look at the tests





## Mode selection and control

### Command-Line Modes

- PLATE_CARREE: Default mode (EPSG:4326), expressed as degrees
- NORTH_STEREO: North Pole stereographic projection (EPSG:3575), expressed as meters
- SOUTH_STEREO: South Pole stereographic projection (EPSG:3031), expressed as meters

### Developer Modes

Directly specify the source and destination CRS:

```python
processor = GeometryProcessor(src_crs="EPSG:3031", dst_crs="EPSG:4326", geom=polygon)
```

## Normal operations

### Command-Line Workflow

- The script densifies the geometry to ensure sufficient detail.
- It reprojects the geometry to the target CRS (EPSG:4326).
- It simplifies the geometry to reduce complexity.
- It back-projects the geometry to the source CRS for validation.
- It visualizes the original, reprojected, and back-projected geometries.

### Developer Workflow

Use the GeometryProcessor class to:

- Densify the geometry: densify_geometry(max_distance).
- Reproject the geometry: reproject_geometry(geom).
- Simplify the geometry: simplify_geometry(geom, tolerance).
- Check polygon validity: check_polygon(polygon).

## Normal termination

- The command-line script terminates normally after displaying the visualization.
- Developers can handle termination using standard Python practices (e.g., try-except blocks).

## Error conditions

Common error conditions include:

- Invalid Geometry: Non-closed polygons or self-intersecting geometries.
- Unsupported CRS: CRS not in PLATE_CARREE, NORTH_STEREO, or SOUTH_STEREO.
- Projection Errors: Issues during coordinate transformation.

**Error Handling**

The script logs errors using the specified log level.
Developers should use try-except blocks to catch exceptions:

```python
try:
    processor = GeometryProcessor(src_crs="EPSG:3031", dst_crs="EPSG:4326", geom=polygon)
except Exception as error:
    print(f"Error: {error}")
```

## Recovery Procedures

Command-Line: If an error occurs, check the log output for details and correct the input geometry or CRS.
Developers: Use the check_polygon function to validate geometries before processing:

```python
from polar2wgs84.projection import check_polygon
check_polygon(polygon, verbose=True)
```

## Examples for Developers

Refer to the test suite for usage examples:

::: tests.acceptance.manual_test


## Visualization

The command-line script generates a 3-panel visualization:

- Original Geometry: In the source CRS.
- Reprojected Geometry: In EPSG:4326.
- Back-Projected Geometry: Reprojected back to the source CRS for validation.

## Checklist for Problem Determination

| Issue                 |  Solution                                             |
|-----------------------|-------------------------------------------------------|
| Invalid geometry      | Use check_polygon to validate the input.              |
| Unsupported CRS       | Use PLATE_CARREE, NORTH_STEREO, or SOUTH_STEREO.      |
| Projection errors     | Verify the input coordinates and CRS.                 |
| Visualization issues  | Ensure matplotlib and cartopy are installed.          |
