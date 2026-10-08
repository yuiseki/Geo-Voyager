import pytest

from geo_voyager.observation import Observation


def test_observation_rejects_empty_text():
    with pytest.raises(ValueError):
        Observation("")
