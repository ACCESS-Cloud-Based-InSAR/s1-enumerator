import warnings

import asf_search as asf
import geopandas as gpd

from .formatter import format_results_for_sent1


def extract_secondary_date(gunw_scene_name: str) -> str:
    """Get Secondary Date from GUNW id"""
    date_pair_str = gunw_scene_name.split('-')[6]
    temp = date_pair_str.split('_')[1]
    secondary_date_str = f'{temp[:4]}-{temp[4:6]}-{temp[6:]}'
    return secondary_date_str


def approximate_cmr_lookup(reference_date: str,
                           secondary_date: str,
                           path_number: int,
                           geometry) -> gpd.GeoDataFrame:
    """
    Looks up by reference/secondary_date and computes intersection overlap
    """

    results = asf.geo_search(intersectsWith=geometry.wkt,
                             maxResults=100,
                             start=reference_date,
                             relativeOrbit=[path_number],
                             processingLevel=[asf.PRODUCT_TYPE.GUNW_STD]
                             )
    df = format_results_for_sent1(results)

    df['secondary_date_str'] = df.sceneName.map(extract_secondary_date)

    # Calculating areas in lat/lon coordinates prompts shapely warning
    warnings.filterwarnings("ignore", category=UserWarning)
    df['percent_intersection'] = df.geometry.intersection(geometry).area / geometry.area

    i0 = (df.start_date_str == reference_date)
    i1 = (df.secondary_date_str == secondary_date)
    df_filtered = df[i0 & i1].reset_index(drop=True)
    df_filtered = df_filtered.sort_values(by='percent_intersection', ascending=False).reset_index(drop=True)
    return df_filtered


def duplicate_gunw_found(gunw_input_data: dict,
                         min_percent_intersection: float = .99) -> str:
    """
    Looks up formatted GUNW metadata and returns either:
        - empty string if no existing item in CMR
        - GUNW id if same reference/secondary dates with specified overlap GUNW found
    """
    df = approximate_cmr_lookup(gunw_input_data['reference_date'],
                                gunw_input_data['secondary_date'],
                                gunw_input_data['path_number'],
                                gunw_input_data['geometry'])
    if df.empty:
        return ''

    # Dataframe is sorted by percent intersection with greatest first
    if df.loc[0, 'percent_intersection'] > min_percent_intersection:
        return df.loc[0, 'sceneName']

    return ''
