import geopandas as gpd
import numpy as np
from rasterio.crs import CRS
from s1_enumerator.gis import get_intersection_area_km2

from .paths import get_test_data_path


def test_km2_intersection():
    data_dir = get_test_data_path()
    utm_dir = data_dir / 'utm_data'

    left_path = utm_dir / 'left.geojson'
    right_path = utm_dir / 'right.geojson'
    inter_path = utm_dir / 'intersection.geojson'

    paths = [left_path, right_path, inter_path]
    dfs_utm = [gpd.read_file(path) for path in paths]
    crs_4326 = CRS.from_epsg(4326)
    dfs_4326 = [df.to_crs(crs_4326) for df in dfs_utm]

    # The return type of get intersection is a geodataframe
    temp = get_intersection_area_km2(dfs_4326[0],
                                     dfs_4326[1].geometry.unary_union)
    km2_from_4326 = temp.values[0]

    km2_from_utm = dfs_utm[2].geometry.unary_union.area / 1e6
    assert(np.isclose(km2_from_4326, km2_from_utm, 1e-3))
