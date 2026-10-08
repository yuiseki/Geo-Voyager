import pytest

from geo_voyager.intent import Intent


def test_intent_rejects_empty_text():
    with pytest.raises(ValueError):
        Intent("")
