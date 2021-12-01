import datetime

import geopandas as gpd
import pytest
from geopandas import testing
from s1_enumerator import get_s1_coverage_tiles
from s1_enumerator.stack import collect_coverage_tiles

from .paths import get_test_data_path

COLS = ['sceneName',
        'start_date_str',
        'pathNumber',
        'geometry']

data_dir = get_test_data_path()
coverage_data_dir = data_dir / 'coverage_data'
aoi_dir = data_dir / 'aoi'


@pytest.mark.parametrize("aoi_name", ['aleutian', 'turkey', 'haiti', 'los_padres_ca'])
@pytest.mark.parametrize("min_date_per_path", [1, 2])
def test_collect_tiles(aoi_name, min_date_per_path):
    coverage_path = coverage_data_dir / f'{aoi_name}_at_least_{min_date_per_path}.geojson'
    df_coverage_tiles_data = gpd.read_file(coverage_path)

    aoi_path = aoi_dir / f'{aoi_name}.geojson'
    aoi_df = gpd.read_file(aoi_path)
    aoi_geo = aoi_df.geometry.values[0]

    start_date = datetime.datetime(2021, 1, 1)
    df_coverage_tiles = collect_coverage_tiles(aoi_geo,
                                               start_date,
                                               min_date_per_path
                                               )

    testing.assert_geodataframe_equal(df_coverage_tiles[COLS],
                                      df_coverage_tiles_data)


@pytest.mark.parametrize("aoi_name", ['aleutian', 'turkey', 'haiti', 'los_padres_ca'])
@pytest.mark.parametrize("dates_per_path", [1, 2])
def test_get_coverage_tiles(aoi_name, dates_per_path):

    coverage_data_dir = data_dir / 'coverage_data'
    coverage_path_exactly = coverage_data_dir / f'{aoi_name}_exactly_{dates_per_path}.geojson'
    df_tiles_data = gpd.read_file(coverage_path_exactly)

    aoi_path = aoi_dir / f'{aoi_name}.geojson'
    aoi_df = gpd.read_file(aoi_path)
    aoi_geo = aoi_df.geometry.values[0]

    start_date = datetime.datetime(2021, 1, 1)
    df_tiles = get_s1_coverage_tiles(aoi_geo,
                                     start_date,
                                     n_dates_per_path=dates_per_path)

    testing.assert_geodataframe_equal(df_tiles[COLS],
                                      df_tiles_data)


def test_get_coverage_error_current_date():
    aoi_path = aoi_dir / 'aleutian.geojson'
    aoi_df = gpd.read_file(aoi_path)
    aoi_geo = aoi_df.geometry.values[0]

    start_date = datetime.datetime.now()
    with pytest.raises(ValueError):
        get_s1_coverage_tiles(aoi_geo,
                              start_date,
                              n_dates_per_path=2)


def test_get_coverage_error_too_many_dates():
    aoi_path = aoi_dir / 'aleutian.geojson'
    aoi_df = gpd.read_file(aoi_path)
    aoi_geo = aoi_df.geometry.values[0]

    start_date = datetime.datetime.now() - datetime.timedelta(days=31)
    with pytest.raises(ValueError):
        get_s1_coverage_tiles(aoi_geo,
                              start_date,
                              n_dates_per_path=10)
