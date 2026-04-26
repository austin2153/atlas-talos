import pytest
import kratix_sdk as ks
from pathlib import Path

TESTS_DIR = Path(__file__).parent


@pytest.fixture(autouse=True)
def reset_dirs():
    ks.set_input_dir(TESTS_DIR / "input")
    ks.set_output_dir(TESTS_DIR / "output")
    ks.set_metadata_dir(TESTS_DIR / "metadata")
    yield
