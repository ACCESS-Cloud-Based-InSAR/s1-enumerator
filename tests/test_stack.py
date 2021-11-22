import datetime

import geopandas as gpd
from geopandas import testing
from s1_enumerator import get_tiles_from_s1_pass
from shapely.geometry import Point

from .paths import get_test_data_path


def test_coverage_tiles():
    # Over Los Padres National Forest, CA
    point = Point(-120.0048, 34.8923)
    aoi = point.buffer(1)

    start_date = datetime.datetime(2021, 1, 1)
    df_coverage_tiles = get_tiles_from_s1_pass(aoi,
                                               start_date=start_date)
    df_coverage_tiles.sort_values(by=['start_date'], inplace=True)
    df_coverage_tiles = df_coverage_tiles[['start_date_str', 'geometry']].reset_index(drop=True)

    data_dir = get_test_data_path()
    tile_data_path = data_dir / 'coverage_tiles.geojson'
    df_coverage_tiles_data = gpd.read_file(tile_data_path)

    testing.assert_geodataframe_equal(df_coverage_tiles,
                                      df_coverage_tiles_data)
