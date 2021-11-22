from warnings import warn

import geopandas as gpd
import pandas as pd
from rasterio.crs import CRS
from shapely.geometry import shape


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
    df.sort_values(by=['startTime', 'pathNumber'], inplace=True)

    return df


def distill_one_pair(pair: dict) -> dict:
    df_ref = pair['reference']
    df_sec = pair['secondary']
    ref_geo = df_ref.geometry.unary_union
    sec_geo = df_sec.geometry.unary_union
    data = {'reference': df_ref.sceneName.tolist(),
            'secondary': df_sec.sceneName.tolist(),
            'reference_date': str(df_ref.start_date.min().date()),
            'secondary_date': str(df_sec.start_date.min().date()),
            'path_number': int(df_ref.pathNumber.tolist()[0]),
            'geometry': ref_geo.intersection(sec_geo).buffer(1e-5)}
    return data


def distill_all_pairs(pairs: list) -> list:
    data = list(map(distill_one_pair, pairs))
    df = pd.DataFrame(data)
    return gpd.GeoDataFrame(df, geometry=df.geometry, crs=CRS.from_epsg(4326))
