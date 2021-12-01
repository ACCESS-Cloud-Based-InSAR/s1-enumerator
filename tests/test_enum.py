import datetime

import geopandas as gpd
import pytest
from geopandas import testing
from s1_enumerator import distill_all_pairs, enumerate_ifgs

from .paths import get_test_data_path

data_dir = get_test_data_path()
enum_dir = data_dir / 'enum_data'
aoi_dir = data_dir / 'aoi'


@pytest.mark.parametrize("aoi_name", ['aleutian', 'turkey', 'haiti', 'los_paredes_ca'])
@pytest.mark.parametrize("enumeration_type", ['tile', 'path'])
def test_enum_annual(enumeration_type, aoi_name):
    aoi_path = aoi_dir / f'{aoi_name}.geojson'
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
    df_test.drop(columns=['reference', 'secondary'], inplace=True)

    data_filename = f'{aoi_name}_annual_{enumeration_type}.geojson'
    df_from_data = gpd.read_file(enum_dir / data_filename)
    testing.assert_geodataframe_equal(df_test,
                                      df_from_data)


@pytest.mark.parametrize("enumeration_type", ['tile', 'path'])
@pytest.mark.parametrize("aoi_name", ['los_paredes_ca'])
@pytest.mark.parametrize("months", [None, [7, 8]])
def test_enum_annual_parameters(enumeration_type, aoi_name, months):
    aoi_path = aoi_dir / f'{aoi_name}.geojson'
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
    df_test.drop(columns=['reference', 'secondary'], inplace=True)

    fixed_month_str = '' if months is None else 'fixed_months_'

    data_filename = f'{aoi_name}_annual_{enumeration_type}_{fixed_month_str}137.geojson'
    df_from_data = gpd.read_file(enum_dir / data_filename)
    testing.assert_geodataframe_equal(df_test,
                                      df_from_data)


@pytest.mark.parametrize("aoi_name", ['aleutian', 'turkey', 'haiti', 'los_paredes_ca'])
@pytest.mark.parametrize("enumeration_type", ['tile'])
def test_enum_annual_full_catalog(enumeration_type, aoi_name):
    aoi_path = aoi_dir / f'{aoi_name}.geojson'
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
    df_pairs = df_pairs.sort_values(by=['path_number', 'reference_date']).reset_index(drop=True)

    df_pairs['reference_year'] = df_pairs['reference_date'].map(lambda x: int(x[:4]))
    df_pairs['secondary_year'] = df_pairs['secondary_date'].map(lambda x: int(x[:4]))

    # Make sure that all pairs are exactly one year apart i.e. they are sequential
    assert(((df_pairs['reference_year'] - df_pairs['secondary_year']) == 1).all())
