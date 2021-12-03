import logging
import warnings
from datetime import datetime, timedelta
from typing import List

import geopandas as gpd
import pandas as pd
from rasterio.crs import CRS
from shapely.geometry import Polygon

from .gis import filter_by_intersection_km2, filter_by_intersection_percent, get_intersection_area_km2
from .stack import (filter_stack_by_path, get_historical_reference_dates,
                    get_s1_coverage_tiles, get_s1_stack_by_dataframe)

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


def enumerate_ifgs_from_stack(df_stack: gpd.GeoDataFrame,
                              aoi: Polygon,
                              min_reference_date: datetime,
                              enumeration_type: str = 'tile',
                              min_days_backward: int = 0,
                              num_neighbors_ref: int = 3,
                              num_neighbors_sec: int = 1,
                              temporal_window_days: int = 60,
                              min_tile_aoi_overlap_km2: float = 1e3,
                              min_ref_tile_overlap_perc: float = .1,
                              minimum_ifg_area_km2: float = 3e4,
                              minimum_path_intersection_km2: float = 1e3) -> List[dict]:

    if enumeration_type not in ['path', 'tile']:
        raise ValueError('enumeration type must be either "path" or "tile"')

    logging.info('Intersecting Stack with AOI')
    # This considers per tile intersection with AOI
    df_stack = df_stack[df_stack.geometry.intersects(aoi)].reset_index(drop=True)

    # This considers full path intersection AOI.
    df_stack = filter_stack_by_path(df_stack,
                                    aoi,
                                    minimum_intersection_km2=minimum_path_intersection_km2)
    if df_stack.empty:
        warnings.warn(('The stack is empty'),
                      UserWarning)
        return []

    max_sec_date = min_reference_date - timedelta(days=min_days_backward)

    paths = df_stack.pathNumber.unique().tolist()
    ifg_pairs = []

    for path_num in paths:
        df_path = df_stack[df_stack.pathNumber == path_num]

        index_date_ref_0 = (df_path.start_date >= min_reference_date)
        index_date_ref_1 = (df_path.start_date <= min_reference_date + timedelta(days=temporal_window_days))
        df_path_ref = df_path[index_date_ref_0 & index_date_ref_1].reset_index()

        if enumeration_type == 'tile':
            df_path_ref = filter_by_intersection_km2(df_path_ref,
                                                     aoi,
                                                     min_tile_aoi_overlap_km2,
                                                     )

        index_date_sec_0 = (df_path.start_date < max_sec_date)
        index_date_sec_1 = (df_path.start_date >= max_sec_date - timedelta(days=temporal_window_days))
        df_path_sec = df_path[index_date_sec_0 & index_date_sec_1].reset_index()

        # Ascending = True means get earliest dates first
        ref_dates = pd.to_datetime(df_path_ref.start_date.unique()).sort_values(ascending=True)

        # Ascending = False means get more recent dates first
        sec_dates = pd.to_datetime(df_path_sec.start_date.unique()).sort_values(ascending=False)

        neighbors = []
        # Won't necessarily have exactly the number of specified neighbors
        sec_dates = sec_dates[:num_neighbors_sec]
        ref_dates = ref_dates[:num_neighbors_ref]

        for ref_date in ref_dates:
            df_ref_temp = df_path_ref[df_path_ref.start_date == ref_date].reset_index(drop=True)

            for sec_date in sec_dates:
                df_sec_temp = df_path_sec[df_path_sec.start_date == sec_date].reset_index(drop=True)

                if enumeration_type == 'path':
                    df_refs = [df_ref_temp]
                    df_secs = [df_sec_temp]

                elif enumeration_type == 'tile':
                    N_tiles = df_ref_temp.shape[0]
                    df_refs = [df_ref_temp.iloc[[i]] for i in range(N_tiles)]

                    def extract_secondary(df_ref):
                        ref_tile_geo = df_ref.geometry.unary_union
                        df_sec = filter_by_intersection_percent(df_sec_temp,
                                                                ref_tile_geo,
                                                                min_ref_tile_overlap_perc,
                                                                relative_to='geometry')
                        return df_sec
                    df_secs = list(map(extract_secondary, df_refs))

                neighbor_pairs = list(zip(df_refs, df_secs))

                def filter_empty(zipped_data):
                    df_ref, df_sec = zipped_data
                    return (not df_ref.empty) and (not df_sec.empty)
                neighbor_pairs = list(filter(filter_empty, neighbor_pairs))

                def filter_by_area(zipped_data):
                    df_ref, df_sec = zipped_data
                    ref_geo = df_ref.geometry.unary_union
                    sec_geo = df_sec.geometry.unary_union
                    df_sec_merged = gpd.GeoDataFrame(geometry=[sec_geo],
                                                     crs=CRS.from_epsg(4326))
                    ifg_area = get_intersection_area_km2(df_sec_merged, ref_geo)
                    assert(ifg_area.shape[0] == 1)
                    return ifg_area.values[0] >= minimum_ifg_area_km2
                neighbor_pairs = list(filter(filter_by_area, neighbor_pairs))

                neighbors += [{'reference': df_ref,
                               'secondary': df_sec} for (df_ref, df_sec) in neighbor_pairs]

        ifg_pairs += neighbors

    return ifg_pairs


