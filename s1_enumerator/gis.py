import geopandas as gpd
import numpy as np
from rasterio.crs import CRS
from shapely.geometry import Polygon


def convert_4326_to_utm(lon: float, lat: float) -> int:
    """
    From: https://gis.stackexchange.com/a/269552
    """
    utm_band = str(int((np.floor((lon + 180) / 6) % 60) + 1))
    if len(utm_band) == 1:
        utm_band = '0' + utm_band
    if lat >= 0:
        epsg_code = '326' + utm_band
    else:
        epsg_code = '327' + utm_band
    return int(epsg_code)


def align_by_utm(df: gpd.GeoDataFrame, geo: Polygon) -> tuple:
    """
    Assuming epsg:4326 for inputs. Align with respect to geometry (second input).
    """
    df_geo = gpd.GeoDataFrame(geometry=[geo],
                              crs=CRS.from_epsg(4326))

    # Get centroid and UTM zone of AOI
    centroid_4326 = geo.centroid.coords[0]
    utm_zone = convert_4326_to_utm(*centroid_4326)
    crs_utm = CRS.from_epsg(utm_zone)

    # Convert Stack to UTM Zone
    df_utm = df.to_crs(crs_utm)
    df_geo_utm = df_geo.to_crs(crs_utm)
    geo_utm = df_geo_utm.geometry.unary_union
    return df_utm, geo_utm


def get_intersection_area_km2(df: gpd.GeoDataFrame,
                              geometry: Polygon) -> gpd.GeoDataFrame:
    """
    From epsg:4326 to UTM (based on geometry centroid) and then calculating

    Note: the return type is for assigning intersection area back to df
    """

    df_utm, geo_utm = align_by_utm(df, geometry)
    geo_intersection = df_utm.geometry.intersection(geo_utm)
    km2_area = geo_intersection.area / 1e6
    return km2_area


def filter_by_intersection_km2(df: gpd.GeoDataFrame,
                               geo: Polygon,
                               min_km2_overlap) -> gpd.GeoDataFrame:

    intersection_km2 = get_intersection_area_km2(df, geo)
    intersection_index = intersection_km2 > min_km2_overlap
    df_f = df[intersection_index].reset_index(drop=True)
    return df_f


def filter_by_intersection_percent(df: gpd.GeoDataFrame,
                                   geo: Polygon,
                                   min_percent_overlap,
                                   relative_to='geometry') -> gpd.GeoDataFrame:
    """Intersection area relative to dataframe or geometry"""

    df_utm, geo_utm = align_by_utm(df, geo)

    if relative_to == 'geometry':
        denominator = geo_utm.area
    elif relative_to == 'dataframe':
        denominator = df_utm.geometry.area
    else:
        raise ValueError('Needs to be dataframe or geometry')

    intersection_percent = df_utm.geometry.intersection(geo_utm).area / denominator
    intersection_index = intersection_percent >= min_percent_overlap
    df_f = df[intersection_index].reset_index(drop=True)
    return df_f


def get_aoi_dataframe(aoi: Polygon) -> gpd.GeoDataFrame:
    df_aoi = gpd.GeoDataFrame(geometry=[aoi],
                              crs=CRS.from_epsg(4326))
    return df_aoi
