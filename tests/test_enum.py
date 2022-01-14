import datetime

import geopandas as gpd
import pytest
from geopandas import testing
from s1_enumerator import distill_all_pairs, enumerate_ifgs


@pytest.mark.parametrize("aoi_name", ['aleutian', 'turkey', 'haiti', 'los_padres_ca'])
@pytest.mark.parametrize("enumeration_type", ['tile', 'path'])
def test_enum_annual(test_data_dir, enumeration_type, aoi_name):
    aoi_path = test_data_dir / 'aoi' / f'{aoi_name}.geojson'
    aoi_df = gpd.read_file(aoi_path)
    aoi_geo = aoi_df.geometry.values[0]

    ifg_pairs_tiles = enumerate_ifgs(aoi_geo,
                                     min_reference_date=datetime.datetime(2021, 7, 9),
                                     enumeration_type=enumeration_type,
                                     min_days_backward=364,
                                     num_neighbors_ref=3,
                                     num_neighbors_sec=2,
                                     temporal_window_days=60,
                                     min_ref_tile_overlap_perc=.1,
                                     min_tile_aoi_overlap_km2=1e3,
                                     minimum_path_intersection_km2=1e3,
                                     entire_s1_catalog=False
                                     )
    df_pairs = distill_all_pairs(ifg_pairs_tiles)
    df_test = df_pairs.sort_values(by=['path_number', 'reference_date']).reset_index(drop=True)
    df_test.drop(columns=['reference', 'secondary', 'hash_id'], inplace=True)

    data_filename = f'{aoi_name}_annual_{enumeration_type}.geojson'
    df_from_data = gpd.read_file(test_data_dir / 'enum_data' / data_filename)
    testing.assert_geodataframe_equal(df_test, df_from_data)


@pytest.mark.parametrize("enumeration_type", ['tile', 'path'])
@pytest.mark.parametrize("aoi_name", ['los_padres_ca'])
@pytest.mark.parametrize("months", [None, [7, 8]])
def test_enum_annual_parameters(test_data_dir, enumeration_type, aoi_name, months):
    aoi_path = test_data_dir / 'aoi' / f'{aoi_name}.geojson'
    aoi_df = gpd.read_file(aoi_path)
    aoi_geo = aoi_df.geometry.values[0]

    ifg_pairs_tiles = enumerate_ifgs(aoi_geo,
                                     min_reference_date=datetime.datetime(2021, 7, 9),
                                     enumeration_type=enumeration_type,
                                     min_days_backward=364,
                                     num_neighbors_ref=3,
                                     num_neighbors_sec=2,
                                     temporal_window_days=60,
                                     min_ref_tile_overlap_perc=.1,
                                     min_tile_aoi_overlap_km2=1e3,
                                     minimum_path_intersection_km2=1e3,
                                     path_numbers=[137],
                                     months=months,
                                     entire_s1_catalog=False
                                     )
    df_pairs = distill_all_pairs(ifg_pairs_tiles)
    df_test = df_pairs.sort_values(by=['path_number', 'reference_date']).reset_index(drop=True)
    df_test.drop(columns=['reference', 'secondary', 'hash_id'], inplace=True)

    fixed_month_str = '' if months is None else 'fixed_months_'

    data_filename = f'{aoi_name}_annual_{enumeration_type}_{fixed_month_str}137.geojson'
    df_from_data = gpd.read_file(test_data_dir / 'enum_data' / data_filename)
    testing.assert_geodataframe_equal(df_test,
                                      df_from_data)
