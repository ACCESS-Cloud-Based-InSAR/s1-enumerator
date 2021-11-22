import logging
from datetime import datetime, timedelta
from typing import List

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
from tqdm import tqdm

from .stack import (filter_by_intersection_percent, get_all_secondary_dates,
                    get_s1_stack_by_dataframe, get_tiles_from_s1_pass)

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


def enumerate_by_tile_from_stack(df_stack: gpd.GeoDataFrame,
                                 df_tiles: gpd.GeoDataFrame,
                                 min_reference_date: datetime,
                                 min_days_backward: int = 0,
                                 num_neighbors: int = 3,
                                 min_tile_overlap_percent: float = .1
                                 ) -> List[dict]:

    date_0 = min_reference_date - timedelta(days=min_days_backward)

    ifg_pairs = []
    N_tiles = df_tiles.shape[0]

    assert(df_tiles.start_date.min() > min_reference_date)

    for i in tqdm(range(N_tiles), desc='tiles'):
        df_tile = df_tiles.iloc[[i]]
        path_num = df_tile.pathNumber.tolist()[0]
        tile_geo = df_tile.geometry.unary_union

        df_path = df_stack[df_stack.pathNumber == path_num]

        date_index = (df_path.start_date < date_0)
        df_path_0 = df_path[date_index]
        df_path_0 = filter_by_intersection_percent(df_path_0,
                                                   tile_geo,
                                                   min_tile_overlap_percent)

        dates_0 = pd.to_datetime(df_path_0.start_date.unique()).sort_values(ascending=False)

        if len(dates_0) < (num_neighbors):
            raise ValueError('Not of enough neighbors in stack')

        neighbors = []
        for j in range(num_neighbors):
            df_0 = df_path_0[df_path_0.start_date == dates_0[j]]
            if (not df_0.empty):
                # Reference is closer to present day
                neighbors += [{'reference': df_tile,
                               'secondary': df_0}]
        ifg_pairs += neighbors

    return ifg_pairs


def enumerate_by_tile(aoi: Polygon,
                      min_reference_date: datetime,
                      min_days_backward: int = 0,
                      num_neighbors: int = 3,
                      min_aoi_overlap_percent: float = .8,
                      min_tile_overlap_percent: float = .1,
                      entire_s1_catalog: bool = False) -> List[dict]:
    logging.info('Getting coverage tiles')
    df_coverage_tiles = get_tiles_from_s1_pass(aoi, start_date=min_reference_date)

    logging.info('Getting stack by tiles')
    df_stack = get_s1_stack_by_dataframe(df_coverage_tiles)

    logging.info('Remove tiles with little overlap of AOI')
    df_coverage_tiles = filter_by_intersection_percent(df_coverage_tiles,
                                                       aoi,
                                                       min_aoi_overlap_percent)
    logging.info('Enumerate each tile')
    secondary_dates = [min_reference_date - timedelta(days=min_days_backward)]
    if entire_s1_catalog:
        secondary_dates = get_all_secondary_dates(min_reference_date, min_days_backward)

    N = len(secondary_dates)
    ifg_pairs = []
    for secondary_date in tqdm(secondary_dates,
                               desc=f'{N} period(s) of {min_days_backward} days'):
        secondary_days_between = (min_reference_date - secondary_date).days
        ifg_pairs += enumerate_by_tile_from_stack(df_stack,
                                                  df_coverage_tiles,
                                                  min_reference_date=min_reference_date,
                                                  min_days_backward=secondary_days_between,
                                                  num_neighbors=num_neighbors,
                                                  min_tile_overlap_percent=min_tile_overlap_percent
                                                  )
    return ifg_pairs
