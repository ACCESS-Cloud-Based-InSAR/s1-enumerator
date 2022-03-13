import hashlib
import json
from warnings import warn

import geopandas as gpd
import pandas as pd
from rasterio.crs import CRS
from shapely.geometry import shape


def get_gunw_hash_id(reference_ids: list, secondary_ids: list) -> str:
    all_ids = json.dumps([' '.join(sorted(reference_ids)),
                          ' '.join(sorted(secondary_ids))
                          ]).encode('utf8')
    hash_id = hashlib.md5(all_ids).hexdigest()
    return hash_id


def format_results_for_sent1(results: list) -> gpd.GeoDataFrame:
    geometry = [shape(r.geojson()['geometry']) for r in results]
    data = [r.properties for r in results]

    df = pd.DataFrame(data)
    df = gpd.GeoDataFrame(df, geometry=geometry, crs=CRS.from_epsg(4326))

    if df.empty:
        warn('Dataframe is empty! Check inputs.')
        return df

    df['startTime'] = pd.to_datetime(df.startTime)
    df['stopTime'] = pd.to_datetime(df.stopTime)
    df['start_date'] = pd.to_datetime(df.startTime.dt.date)
    df['start_date_str'] = df.start_date.dt.date.map(str)
    df['pathNumber'] = df['pathNumber'].astype(int)
    df.drop(columns=['browse'], inplace=True)
    df = df.sort_values(by=['startTime', 'pathNumber']).reset_index(drop=True)

    return df


def distill_one_pair(pair: dict) -> dict:
    df_ref = pair['reference']
    df_sec = pair['secondary']
    ref_geo = df_ref.geometry.unary_union
    sec_geo = df_sec.geometry.unary_union
    reference = df_ref.sceneName.tolist()
    secondary = df_sec.sceneName.tolist()
    data = {'reference': reference,
            'secondary': secondary,
            'hash_id': get_gunw_hash_id(reference, secondary),
            'reference_date': str(df_ref.start_date.min().date()),
            'secondary_date': str(df_sec.start_date.min().date()),
            'path_number': int(df_ref.pathNumber.tolist()[0]),
            'geometry': ref_geo.intersection(sec_geo).buffer(1e-5),
            'startTime': df_sec.startTime.tolist()[0],
            'stopTime': df_sec.stopTime.tolist()[-1],
            'fileID': ''.join(df_ref.fileID.tolist()[0])}
    return data


def distill_all_pairs(pairs: list) -> list:
    data = list(map(distill_one_pair, pairs))
    df = pd.DataFrame(data)
    return gpd.GeoDataFrame(df, geometry=df.geometry, crs=CRS.from_epsg(4326))
