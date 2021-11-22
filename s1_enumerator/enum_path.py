import logging
from datetime import datetime, timedelta
from typing import List

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
from tqdm import tqdm

from .stack import (filter_stack_by_path, get_all_secondary_dates,
                    get_s1_stack_by_dataframe, get_tiles_from_s1_pass)

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


def enumerate_by_path_from_stack(df_stack: gpd.GeoDataFrame,
                                 min_reference_date: datetime,
                                 min_days_backward: int = 0,
                                 num_neighbors: int = 3) -> List[dict]:

    date_1 = min_reference_date
    date_0 = min_reference_date - timedelta(days=min_days_backward)

    paths = df_stack.pathNumber.unique().tolist()
    ifg_pairs = []

    N = len(paths)
    for path_num in tqdm(paths, desc=f'Enumerating {N} paths'):
        df_path = df_stack[df_stack.pathNumber == path_num]

        df_path_0 = df_path[df_path.start_date < date_0].reset_index()
        df_path_1 = df_path[df_path.start_date >= date_1].reset_index()

        dates_0 = pd.to_datetime(df_path_0.start_date.unique()).sort_values(ascending=False)
        dates_1 = pd.to_datetime(df_path_1.start_date.unique()).sort_values()

        if len(dates_0) < (num_neighbors):
            raise ValueError('Too many neighbors for stack')

        neighbors = []
        for k in range(num_neighbors):
            df_0 = df_path_0[df_path_0.start_date == dates_0[k]]
            df_1 = df_path_1[df_path_1.start_date == dates_1[0]].reset_index(drop=True)
            if (not df_0.empty) and (not df_1.empty):
                # Reference is date that is closer to the present date
                neighbors += [{'reference': df_1,
                               'secondary': df_0}]
        ifg_pairs += neighbors

    return ifg_pairs


def enumerate_by_path(aoi: Polygon,
                      min_reference_date: datetime,
                      min_days_backward: int = 0,
                      num_neighbors: int = 3,
                      minimum_intersection_km2=500,
                      entire_s1_catalog: bool = False) -> List[dict]:
    if entire_s1_catalog and min_days_backward < 180:
        raise ValueError('Backward period look up smaller than 180 days is not permissible')

    logging.info('Getting coverage tiles')
    df_coverage_tiles = get_tiles_from_s1_pass(aoi, start_date=min_reference_date)

    logging.info('Getting stack by tiles')
    df_stack = get_s1_stack_by_dataframe(df_coverage_tiles)

    logging.info('Intersecting Stack with AOI')
    df_stack = df_stack[df_stack.geometry.intersects(aoi)].reset_index(drop=True)
    # This considers path intersection, so previous step is necessary.
    df_stack = filter_stack_by_path(df_stack,
                                    aoi,
                                    minimum_intersection_km2=minimum_intersection_km2)

    logging.info('Enumerating stack')
    secondary_dates = [min_reference_date - timedelta(days=min_days_backward)]
    if entire_s1_catalog:
        secondary_dates = get_all_secondary_dates(min_reference_date, min_days_backward)

    N = len(secondary_dates)
    ifg_pairs = []
    for secondary_date in tqdm(secondary_dates,
                               desc=f'{N} period(s) of {min_days_backward} days'):
        secondary_days_between = (min_reference_date - secondary_date).days
        ifg_pairs += enumerate_by_path_from_stack(df_stack,
                                                  min_reference_date,
                                                  min_days_backward=secondary_days_between,
                                                  num_neighbors=num_neighbors)

    return ifg_pairs
