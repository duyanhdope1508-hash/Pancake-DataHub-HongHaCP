import argparse
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "load_test.py"
SPEC = importlib.util.spec_from_file_location("load_test_script", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
load_test = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = load_test
SPEC.loader.exec_module(load_test)


def test_load_stages_are_strictly_increasing_and_capped() -> None:
    assert load_test.parse_stages("5,10,20,35,50") == [5, 10, 20, 35, 50]

    with pytest.raises(argparse.ArgumentTypeError):
        load_test.parse_stages("5,5")
    with pytest.raises(argparse.ArgumentTypeError):
        load_test.parse_stages("51")


def test_load_test_requires_safe_base_url() -> None:
    assert (
        load_test.validate_base_url("https://datahub.example.com/", allow_http=False)
        == "https://datahub.example.com"
    )

    with pytest.raises(ValueError):
        load_test.validate_base_url("http://datahub.example.com", allow_http=False)
    with pytest.raises(ValueError):
        load_test.validate_base_url("https://datahub.example.com/api/orders", allow_http=False)


def test_percentile_uses_nearest_rank() -> None:
    values = [0.1, 0.2, 0.3, 0.4, 1.0]

    assert load_test.percentile(values, 50) == 0.3
    assert load_test.percentile(values, 95) == 1.0
