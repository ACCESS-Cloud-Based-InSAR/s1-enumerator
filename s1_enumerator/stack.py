from concurrent import futures
from datetime import datetime, timedelta
from typing import Union

import asf_search as asf
import geopandas as gpd
import pandas as pd
from rasterio.crs import CRS
from shapely.geometry import Polygon
from tqdm import tqdm

from .constants import S1_EARLIEST_LOOKUP_DATE, S1_REPEAT_CYCLE_DAYS
from .formatter import format_results_for_sent1
from .gis import align_by_utm, get_intersection_area_km2


def get_tiles_from_s1_pass(aoi: Polygon,
                           start_date: datetime,
                           period_in_days: int = None,
                           max_results: int = 1_000) -> gpd.GeoDataFrame:

    period_in_days = period_in_days or 2 * S1_REPEAT_CYCLE_DAYS + 1
    last_date = start_date + timedelta(days=period_in_days)

    results = asf.geo_search(platform=[asf.PLATFORM.SENTINEL1],
                             intersectsWith=aoi.wkt,
                             start=start_date,
                             end=last_date,
                             maxResults=max_results,
                             beamMode=[asf.BEAMMODE.IW],
                             processingLevel=[asf.PRODUCT_TYPE.SLC]
                             )
    df = format_results_for_sent1(results)
    return df


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


def get_s1_stack_by_dataframe(df: gpd.GeoDataFrame
                              ) -> gpd.GeoDataFrame:
    geometries = df.geometry.tolist()
    path_nums = df.pathNumber.tolist()

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


def filter_by_intersection_percent(df: gpd.GeoDataFrame,
                                   geo: Polygon,
                                   min_percent_overlap) -> gpd.GeoDataFrame:

    df_utm, geo_utm = align_by_utm(df, geo)
    intersection_area = df_utm.geometry.intersection(geo_utm).area
    intersection_index = (intersection_area / geo_utm.area > min_percent_overlap)
    df_f = df[intersection_index].reset_index()
    return df_f


def get_all_secondary_dates(start_date, backward_period_days) -> list:
    assert(backward_period_days > 0)
    earliest_date = S1_EARLIEST_LOOKUP_DATE

    secondary_dates = []
    secondary_date_pointer = start_date - timedelta(days=backward_period_days)
    while secondary_date_pointer >= earliest_date:
        secondary_dates.append(secondary_date_pointer)
        secondary_date_pointer -= timedelta(days=backward_period_days)
    return secondary_dates