def enumerate_ifgs(aoi: Polygon,
                   min_reference_date: datetime,
                   enumeration_type: str = 'tile',
                   min_days_backward: int = 0,
                   num_neighbors_ref: int = 3,
                   num_neighbors_sec: int = 1,
                   temporal_window_days: int = 90,
                   minimum_path_intersection_km2: float = 500,
                   min_ref_tile_overlap_perc: float = .1,
                   min_tile_aoi_overlap_km2: float = 100,
                   minimum_ifg_area_km2: float = 3e4,
                   path_numbers: List[int] = None,
                   months: List[int] = None,
                   entire_s1_catalog: bool = False,
                   ) -> List[dict]:
    """Generates interferograms (IFGs) for Gunws

    Parameters
    ----------
    aoi : Polygon
        Area of interest as a shapely polygon
    min_reference_date : datetime
        Reference dates used will occur on or after this date.
    enumeration_type : str, optional
        Possibly 'tile' or 'path'.
            + 'tile' means reference consists of single tile. All tiles for
            admissible date in path are considered.
            + 'path' means reference are all images along path for single
            date
        By default 'tile'
    min_days_backward : int, optional
        Minimum number of days prior that secondary will be searched, by default
        0. Secondary dates will occur latest at  `minimum_reference_date - min_days_backwards`
    num_neighbors_ref : int, optional
        The number of reference dates within temporal_window after min_reference_date,
        by default 3. Dates are searched in order of closesness to
        `min_reference_date` (earliest first).
    num_neighbors_sec : int, optional
        The number of secondary dates within temporal window, by default 1.
        Dates are searched in order of closeness to `min_reference_date` (most
        recent first)
    temporal_window_days : int, optional
        The window which interferegram neighbors are searched, by default 90.
        For reference dates, this is [`min_reference_date`, `min_reference_date + temporal_window_days`].
        For secondary_dates, this is [`x - temporal_window_days`, `x`), where
        `x = minimum_reference_date - min_days_backwards`
    minimum_path_intersection_km2 : float, optional
        Overlap of path with respect to AOI in km2, by default 500
    min_ref_tile_overlap_perc : float, optional
        Relative overlap of secondary frames over reference frame, by default `.1`.
        Only relevant for `tile` enumeration.
    min_tile_aoi_overlap_km2 : float, optional
        Minimum reference tile overlap of AOI in km2, by default 100. Only
        relevant for `tile` enumeration
    minimum_ifg_area_km2 : float, optional
        The minimum overlap of reference and secondary in km2, by default 3e4.
        Default ensures area is roughly at least one tile.
    path_numbers : List[int], optional
        Only tiles along path_number are considered, by default None and all
        overlapping paths.
    months : List[int], optional
        Months to restrict stack to, by default None and all months are permissible.
    entire_s1_catalog : bool, optional
        Whether to consider all frames, by default False

    Returns
    -------
    List[dict]:
        List of dictionaries as in {'reference': reference_geodataframe, 'secondary': secondary_dataframe}.
        The columns are derived from properties of `asf_search` and slightly formatted to allow for expedient
        analysis.
    """

    if enumeration_type not in ['path', 'tile']:
        raise ValueError('enumeration type must be either path or tile')

    if entire_s1_catalog and temporal_window_days > min_days_backward:
        raise ValueError(f'The temporal window of {temporal_window_days} days '
                         f'exceeds the backward lookup of {min_days_backward} days. '
                         'Interferograms could be repeated. Shorten the window.')

    if entire_s1_catalog and min_days_backward < 180:
        raise ValueError('Backward period look up smaller than 180 days is not permissible')

    logging.info('Getting coverage tiles')
    df_coverage_tiles = get_s1_coverage_tiles(aoi,
                                              # the date is used to get coverage tiles for extracting stack.
                                              # Recent data has reliable coverage.
                                              start_date=datetime(2021, 1, 1))

    logging.info('Getting stack by tiles')
    df_stack = get_s1_stack_by_dataframe(df_coverage_tiles,
                                         path_numbers=path_numbers)

    if months is not None:
        df_stack = df_stack[df_stack.start_date.dt.month.isin(months)].reset_index(drop=True)

    logging.info('Enumerating stack')
    reference_dates = [min_reference_date]
    if entire_s1_catalog:
        reference_dates = get_historical_reference_dates(min_reference_date, min_days_backward)

    ifg_pairs = []
    for reference_date in reference_dates:
        ifg_pairs += enumerate_ifgs_from_stack(df_stack,
                                               aoi,
                                               reference_date,
                                               enumeration_type=enumeration_type,
                                               min_days_backward=min_days_backward,
                                               num_neighbors_ref=num_neighbors_ref,
                                               num_neighbors_sec=num_neighbors_sec,
                                               temporal_window_days=temporal_window_days,
                                               min_tile_aoi_overlap_km2=min_tile_aoi_overlap_km2,
                                               min_ref_tile_overlap_perc=min_ref_tile_overlap_perc,
                                               minimum_path_intersection_km2=minimum_path_intersection_km2,
                                               minimum_ifg_area_km2=minimum_ifg_area_km2)

    return ifg_pairs
