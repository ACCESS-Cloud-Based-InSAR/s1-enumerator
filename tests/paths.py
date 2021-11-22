from pathlib import Path

TEST_DIR = Path(__file__).parents[0].absolute()


def get_test_data_path():
    return TEST_DIR / 'data'
