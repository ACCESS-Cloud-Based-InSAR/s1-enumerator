import json

from s1_enumerator import duplicate_gunw_found
from s1_enumerator.cmr import extract_secondary_date
from shapely.geometry import shape


def test_secondary_date():
    gunw_id = 'S1-GUNW-D-R-144-tops-20210710_20200703-140051-35745N_33766N-PP-12c6-v2_0_4'
    secondary_date_str = extract_secondary_date(gunw_id)
    assert secondary_date_str == '2020-07-03'


def test_duplicate_entry(test_data_dir):

    duplicate_entry_path = test_data_dir / 'duplicate_entry.json'
    duplicate_entry = json.loads(duplicate_entry_path.read_text())

    # Convert Geojson to Shapely Geometry
    duplicate_entry['geometry'] = shape(duplicate_entry['geometry'])

    gunw_id = duplicate_gunw_found(duplicate_entry)
    assert gunw_id == 'S1-GUNW-D-R-144-tops-20210710_20200703-140051-35745N_33766N-PP-12c6-v2_0_4'
