import datetime

import geopandas as gpd
from geopandas import testing
from s1_enumerator import (distill_all_pairs, enumerate_by_path,
                           enumerate_by_tile)
from shapely.geometry import Point

from .paths import get_test_data_path


def test_enum_path():
    # Over Los Padres National Forest, CA
    point = Point(-120.0048, 34.8923)
    aoi = point.buffer(1)

    num_neighbors = 3
    ifg_pairs_path = enumerate_by_path(aoi,
                                       min_reference_date=datetime.datetime(2021, 1, 1),
                                       min_days_backward=0,
                                       num_neighbors=num_neighbors,
                                       )
    N = len(ifg_pairs_path)
    remainder = N % num_neighbors
    assert(remainder == 0)

    df_pairs = distill_all_pairs(ifg_pairs_path)
    df_pairs = df_pairs.sort_values(by=['path_number', 'reference_date']).reset_index(drop=True)
    df_pairs.drop(columns=['reference', 'secondary'], inplace=True)

    data_path = get_test_data_path()
    df_pairs_data = gpd.read_file(data_path / 'enum_path.geojson')

    testing.assert_geodataframe_equal(df_pairs,
                                      df_pairs_data)


def test_enum_tile():
    # Over Los Padres National Forest, CA
    point = Point(-120.0048, 34.8923)
    aoi = point.buffer(1)

    num_neighbors = 3
    ifg_pairs_tile = enumerate_by_tile(aoi,
                                       min_reference_date=datetime.datetime(2021, 7, 9),
                                       min_days_backward=365,
                                       num_neighbors=num_neighbors,
                                       )
    N = len(ifg_pairs_tile)
    remainder = N % num_neighbors
    assert(remainder == 0)

    df_pairs = distill_all_pairs(ifg_pairs_tile)
    df_pairs = df_pairs.sort_values(by=['path_number', 'reference_date']).reset_index(drop=True)
    df_pairs.drop(columns=['reference', 'secondary'], inplace=True)

    data_path = get_test_data_path()
    df_pairs_data = gpd.read_file(data_path / 'enum_tile.geojson')

    testing.assert_geodataframe_equal(df_pairs,
                                      df_pairs_data)
