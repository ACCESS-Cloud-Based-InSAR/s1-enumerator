import warnings
from concurrent import futures
from datetime import datetime, timedelta
from typing import List, Union

import asf_search as asf
import geopandas as gpd
import pandas as pd
from rasterio.crs import CRS
from shapely.geometry import Polygon
from tqdm import tqdm

from .constants import S1_EARLIEST_LOOKUP_DATE, S1_REPEAT_CYCLE_DAYS
from .formatter import format_results_for_sent1
from .gis import get_intersection_area_km2


def get_earliest_n_dates_per_path(df: gpd.GeoDataFrame,
                                  n_dates: int) -> gpd.GeoDataFrame:
    cols = ['pathNumber', 'start_date']

    # Sort by path, date
    df_sorted = df.sort_values(by=cols)

    # Get unique dates per path
    df_temp = df_sorted.drop_duplicates(subset=cols)[cols].reset_index(drop=True)

    # Get earliest n dates
    def nsmallest(index, grouped_df):
        df_out = pd.DataFrame()
        df_out['start_date'] = grouped_df['start_date'].nsmallest(n_dates)
        df_out['pathNumber'] = index
        df_out = df_out[['pathNumber', 'start_date']]
        return df_out

    dfs = [nsmallest(index, grouped_df) for index, grouped_df in df_temp.groupby(['pathNumber'])]
    df_path_date = pd.concat(dfs, axis=0).reset_index(drop=True)

    # Filter original dataframe
    df_n_earliest = pd.merge(df,
                             df_path_date,
                             on=cols,
                             how='inner').reset_index(drop=True)
    return df_n_earliest


def collect_coverage_tiles(aoi: Polygon,
                           start_date: datetime,
                           min_dates_per_path: int = 1,
                           path_number: int = None,
                           max_results: int = 1_000,
                           pass_buffer: int = 0) -> gpd.GeoDataFrame:
    # Get Sentinel-1 A and B to pass at least min_dates_per_path
    # Provides a buffer of an additional pass for high/low latitudes
    n_passes = min_dates_per_path * 2 + pass_buffer * 2
    period_in_days = n_passes * S1_REPEAT_CYCLE_DAYS + 1
    last_date = start_date + timedelta(days=period_in_days)

    path_number_input = None
    if path_number is not None:
        path_number_input = [path_number]
    results = asf.geo_search(platform=[asf.PLATFORM.SENTINEL1],
                             intersectsWith=aoi.wkt,
                             start=start_date,
                             end=last_date,
                             maxResults=max_results,
                             beamMode=[asf.BEAMMODE.IW],
                             relativeOrbit=path_number_input,
                             processingLevel=[asf.PRODUCT_TYPE.SLC]
                             )
    df = format_results_for_sent1(results)
    return df


def get_min_dates_per_path(df: pd.DataFrame) -> int:
    df_date_count = df.groupby(['pathNumber']).apply(lambda grp: len(grp['start_date'].unique()))
    df_date_count = df_date_count.reset_index(drop=False)
    df_date_count = df_date_count.rename(columns={0: 'count'})
    min_dates_per_path = df_date_count['count'].min()
    return min_dates_per_path


def get_s1_coverage_tiles(aoi: Polygon,
                          start_date: datetime,
                          n_dates_per_path: int = 1,
                          path_number: int = None,
                          max_results: int = 1_000,
                          pass_buffer_max: int = 5) -> gpd.GeoDataFrame:

    # Get at least n_passes_per_path for each pathNumber
    for k in range(pass_buffer_max + 1):
        df = collect_coverage_tiles(aoi,
                                    start_date,
                                    min_dates_per_path=n_dates_per_path,
                                    max_results=max_results,
                                    path_number=path_number,
                                    pass_buffer=k)
        if (df.empty) or (get_min_dates_per_path(df) < n_dates_per_path):
            warnings.warn('Not enough data; retrying with addtional pass of A/B')
            continue
        df_n_earliest_dates = get_earliest_n_dates_per_path(df,
                                                            n_dates_per_path)
        if not df.empty:
            return df_n_earliest_dates
    raise ValueError('Not enough data; try lowering n_dates_per_path or increasing pass_buffer_max')


def get_s1_stack_by_poly_and_path(geometry: Polygon,
                                  path_num: Union[int, str],
                                  max_results: int = 1_000) -> gpd.GeoDataFrame:
    results = asf.geo_search(platform=[asf.PLATFORM.SENTINEL1],
                             intersectsWith=geometry.wkt,
                             maxResults=max_results,
                             relativeOrbit=[int(path_num)],
                             beamMode=[asf.BEAMMODE.IW],
                             processingLevel=[asf.PRODUCT_TYPE.SLC]
                             )
    df = format_results_for_sent1(results)
    return df


def get_s1_stack_by_dataframe(df: gpd.GeoDataFrame,
                              path_numbers: List[int] = None,
                              ) -> gpd.GeoDataFrame:

    df_input = df.copy()
    if path_numbers is not None:
        df_input = df[df.pathNumber.isin(path_numbers)].reset_index(drop=True)
        if df_input.empty:
            warnings.warn('Path Numbers specified are not in dataframe',
                          UserWarning)

    geometries = df_input.geometry.tolist()
    path_nums = df_input.pathNumber.tolist()

    def get_s1_stack_by_poly_and_path_p(data):
        return get_s1_stack_by_poly_and_path(*data)
    N = len(geometries)
    # We restrict by path to ensure that additional overlapping geometries are
    # excluded
    with futures.ThreadPoolExecutor(max_workers=15) as executor:
        dfs = list(tqdm(executor.map(get_s1_stack_by_poly_and_path_p,
                                     zip(geometries, path_nums)),
                        total=N,
                        desc=f'Downloading stack for {N} tiles'))
    df_stack = pd.concat(dfs, axis=0)
    df_stack.crs = CRS.from_epsg(4326)
    df_stack = df_stack.drop_duplicates(subset='fileID').reset_index(drop=True)
    return df_stack


def filter_stack_by_path(df_stack: gpd.GeoDataFrame,
                         aoi: Polygon,
                         minimum_intersection_km2: float = 500) -> gpd.GeoDataFrame:

    df_stack_path = df_stack.dissolve(by='pathNumber').reset_index(drop=False)
    df_stack_path['intersection_area'] = get_intersection_area_km2(df_stack_path, aoi)

    # Filter original Paths
    min_area_ind = (df_stack_path['intersection_area'] > minimum_intersection_km2)
    df_stack_path_f = df_stack_path[min_area_ind].reset_index()
    paths_with_enough_overlap = df_stack_path_f.pathNumber.tolist()
    return df_stack[df_stack.pathNumber.isin(paths_with_enough_overlap)].reset_index(drop=True)


def get_historical_reference_dates(start_date, backward_period_days) -> list:
    assert(backward_period_days > 0)
    earliest_date = S1_EARLIEST_LOOKUP_DATE

    reference_dates = []
    reference_date_pointer = start_date - timedelta(days=0)
    while reference_date_pointer >= earliest_date:
        reference_dates.append(reference_date_pointer)
        reference_date_pointer -= timedelta(days=backward_period_days)
    return reference_dates
