import pytest

from geo_voyager.hypothesis import Hypothesis


def test_hypothesis_rejects_empty_text():
    with pytest.raises(ValueError):
        Hypothesis("")
