from pathlib import Path

import pytest


@pytest.fixture
def test_data_dir():
    data_dir = Path(__file__).resolve().parent / 'data'
    return data_dir
