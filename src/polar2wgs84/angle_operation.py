from shapely.ops import transform


def shift_coords_to_minus_180(coords):
    """
    Reorder coordinates to start at -180 longitude and follow a logical sequence.

    Args:
        coords: List of (longitude, latitude) tuples in CCW order.

    Returns:
        tuple: Reordered coordinates.
    """
    coords_list = list(coords[:-1])  # Exclude the last point (duplicate of the first)
    # Normalize longitudes to the range [-180, 180]
    normalized_coords = []
    for lon, lat in coords_list:
        while lon > 180:
            lon -= 360
        while lon < -180:
            lon += 360
        normalized_coords.append((lon, lat))
    # Find the index of the point closest to -180 longitude
    min_index = min(
        range(len(normalized_coords)),
        key=lambda i: abs(normalized_coords[i][0] + 180),
    )
    # Reorder points to start at the point closest to -180
    reordered_coords = normalized_coords[min_index:] + normalized_coords[:min_index]
    # Sort coordinates by longitude to ensure a logical sequence
    sorted_coords = sorted(reordered_coords, key=lambda coord: coord[0])
    return tuple(sorted_coords)


def normalize_lon_to_360(geom):
    """
    Shift longitude from [-180, 180] to [0, 360].
    """

    def _shift(x, y):
        x_new = x + 360 if x < 0 else x
        return x_new, y

    return transform(_shift, geom)


def normalize_lon_to_180(geom, is_360_space: bool = False):
    """
    Convert a geometry with longitudes in [0, 360] back to [-180, 180].
    """

    def _unshift(x, y):
        if not is_360_space:
            x_new = x - 360 if x > 180 else x
        else:
            x_new = x - 360 if x >= 180 else x
        return x_new, y

    return transform(_unshift, geom)
